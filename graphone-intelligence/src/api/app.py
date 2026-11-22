from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter

from fastapi import Depends, FastAPI
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.config.settings import get_settings
from src.exporters.google_sheets import GoogleSheetsExporter, GoogleSheetsService
from src.pipelines.phase1 import ingest_products, ingest_research, ingest_startups
from src.pipelines.phase2 import ingest_jobs, ingest_news
from src.storage.database import get_session, init_db
from src.storage.models import (
    CrawlCheckpoint,
    Entity,
    ExportCheckpoint,
    ExtractionTask,
    FailedTask,
    IngestionRun,
    Job,
    NewsArticle,
    Product,
    QuarantineRecord,
    ResearchPaper,
    Startup,
)
from src.utils.observability import (
    clear_observability_context,
    configure_logging,
    log_event,
    metrics,
    new_run_id,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(get_settings().log_level)
    await init_db()
    yield


app = FastAPI(title="GraphOne Intelligence", lifespan=lifespan)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    run_id = new_run_id()
    started = perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        log_event(
            20,
            "http_request",
            event="http_request",
            runId=run_id,
            statusCode=response.status_code if response else 500,
            durationMs=duration_ms,
            method=request.method,
            path=request.url.path,
        )
        clear_observability_context()


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    await session.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": "graphone-intelligence",
        "database": "configured",
    }


@app.get("/api/stats")
async def stats(session: AsyncSession = Depends(get_session)):
    extraction_completed = await session.scalar(
        select(func.count())
        .select_from(ExtractionTask)
        .where(ExtractionTask.status == "completed")
    )
    extraction_failed = await session.scalar(
        select(func.count())
        .select_from(ExtractionTask)
        .where(ExtractionTask.status == "failed")
    )
    failed_tasks = await session.scalar(select(func.count()).select_from(FailedTask))
    runs = await session.scalar(select(func.count()).select_from(IngestionRun))
    return {
        "startups": await session.scalar(select(func.count()).select_from(Startup)),
        "products": await session.scalar(select(func.count()).select_from(Product)),
        "research_papers": await session.scalar(
            select(func.count()).select_from(ResearchPaper)
        ),
        "news_articles": await session.scalar(
            select(func.count()).select_from(NewsArticle)
        ),
        "jobs": await session.scalar(select(func.count()).select_from(Job)),
        "quarantined": await session.scalar(
            select(func.count()).select_from(QuarantineRecord)
        ),
        "extraction": {
            "completed": extraction_completed or 0,
            "failed": extraction_failed or 0,
            "failed_tasks": failed_tasks or 0,
        },
        "ingestion_runs": runs or 0,
        "runtime": metrics.snapshot(),
    }


@app.post("/api/crawl/startups")
async def crawl_startups(session: AsyncSession = Depends(get_session)):
    inserted = await ingest_startups(session)
    return {"inserted": inserted, "status": "completed"}


@app.post("/api/crawl/products")
async def crawl_products(session: AsyncSession = Depends(get_session)):
    inserted = await ingest_products(session)
    return {"inserted": inserted, "status": "completed"}


@app.post("/api/crawl/research")
async def crawl_research(session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    inserted = await ingest_research(session, github_token=settings.github_token)
    return {"inserted": inserted, "status": "completed"}


@app.post("/api/crawl/news")
async def crawl_news(session: AsyncSession = Depends(get_session)):
    inserted = await ingest_news(session)
    return {"inserted": inserted, "status": "completed"}


@app.post("/api/crawl/jobs")
async def crawl_jobs(session: AsyncSession = Depends(get_session)):
    inserted = await ingest_jobs(session)
    return {"inserted": inserted, "status": "completed"}


@app.post("/api/pipeline/run")
async def run_pipeline(session: AsyncSession = Depends(get_session)):
    run = IngestionRun(
        pipeline_name="complete",
        status="running",
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.commit()
    news = await ingest_news(session)
    jobs = await ingest_jobs(session)
    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    run.inserted_count = news + jobs
    run.metrics = {
        "news": news,
        "jobs": jobs,
    }
    await session.commit()
    metrics.increment("pipeline_runs")
    metrics.increment("news_inserted", news)
    metrics.increment("jobs_inserted", jobs)
    return {
        "status": "completed",
        "inserted": {"news": news, "jobs": jobs},
    }


@app.get("/api/pipeline/status")
async def pipeline_status(session: AsyncSession = Depends(get_session)):
    running = await session.scalar(
        select(func.count())
        .select_from(ExtractionTask)
        .where(ExtractionTask.status == "running")
    )
    failed = await session.scalar(
        select(func.count())
        .select_from(ExtractionTask)
        .where(ExtractionTask.status == "failed")
    )
    return {"running": running or 0, "failed": failed or 0}


@app.get("/api/entities")
async def list_entities(session: AsyncSession = Depends(get_session)):
    entities = (await session.scalars(select(Entity).limit(500))).all()
    return [
        {
            "canonicalId": entity.canonical_id,
            "canonicalName": entity.canonical_name,
            "entityType": entity.entity_type,
        }
        for entity in entities
    ]


@app.get("/api/crawl/status")
async def crawl_status(session: AsyncSession = Depends(get_session)):
    checkpoints = (await session.scalars(select(CrawlCheckpoint))).all()
    return [
        {
            "sourceName": checkpoint.source_name,
            "blockingStatus": checkpoint.blocking_status,
            "lastCrawledAt": checkpoint.last_crawled_at,
            "lastSuccessAt": checkpoint.last_success_at,
            "metrics": checkpoint.raw_metadata,
        }
        for checkpoint in checkpoints
    ]


@app.get("/api/exports/status")
async def exports_status(session: AsyncSession = Depends(get_session)):
    checkpoints = (
        await session.scalars(
            select(ExportCheckpoint).order_by(ExportCheckpoint.tab_name)
        )
    ).all()
    return [
        {
            "tabName": checkpoint.tab_name,
            "status": checkpoint.status,
            "lastRecordId": checkpoint.last_record_id,
            "lastRowCount": checkpoint.last_row_count,
            "lastExportedAt": checkpoint.last_exported_at,
        }
        for checkpoint in checkpoints
    ]


@app.post("/api/exports/run")
async def run_exports(session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    if not settings.google_sheets_spreadsheet_id:
        return {"status": "not_configured", "inserted": {}}
    sheets = GoogleSheetsService(
        settings.google_sheets_spreadsheet_id,
        settings.google_application_credentials,
    )
    exporter = GoogleSheetsExporter(sheets=sheets)
    counts = await exporter.export_all(session)
    return {"status": "completed", "inserted": counts}
