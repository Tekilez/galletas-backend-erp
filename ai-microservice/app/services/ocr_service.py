"""Shim hexagonal: re-exporta desde infrastructure.ocr.ocr_adapter."""
from app.infrastructure.ocr.ocr_adapter import (  # noqa: F401
    MOCK_CATALOG,
    validate_upload,
    extract_receipt,
    ocr_adapter,
    _ocr_mock,
    _ocr_google_vision,
    _ocr_huggingface,
)
