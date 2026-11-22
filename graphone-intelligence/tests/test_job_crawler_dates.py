import asyncio

import pytest

from src.crawlers.jobs import AtsJobCrawler


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    def get(self, url):
        return FakeResponse(self.payload)


@pytest.mark.parametrize(
    ("job", "expected_published"),
    [
        ({"updated_at": "2026-11-22T10:00:00Z"}, None),
        (
            {
                "first_published": "2026-11-21T10:00:00Z",
                "updated_at": "2026-11-22T10:00:00Z",
            },
            "2026-11-21T10:00:00Z",
        ),
    ],
)
def test_greenhouse_uses_first_publication_not_updated_at(
    monkeypatch, job, expected_published
):
    job = {
        "id": 123,
        "title": "AI Engineer",
        "absolute_url": "https://boards.greenhouse.io/example/jobs/123",
        "location": {"name": "Remote"},
        **job,
    }
    monkeypatch.setattr(
        "src.crawlers.jobs.aiohttp.ClientSession",
        lambda: FakeSession({"jobs": [job]}),
    )
    crawler = AtsJobCrawler(
        sources={
            "Greenhouse - Example": (
                "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true"
            )
        }
    )

    async def get_record():
        return [record async for record in crawler.crawl()][0]

    record = asyncio.run(get_record())

    assert record["published_value"] == expected_published
    assert record["last_modified_value"] == job.get("updated_at")
