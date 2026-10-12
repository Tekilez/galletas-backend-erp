"""Entidad Devolucion."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class Devolucion:
    id: str
    codigo: str  # DV-YYYYMMDD-XXXX
    nota_codigo: str  # FK notas_venta.codigo_barras
    cliente: Optional[Dict[str, Any]]
    motivo: Optional[str]
    items: List[Dict[str, Any]]  # [{variante_id,cantidad,motivo}]
    total_devuelto: float
    created_at: datetime
    created_by: Optional[str] = None
