from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.redis import append_message, load_history
from ..core.security import UserContext, get_current_user
from ..schemas import ChatRequest, ChatResponse
from ..services.gemini_client import GeminiError, generate_text
from ..services.finance_client import fetch_finance_context

router = APIRouter(tags=["chat"])


def _build_prompt(user: UserContext, message: str, context: dict, history: list[dict]) -> str:
    history_snippet = "\n".join(
        f"{item.get('role', 'user')}: {item.get('content', '')}" for item in history[-8:]
    )
    system = (
        "You are SmartSpend, a concise personal finance assistant for India. "
        "Use the provided context to answer the user's question. "
        "Avoid legal or tax advice beyond high-level guidance. "
        "Keep replies under 120 words."
    )
    context_json = json.dumps(context, ensure_ascii=False)
    return (
        f"{system}\n\nHISTORY:\n{history_snippet}\n\nCONTEXT:\n{context_json}\n\n"
        f"USER: {message.strip()}\nASSISTANT:"
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: UserContext = Depends(get_current_user),
):
    try:
        context = fetch_finance_context(user.id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Finance context unavailable") from exc

    history = load_history(user.id, limit=16)
    prompt = _build_prompt(user, payload.message, context, history)
    try:
        reply = generate_text(prompt, response_format="text")
    except GeminiError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    append_message(user.id, "user", payload.message)
    append_message(user.id, "assistant", reply)

    updated_history = load_history(user.id, limit=16)

    return ChatResponse(reply=reply, context=context, history=updated_history)
