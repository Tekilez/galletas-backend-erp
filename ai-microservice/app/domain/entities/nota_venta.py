"""Entidades NotaVenta + DetalleNota."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class DetalleNota:
    id: str
    nota_id: str
    variante_id: str
    cantidad: int
    precio_unitario: float
    created_at: datetime

@dataclass
class NotaVenta:
    id: str
    cliente_id: Optional[str]
    vendedor_id: Optional[str]
    codigo_barras: str  # NV-YYYYMMDD-XXXX
    total: float
    created_at: datetime
    # detalle cargado opcional
    detalles: Optional[List[DetalleNota]] = None
