"""Adapter primario: HTTP -> DevolucionUseCases."""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.interfaces.api.schemas import DevolucionCreate, DevolucionResponse
from app.application.use_cases.devolucion_use_cases import DevolucionUseCases
from app.interfaces.api.dependencies import get_devolucion_use_cases
from app.infrastructure.auth.jwt_handler import get_current_vendedor_optional

router = APIRouter(prefix="/api/v1/devoluciones", tags=["Devoluciones"])

@router.post("", response_model=DevolucionResponse, status_code=201, summary="Crear devolución (repone stock)")
def create_devolucion(
    payload: DevolucionCreate,
    vendedor=Depends(get_current_vendedor_optional),
    uc: DevolucionUseCases = Depends(get_devolucion_use_cases)
):
    items = [it.model_dump() for it in payload.items]
    motivo = payload.motivo_general or payload.motivo or "Devolución"
    created_by = vendedor["id"] if vendedor and isinstance(vendedor, dict) and "id" in vendedor else None
    return uc.create(payload.nota_codigo, items, motivo, created_by=created_by)

@router.get("", response_model=List[DevolucionResponse], summary="Historial devoluciones")
def list_devoluciones(
    nota_codigo: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uc: DevolucionUseCases = Depends(get_devolucion_use_cases)
):
    return uc.list(nota_codigo, q, limit, offset)

@router.get("/{codigo}", response_model=DevolucionResponse, summary="Detalle devolución por codigo DV-...")
def get_devolucion(codigo: str, uc: DevolucionUseCases = Depends(get_devolucion_use_cases)):
    return uc.get(codigo)
