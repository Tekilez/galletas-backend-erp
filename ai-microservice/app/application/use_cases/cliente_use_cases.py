"""Application - Cliente use cases."""
from typing import Optional
from app.domain.ports.cliente_repository import ClienteRepositoryPort

class ClienteUseCases:
    def __init__(self, repo: ClienteRepositoryPort):
        self.repo = repo

    def list(self, search: Optional[str], limit: int, offset: int):
        return self.repo.list(search, limit, offset)

    def get(self, cliente_id: str):
        return self.repo.get_by_id(cliente_id)

    def create(self, data: dict):
        if not data.get("nombre"):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="nombre requerido")
        return self.repo.create(data)

    def update(self, cliente_id: str, data: dict):
        return self.repo.update(cliente_id, data)

    def delete(self, cliente_id: str):
        return self.repo.delete(cliente_id)
