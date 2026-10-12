"""Shim hexagonal: re-exporta desde interfaces.api.routers.transacciones"""
from app.interfaces.api.routers.transacciones import router  # noqa: F401
__all__ = ["router"]
