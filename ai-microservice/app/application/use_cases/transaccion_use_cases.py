"""Application - Casos de uso Transaccion/Kardex (inmutable)."""
from typing import Optional
from app.domain.ports.transaccion_repository import TransaccionRepositoryPort

class TransaccionUseCases:
    def __init__(self, repo: TransaccionRepositoryPort):
        self.repo = repo

    def list_transacciones(self, variante_id: Optional[str], tipo: Optional[str], referencia: Optional[str], limit: int, offset: int):
        return self.repo.list(variante_id, tipo, referencia, limit, offset)

    def list_kardex_detalle(self, variante_id: Optional[str], producto_id: Optional[str], limit: int, offset: int):
        return self.repo.list_kardex_detalle(variante_id, producto_id, limit, offset)

    def get_transaccion(self, transaccion_id: str):
        return self.repo.get_by_id(transaccion_id)

    def create_transaccion(self, data: dict):
        # Regla dominio: stock_nuevo coherente ya validado en adapter, pero también aquí
        return self.repo.create(data)
