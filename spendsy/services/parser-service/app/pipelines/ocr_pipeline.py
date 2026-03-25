"""
OCRPipeline — handles scanned PDFs and image files.

Pipeline:
  pdf2image (poppler) → PIL images per page
  → ImagePreprocessor (OpenCV: deskew, denoise, binarize)
  → PaddleOCREngine (PP-OCRv4)
  → LayoutReconstructor (bbox clustering → table rows)
"""
from __future__ import annotations

import io
import logging
import os
import shutil
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    _NUMPY_AVAILABLE = False

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore
    _CV2_AVAILABLE = False

try:
    from pdf2image import convert_from_bytes
    _PDF2IMAGE_AVAILABLE = True
except ImportError:
    convert_from_bytes = None  # type: ignore
    _PDF2IMAGE_AVAILABLE = False

_POPPLER_AVAILABLE = shutil.which("pdftoppm") is not None

try:
    from paddleocr import PaddleOCR
    _PADDLE_AVAILABLE = True
except Exception:
    _PADDLE_AVAILABLE = False

_PADDLE_INSTANCE: 'PaddleOCR' | None = None

ROW_GAP_THRESHOLD = 8   # px — Y gap above which a new row starts
COLUMN_GAP        = 20  # px — X gap for column boundary clustering
MIN_CONFIDENCE    = 0.55


@dataclass
class OCRBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    text: str
    confidence: float


@dataclass
class PageData:
    page_number: int
    tables: list[list[list[str]]] = field(default_factory=list)
    raw_text: str = ""
    method_used: str = "paddleocr"


class OCRPipeline:
    def __init__(self) -> None:
        self.last_error: dict[str, Any] | None = None

    @staticmethod
    def dependency_issue() -> dict[str, Any] | None:
        if not _PDF2IMAGE_AVAILABLE:
            return {
                "error_code": "MISSING_OCR_DEP",
                "message": "pdf2image is not installed in the parser runtime.",
                "details": {"missing": "pdf2image"},
            }
        if not _POPPLER_AVAILABLE:
            return {
                "error_code": "MISSING_OCR_DEP",
                "message": "Poppler is not installed or `pdftoppm` is unavailable in PATH.",
                "details": {"missing": "poppler-utils"},
            }
        return None

    def run(self, file_path: str) -> list[PageData]:
        with open(file_path, "rb") as f:
            return self.run_bytes(f.read())

    def run_bytes(self, content: bytes) -> list[PageData]:
        self.last_error = None
        dependency_issue = self.dependency_issue()
        if dependency_issue:
            self.last_error = dependency_issue
            logger.error("OCRPipeline: %s", dependency_issue["message"])
            return []

        try:
            images = convert_from_bytes(content, dpi=300, fmt="PNG")
        except Exception as e:
            self.last_error = {
                "error_code": "OCR_CONVERSION_FAILED",
                "message": "Failed to rasterize PDF for OCR.",
                "details": {"exception": str(e)},
            }
            logger.error("OCRPipeline: pdf2image failed: %s", e)
            return []

        all_pages = []
        for idx, pil_image in enumerate(images):
            page_data = self._process_image(pil_image, idx)
            all_pages.append(page_data)
        return all_pages

    def _process_image(self, pil_image: Any, page_idx: int) -> PageData:
        processed = ImagePreprocessor.process(pil_image)
        boxes     = PaddleOCREngine.run(processed)
        return LayoutReconstructor.reconstruct(boxes, page_idx)


