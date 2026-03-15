from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agents.tora_agent import handle_user_question
from config import settings

app = FastAPI(title="Ask Tora AI Service")

# Add CORS middleware — restrict to known frontend origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:8080",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class QuestionRequest(BaseModel):
    user_id: int = 1
    question: str

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "spendsy-ai"}

@app.post("/ask-tora")
async def handle_ask_tora(request: QuestionRequest):
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Route to the new OpenAI-powered TORA Agent
        answer = handle_user_question(request.user_id, request.question)
        if "error" in answer:
            raise HTTPException(status_code=500, detail=answer["error"])
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
