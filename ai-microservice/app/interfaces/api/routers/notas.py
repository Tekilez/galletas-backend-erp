"""Adapter primario: HTTP -> NotaUseCases + barcode/PDF."""
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from app.interfaces.api.schemas import NotaCreate, NotaResponse
from app.application.use_cases.nota_use_cases import NotaUseCases
from app.interfaces.api.dependencies import get_nota_use_cases, get_cliente_use_cases


router = APIRouter(prefix="/api/v1/notas", tags=["Notas de Venta"])

@router.post("", response_model=NotaResponse, status_code=201, summary="Crear nota (genera NV-YYYYMMDD-XXXX + descuenta stock)")
def create_nota(payload: NotaCreate, nota_uc: NotaUseCases = Depends(get_nota_use_cases), cliente_uc = Depends(get_cliente_use_cases)):
    cliente_id = payload.cliente_id
    # si viene cliente inline, crearlo
    if payload.cliente and not cliente_id:
        cli = cliente_uc.create(payload.cliente.model_dump(exclude_none=True))
        cliente_id = cli["id"]
    items = [it.model_dump() for it in payload.items]
    return nota_uc.create(cliente_id, payload.vendedor_id, payload.codigo_barras, items)

@router.get("", response_model=List[NotaResponse])
def list_notas(cliente_id: Optional[str] = Query(None), vendedor_id: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), uc: NotaUseCases = Depends(get_nota_use_cases)):
    return uc.list(cliente_id, vendedor_id, limit, offset)

@router.get("/{nota_id}", response_model=NotaResponse)
def get_nota(nota_id: str, uc: NotaUseCases = Depends(get_nota_use_cases)):
    return uc.get_detalle(nota_id)

@router.get("/{nota_id}/pdf", summary="PDF nota con barcode")
def pdf_nota(nota_id: str, uc: NotaUseCases = Depends(get_nota_use_cases)):
    nota = uc.get_detalle(nota_id)
    # generar PDF con ReportLab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        import barcode
        from barcode.writer import ImageWriter
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"PDF deps faltan: {e}")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, h-20*mm, f"Nota de Venta {nota['codigo_barras']}")
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, h-30*mm, f"Cliente: {nota.get('cliente_id') or 'Sin cliente'}  Total: S/ {nota['total']}")
    y = h-45*mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20*mm, y, "Cant  Variante  Precio  Subtotal")
    y -= 6*mm
    c.setFont("Helvetica", 8)
    for d in nota.get("detalles", []):
        subtotal = float(d["precio_unitario"]) * int(d["cantidad"])
        c.drawString(20*mm, y, f"{d['cantidad']} x {d['variante_id'][:8]}  S/ {d['precio_unitario']}  S/ {subtotal:.2f}")
        y -= 5*mm
        if y < 30*mm:
            c.showPage()
            y = h-20*mm

    # barcode Code128
    try:
        CODE128 = barcode.get_barcode_class('code128')
        writer = ImageWriter()
        bc = CODE128(nota["codigo_barras"], writer=writer)
        bc_buf = io.BytesIO()
        bc.write(bc_buf)
        bc_buf.seek(0)
        img = ImageReader(bc_buf)
        c.drawImage(img, 20*mm, 20*mm, width=80*mm, height=15*mm)
    except Exception:
        c.drawString(20*mm, 20*mm, nota["codigo_barras"])

    c.showPage()
    c.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{nota["codigo_barras"]}.pdf"'})

@router.delete("/{nota_id}", status_code=204)
def delete_nota(nota_id: str, uc: NotaUseCases = Depends(get_nota_use_cases)):
    uc.delete(nota_id)
    return None
