"""Adapter primario: HTTP -> TransaccionUseCases."""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from app.interfaces.api.schemas import TransaccionCreate, TransaccionResponse
from app.application.use_cases.transaccion_use_cases import TransaccionUseCases
from app.interfaces.api.dependencies import get_transaccion_use_cases

router = APIRouter(prefix="/api/v1/transacciones", tags=["Transacciones (Kardex)"])

@router.get("", response_model=List[TransaccionResponse], summary="Listar transacciones (kardex)")
def list_transacciones(
    variante_id: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None, description="entrada | salida | ajuste"),
    referencia: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uc: TransaccionUseCases = Depends(get_transaccion_use_cases),
):
    return uc.list_transacciones(variante_id, tipo, referencia, limit, offset)

@router.get("/kardex", summary="Kardex enriquecido (vista v_kardex_detalle)")
def list_kardex_detalle(
    variante_id: Optional[str] = Query(None),
    producto_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uc: TransaccionUseCases = Depends(get_transaccion_use_cases),
):
    return uc.list_kardex_detalle(variante_id, producto_id, limit, offset)

@router.get("/{transaccion_id}", response_model=TransaccionResponse, summary="Obtener transacción por ID")
def get_transaccion(transaccion_id: str, uc: TransaccionUseCases = Depends(get_transaccion_use_cases)):
    return uc.get_transaccion(transaccion_id)

@router.post("", response_model=TransaccionResponse, status_code=201, summary="Crear movimiento kardex (actualiza stock vía trigger)")
def create_transaccion(payload: TransaccionCreate, uc: TransaccionUseCases = Depends(get_transaccion_use_cases)):
    return uc.create_transaccion(payload.model_dump(exclude_none=True))

@router.put("/{transaccion_id}", include_in_schema=False)
def _no_update(transaccion_id: str):
    raise HTTPException(status_code=405, detail="Kardex inmutable: no se permite UPDATE. Usa tipo='ajuste' para correcciones.")

@router.delete("/{transaccion_id}", include_in_schema=False)
def _no_delete(transaccion_id: str):
    raise HTTPException(status_code=405, detail="Kardex inmutable: no se permite DELETE.")
