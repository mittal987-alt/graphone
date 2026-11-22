from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    async def crawl(self) -> AsyncIterator[dict[str, Any]]:
        """Yield source records with traceable source URLs."""
