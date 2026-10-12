"""
Schemas Pydantic para validación y documentación OpenAPI.
Hexagonal: viven en interfaces/api (contrato de entrada/salida).
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

# ---------- OCR ----------

class ReceiptItem(BaseModel):
    nombre_general: str = Field(..., example="Galleta Chocochips")
    cantidad: int = Field(..., ge=1, example=12)
    precio_costo: float = Field(..., ge=0, description="Precio de Costo unitario", example=15.00)
    talla: Optional[str] = Field(default=None, example="PAQ12", description="Presentacion (columna talla por compatibilidad)")
    color: Optional[str] = Field(default=None, example="CHOCOCHIPS", description="Sabor (columna color por compatibilidad)")
    sku_sugerido: Optional[str] = Field(default=None, example="GALL-CHOCO-PAQ12-001")

class ScanReceiptResponse(BaseModel):
    success: bool = True
    proveedor: Optional[str] = Field(default=None, example="Molino Galletar S.A.C")
    fecha_boleta: Optional[str] = Field(default=None, example="2026-09-10")
    moneda: str = Field(default="PEN", example="PEN")
    items: List[ReceiptItem]
    cantidad_total: int = Field(..., example=24)
    costo_total: float = Field(..., example=852.0)
    raw_text_preview: Optional[str] = Field(default=None, description="Primeras líneas del OCR para debug")
    ocr_provider: str = Field(..., example="mock")
    processing_time_ms: int

class ScanReceiptError(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None

# ---------- INSIGHTS ----------

class KardexItemStat(BaseModel):
    producto_nombre: str = Field(..., example="Galleta Chocochips Clasica")
    variante_sku: Optional[str] = Field(default=None, example="GALL-CHOCO-PAQ12-001")
    categoria: Optional[str] = Field(default=None, example="clasicas")
    total_vendido: int = Field(..., ge=0, example=120)
    total_comprado: Optional[int] = Field(default=None, example=150)
    stock_actual: Optional[int] = Field(default=None, example=30)
    precio_venta: Optional[float] = Field(default=None, example=59.90)

class InventoryInsightsRequest(BaseModel):
    periodo: str = Field(default="últimos 30 días", example="2026-08-01 a 2026-09-14")
    productos_mas_vendidos: List[KardexItemStat] = Field(..., description="Top sellers")
    productos_menos_vendidos: List[KardexItemStat] = Field(..., description="Low sellers / stock muerto")
    stock_critico: Optional[List[KardexItemStat]] = Field(default=None, description="Variantes con stock <= stock_minimo")
    notas_adicionales: Optional[str] = Field(default=None, example="Campaña navideña próxima")

class InventoryInsightsResponse(BaseModel):
    success: bool = True
    analisis: str = Field(..., description="Párrafo único en lenguaje natural con recomendaciones accionables")
    llm_provider: str
    model: str
    generated_at: datetime

# ---------- HEALTH ----------
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    llm_provider: str
    ocr_provider: str


# ---------- PRODUCTOS CRUD ----------
class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150, example="Galleta Chocochips Clasica")
    descripcion: Optional[str] = Field(default=None, example="Galleta con chispas de chocolate")
    categoria: Optional[str] = Field(default=None, max_length=80, example="clasicas")
    margen_ganancia: float = Field(default=40.0, ge=0, le=500, example=45.0)
    activo: bool = Field(default=True)

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=150)
    descripcion: Optional[str] = None
    categoria: Optional[str] = Field(default=None, max_length=80)
    margen_ganancia: Optional[float] = Field(default=None, ge=0, le=500)
    activo: Optional[bool] = None

class ProductoResponse(ProductoBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- VARIANTES CRUD ----------
class VarianteBase(BaseModel):
    producto_id: str = Field(..., description="UUID del producto padre")
    sku: str = Field(..., min_length=1, max_length=50, example="GALL-CHOCO-PAQ12-001")
    talla: str = Field(..., min_length=1, max_length=20, example="PAQ12", description="Presentacion galleta (UNIDAD,PAQ6,PAQ12,CAJA24,BOLSA500G,BOLSA1KG). Nombre de columna se mantiene por compatibilidad.")
    color: str = Field(..., min_length=1, max_length=50, example="CHOCOCHIPS", description="Sabor galleta (CHOCOCHIPS,VAINILLA,AVENA,RELLENA,MANTEQUILLA,COCO). Nombre de columna se mantiene por compatibilidad.")
    stock_actual: int = Field(default=0, ge=0, example=25)
    stock_minimo: int = Field(default=5, ge=0, example=5)
    precio_costo: float = Field(..., ge=0, example=15.00)
    precio_venta: float = Field(..., ge=0, example=21.75, description="Si = precio_costo, el trigger DB calcula con margen")
    imagen_url: Optional[str] = None
    activo: bool = Field(default=True)

class VarianteCreate(VarianteBase):
    pass

class VarianteUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, max_length=50)
    talla: Optional[str] = Field(default=None, max_length=20)
    color: Optional[str] = Field(default=None, max_length=50)
    stock_minimo: Optional[int] = Field(default=None, ge=0)
    precio_costo: Optional[float] = Field(default=None, ge=0)
    precio_venta: Optional[float] = Field(default=None, ge=0)
    imagen_url: Optional[str] = None
    activo: Optional[bool] = None

class VarianteResponse(VarianteBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- CHAT STOCK ----------
class ChatRequest(BaseModel):
    pregunta: str = Field(..., example="¿Cuánto stock tienen las chocochips?", description="Pregunta en lenguaje natural sobre stock")
    categoria: Optional[str] = Field(default=None, example="clasicas", description="Opcional: filtra por categoria")
    talla: Optional[str] = Field(default=None, example="PAQ12", description="Presentacion (columna talla por compatibilidad)")
    color: Optional[str] = Field(default=None, example="CHOCOCHIPS", description="Sabor (columna color por compatibilidad)")

class ChatResponse(BaseModel):
    success: bool = True
    pregunta: str
    respuesta: str
    datos: Optional[dict] = Field(default=None, description="Conteo real usado para la respuesta")
    llm_provider: str
    model: str
    generated_at: datetime
    class Config:
        from_attributes = True

# ---------- CLIENTES ----------
class ClienteBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150, example="Juan Pérez")
    dni: Optional[str] = Field(default=None, max_length=20, example="12345678")
    telefono: Optional[str] = Field(default=None, max_length=20, example="987654321")

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=150)
    dni: Optional[str] = Field(default=None, max_length=20)
    telefono: Optional[str] = Field(default=None, max_length=20)

class ClienteResponse(ClienteBase):
    id: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# ---------- NOTAS VENTA ----------
class NotaItem(BaseModel):
    variante_id: str = Field(..., example="uuid-variante")
    cantidad: int = Field(..., gt=0, example=2)
    precio_unitario: float = Field(..., ge=0, example=19.60)

class NotaCreate(BaseModel):
    cliente: Optional[ClienteCreate] = Field(default=None, description="Si se envía, crea cliente al vuelo")
    cliente_id: Optional[str] = Field(default=None, description="o usa id existente")
    vendedor_id: Optional[str] = Field(default=None)
    codigo_barras: Optional[str] = Field(default=None, example="NV-20250920-AB12", description="Si vacío, genera NV-YYYYMMDD-XXXX")
    items: List[NotaItem] = Field(..., min_length=1)

class NotaResponse(BaseModel):
    id: str
    cliente_id: Optional[str] = None
    vendedor_id: Optional[str] = None
    codigo_barras: str
    total: float
    created_at: datetime
    detalles: Optional[List[dict]] = None
    class Config:
        from_attributes = True

# ---------- TRANSACCIONES (KARDEX) ----------
class TipoTransaccion(str, Enum):
    entrada = "entrada"
    salida = "salida"
    ajuste = "ajuste"

class TransaccionBase(BaseModel):
    variante_id: str = Field(..., description="UUID variante")
    tipo: TipoTransaccion = Field(..., example="salida")
    cantidad: int = Field(..., gt=0, example=2)
    precio_unitario: float = Field(..., ge=0, example=59.90)
    stock_anterior: int = Field(..., ge=0, example=25, description="Debe coincidir con stock_actual actual")
    stock_nuevo: int = Field(..., ge=0, example=23, description="Para entrada/salida se valida; para ajuste es el stock final deseado")
    motivo: Optional[str] = Field(default=None, max_length=100, example="venta POS")
    referencia: Optional[str] = Field(default=None, max_length=150, example="TICKET POS-889")
    notas: Optional[str] = None

class TransaccionCreate(TransaccionBase):
    pass

class TransaccionResponse(TransaccionBase):
    id: str
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
