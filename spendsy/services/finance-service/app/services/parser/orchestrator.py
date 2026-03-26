import io
import re
import logging
import json
import hashlib
from datetime import datetime
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
from .detector import detect_pdf_type
from .prompts import get_prompts_for_type
from .normalizer import normalize_document, asdict

logger = logging.getLogger("finance.parser.orchestrator")

# Initialize Gemini Client
client = None
if settings.google_api_key:
    client = genai.Client(api_key=settings.google_api_key)

def extract_text_for_type(content: bytes, pdf_type: str) -> str:
    """
    Extracts text from PDF optimized for the detected type.
    """
    if pdf_type == "ocr_scanned":
        logger.info("Extracting text via OCR (Tesseract)...")
        images = convert_from_bytes(content, dpi=200)
        full_text = []
        for i, img in enumerate(images):
            # Sample only first 5 pages for speed and token limits if it's very long
            if i >= 5: break
            text = pytesseract.image_to_string(img)
            full_text.append(f"--- PAGE {i+1} ---\n{text}")
        return "\n".join(full_text)
    
    elif pdf_type == "structured_ledger":
        logger.info("Extracting text/tables via pdfplumber...")
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            full_text = []
            for i, page in enumerate(pdf.pages):
                if i >= 10: break # Safety limit
                text = page.extract_text() or ""
                # We could also use extract_tables here, but LLMs often work better with 
                # the raw text if it preserves alignment, which pdfplumber usually does.
                full_text.append(f"--- PAGE {i+1} ---\n{text}")
            return "\n".join(full_text)
            
    else: # unstructured_text
        logger.info("Extracting plain text via pdfplumber...")
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages[:10]])

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception)
)
def call_llm(system_prompt: str, user_prompt: str):
    if not client:
        raise RuntimeError("Gemini API key not configured")
    
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.1
        ),
        contents=user_prompt
    )
    
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {response.text}")
        # Try to strip markdown fences if present
        clean_text = re.sub(r"```json\s*|\s*```", "", response.text).strip()
        return json.loads(clean_text)

def process_pdf(content: bytes) -> dict:
    """
    Main orchestrator for the 4-step parsing pipeline.
    """
    # Step 1: Detect PDF Type
    pdf_type = detect_pdf_type(content)
    
    # Step 2: Get Prompts
    prompts = get_prompts_for_type(pdf_type)
    
    # Step 3: Extract Text
    extracted_text = extract_text_for_type(content, pdf_type)
    
    # Step 4: Call LLM
    # Fill the template (inject text into the appropriate field)
    if pdf_type == "ocr_scanned":
        user_prompt = prompts["user_template"].format(ocr_text=extracted_text)
    elif pdf_type == "structured_ledger":
        user_prompt = prompts["user_template"].format(table_text=extracted_text)
    else:
        user_prompt = prompts["user_template"].format(document_text=extracted_text)
        
    try:
        raw_json = call_llm(prompts["system"], user_prompt)
    except Exception as e:
        logger.error(f"LLM extraction failed after retries: {e}")
        return {
            "status": "error",
            "error": f"AI extraction failed: {str(e)}",
            "transactions": []
        }
    
    # Step 5: Normalize Document
    normalized_doc = normalize_document(raw_json, pdf_type)
    
    # Determine if review is required
    requires_review = (
        normalized_doc.extraction_confidence == "low" or 
        len(normalized_doc.transactions) == 0
    )
    
    # Convert to dict for response
    result = asdict(normalized_doc)
    result["status"] = "success"
    result["requires_review"] = requires_review
    
    return result

async def process_pdf_async(content: bytes):
    """
    Async wrapper for the orchestrator (can be run in threadpool if needed).
    """
    import asyncio
    loop = asyncio.get_running_loop()
    # Using run_in_executor to avoid blocking the event loop with OCR/LLM
    return await loop.run_in_executor(None, process_pdf, content)
