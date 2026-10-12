from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class DevolucionRepositoryPort(ABC):
    @abstractmethod
    def list(self, nota_codigo: Optional[str], q: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_by_codigo(self, codigo: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def create(self, nota_codigo: str, items: List[Dict[str, Any]], motivo_general: Optional[str], created_by: Optional[str]) -> Dict[str, Any]:
        ...
