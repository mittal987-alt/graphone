import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipelines.phase2 import ingest_jobs, ingest_news
from src.storage.database import init_db, session_factory
from src.utils.observability import configure_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    configure_logging("INFO")
    await init_db()
    now = datetime.now(UTC)
    print(f"Starting Phase 2 Ingestion (24-hour freshness cutoff: {now.isoformat()})...")

    async with session_factory() as session:
        news_count = await ingest_news(session, now=now)
        jobs_count = await ingest_jobs(session, now=now)

    print(
        f"Phase 2 complete: news_articles={news_count}, "
        f"jobs={jobs_count} (ingested within last 24h)"
    )


if __name__ == "__main__":
    asyncio.run(main())
