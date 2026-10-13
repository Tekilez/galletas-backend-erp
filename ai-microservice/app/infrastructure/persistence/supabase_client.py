"""
Infrastructure - Supabase client adapter.
Wrapper hexagonal sobre supabase-py. Único lugar que conoce create_client.
"""
from functools import lru_cache
from typing import Optional
from supabase import create_client, Client
from app.infrastructure.config.settings import get_settings

_settings = get_settings()

@lru_cache(maxsize=1)
def get_supabase() -> Optional[Client]:
    if not _settings.supabase_url or not _settings.supabase_service_key:
        return None
    return create_client(_settings.supabase_url, _settings.supabase_service_key)

def require_supabase() -> Client:
    client = get_supabase()
    if client is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Supabase no configurado. Define SUPABASE_URL y SUPABASE_SERVICE_KEY en .env"
        )
    return client

def single_row(res):
    """Extrae la primera fila (dict) de una respuesta supabase-py con .select(), o None."""
    try:
        data = getattr(res, "data", res)
        if isinstance(data, list):
            return data[0] if data else None
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None
