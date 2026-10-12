"""Adapter primario: HTTP -> VarianteUseCases."""
import io
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import Response
from typing import List, Optional
from app.interfaces.api.schemas import VarianteCreate, VarianteUpdate, VarianteResponse
from app.application.use_cases.variante_use_cases import VarianteUseCases
from app.interfaces.api.dependencies import get_variante_use_cases
from app.infrastructure.persistence.supabase_client import require_supabase

router = APIRouter(prefix="/api/v1/variantes", tags=["Variantes"])

@router.get("", response_model=List[VarianteResponse], summary="Listar variantes")
def list_variantes(
    producto_id: Optional[str] = Query(None),
    sku: Optional[str] = Query(None),
    talla: Optional[str] = Query(None, description="Presentacion galleta: PAQ6,PAQ12,CAJA24,BOLSA500G,BOLSA1KG,UNIDAD"),
    color: Optional[str] = Query(None, description="Sabor galleta: CHOCOCHIPS,VAINILLA,AVENA,RELLENA,MANTEQUILLA,COCO"),
    activo: Optional[bool] = Query(None),
    stock_critico: Optional[bool] = Query(None, description="Si true, solo stock_actual <= stock_minimo"),
    categoria: Optional[str] = Query(None, description="Filtra por categoria del producto (clasicas, rellenas, saludables, premium...)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uc: VarianteUseCases = Depends(get_variante_use_cases),
):
    return uc.list_variantes(producto_id, sku, talla, color, activo, limit, offset, bool(stock_critico), categoria)

@router.get("/{variante_id}", response_model=VarianteResponse, summary="Obtener variante por ID")
def get_variante(variante_id: str, uc: VarianteUseCases = Depends(get_variante_use_cases)):
    return uc.get_variante(variante_id)

@router.post("", response_model=VarianteResponse, status_code=201, summary="Crear variante (SKU vendible)")
def create_variante(payload: VarianteCreate, uc: VarianteUseCases = Depends(get_variante_use_cases)):
    return uc.create_variante(payload.model_dump(exclude_none=True))

@router.put("/{variante_id}", response_model=VarianteResponse, summary="Actualizar variante (no stock_actual)")
def update_variante(variante_id: str, payload: VarianteUpdate, uc: VarianteUseCases = Depends(get_variante_use_cases)):
    data = {k: v for k, v in payload.model_dump(exclude_none=True).items() if v is not None}
    return uc.update_variante(variante_id, data)

@router.get("/{variante_id}/barcode", summary="PNG barcode Code128 de variante (para etiqueta)")
def variante_barcode(variante_id: str):
    sb = require_supabase()
    try:
        var = sb.table("variantes").select("sku").eq("id", variante_id).single().execute()
        if not var.data:
            raise HTTPException(status_code=404, detail="Variante no encontrada")
        sku = var.data["sku"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        import barcode
        from barcode.writer import ImageWriter
        CODE128 = barcode.get_barcode_class('code128')
        writer = ImageWriter()
        bc = CODE128(sku, writer=writer)
        buf = io.BytesIO()
        bc.write(buf)
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{variante_id}", status_code=204, summary="Eliminar variante (bloqueado si tiene transacciones)")
def delete_variante(variante_id: str, uc: VarianteUseCases = Depends(get_variante_use_cases)):
    uc.delete_variante(variante_id)
    return None
