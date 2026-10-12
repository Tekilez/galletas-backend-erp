"""Application - Casos de uso Producto (orquesta domain + ports)."""
from typing import Optional
from app.domain.ports.producto_repository import ProductoRepositoryPort

class ProductoUseCases:
    def __init__(self, repo: ProductoRepositoryPort):
        self.repo = repo

    def list_productos(self, categoria: Optional[str], activo: Optional[bool], search: Optional[str], limit: int, offset: int):
        return self.repo.list(categoria, activo, search, limit, offset)

    def get_producto(self, producto_id: str):
        return self.repo.get_by_id(producto_id)

    def create_producto(self, data: dict):
        # Regla dominio: nombre no vacío, margen ya validado por Pydantic
        return self.repo.create(data)

    def update_producto(self, producto_id: str, data: dict):
        return self.repo.update(producto_id, data)

    def delete_producto(self, producto_id: str):
        return self.repo.delete(producto_id)

    def list_variantes_de_producto(self, producto_id: str):
        # valida que producto exista? repo variante lo hace; aquí delega
        return self.repo.list_variantes(producto_id)
