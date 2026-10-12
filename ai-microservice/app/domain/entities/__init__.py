"""Entidades de dominio Kardex/POS."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Producto:
    id: str
    nombre: str
    descripcion: Optional[str]
    categoria: Optional[str]
    margen_ganancia: float
    activo: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class Variante:
    id: str
    producto_id: str
    sku: str
    talla: str  # flexible: 29, 32, S, M, L, XL, 2XL
    color: str
    stock_actual: int
    stock_minimo: int
    precio_costo: float
    precio_venta: float
    imagen_url: Optional[str]
    activo: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class Transaccion:
    id: str
    variante_id: str
    tipo: str  # entrada | salida | ajuste
    cantidad: int
    precio_unitario: float
    stock_anterior: int
    stock_nuevo: int
    motivo: Optional[str]
    referencia: Optional[str]
    notas: Optional[str]
    created_by: Optional[str]
    created_at: datetime
