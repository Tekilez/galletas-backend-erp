"""Adapter primario: HTTP -> ProductoUseCases (hexagonal)."""
from fastapi import APIRouter, Query, Depends
from typing import List, Optional
from app.interfaces.api.schemas import ProductoCreate, ProductoUpdate, ProductoResponse
from app.application.use_cases.producto_use_cases import ProductoUseCases
from app.interfaces.api.dependencies import get_producto_use_cases

router = APIRouter(prefix="/api/v1/productos", tags=["Productos"])

@router.get("", response_model=List[ProductoResponse], summary="Listar productos")
def list_productos(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    activo: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Búsqueda por nombre/descripcion (ilike)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uc: ProductoUseCases = Depends(get_producto_use_cases),
):
    return uc.list_productos(categoria, activo, search, limit, offset)

@router.get("/{producto_id}", response_model=ProductoResponse, summary="Obtener producto por ID")
def get_producto(producto_id: str, uc: ProductoUseCases = Depends(get_producto_use_cases)):
    return uc.get_producto(producto_id)

@router.post("", response_model=ProductoResponse, status_code=201, summary="Crear producto")
def create_producto(payload: ProductoCreate, uc: ProductoUseCases = Depends(get_producto_use_cases)):
    return uc.create_producto(payload.model_dump(exclude_none=True))

@router.put("/{producto_id}", response_model=ProductoResponse, summary="Actualizar producto")
def update_producto(producto_id: str, payload: ProductoUpdate, uc: ProductoUseCases = Depends(get_producto_use_cases)):
    data = {k: v for k, v in payload.model_dump(exclude_none=True).items() if v is not None}
    return uc.update_producto(producto_id, data)

@router.delete("/{producto_id}", status_code=204, summary="Eliminar producto (cascade variantes)")
def delete_producto(producto_id: str, uc: ProductoUseCases = Depends(get_producto_use_cases)):
    uc.delete_producto(producto_id)
    return None

@router.get("/{producto_id}/variantes", summary="Variantes de un producto")
def list_variantes_de_producto(producto_id: str, uc: ProductoUseCases = Depends(get_producto_use_cases)):
    return uc.list_variantes_de_producto(producto_id)
