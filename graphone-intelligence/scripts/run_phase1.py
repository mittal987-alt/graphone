import asyncio

from src.config.settings import get_settings
from src.pipelines.phase1 import ingest_products, ingest_research, ingest_startups
from src.storage.database import init_db, session_factory


async def main() -> None:
    await init_db()
    settings = get_settings()
    async with session_factory() as session:
        startups = await ingest_startups(session)
        products = await ingest_products(session)
        papers = await ingest_research(session, github_token=settings.github_token)
    print(
        f"Phase 1 complete: startups={startups}, "
        f"products={products}, research_papers={papers}"
    )


if __name__ == "__main__":
    asyncio.run(main())
