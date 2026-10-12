"""
Container / DI wiring hexagonal - punto único de composición.
Usado por main.py y tests para inyectar adapters.
"""
from app.interfaces.api.dependencies import (
    get_producto_use_cases,
    get_variante_use_cases,
    get_transaccion_use_cases,
    get_ocr_use_cases,
    get_insights_use_cases,
)

__all__ = [
    "get_producto_use_cases",
    "get_variante_use_cases",
    "get_transaccion_use_cases",
    "get_ocr_use_cases",
    "get_insights_use_cases",
]
