from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.pipeline import DocumentParserPipeline
from app.core.internal_auth import verify_internal_api_key
from app.utils.files import validate_file_security, sanitize_filename

router = APIRouter(tags=["parser"])

pipeline = DocumentParserPipeline()


@router.post("/parse")
async def parse_statement(
    file: UploadFile = File(...),
    _: None = Depends(verify_internal_api_key),
):
    # Internal defense-in-depth: Validate file even from internal services
    validate_file_security(file)
    file.filename = sanitize_filename(file.filename or "statement.pdf")

    content = await file.read()
    result = pipeline.run(content, filename=file.filename, content_type=file.content_type)
    return result.model_dump(mode="json")
