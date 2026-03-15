from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.parser import IntegratedParser

router = APIRouter(tags=["parser"])

parser = IntegratedParser()


@router.post("/parse")
async def parse_statement(file: UploadFile = File(...)):
    content = await file.read()
    result = parser.parse(content, filename=file.filename, content_type=file.content_type)
    return result.model_dump(mode="json")
