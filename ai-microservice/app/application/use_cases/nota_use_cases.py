"""Application - NotaVenta use cases (vendedor)."""
from typing import Optional, List
from app.domain.ports.nota_venta_repository import NotaVentaRepositoryPort

class NotaUseCases:
    def __init__(self, repo: NotaVentaRepositoryPort):
        self.repo = repo

    def list(self, cliente_id: Optional[str], vendedor_id: Optional[str], limit: int, offset: int):
        return self.repo.list(cliente_id, vendedor_id, limit, offset)

    def get(self, nota_id: str):
        return self.repo.get_by_id(nota_id)

    def get_detalle(self, nota_id: str):
        return self.repo.get_with_detalle(nota_id)

    def create(self, cliente_id: Optional[str], vendedor_id: Optional[str], codigo_barras: Optional[str], items: List[dict]):
        if not items:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="items requerido")
        # total = sum cantidad*precio
        total = round(sum(float(it["precio_unitario"]) * int(it["cantidad"]) for it in items), 2)
        codigo = codigo_barras or ""
        return self.repo.create_nota(cliente_id, vendedor_id, codigo, total, items)

    def delete(self, nota_id: str):
        return self.repo.delete(nota_id)
