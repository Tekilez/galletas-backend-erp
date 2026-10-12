"""Adapter secundario: Supabase -> VarianteRepositoryPort"""
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from app.domain.ports.variante_repository import VarianteRepositoryPort
from app.infrastructure.persistence.supabase_client import require_supabase

def _handle_error(e: Exception):
    msg = str(e)
    if "duplicate" in msg.lower() or "23505" in msg or "sku" in msg.lower():
        raise HTTPException(status_code=409, detail=f"SKU duplicado o conflicto: {msg}")
    if "violates" in msg.lower() or "23514" in msg or "check" in msg.lower():
        raise HTTPException(status_code=400, detail=msg)
    if "foreign key" in msg.lower() or "23503" in msg:
        raise HTTPException(status_code=400, detail=f"producto_id no existe: {msg}")
    raise HTTPException(status_code=400, detail=msg)

class SupabaseVarianteRepository(VarianteRepositoryPort):
    def list(self, producto_id: Optional[str], sku: Optional[str], talla: Optional[str], color: Optional[str], activo: Optional[bool], limit: int, offset: int, categoria: Optional[str] = None) -> List[Dict[str, Any]]:
        sb = require_supabase()
        # Si filtra por categoria, primero resolver producto_ids
        if categoria:
            try:
                prod_res = sb.table("productos").select("id").ilike("categoria", f"%{categoria}%").execute()
                ids = [p["id"] for p in prod_res.data]
                if not ids:
                    return []
                # si ya hay producto_id, intersectar
                if producto_id and producto_id not in ids:
                    return []
                if not producto_id:
                    # traer variantes de esos productos (in)
                    q = sb.table("variantes").select("*").in_("producto_id", ids).order("created_at", desc=True).range(offset, offset + limit - 1)
                    if sku:
                        q = q.eq("sku", sku)
                    if talla:
                        q = q.eq("talla", talla)
                    if color:
                        q = q.eq("color", color)
                    if activo is not None:
                        q = q.eq("activo", activo)
                    try:
                        res = q.execute()
                    except Exception as e:
                        _handle_error(e)
                    return res.data
            except Exception as e:
                _handle_error(e)
        q = sb.table("variantes").select("*").order("created_at", desc=True).range(offset, offset + limit - 1)
        if producto_id:
            q = q.eq("producto_id", producto_id)
        if sku:
            q = q.eq("sku", sku)
        if talla:
            q = q.eq("talla", talla)
        if color:
            q = q.eq("color", color)
        if activo is not None:
            q = q.eq("activo", activo)
        try:
            res = q.execute()
        except Exception as e:
            _handle_error(e)
        data = res.data
        return data

    def get_by_id(self, variante_id: str) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        try:
            res = sb.table("variantes").select("*").eq("id", variante_id).single().execute()
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Variante no encontrada: {e}")
        if not res.data:
            raise HTTPException(status_code=404, detail="Variante no encontrada")
        return res.data

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sb = require_supabase()
        try:
            res = sb.table("variantes").insert(data).select().single().execute()
        except Exception as e:
            _handle_error(e)
        return res.data

    def update(self, variante_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        if not data:
            raise HTTPException(status_code=400, detail="Nada para actualizar")
        if "stock_actual" in data:
            raise HTTPException(status_code=400, detail="stock_actual no editable directo. Usa POST /transacciones con tipo entrada/salida/ajuste")
        try:
            res = sb.table("variantes").update(data).eq("id", variante_id).select().single().execute()
        except Exception as e:
            _handle_error(e)
        if not res.data:
            raise HTTPException(status_code=404, detail="Variante no encontrada")
        return res.data

    def delete(self, variante_id: str) -> None:
        sb = require_supabase()
        try:
            existing = sb.table("variantes").select("id").eq("id", variante_id).single().execute()
        except Exception:
            raise HTTPException(status_code=404, detail="Variante no encontrada")
        if not existing.data:
            raise HTTPException(status_code=404, detail="Variante no encontrada")
        try:
            sb.table("variantes").delete().eq("id", variante_id).execute()
        except Exception as e:
            msg = str(e).lower()
            if "restrict" in msg or "23503" in msg:
                raise HTTPException(status_code=409, detail="No se puede eliminar: variante tiene transacciones (kardex). Desactívala con activo=false")
            _handle_error(e)
