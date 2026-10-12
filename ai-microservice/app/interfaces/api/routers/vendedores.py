"""Adapter primario: Vendedores (solo admin) - alias de auth."""
from fastapi import APIRouter, Depends, HTTPException
from app.infrastructure.auth.jwt_handler import get_current_vendedor
from app.infrastructure.persistence.supabase_client import require_supabase

router = APIRouter(prefix="/api/v1/vendedores", tags=["Vendedores"])

@router.get("", summary="Lista vendedores (solo admin)")
def list_vendedores(vendedor=Depends(get_current_vendedor)):
    if vendedor.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    sb = require_supabase()
    res = sb.table("vendedores").select("id,usuario,nombre,rol,activo,created_at").order("created_at").execute()
    return res.data
