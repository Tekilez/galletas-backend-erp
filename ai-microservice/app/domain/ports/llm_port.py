from abc import ABC, abstractmethod
from typing import Tuple

class LlmPort(ABC):
    """Port para generación de insights."""
    @abstractmethod
    async def generate(self, payload) -> Tuple[str, str, str]:
        """Retorna (analisis, provider, model)."""
        ...
