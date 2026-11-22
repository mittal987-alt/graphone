import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from src.crawlers.base import SourceAdapter
from src.utils.http import AsyncHttpClient


class HuggingFaceOrganizationsCrawler(SourceAdapter):
    name = "Hugging Face Organizations"

    def __init__(self, concurrency: int = 8, max_pages: int = 100):
        self.client = AsyncHttpClient(concurrency=concurrency)
        self.max_pages = max_pages

    async def crawl(self) -> AsyncIterator[dict[str, Any]]:
        for page in range(1, self.max_pages + 1):
            payload = await self.client.get_json(
                "https://huggingface.co/api/organizations",
                params={"page": page, "limit": 100},
            )
            if not payload:
                return
            for item in payload:
                website = item.get("website")
                yield {
                    "entityName": item.get("fullname") or item.get("name"),
                    "website": website,
                    "description": item.get("description"),
                    "industry": "Artificial Intelligence",
                    "employeeCount": None,
                    "sourceName": self.name,
                    "sourceUrl": f"https://huggingface.co/{quote(str(item['name']))}",
                    "collectedAt": datetime.now(UTC),
                }
            await asyncio.sleep(0.1)


class HuggingFaceSpacesCrawler(SourceAdapter):
    name = "Hugging Face Spaces"

    def __init__(self, concurrency: int = 8, max_pages: int = 100):
        self.client = AsyncHttpClient(concurrency=concurrency)
        self.max_pages = max_pages

    async def crawl(self) -> AsyncIterator[dict[str, Any]]:
        for page in range(1, self.max_pages + 1):
            payload = await self.client.get_json(
                "https://huggingface.co/api/spaces",
                params={"p": page, "limit": 100},
            )
            if not payload:
                return
            for item in payload:
                name = item.get("name")
                if not name:
                    continue
                yield {
                    "name": item.get("title") or name.rsplit("/", 1)[-1],
                    "description": item.get("cardData", {}).get("description")
                    if isinstance(item.get("cardData"), dict)
                    else None,
                    "website": f"https://huggingface.co/spaces/{name}",
                    "startupName": name.split("/", 1)[0],
                    "pricingModel": "UNKNOWN",
                    "sourceName": self.name,
                    "sourceUrl": f"https://huggingface.co/spaces/{name}",
                    "collectedAt": datetime.now(UTC),
                }
            await asyncio.sleep(0.1)
