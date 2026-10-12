"""Adapter primario: HTTP -> ClienteUseCases."""
from fastapi import APIRouter, Query, Depends
from typing import List, Optional
from app.interfaces.api.schemas import ClienteCreate, ClienteUpdate, ClienteResponse
from app.application.use_cases.cliente_use_cases import ClienteUseCases
from app.interfaces.api.dependencies import get_cliente_use_cases

router = APIRouter(prefix="/api/v1/clientes", tags=["Clientes"])

@router.get("", response_model=List[ClienteResponse], summary="Listar clientes")
def list_clientes(search: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), uc: ClienteUseCases = Depends(get_cliente_use_cases)):
    return uc.list(search, limit, offset)

@router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(cliente_id: str, uc: ClienteUseCases = Depends(get_cliente_use_cases)):
    return uc.get(cliente_id)

@router.post("", response_model=ClienteResponse, status_code=201)
def create_cliente(payload: ClienteCreate, uc: ClienteUseCases = Depends(get_cliente_use_cases)):
    return uc.create(payload.model_dump(exclude_none=True))

@router.put("/{cliente_id}", response_model=ClienteResponse)
def update_cliente(cliente_id: str, payload: ClienteUpdate, uc: ClienteUseCases = Depends(get_cliente_use_cases)):
    data = {k: v for k, v in payload.model_dump(exclude_none=True).items() if v is not None}
    return uc.update(cliente_id, data)

@router.delete("/{cliente_id}", status_code=204)
def delete_cliente(cliente_id: str, uc: ClienteUseCases = Depends(get_cliente_use_cases)):
    uc.delete(cliente_id)
    return None
