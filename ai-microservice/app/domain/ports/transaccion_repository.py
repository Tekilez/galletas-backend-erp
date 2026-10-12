from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class TransaccionRepositoryPort(ABC):
    @abstractmethod
    def list(self, variante_id: Optional[str], tipo: Optional[str], referencia: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def list_kardex_detalle(self, variante_id: Optional[str], producto_id: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_by_id(self, transaccion_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ...
