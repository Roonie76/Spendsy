from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, Body, HTTPException
from .schemas import StatementResponse
from .parser_logic import parse_statement_text

app = FastAPI(title="Bank Statement Parser Service")

@app.post("/v1/parse", response_model=StatementResponse)
async def parse_v1(
    raw_text: str = Body(None),
    file: UploadFile = File(None)
):
    """
    Parse a bank statement provided as raw text or a text file.
    """
    if file:
        content = await file.read()
        raw_text = content.decode("utf-8")
    
    if not raw_text:
        raise HTTPException(status_code=400, detail="No text provided for parsing")
        
    try:
        result = parse_statement_text(raw_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

# CLI support
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
