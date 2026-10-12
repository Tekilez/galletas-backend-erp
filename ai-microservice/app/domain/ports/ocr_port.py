from abc import ABC, abstractmethod
from typing import Tuple, List, Dict

class OcrPort(ABC):
    """Port para OCR de boletas. Retorna (raw_text, items, provider, elapsed_ms)."""
    @abstractmethod
    async def extract(self, file) -> Tuple[str, List[Dict], str, int]:
        ...

    @abstractmethod
    async def validate(self, file) -> None:
        ...
