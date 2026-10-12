"""Adapter secundario: Supabase -> ProductoRepositoryPort"""
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from app.domain.ports.producto_repository import ProductoRepositoryPort
from app.infrastructure.persistence.supabase_client import require_supabase

def _handle_supabase_error(e: Exception):
    msg = str(e)
    if "duplicate" in msg.lower() or "23505" in msg:
        raise HTTPException(status_code=409, detail=msg)
    if "violates check" in msg.lower() or "23514" in msg:
        raise HTTPException(status_code=400, detail=msg)
    raise HTTPException(status_code=400, detail=msg)

class SupabaseProductoRepository(ProductoRepositoryPort):
    def list(self, categoria: Optional[str], activo: Optional[bool], search: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        sb = require_supabase()
        q = sb.table("productos").select("*").order("created_at", desc=True).range(offset, offset + limit - 1)
        if categoria:
            q = q.eq("categoria", categoria)
        if activo is not None:
            q = q.eq("activo", activo)
        if search:
            q = q.ilike("nombre", f"%{search}%")
        try:
            res = q.execute()
        except Exception as e:
            _handle_supabase_error(e)
        return res.data

    def get_by_id(self, producto_id: str) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        try:
            res = sb.table("productos").select("*").eq("id", producto_id).single().execute()
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado: {e}")
        if not res.data:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return res.data

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sb = require_supabase()
        try:
            res = sb.table("productos").insert(data).select().single().execute()
        except Exception as e:
            _handle_supabase_error(e)
        return res.data

    def update(self, producto_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        if not data:
            raise HTTPException(status_code=400, detail="Nada para actualizar")
        try:
            res = sb.table("productos").update(data).eq("id", producto_id).select().single().execute()
        except Exception as e:
            _handle_supabase_error(e)
        if not res.data:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return res.data

    def delete(self, producto_id: str) -> None:
        sb = require_supabase()
        try:
            existing = sb.table("productos").select("id").eq("id", producto_id).single().execute()
        except Exception:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        if not existing.data:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        try:
            sb.table("productos").delete().eq("id", producto_id).execute()
        except Exception as e:
            _handle_supabase_error(e)

    def list_variantes(self, producto_id: str) -> List[Dict[str, Any]]:
        sb = require_supabase()
        try:
            res = sb.table("variantes").select("*").eq("producto_id", producto_id).order("created_at").execute()
        except Exception as e:
            _handle_supabase_error(e)
        return res.data
