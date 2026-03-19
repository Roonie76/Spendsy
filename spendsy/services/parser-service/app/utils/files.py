from __future__ import annotations

import re
import unicodedata
from typing import Any

from fastapi import HTTPException, UploadFile, status
from app.core.config import settings


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing potentially dangerous characters.
    Simplified version of werkzeug.utils.secure_filename.
    """
    # Remove directory paths
    filename = filename.replace("\\", "/").split("/")[-1]
    
    # Normalize unicode characters
    filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
    
    # Remove non-alphanumeric (except . - _)
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    filename = filename.strip("._")
    
    return filename or "upload"


def validate_file_security(file: UploadFile) -> None:
    """
    Verify file size, extension, and MIME type.
    Raises HTTPException if insecure.
    """
    # 1. Size Check
    file_size = getattr(file, "size", 0)
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB"
        )

    # 2. Extension Check
    filename = file.filename or ""
    extension = filename.split(".")[-1].lower() if "." in filename else ""
    if extension not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{extension}' is not allowed"
        )

    # 3. MIME Type Check
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type '{file.content_type}' is not allowed"
        )
