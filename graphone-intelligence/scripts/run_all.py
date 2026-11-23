import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import get_settings
from src.pipelines.phase1 import ingest_products, ingest_research, ingest_startups
from src.pipelines.phase2 import ingest_jobs, ingest_news
from src.storage.database import init_db, session_factory
from src.utils.observability import configure_logging

logger = logging.getLogger(__name__)


async def run_all() -> None:
    configure_logging("INFO")
    await init_db()
    settings = get_settings()
    now = datetime.now(UTC)

    print("==================================================")
    print(" GraphOne Intelligence - Master Ingestion Runner  ")
    print("==================================================")

    async with session_factory() as session:
        # 1. Phase 1
        print("\n[Phase 1] Ingesting Startups...")
        startups = await ingest_startups(session)
        print(f"  -> Ingested {startups} startups")

        print("\n[Phase 1] Ingesting Products...")
        products = await ingest_products(session)
        print(f"  -> Ingested {products} products")

        print("\n[Phase 1] Ingesting Research Papers...")
        papers = await ingest_research(session, github_token=settings.github_token)
        print(f"  -> Ingested {papers} research papers")

        # 2. Phase 2
        print(f"\n[Phase 2] Ingesting News (24h cutoff: {now.isoformat()})...")
        news = await ingest_news(session, now=now)
        print(f"  -> Ingested {news} news articles")

        print(f"\n[Phase 2] Ingesting Jobs (24h cutoff: {now.isoformat()})...")
        jobs = await ingest_jobs(session, now=now)
        print(f"  -> Ingested {jobs} fresh jobs")

    print("\n==================================================")
    print(" Pipeline Execution Complete!                     ")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_all())
