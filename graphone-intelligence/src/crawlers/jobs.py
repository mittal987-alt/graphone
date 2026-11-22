from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import aiohttp

JOB_SOURCES = {
    "Greenhouse - OpenAI": "https://boards-api.greenhouse.io/v1/boards/openai/jobs?content=true",
    "Lever - Anthropic": "https://api.lever.co/v0/postings/anthropic?mode=json",
    "Greenhouse - DeepMind": "https://boards-api.greenhouse.io/v1/boards/deepmind/jobs?content=true",
    "Lever - Scale AI": "https://api.lever.co/v0/postings/scaleai?mode=json",
    "Greenhouse - Cohere": "https://boards-api.greenhouse.io/v1/boards/cohere/jobs?content=true",
}


class AtsJobCrawler:
    name = "ATS Jobs"

    def __init__(self, sources: dict[str, str] | None = None):
        self.sources = sources or JOB_SOURCES

    async def crawl(self) -> AsyncIterator[dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            for source_name, api_url in self.sources.items():
                async with session.get(api_url) as response:
                    if response.status in (401, 403, 429):
                        yield {
                            "_blocking": True,
                            "_source": source_name,
                            "_status": str(response.status),
                        }
                        continue
                    if response.status >= 400:
                        continue
                    payload = await response.json()

                if "greenhouse" in api_url:
                    for job in payload.get("jobs", []):
                        location = job.get("location", {}).get("name")
                        published = job.get("first_published")
                        yield {
                            "company": source_name.split(" - ", 1)[-1],
                            "title": job.get("title"),
                            "role_family": None,
                            "location": location,
                            "is_remote": bool(
                                location and "remote" in location.lower()
                            ),
                            "published_value": published,
                            "source_url": job.get("absolute_url"),
                            "source_name": source_name,
                            "description": job.get("content"),
                            "last_modified_value": job.get("updated_at"),
                            "collected_at": datetime.now(UTC),
                            "raw_metadata": {
                                "api_url": api_url,
                                "job_id": job.get("id"),
                            },
                        }
                else:
                    for job in payload:
                        location = job.get("categories", {}).get("location")
                        hosted_url = job.get("hostedUrl")
                        date_ms = job.get("createdAt")
                        published = (
                            datetime.fromtimestamp(date_ms / 1000, tz=UTC).isoformat()
                            if isinstance(date_ms, int | float)
                            else None
                        )
                        yield {
                            "company": source_name.split(" - ", 1)[-1],
                            "title": job.get("text"),
                            "role_family": job.get("categories", {}).get("commitment"),
                            "location": location,
                            "is_remote": bool(
                                location and "remote" in location.lower()
                            ),
                            "published_value": published,
                            "source_url": hosted_url,
                            "source_name": source_name,
                            "description": job.get("description"),
                            "last_modified_value": published,
                            "collected_at": datetime.now(UTC),
                            "raw_metadata": {
                                "api_url": api_url,
                                "job_id": job.get("id"),
                            },
                        }
