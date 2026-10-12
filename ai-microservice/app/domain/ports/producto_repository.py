from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class ProductoRepositoryPort(ABC):
    """Port para persistencia de productos."""

    @abstractmethod
    def list(self, categoria: Optional[str], activo: Optional[bool], search: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_by_id(self, producto_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def update(self, producto_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def delete(self, producto_id: str) -> None:
        ...

    @abstractmethod
    def list_variantes(self, producto_id: str) -> List[Dict[str, Any]]:
        ...
