from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class VarianteRepositoryPort(ABC):
    @abstractmethod
    def list(self, producto_id: Optional[str], sku: Optional[str], talla: Optional[str], color: Optional[str], activo: Optional[bool], limit: int, offset: int, categoria: Optional[str] = None) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_by_id(self, variante_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def update(self, variante_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def delete(self, variante_id: str) -> None:
        ...
