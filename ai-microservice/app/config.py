"""Shim hexagonal: re-exporta desde infrastructure.config.settings para compatibilidad."""
from app.infrastructure.config.settings import Settings, get_settings  # noqa: F401

__all__ = ["Settings", "get_settings"]
