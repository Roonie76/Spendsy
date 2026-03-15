from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agents.tora_agent import handle_user_question
from config import settings

app = FastAPI(title="Ask Tora AI Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
