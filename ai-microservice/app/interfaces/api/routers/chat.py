"""Adapter primario: HTTP -> ChatUseCases (stock real)."""
from fastapi import APIRouter, Depends
from app.interfaces.api.schemas import ChatRequest, ChatResponse
from app.application.use_cases.chat_use_cases import ChatUseCases
from app.interfaces.api.dependencies import get_chat_use_cases

router = APIRouter(prefix="/api/v1", tags=["Chat Stock"])

@router.post("/chat", response_model=ChatResponse, summary="Chat stock con datos reales")
async def chat(payload: ChatRequest, uc: ChatUseCases = Depends(get_chat_use_cases)):
    return await uc.ask(payload.pregunta, payload.categoria, payload.talla, payload.color)

@router.get("/chat/stock-polos", summary="Atajo: stock polos")
async def stock_polos(uc: ChatUseCases = Depends(get_chat_use_cases)):
    return await uc.ask("¿Cuántos stock tienen los polos?", categoria="polos")