class ImagePreprocessor:
    @staticmethod
    def process(pil_image: Any) -> Any:
        if not _CV2_AVAILABLE or not _NUMPY_AVAILABLE:
            logger.warning("OpenCV not available — returning raw PIL image")
            return pil_image

        img  = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # Upscale if too small
        h, w = gray.shape
        if w < 1800:
            scale = 1800 / w
            gray  = cv2.resize(gray, (0, 0), fx=scale, fy=scale,
                               interpolation=cv2.INTER_CUBIC)

        # Deskew
        angle = ImagePreprocessor._detect_skew(gray)
        if abs(angle) > 0.3:
            (ch, cw) = gray.shape
            M    = cv2.getRotationMatrix2D((cw // 2, ch // 2), angle, 1.0)
            gray = cv2.warpAffine(gray, M, (cw, ch),
                                  flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)

        # Denoise
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # Adaptive binarization
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15, C=8,
        )

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        return binary

    @staticmethod
    def _detect_skew(gray: Any) -> float:
        if not _CV2_AVAILABLE:
            return 0.0
        import math
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, math.pi / 180, 100, minLineLength=100, maxLineGap=10)
        if lines is None:
            return 0.0
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(angle) < 45:
                angles.append(angle)
        return float(sorted(angles)[len(angles) // 2]) if angles else 0.0


class PaddleOCREngine:
    @staticmethod
    def run(image: Any) -> list[OCRBox]:
        global _PADDLE_INSTANCE
        if not _PADDLE_AVAILABLE:
            logger.warning("PaddleOCR not available — returning empty OCR result")
            return []
            
        if _PADDLE_INSTANCE is None:
            logger.info("Initializing PaddleOCR for the first time... (may download models)")
            import os
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            from paddleocr import PaddleOCR
            _PADDLE_INSTANCE = PaddleOCR(
                use_angle_cls=True, lang="en", use_gpu=False,
                det_db_thresh=0.3, rec_batch_num=6,
                show_log=False,
            )

        try:
            raw = _PADDLE_INSTANCE.ocr(image, cls=True)
            boxes: list[OCRBox] = []
            for detection in (raw[0] or []):
                bbox, (text, conf) = detection
                if conf < MIN_CONFIDENCE:
                    continue
                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]
                boxes.append(OCRBox(
                    x_min=min(xs), y_min=min(ys),
                    x_max=max(xs), y_max=max(ys),
                    text=str(text).strip(),
                    confidence=float(conf),
                ))
            return boxes
        except Exception as e:
            logger.error("PaddleOCREngine.run: %s", e)
            return []


class LayoutReconstructor:
    @staticmethod
    def reconstruct(boxes: list[OCRBox], page_number: int) -> PageData:
        if not boxes:
            return PageData(page_number=page_number)

        # Sort top → bottom
        sorted_boxes = sorted(boxes, key=lambda b: b.y_min)

        # Cluster into rows by Y overlap
        rows: list[list[OCRBox]] = []
        current: list[OCRBox] = [sorted_boxes[0]]

        for box in sorted_boxes[1:]:
            last = current[-1]
            overlap = min(box.y_max, last.y_max) - max(box.y_min, last.y_min)
            gap     = box.y_min - last.y_max
            if overlap > 0 or gap < ROW_GAP_THRESHOLD:
                current.append(box)
            else:
                rows.append(current)
                current = [box]
        rows.append(current)

        # Sort each row left → right
        for row in rows:
            row.sort(key=lambda b: b.x_min)

        # Detect column boundaries
        all_x_starts = sorted({b.x_min for row in rows for b in row})
        col_bounds   = LayoutReconstructor._cluster_x(all_x_starts)

        # Build table
        table: list[list[str]] = []
        for row in rows:
            cells = [""] * len(col_bounds)
            for box in row:
                col_idx = LayoutReconstructor._find_col(box.x_min, col_bounds)
                if cells[col_idx]:
                    cells[col_idx] += " " + box.text
                else:
                    cells[col_idx] = box.text
            table.append(cells)

        raw_text = " ".join(b.text for row in rows for b in row)
        return PageData(
            page_number=page_number,
            tables=[table],
            raw_text=raw_text,
            method_used="paddleocr",
        )

    @staticmethod
    def _cluster_x(x_starts: list[float]) -> list[float]:
        if not x_starts:
            return []
        clusters: list[list[float]] = [[x_starts[0]]]
        for x in x_starts[1:]:
            if x - clusters[-1][-1] < COLUMN_GAP:
                clusters[-1].append(x)
            else:
                clusters.append([x])
        return [sum(c) / len(c) for c in clusters]

    @staticmethod
    def _find_col(x: float, bounds: list[float]) -> int:
        for i in range(len(bounds) - 1):
            if bounds[i] <= x < bounds[i + 1]:
                return i
        return len(bounds) - 1
