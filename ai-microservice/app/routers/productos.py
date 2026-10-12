"""Shim hexagonal: re-exporta desde interfaces.api.routers.productos"""
from app.interfaces.api.routers.productos import router  # noqa: F401
__all__ = ["router"]
