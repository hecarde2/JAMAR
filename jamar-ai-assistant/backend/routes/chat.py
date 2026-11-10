"""Endpoints de conversación."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from agent import get_agent
from schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["Conversación"])


@router.post("/chat", response_model=ChatResponse, summary="Procesa un mensaje del usuario")
def chat(payload: ChatRequest) -> ChatResponse:
    """Punto de entrada omnicanal: web, Mini App, Telegram o integraciones API."""
    try:
        return get_agent().process(
            message=payload.message,
            user_id=payload.user_id,
            session_id=payload.session_id,
            city=payload.city,
            channel=payload.channel,
        )
    except Exception as exc:  # pragma: no cover - protección de borde
        raise HTTPException(status_code=500, detail="No fue posible procesar el mensaje") from exc


@router.get("/chat/history/{session_id}", summary="Consulta el historial de una sesión")
def chat_history(session_id: str) -> dict:
    """Devuelve los turnos guardados para la sesión indicada."""
    history = get_agent().get_history(session_id)
    return {"session_id": session_id, "messages": history, "count": len(history)}


@router.delete("/chat/history/{session_id}", summary="Reinicia una sesión")
def reset_chat(session_id: str, user_id: str | None = Query(default=None)) -> dict:
    """Limpia el contexto de conversación para iniciar una asesoría nueva."""
    key = get_agent().sessions.resolve_key(user_id, session_id)
    get_agent().reset(key)
    return {"session_id": key, "reset": True}
