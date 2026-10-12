"""Shim hexagonal: re-exporta desde infrastructure.persistence.supabase_client."""
from app.infrastructure.persistence.supabase_client import get_supabase, require_supabase  # noqa: F401
