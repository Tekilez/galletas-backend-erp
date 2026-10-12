"""Adapter secundario: Supabase -> ClienteRepositoryPort"""
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from app.domain.ports.cliente_repository import ClienteRepositoryPort
from app.infrastructure.persistence.supabase_client import require_supabase

class SupabaseClienteRepository(ClienteRepositoryPort):
    def list(self, search: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        sb = require_supabase()
        q = sb.table("clientes").select("*").order("created_at", desc=True).range(offset, offset + limit - 1)
        if search:
            q = q.ilike("nombre", f"%{search}%")
        try:
            res = q.execute()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        return res.data

    def get_by_id(self, cliente_id: str) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        try:
            res = sb.table("clientes").select("*").eq("id", cliente_id).single().execute()
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado: {e}")
        if not res.data:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return res.data

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sb = require_supabase()
        try:
            res = sb.table("clientes").insert(data).select().single().execute()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        return res.data

    def update(self, cliente_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not data:
            raise HTTPException(status_code=400, detail="Nada para actualizar")
        sb = require_supabase()
        try:
            res = sb.table("clientes").update(data).eq("id", cliente_id).select().single().execute()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not res.data:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return res.data

    def delete(self, cliente_id: str) -> None:
        sb = require_supabase()
        try:
            sb.table("clientes").delete().eq("id", cliente_id).execute()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
