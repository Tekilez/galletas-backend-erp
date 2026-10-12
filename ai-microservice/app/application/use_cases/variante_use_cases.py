"""Application - Casos de uso Variante."""
from typing import Optional
from fastapi import HTTPException
from app.domain.ports.variante_repository import VarianteRepositoryPort

class VarianteUseCases:
    def __init__(self, repo: VarianteRepositoryPort):
        self.repo = repo

    def list_variantes(self, producto_id: Optional[str], sku: Optional[str], talla: Optional[str], color: Optional[str], activo: Optional[bool], limit: int, offset: int, stock_critico: bool = False, categoria: Optional[str] = None):
        data = self.repo.list(producto_id, sku, talla, color, activo, limit, offset, categoria)
        if stock_critico:
            data = [v for v in data if v.get("stock_actual", 999) <= v.get("stock_minimo", 0)]
        return data

    def get_variante(self, variante_id: str):
        return self.repo.get_by_id(variante_id)

    def create_variante(self, data: dict):
        # Dominio: talla flexible 29 o M, ya normalizada en DB trigger
        # Validación extra: stock_actual >=0, ya en schema
        return self.repo.create(data)

    def update_variante(self, variante_id: str, data: dict):
        if "stock_actual" in data:
            raise HTTPException(status_code=400, detail="stock_actual no editable directo. Usa POST /transacciones con tipo entrada/salida/ajuste")
        return self.repo.update(variante_id, data)

    def delete_variante(self, variante_id: str):
        return self.repo.delete(variante_id)
