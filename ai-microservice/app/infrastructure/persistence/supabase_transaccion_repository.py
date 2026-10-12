"""Adapter secundario: Supabase -> TransaccionRepositoryPort"""
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from app.domain.ports.transaccion_repository import TransaccionRepositoryPort
from app.infrastructure.persistence.supabase_client import require_supabase

def _handle_error(e: Exception):
    msg = str(e)
    if "stock desincronizado" in msg.lower() or "desincronizado" in msg.lower():
        raise HTTPException(status_code=409, detail=msg)
    if "stock insuficiente" in msg.lower():
        raise HTTPException(status_code=409, detail=msg)
    if "incongruente" in msg.lower():
        raise HTTPException(status_code=400, detail=msg)
    if "no existe" in msg.lower():
        raise HTTPException(status_code=404, detail=msg)
    if "violates" in msg.lower() or "23514" in msg:
        raise HTTPException(status_code=400, detail=msg)
    raise HTTPException(status_code=400, detail=msg)

class SupabaseTransaccionRepository(TransaccionRepositoryPort):
    def list(self, variante_id: Optional[str], tipo: Optional[str], referencia: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        sb = require_supabase()
        q = sb.table("transacciones").select("*").order("created_at", desc=True).range(offset, offset + limit - 1)
        if variante_id:
            q = q.eq("variante_id", variante_id)
        if tipo:
            if tipo not in ("entrada", "salida", "ajuste"):
                raise HTTPException(status_code=400, detail="tipo debe ser entrada|salida|ajuste")
            q = q.eq("tipo", tipo)
        if referencia:
            q = q.eq("referencia", referencia)
        try:
            res = q.execute()
        except Exception as e:
            _handle_error(e)
        return res.data

    def list_kardex_detalle(self, variante_id: Optional[str], producto_id: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        sb = require_supabase()
        q = sb.table("v_kardex_detalle").select("*").order("created_at", desc=True).range(offset, offset + limit - 1)
        if variante_id:
            q = q.eq("variante_id", variante_id)
        if producto_id:
            q = q.eq("producto_id", producto_id)
        try:
            res = q.execute()
        except Exception as e:
            _handle_error(e)
        return res.data

    def get_by_id(self, transaccion_id: str) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        try:
            res = sb.table("transacciones").select("*").eq("id", transaccion_id).single().execute()
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Transacción no encontrada: {e}")
        if not res.data:
            raise HTTPException(status_code=404, detail="Transacción no encontrada")
        return res.data

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sb = require_supabase()
        if data.get("tipo") in ("entrada", "salida"):
            esperado = data["stock_anterior"] + data["cantidad"] if data["tipo"] == "entrada" else data["stock_anterior"] - data["cantidad"]
            if data["stock_nuevo"] != esperado:
                raise HTTPException(status_code=400, detail=f"stock_nuevo incongruente: para {data['tipo']} esperado {esperado}, recibido {data['stock_nuevo']}")
            if esperado < 0:
                raise HTTPException(status_code=400, detail="Stock resultante negativo")
        try:
            res = sb.table("transacciones").insert(data).select().single().execute()
        except Exception as e:
            _handle_error(e)
        if not res.data:
            raise HTTPException(status_code=500, detail="No se pudo crear la transacción")
        return res.data
