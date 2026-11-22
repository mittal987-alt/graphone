from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import aiohttp
import feedparser

NEWS_SOURCES = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "The Decoder": "https://the-decoder.com/feed/",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
}


class RssNewsCrawler:
    name = "RSS News"

    def __init__(self, sources: dict[str, str] | None = None):
        self.sources = sources or NEWS_SOURCES

    async def crawl(self) -> AsyncIterator[dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            for publisher, feed_url in self.sources.items():
                async with session.get(feed_url) as response:
                    if response.status in (401, 403, 429):
                        yield {
                            "_blocking": True,
                            "_source": publisher,
                            "_status": str(response.status),
                        }
                        continue
                    if response.status >= 400:
                        continue
                    feed = feedparser.parse(await response.text())

                for entry in feed.entries:
                    link = entry.get("link")
                    if not link:
                        continue
                    yield {
                        "title": entry.get("title"),
                        "publisher": publisher,
                        "source_url": link,
                        "publication_value": entry.get("published")
                        or entry.get("date"),
                        "summary": entry.get("summary"),
                        "last_modified_value": entry.get("updated"),
                        "collected_at": datetime.now(UTC),
                        "raw_metadata": {
                            "feed_url": feed_url,
                            "entry_id": entry.get("id"),
                        },
                    }
