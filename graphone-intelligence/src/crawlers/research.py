import asyncio
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import aiohttp
import feedparser
from dateutil import parser as date_parser

from src.crawlers.base import SourceAdapter
from src.utils.http import AsyncHttpClient

GITHUB_RE = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
ARXIV_REQUEST_INTERVAL_SECONDS = 3


class ArxivCrawler(SourceAdapter):
    name = "arXiv"

    def __init__(
        self,
        categories: tuple[str, ...] = ("cs.AI", "cs.LG", "cs.CL", "cs.CV"),
        max_results: int = 2000,
    ):
        if max_results < 0:
            raise ValueError("max_results must not be negative")
        if not categories:
            raise ValueError("at least one arXiv category is required")
        self.categories = categories
        self.max_results = max_results
        self.client = AsyncHttpClient()

    async def crawl(self) -> AsyncIterator[dict[str, Any]]:
        query = quote(
            " OR ".join(f"cat:{category}" for category in self.categories),
            safe="",
        )
        page_size = 200
        async with aiohttp.ClientSession(timeout=self.client.timeout) as session:
            for start in range(0, self.max_results, page_size):
                if start:
                    await asyncio.sleep(ARXIV_REQUEST_INTERVAL_SECONDS)
                result_count = min(page_size, self.max_results - start)
                url = (
                    "https://export.arxiv.org/api/query"
                    f"?search_query={query}&start={start}&max_results={result_count}"
                    "&sortBy=submittedDate&sortOrder=descending"
                )
                async with session.get(url) as response:
                    response.raise_for_status()
                    text = await response.text()
                feed = feedparser.parse(text)
                if not feed.entries:
                    break
                for entry in feed.entries:
                    paper_url = entry.get("link")
                    if not paper_url:
                        continue
                    combined = f"{entry.get('title', '')}\n{entry.get('summary', '')}"
                    github_match = GITHUB_RE.search(combined)
                    github_url = (
                        github_match.group(0).rstrip("),.") if github_match else None
                    )
                    published = entry.get("published")
                    published_date = None
                    if published:
                        try:
                            published_date = date_parser.parse(published).astimezone(
                                UTC
                            )
                        except (TypeError, ValueError):
                            published_date = None
                    yield {
                        "title": entry.get("title", "").strip().replace("\n", " "),
                        "authors": [author.name for author in entry.get("authors", [])],
                        "abstract": entry.get("summary"),
                        "published_date": published_date,
                        "paper_url": paper_url,
                        "github_url": github_url,
                        "github_stars": None,
                        "source_name": self.name,
                        "collected_at": datetime.now(UTC),
                        "raw_metadata": {
                            "arxiv_id": entry.get("id"),
                            "categories": entry.get("tags", []),
                        },
                    }
