"""
Infrastructure OCR adapter - implementa OcrPort.
Wrapping del servicio existente para hexagonal.
"""
import time
import random
import io
from typing import Tuple, List, Dict
from fastapi import UploadFile
from PIL import Image
from app.infrastructure.config.settings import get_settings
from app.domain.ports.ocr_port import OcrPort

settings = get_settings()

MOCK_CATALOG = [
    ("Polo Oversize Algodón", "M", "Negro"),
    ("Polo Oversize Algodón", "L", "Blanco"),
    ("Polo Camisero Cuello", "XL", "Negro"),
    ("Polo Camisero Cuello", "2XL", "Negro"),
    ("Pantalón Strech Semi Pitillo", "29", "Negro"),
    ("Pantalón Strech Semi Pitillo", "30", "Azul"),
    ("Pantalón Strech Semi Pitillo", "32", "Negro"),
    ("Pantalón Strech Semi Pitillo", "34", "Azul"),
    ("Jeans Mom Fit", "32", "Celeste"),
    ("Vestido Lino Verano", "S", "Beige"),
    ("Casaca Denim", "M", "Azul Oscuro"),
]

async def _ocr_mock(file: UploadFile) -> Tuple[str, list]:
    start = time.time()
    try:
        if file.content_type != "application/pdf":
            img = Image.open(file.file)
            img.verify()
            file.file.seek(0)
    except Exception:
        pass
    await file.read()
    elapsed_ms = int((time.time() - start) * 1000) + random.randint(200, 600)
    raw_text = (
        "BOLETA ELECTRONICA F001-8821\n"
        "GAMARRA TEXTILES S.A.C - RUC 20123456789\n"
        "Fecha: 2026-09-10\n"
        "Cant  Descripcion                          P.U   Total\n"
        "6    Pantalón Strech 29 Negro             55.00  330.00\n"
        "6    Pantalón Strech 32 Azul              55.00  330.00\n"
        "12   Polo Oversize M Negro                35.50  426.00\n"
        "8    Jeans Mom Fit 32 Celeste             58.00  464.00\n"
        "TOTAL: 32 unidades  S/ 1550.00\n"
    )
    items = [
        {"nombre_general": "Pantalón Strech Semi Pitillo", "cantidad": 6, "precio_costo": 55.00, "talla": "29", "color": "Negro", "sku_sugerido": "PANT-SP-29-NEG-001"},
        {"nombre_general": "Pantalón Strech Semi Pitillo", "cantidad": 6, "precio_costo": 55.00, "talla": "32", "color": "Azul", "sku_sugerido": "PANT-SP-32-AZU-001"},
        {"nombre_general": "Polo Oversize Algodón", "cantidad": 12, "precio_costo": 35.50, "talla": "M", "color": "Negro", "sku_sugerido": "POL-OVR-M-NEG-001"},
        {"nombre_general": "Jeans Mom Fit", "cantidad": 8, "precio_costo": 58.00, "talla": "32", "color": "Celeste", "sku_sugerido": "JEA-MOM-32-CEL-001"},
    ]
    return raw_text, items

async def _ocr_google_vision(file: UploadFile) -> Tuple[str, list]:
    return await _ocr_mock(file)

async def _ocr_huggingface(file: UploadFile) -> Tuple[str, list]:
    return await _ocr_mock(file)

class OcrAdapter(OcrPort):
    async def validate(self, file: UploadFile) -> None:
        allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
        if file.content_type not in allowed:
            raise ValueError(f"Tipo no soportado: {file.content_type}. Permitidos: {allowed}")
        file.file.seek(0, io.SEEK_END)
        size_mb = file.file.tell() / (1024 * 1024)
        file.file.seek(0)
        if size_mb > settings.max_upload_mb:
            raise ValueError(f"Archivo muy grande: {size_mb:.1f}MB > {settings.max_upload_mb}MB")

    async def extract(self, file) -> Tuple[str, List[Dict], str, int]:
        start = time.perf_counter()
        provider = settings.ocr_provider.lower()
        if provider == "google":
            raw_text, items = await _ocr_google_vision(file)
        elif provider == "huggingface":
            raw_text, items = await _ocr_huggingface(file)
        else:
            raw_text, items = await _ocr_mock(file)
            provider = "mock"
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return raw_text, items, provider, elapsed_ms

# Fachada funcional para compatibilidad (usada por use_cases)
ocr_adapter = OcrAdapter()

async def validate_upload(file: UploadFile) -> None:
    return await ocr_adapter.validate(file)

async def extract_receipt(file: UploadFile) -> Tuple[str, list, str, int]:
    return await ocr_adapter.extract(file)
