import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.pipelines.phase1 import ingest_research
from src.storage.models import Base, GitHubRepository, ResearchPaper


class FixtureArxivCrawler:
    def __init__(self, max_results):
        self.records = [
            {
                "title": f"Paper {index}",
                "authors": ["Researcher"],
                "abstract": "Verified abstract",
                "published_date": datetime.now(UTC),
                "paper_url": f"https://arxiv.org/abs/{uuid.uuid4()}",
                "github_url": "https://github.com/example/research-code",
                "source_name": "arXiv",
                "collected_at": datetime.now(UTC),
                "raw_metadata": {"arxiv_id": str(index)},
            }
            for index in range(2)
        ]

    async def crawl(self):
        for record in self.records:
            yield record


@pytest.mark.asyncio
async def test_research_import_defers_and_backfills_github_stars(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    crawler = FixtureArxivCrawler(max_results=2)
    metric_calls = []

    async def get_metrics(github_url, token, *, client):
        metric_calls.append((github_url, token))
        return "https://github.com/example/research-code", 15

    monkeypatch.setattr("src.pipelines.phase1.ArxivCrawler", lambda **kwargs: crawler)
    monkeypatch.setattr("src.pipelines.phase1.get_github_metrics", get_metrics)

    async with session_factory() as session:
        inserted = await ingest_research(session, max_results=2)
        assert inserted == 2
        assert metric_calls == []

        updated = await ingest_research(
            session,
            max_results=2,
            github_token="configured-test-token",
        )
        assert updated == 0
        assert len(metric_calls) == 1
        papers = (await session.scalars(select(ResearchPaper))).all()
        repositories = (await session.scalars(select(GitHubRepository))).all()

    assert all(paper.github_stars == 15 for paper in papers)
    assert len(repositories) == 1
    await engine.dispose()
