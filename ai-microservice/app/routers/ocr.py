"""Shim hexagonal: re-exporta desde interfaces.api.routers.ocr"""
from app.interfaces.api.routers.ocr import router  # noqa: F401
__all__ = ["router"]
