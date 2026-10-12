"""Entidad Cliente."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Cliente:
    id: str
    nombre: str
    dni: Optional[str]
    telefono: Optional[str]
    created_at: datetime
    updated_at: datetime
