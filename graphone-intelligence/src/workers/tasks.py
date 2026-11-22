import asyncio

from src.pipelines.phase1 import ingest_products, ingest_research, ingest_startups
from src.pipelines.phase2 import ingest_jobs, ingest_news
from src.storage.database import init_db, session_factory
from src.workers.celery_app import celery_app


def run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="graphone.crawl.startups")
def crawl_startups() -> dict[str, int]:
    async def operation():
        await init_db()
        async with session_factory() as session:
            return {"inserted": await ingest_startups(session)}

    return run_async(operation())


@celery_app.task(name="graphone.crawl.products")
def crawl_products() -> dict[str, int]:
    async def operation():
        await init_db()
        async with session_factory() as session:
            return {"inserted": await ingest_products(session)}

    return run_async(operation())


@celery_app.task(name="graphone.crawl.research")
def crawl_research() -> dict[str, int]:
    async def operation():
        await init_db()
        async with session_factory() as session:
            return {"inserted": await ingest_research(session)}

    return run_async(operation())


@celery_app.task(name="graphone.crawl.news")
def crawl_news() -> dict[str, int]:
    async def operation():
        await init_db()
        async with session_factory() as session:
            return {"inserted": await ingest_news(session)}

    return run_async(operation())


@celery_app.task(name="graphone.crawl.jobs")
def crawl_jobs() -> dict[str, int]:
    async def operation():
        await init_db()
        async with session_factory() as session:
            return {"inserted": await ingest_jobs(session)}

    return run_async(operation())
