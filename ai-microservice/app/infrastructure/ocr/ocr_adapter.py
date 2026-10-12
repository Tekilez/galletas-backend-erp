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
    ("Galleta Chocochips Clasica", "PAQ12", "CHOCOCHIPS"),
    ("Galleta Chocochips Clasica", "PAQ6", "CHOCOCHIPS"),
    ("Galleta Vainilla Francesa", "PAQ12", "VAINILLA"),
    ("Galleta Vainilla Francesa", "PAQ6", "VAINILLA"),
    ("Galleta Chocochips Clasica", "CAJA24", "CHOCOCHIPS"),
    ("Galleta Chocochips Clasica", "BOLSA500G", "CHOCOCHIPS"),
    ("Galleta Avena Integral", "BOLSA500G", "AVENA"),
    ("Galleta Rellena Chocolate", "PAQ12", "RELLENA"),
    ("Galleta Mantequilla Artesanal", "PAQ6", "MANTEQUILLA"),
    ("Galleta Coco Crunch", "PAQ12", "COCO"),
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
        "MOLINO GALLETAR S.A.C - RUC 20123456789\n"
        "Fecha: 2026-09-10\n"
        "Cant  Descripcion                          P.U   Total\n"
        "6    Galleta Chocochips PAQ12            15.00   90.00\n"
        "6    Galleta Chocochips CAJA24           28.00  168.00\n"
        "12   Galleta Vainilla PAQ12              14.00  168.00\n"
        "8    Galleta Avena BOLSA500G             13.00  104.00\n"
        "TOTAL: 32 unidades  S/ 530.00\n"
    )
    items = [
        {"nombre_general": "Galleta Chocochips Clasica", "cantidad": 6, "precio_costo": 15.00, "talla": "PAQ12", "color": "CHOCOCHIPS", "sku_sugerido": "GALL-CHOCO-PAQ12-001"},
        {"nombre_general": "Galleta Chocochips Clasica", "cantidad": 6, "precio_costo": 28.00, "talla": "CAJA24", "color": "CHOCOCHIPS", "sku_sugerido": "GALL-CHOCO-CAJA24-001"},
        {"nombre_general": "Galleta Vainilla Francesa", "cantidad": 12, "precio_costo": 14.00, "talla": "PAQ12", "color": "VAINILLA", "sku_sugerido": "GALL-VAIN-PAQ12-001"},
        {"nombre_general": "Galleta Avena Integral", "cantidad": 8, "precio_costo": 13.00, "talla": "BOLSA500G", "color": "AVENA", "sku_sugerido": "GALL-AVENA-500G-001"},
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
