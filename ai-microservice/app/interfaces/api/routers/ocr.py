"""Adapter primario: HTTP -> OcrUseCases."""
from fastapi import APIRouter, UploadFile, File, Depends
from app.interfaces.api.schemas import ScanReceiptResponse
from app.application.use_cases.ocr_use_cases import OcrUseCases
from app.interfaces.api.dependencies import get_ocr_use_cases

router = APIRouter(prefix="/api/v1", tags=["OCR"])

@router.post(
    "/scan-receipt",
    response_model=ScanReceiptResponse,
    summary="OCR de boleta de compra",
    description="Recibe imagen/PDF de boleta, extrae items y devuelve JSON estructurado con Nombre, Cantidad y Precio de Costo."
)
async def scan_receipt(file: UploadFile = File(..., description="Imagen JPG/PNG/WEBP o PDF de la boleta"), uc: OcrUseCases = Depends(get_ocr_use_cases)):
    return await uc.scan_receipt(file)

@router.post(
    "/scan-receipt/simple",
    summary="OCR simple (1 item agregado)",
    include_in_schema=False,
)
async def scan_receipt_simple(file: UploadFile = File(...), uc: OcrUseCases = Depends(get_ocr_use_cases)):
    resp = await uc.scan_receipt(file)
    return {
        "nombre_general": resp.items[0].nombre_general if resp.items else None,
        "cantidad_total": resp.cantidad_total,
        "precio_costo_promedio": round(resp.costo_total / resp.cantidad_total, 2) if resp.cantidad_total else 0,
        "detalle": resp.model_dump(),
    }
