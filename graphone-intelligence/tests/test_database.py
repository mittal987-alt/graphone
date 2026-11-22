import pytest
from sqlalchemy import select

from src.storage.database import init_db, session_factory
from src.storage.models import Startup


@pytest.mark.asyncio
async def test_duplicate_startup_source_is_prevented():
    await init_db()
    source_url = (
        f"https://fixture.example/startups/example-ai-{__import__('uuid').uuid4()}"
    )
    async with session_factory() as session:
        session.add(
            Startup(
                entity_name="Example AI",
                website="https://example.com",
                source_name="Fixture",
                source_url=source_url,
                collected_at=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ),
            )
        )
        await session.commit()

        duplicate = await session.scalar(
            select(Startup.id).where(Startup.source_url == source_url)
        )
        assert duplicate is not None
