"""FastAPI routes for Risk Mitigation interactive AI."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from physics.mitigation_chat import answer_mitigation, immediate_priorities

router = APIRouter(tags=["mitigation"])


class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class MitigationChatRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[ChatMessage] = Field(default_factory=list)


@router.post("/api/mitigation/chat")
def mitigation_chat(body: MitigationChatRequest):
    history = [{"role": m.role, "content": m.content} for m in body.history]
    return answer_mitigation(
        message=body.message,
        context=body.context,
        history=history,
    )


@router.get("/api/mitigation/priorities")
def mitigation_priorities(surface: str = "unknown"):
    return {
        "status": "ok",
        "surface": surface,
        "immediate_priorities": immediate_priorities(surface),
    }
