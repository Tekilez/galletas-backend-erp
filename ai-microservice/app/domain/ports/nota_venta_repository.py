from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class NotaVentaRepositoryPort(ABC):
    @abstractmethod
    def list(self, cliente_id: Optional[str], vendedor_id: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_by_id(self, nota_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_with_detalle(self, nota_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def create_nota(self, cliente_id: Optional[str], vendedor_id: Optional[str], codigo_barras: str, total: float, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Crea nota + detalle + dispara transacciones salida. Implementación debe ser atómica."""
        ...

    @abstractmethod
    def delete(self, nota_id: str) -> None:
        ...
