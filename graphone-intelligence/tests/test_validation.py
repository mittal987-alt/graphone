from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.exporters.records import (
    JobExport,
    NewsExport,
    ProductExport,
    ResearchExport,
    StartupExport,
)


def test_startup_export_rejects_naive_timestamp():
    try:
        StartupExport(
            source={"name": "Fixture", "url": "https://fixture.example/startup"},
            entityName="Fixture AI",
            employeeCount=None,
            collectedAt=datetime(2026, 11, 21, 10, 0),
        )
    except ValidationError:
        assert True
    else:
        assert False


def test_product_export_preserves_unknown_pricing():
    record = ProductExport(
        source={"name": "Fixture", "url": "https://fixture.example/product"},
        entityName="Fixture Product",
        startupName=None,
        pricingModel="UNKNOWN",
        collectedAt=datetime.now(UTC),
    )
    assert record.pricingModel.value == "UNKNOWN"


def test_research_export_accepts_null_github_data():
    record = ResearchExport(
        title="Fixture Paper",
        authors=[],
        paperUrl="https://arxiv.org/abs/1234",
        githubUrl=None,
        githubStars=None,
        publishedDate=datetime.now(UTC) - timedelta(days=1),
        collectedAt=datetime.now(UTC),
    )
    assert record.githubUrl is None
    assert record.githubStars is None


def test_job_export_normalizes_timestamp_to_utc():
    record = JobExport(
        company="Fixture",
        title="AI Engineer",
        date="2026-11-21T10:00:00+05:30",
        isRemote=True,
        roleFamily="Engineering",
        sourceUrl="https://jobs.fixture.example/1",
        sourceName="Fixture Jobs",
    )
    assert record.date.isoformat() == "2026-11-21T04:30:00+00:00"


def test_news_export_requires_verified_publication_timestamp():
    record = NewsExport(
        title="Fixture News",
        publisher="Fixture Publisher",
        url="https://news.fixture.example/article",
        publicationDate=datetime.now(UTC),
        collectedAt=datetime.now(UTC),
    )
    assert record.publicationDate.tzinfo is not None


@pytest.mark.parametrize(
    "url",
    [
        "ftp://fixture.example/file",
        "http://localhost/article",
        "http://127.0.0.1/article",
    ],
)
def test_export_source_rejects_invalid_urls(url):
    with pytest.raises(ValidationError):
        from src.exporters.records import ExportSource

        ExportSource(name="Invalid", url=url)
