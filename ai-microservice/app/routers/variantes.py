"""Shim hexagonal: re-exporta desde interfaces.api.routers.variantes"""
from app.interfaces.api.routers.variantes import router  # noqa: F401
__all__ = ["router"]
