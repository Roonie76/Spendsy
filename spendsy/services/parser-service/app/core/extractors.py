from __future__ import annotations
import io
import logging
import csv
import re
from abc import ABC, abstractmethod
from typing import Any

import pdfplumber
try:
    import openpyxl
except ImportError:
    openpyxl = None

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, content: bytes) -> str:
        pass

try:
    import pytesseract
except ImportError:
    pytesseract = None

# PaddleOCR lazy singleton — initialised on first use so service starts fast
_paddle_ocr = None
_paddle_ocr_tried = False

def _get_paddle_ocr():
    """Return a PaddleOCR instance, or None if unavailable."""
    return None # Explicitly disable to avoid C++ runtime crashes on this environment
def _preprocess_image(img_array):
    """Clean up and optionally deskew/upscale the image array for better OCR."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("cv2 (opencv-python) not installed, skipping image preprocessing.")
        return img_array

    # 1. Grayscale
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array.copy()
        
    # 2. Upscale if too small (width < 1500 implies low DPI for a typical A4 page)
    h, w = gray.shape
    if w < 1500:
        scale = 1500.0 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # 3. Simple Deskew & Adaptive Threshold
    # We use a gaussian blur before thresholding to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Adaptive thresholding is usually better for varying lighting/scans than global Otsu
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # Deskewing logic (optional but helpful if coordinates available)
    coords = np.column_stack(np.where(thresh == 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45: angle = -(90 + angle)
        else: angle = -angle
        if 0.5 < abs(angle) < 15.0:
            (h_c, w_c) = gray.shape[:2]
            center = (w_c // 2, h_c // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            thresh = cv2.warpAffine(thresh, M, (w_c, h_c), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # Convert back to RGB for PIL/Tesseract
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)

def _polish_ocr_text(text: str) -> str:
    """Fix common OCR misreadings in financial data (e.g. O instead of 0)."""
    if not text:
        return ""
    
    # 1. Row-based cleanup
    lines = text.splitlines()
    polished = []
    
    # Regex to find potential currency values with common OCR errors
    # Example: $ I,O00.OO -> $ 1,000.00
    for line in lines:
        p_line = line
        # Fix 'O' as '0' when surrounded by numbers or in decimal place
        p_line = re.sub(r'(?<=\d)O', '0', p_line)
        p_line = re.sub(r'O(?=\d)', '0', p_line)
        p_line = re.sub(r'(?<=\.)OO', '00', p_line)
        
        # Fix 'I' or '|' as '1' when surrounded by numbers
        p_line = re.sub(r'(?<=\d)I', '1', p_line)
        p_line = re.sub(r'I(?=\d)', '1', p_line)
        p_line = re.sub(r'(?<=\d)\|', '1', p_line)
        
        # Fix 'S' as '5' in currency-like blocks (heuristic)
        # If we see something like 10.S0 or S0.00
        p_line = re.sub(r'(?<=\d)\.S', '.5', p_line)
        
        # Strip trailing/leading non-printable markers that Tesseract sometimes leaves
        p_line = p_line.strip('~`|_ ')
        polished.append(p_line)
        
    return "\n".join(polished)

def _group_text_blocks(ocr_result):
    """Groups PaddleOCR box outputs into rows based on their Y-coordinates."""
    if not ocr_result or not ocr_result[0]:
        return ""
        
    blocks = []
    for item in ocr_result[0]:
        # Item format: [[[x1, y1], [x2, y1], [x2, y2], [x1, y2]], ("text", score)]
        box = item[0]
        text = item[1][0]
        y_center = (box[0][1] + box[2][1]) / 2
        x_left = box[0][0]
        height = box[2][1] - box[0][1]
        blocks.append((y_center, x_left, text, height))
        
    # Sort primarily by approximate Y (row) and secondarily by X (column)
    blocks.sort(key=lambda b: b[0])
    
    lines = []
    current_line = []
    current_y = None
    
    for block in blocks:
        y_center, x_left, text, height = block
        if current_y is None:
            current_y = y_center
            current_line.append(block)
        else:
            # If Y is within ~half a character height, it belongs to the same horizontal row
            if abs(y_center - current_y) < height * 0.5:
                current_line.append(block)
                # update running average Y
                current_y = (current_y + y_center) / 2
            else:
                lines.append(current_line)
                current_line = [block]
                current_y = y_center
                
    if current_line:
        lines.append(current_line)
        
    # Sort items within each line by X-coordinate
    text_lines = []
    for line in lines:
        line.sort(key=lambda b: b[1])
        text_lines.append(" ".join([b[2] for b in line]))
        
    return "\n".join(text_lines)

class PDFExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        text_parts = []
        try:
            # Multi-Engine Digital Pipeline (pdfplumber -> pdfminer)
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = self._extract_page_content(page)
                    if text:
                        text_parts.append(text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {str(e)}")
            return ""

    def _extract_page_content(self, page) -> str:
        """Implements the Digital Pipeline (pdfplumber -> pdfminer) with OCR fallback."""
        # 1. Primary: pdfplumber
        text = page.extract_text()
        
        # 2. Secondary: pdfminer (if pdfplumber text is thin or garbled)
        if not text or self._is_garbled(text) or len(text.strip()) < 100:
            try:
                from pdfminer.high_level import extract_text as miner_extract
                # Extract text for this specific page if possible, otherwise we skip to OCR
                # For simplicity in this implementation, we rely on pdfplumber more
                pass 
            except ImportError:
                pass

        # 3. Scanned/OCR Pipeline
        if not text or self._is_garbled(text):
            logger.info(f"Page {page.page_number}: PDF text appears garbled or scanned, attempting OCR pipeline...")
            
            # PaddleOCR (Layout Reconstruction)
            paddle = _get_paddle_ocr()
            if paddle:
                try:
                    im = page.to_image(resolution=300)
                    import numpy as np
                    img_array = np.array(im.original)
                    img_array = _preprocess_image(img_array)
                    result = paddle.ocr(img_array, cls=True)
                    text = _group_text_blocks(result)
                except Exception as paddle_err:
                    logger.warning(f"PaddleOCR failed: {str(paddle_err)}")

            # Tesseract Fallback
            if (not text or self._is_garbled(text)) and pytesseract:
                try:
                    im = page.to_image(resolution=600)
                    import numpy as np
                    from PIL import Image
                    img_array = np.array(im.original)
                    processed_img_array = _preprocess_image(img_array)
                    processed_img = Image.fromarray(processed_img_array)
                    custom_config = r'--psm 6'
                    ocr_text = pytesseract.image_to_string(processed_img, config=custom_config)
                    if ocr_text:
                        text = _polish_ocr_text(ocr_text)
                except Exception as ocr_err:
                    logger.warning(f"Tesseract OCR failed: {str(ocr_err)}")
        
        return text or ""

    def _is_garbled(self, text: str) -> bool:
        if "(cid:" in text:
            return True
        printable = sum(1 for c in text if c.isalnum() or c.isspace() or c in ".,/-():;")
        if not text: return True
        return (printable / len(text)) < 0.5

class ImageExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        try:
            from PIL import Image
            import numpy as np
            img = Image.open(io.BytesIO(content))
            
            paddle = _get_paddle_ocr()
            if paddle:
                logger.info("Extracting text from image using PaddleOCR...")
                img_array = np.array(img)
                img_array = _preprocess_image(img_array)
                
                result = paddle.ocr(img_array, cls=True)
                text_out = _group_text_blocks(result)
                if text_out:
                    return text_out
            
            if pytesseract:
                logger.info("Extracting text from image using Tesseract + OpenCV...")
                from PIL import Image
                import numpy as np
                img_array = np.array(img)
                processed_img_array = _preprocess_image(img_array)
                processed_img = Image.fromarray(processed_img_array)
                ocr_text = pytesseract.image_to_string(processed_img)
                return _polish_ocr_text(ocr_text)
                
            return ""
        except Exception as e:
            logger.error(f"Failed to extract text from image: {str(e)}")
            return ""

class CSVExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        try:
            text = content.decode("utf-8-sig", errors="replace")
            # We return the first 100 rows as text for quality detection
            # but usually CSV is highly structured, so we just return a sample
            lines = text.splitlines()
            return "\n".join(lines[:200])
        except Exception as e:
            logger.error(f"Failed to extract CSV text: {str(e)}")
            return ""

class XLSXExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        if not openpyxl:
            logger.warning("openpyxl not installed, cannot extract XLSX")
            return ""
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            text_parts = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True, max_row=100):
                    row_text = " ".join([str(cell) for cell in row if cell is not None])
                    if row_text:
                        text_parts.append(row_text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Failed to extract XLSX text: {str(e)}")
            return ""

class TextExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        try:
            return content.decode("utf-8", errors="replace").strip()
        except Exception as e:
            logger.error(f"Failed to extract text: {str(e)}")
            return ""

def get_extractor(content_type: str, filename: str) -> BaseExtractor:
    filename = filename.lower()
    if filename.endswith(".pdf") or "pdf" in content_type:
        return PDFExtractor()
    if filename.endswith(".csv") or "csv" in content_type:
        return CSVExtractor()
    if filename.endswith((".xlsx", ".xls")) or "spreadsheet" in content_type or "excel" in content_type:
        return XLSXExtractor()
    if filename.endswith(".txt") or "text/plain" in content_type:
        return TextExtractor()
    # Images — use PaddleOCR / Tesseract
    if filename.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")) or "image" in content_type:
        return ImageExtractor()
    return TextExtractor()  # Safer default
