from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from src.storage.database import init_db, session_factory
from src.storage.models import CrawlTask, IngestionRun


@pytest.mark.asyncio
async def test_ingestion_run_persists():
    await init_db()
    async with session_factory() as session:
        run = IngestionRun(
            pipeline_name="phase6-fixture",
            status="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            inserted_count=3,
            quarantined_count=1,
        )
        session.add(run)
        await session.commit()
        persisted = await session.scalar(
            select(IngestionRun).where(IngestionRun.id == run.id)
        )
        assert persisted is not None
        assert persisted.inserted_count == 3


@pytest.mark.asyncio
async def test_crawl_task_tracks_retry_and_status():
    await init_db()
    async with session_factory() as session:
        task = CrawlTask(
            source_name="Fixture Source",
            task_type="NEWS",
            status="pending",
            retry_count=2,
            scheduled_at=datetime.now(UTC),
        )
        session.add(task)
        await session.commit()
        persisted = await session.scalar(
            select(CrawlTask).where(CrawlTask.id == task.id)
        )
        assert persisted is not None
        assert persisted.retry_count == 2
