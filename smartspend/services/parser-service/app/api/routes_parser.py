from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from ..parser import IntegratedParser

router = APIRouter(tags=["parser"])

parser = IntegratedParser()


@router.post("/parse")
async def parse_statement(file: UploadFile = File(...)):
    content = await file.read()
    result = parser.parse(content)
    return result.model_dump(mode="json")
