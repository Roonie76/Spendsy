import json
import logging
import os
import urllib.request
import urllib.error
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

def call_gemini(prompt: str, context: Dict[str, Any]) -> str:
    """
    Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-latest.
    """
    api_key = settings.google_api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Gemini 1.5 prefers a clear instruction to return JSON
    effective_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No markdown backticks, no preamble."
    
    payload = {
        "contents": [{"parts": [{"text": effective_prompt}]}],
        "generationConfig": {
            "temperature": 0.2
        }
    }
    
    # Use urllib for zero-dependency standalone support if needed, 
    # but TORA typically runs with dependencies.
    # We'll stick to a robust implementation.
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers=headers, 
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30.0) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Gemini API Error ({e.code}): {error_body}")
        raise RuntimeError(f"Gemini API Error ({e.code}): {error_body}")
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise RuntimeError(f"Request failed: {str(e)}")
