from urllib.parse import parse_qs, urlparse

import pytest

from src.crawlers.research import ArxivCrawler

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>https://arxiv.org/abs/2601.12345v1</id>
    <updated>2026-11-21T00:00:00Z</updated>
    <published>2026-11-20T00:00:00Z</published>
    <title>Verified AI Research</title>
    <summary>Repository: https://github.com/example/research-code</summary>
    <author><name>Researcher</name></author>
    <link href="https://arxiv.org/abs/2601.12345v1" rel="alternate"
          type="text/html"/>
    <category term="cs.AI"/>
  </entry>
</feed>
"""


class FakeResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    def raise_for_status(self):
        return None

    async def text(self):
        return FEED


class FakeSession:
    def __init__(self):
        self.urls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    def get(self, url):
        self.urls.append(url)
        return FakeResponse()


@pytest.mark.asyncio
async def test_arxiv_query_is_bounded_and_rate_spaced(monkeypatch):
    session = FakeSession()
    delays = []

    async def fake_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr(
        "src.crawlers.research.aiohttp.ClientSession",
        lambda **kwargs: session,
    )
    monkeypatch.setattr("src.crawlers.research.asyncio.sleep", fake_sleep)
    crawler = ArxivCrawler(categories=("cs.AI", "cs.LG"), max_results=250)

    records = [record async for record in crawler.crawl()]

    assert len(records) == 2
    assert records[0]["github_url"] == "https://github.com/example/research-code"
    assert delays == [3]
    queries = [parse_qs(urlparse(url).query) for url in session.urls]
    assert [query["start"][0] for query in queries] == ["0", "200"]
    assert [query["max_results"][0] for query in queries] == ["200", "50"]
    assert queries[0]["search_query"] == ["cat:cs.AI OR cat:cs.LG"]


def test_arxiv_crawler_rejects_invalid_limits():
    with pytest.raises(ValueError, match="must not be negative"):
        ArxivCrawler(max_results=-1)
