from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class ClienteRepositoryPort(ABC):
    @abstractmethod
    def list(self, search: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_by_id(self, cliente_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def update(self, cliente_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def delete(self, cliente_id: str) -> None:
        ...
