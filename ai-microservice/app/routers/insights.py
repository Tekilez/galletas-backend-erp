"""Shim hexagonal: re-exporta desde interfaces.api.routers.insights"""
from app.interfaces.api.routers.insights import router  # noqa: F401
__all__ = ["router"]
