"""Application - Devolucion use cases."""
from typing import Optional, List
from app.domain.ports.devolucion_repository import DevolucionRepositoryPort

class DevolucionUseCases:
    def __init__(self, repo: DevolucionRepositoryPort):
        self.repo = repo

    def list(self, nota_codigo: Optional[str], q: Optional[str], limit: int, offset: int):
        return self.repo.list(nota_codigo, q, limit, offset)

    def get(self, codigo: str):
        return self.repo.get_by_codigo(codigo)

    def create(self, nota_codigo: str, items: List[dict], motivo_general: Optional[str], created_by: Optional[str] = None):
        if not nota_codigo:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="nota_codigo requerido")
        if not items:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="items requerido")
        return self.repo.create(nota_codigo, items, motivo_general, created_by)
