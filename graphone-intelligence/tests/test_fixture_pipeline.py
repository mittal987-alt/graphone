import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.exporters.records import JobExport
from src.processors.freshness import (
    content_hash,
    is_within_24_hours,
    parse_verified_datetime,
)
from src.storage.database import init_db, session_factory
from src.storage.models import Job


@pytest.mark.asyncio
async def test_fixture_job_pipeline_and_deduplication():
    fixture = json.loads(
        Path(__file__)
        .parent.joinpath("fixtures", "job.json")
        .read_text(encoding="utf-8")
    )
    job = fixture["jobs"][0]
    source_url = f"https://jobs.fixture.example/ai-engineer-{uuid.uuid4()}"
    job["absolute_url"] = source_url
    published = parse_verified_datetime(job["updated_at"])
    assert published is not None
    assert is_within_24_hours(published, now=datetime(2026, 11, 22, 13, 0, tzinfo=UTC))

    export = JobExport(
        company="Fixture",
        title=job["title"],
        date=published,
        isRemote=True,
        roleFamily=None,
        sourceUrl=job["absolute_url"],
        sourceName="Fixture ATS",
    )
    assert export.sourceUrl.host == "jobs.fixture.example"

    await init_db()
    hash_value = content_hash(
        "Fixture",
        job["title"],
        job["content"],
        job["absolute_url"],
    )
    async with session_factory() as session:
        record = Job(
            company="Fixture",
            title=job["title"],
            location="Remote",
            is_remote=True,
            published_at=published,
            source_url=job["absolute_url"],
            source_name="Fixture ATS",
            description=job["content"],
            content_hash=hash_value,
            collected_at=datetime.now(UTC),
        )
        session.add(record)
        await session.commit()

        duplicate = Job(
            company="Fixture",
            title=job["title"],
            published_at=published,
            source_url=job["absolute_url"],
            source_name="Fixture ATS",
            content_hash=hash_value,
            collected_at=datetime.now(UTC),
        )
        session.add(duplicate)
        try:
            await session.commit()
        except Exception:
            await session.rollback()
        else:
            pytest.fail("Duplicate source URL should be rejected")
