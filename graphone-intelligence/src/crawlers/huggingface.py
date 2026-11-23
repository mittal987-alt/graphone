import asyncio
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import aiohttp

from src.crawlers.base import SourceAdapter
from src.utils.http import AsyncHttpClient

NEXT_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


class HuggingFaceOrganizationsCrawler(SourceAdapter):
    name = "Hugging Face Organizations"

    def __init__(self, concurrency: int = 8, max_pages: int = 100):
        self.client = AsyncHttpClient(concurrency=concurrency)
        self.max_pages = max_pages

    async def crawl(self) -> AsyncIterator[dict[str, Any]]:
        yielded_count = 0
        seen_entities: set[str] = set()

        # 1. Attempt official organization API first
        try:
            for page in range(1, 5):
                payload = await self.client.get_json(
                    "https://huggingface.co/api/organizations",
                    params={"page": page, "limit": 100},
                )
                if not payload or not isinstance(payload, list):
                    break
                for item in payload:
                    raw_name = str(item.get("name") or "")
                    if not raw_name or raw_name in seen_entities:
                        continue
                    seen_entities.add(raw_name)
                    yielded_count += 1
                    yield {
                        "entityName": item.get("fullname") or raw_name,
                        "website": item.get("website")
                        or f"https://huggingface.co/{quote(raw_name)}",
                        "description": item.get("description"),
                        "industry": "Artificial Intelligence",
                        "employeeCount": None,
                        "sourceName": self.name,
                        "sourceUrl": f"https://huggingface.co/{quote(raw_name)}",
                        "collectedAt": datetime.now(UTC),
                    }
                await asyncio.sleep(0.1)
        except Exception:
            pass

        # 2. Extract organizations/creators from models and spaces directory via cursor pagination
        endpoints = [
            "https://huggingface.co/api/models?limit=100",
            "https://huggingface.co/api/spaces?limit=100",
        ]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        for base_url in endpoints:
            current_url: str | None = base_url
            pages_read = 0
            async with aiohttp.ClientSession() as session:
                while current_url and pages_read < self.max_pages:
                    pages_read += 1
                    try:
                        async with session.get(current_url, headers=headers) as resp:
                            if resp.status >= 400:
                                break
                            items = await resp.json()
                            link_header = resp.headers.get("Link", "")
                            match = NEXT_LINK_RE.search(link_header)
                            current_url = match.group(1) if match else None

                            if not isinstance(items, list):
                                break

                            for item in items:
                                item_id = item.get("id") or ""
                                if "/" not in item_id:
                                    continue
                                author = item_id.split("/", 1)[0].strip()
                                if not author or author in seen_entities:
                                    continue
                                seen_entities.add(author)
                                yielded_count += 1
                                yield {
                                    "entityName": author,
                                    "website": f"https://huggingface.co/{quote(author)}",
                                    "description": f"AI creator and developer on Hugging Face: {author}",
                                    "industry": "Artificial Intelligence",
                                    "employeeCount": None,
                                    "sourceName": self.name,
                                    "sourceUrl": f"https://huggingface.co/{quote(author)}",
                                    "collectedAt": datetime.now(UTC),
                                }
                    except Exception:
                        break
                    await asyncio.sleep(0.05)


class HuggingFaceSpacesCrawler(SourceAdapter):
    name = "Hugging Face Spaces"

    def __init__(self, concurrency: int = 8, max_pages: int = 100):
        self.client = AsyncHttpClient(concurrency=concurrency)
        self.max_pages = max_pages

    async def crawl(self) -> AsyncIterator[dict[str, Any]]:
        current_url: str | None = "https://huggingface.co/api/spaces?limit=100"
        pages_read = 0
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        async with aiohttp.ClientSession() as session:
            while current_url and pages_read < self.max_pages:
                pages_read += 1
                try:
                    async with session.get(current_url, headers=headers) as resp:
                        if resp.status >= 400:
                            break
                        items = await resp.json()
                        link_header = resp.headers.get("Link", "")
                        match = NEXT_LINK_RE.search(link_header)
                        current_url = match.group(1) if match else None

                        if not isinstance(items, list):
                            break

                        for item in items:
                            name = item.get("id") or item.get("name")
                            if not name:
                                continue
                            startup = name.split("/", 1)[0] if "/" in name else None
                            yield {
                                "name": item.get("title") or name.rsplit("/", 1)[-1],
                                "description": item.get("cardData", {}).get(
                                    "description"
                                )
                                if isinstance(item.get("cardData"), dict)
                                else None,
                                "website": f"https://huggingface.co/spaces/{name}",
                                "startupName": startup,
                                "pricingModel": "UNKNOWN",
                                "sourceName": self.name,
                                "sourceUrl": f"https://huggingface.co/spaces/{name}",
                                "collectedAt": datetime.now(UTC),
                            }
                except Exception:
                    break
                await asyncio.sleep(0.05)
