from datetime import UTC, datetime
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.crawlers.jobs import AtsJobCrawler
from src.crawlers.news import RssNewsCrawler
from src.processors.freshness import (
    content_hash,
    is_within_24_hours,
    parse_verified_datetime,
)
from src.resolution.resolver import EntityResolver
from src.storage.models import (
    CrawlCheckpoint,
    Job,
    NewsArticle,
    QuarantineRecord,
)


async def fetch_article_text(url: str) -> str | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status >= 400:
                    return None
                html = await response.text()
    except (aiohttp.ClientError, TimeoutError):
        return None

    soup = BeautifulSoup(html, "lxml")
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()
    paragraphs = [
        paragraph.get_text(" ", strip=True)
        for paragraph in soup.select("article p, main p")
        if paragraph.get_text(" ", strip=True)
    ]
    if not paragraphs:
        paragraphs = [
            paragraph.get_text(" ", strip=True)
            for paragraph in soup.find_all("p")
            if len(paragraph.get_text(" ", strip=True)) >= 40
        ]
    text = "\n".join(paragraphs).strip()
    return text or None


async def quarantine(
    session: AsyncSession,
    record_type: str,
    source_name: str,
    source_url: str | None,
    reason: str,
    raw_metadata: dict[str, Any],
) -> None:
    session.add(
        QuarantineRecord(
            record_type=record_type,
            source_name=source_name,
            source_url=source_url,
            reason=reason,
            collected_at=datetime.now(UTC),
            raw_metadata=raw_metadata,
        )
    )
    await session.commit()


async def update_checkpoint(
    session: AsyncSession,
    source_name: str,
    status: str | None = None,
) -> None:
    checkpoint = await session.scalar(
        select(CrawlCheckpoint).where(CrawlCheckpoint.source_name == source_name)
    )
    now = datetime.now(UTC)
    if checkpoint is None:
        checkpoint = CrawlCheckpoint(
            source_name=source_name,
            last_crawled_at=now,
            last_success_at=now if status is None else None,
            blocking_status=status,
            raw_metadata={
                "blocked_requests": 1 if status is not None else 0,
                "successful_crawls": 0 if status is not None else 1,
            },
        )
        session.add(checkpoint)
    else:
        checkpoint.last_crawled_at = now
        if status is None:
            checkpoint.last_success_at = now
        checkpoint.blocking_status = status
        metadata = dict(checkpoint.raw_metadata or {})
        if status is None:
            metadata["successful_crawls"] = metadata.get("successful_crawls", 0) + 1
        else:
            metadata["blocked_requests"] = metadata.get("blocked_requests", 0) + 1
        checkpoint.raw_metadata = metadata
    await session.commit()


async def ingest_news(session: AsyncSession, now: datetime | None = None) -> int:
    count = 0
    crawler = RssNewsCrawler()
    async for record in crawler.crawl():
        if record.get("_blocking"):
            await update_checkpoint(
                session,
                record["_source"],
                f"HTTP {record['_status']}",
            )
            continue

        source_name = record["publisher"]
        source_url = record["source_url"]
        published = parse_verified_datetime(record.get("publication_value"))
        if published is None:
            await quarantine(
                session,
                "NEWS",
                source_name,
                source_url,
                "Missing or unverifiable publication date",
                record["raw_metadata"],
            )
            await update_checkpoint(session, source_name)
            continue
        if not is_within_24_hours(published, now=now):
            await update_checkpoint(session, source_name)
            continue

        full_text = await fetch_article_text(source_url)
        hash_value = content_hash(record["title"], full_text or record.get("summary"))
        existing = await session.scalar(
            select(NewsArticle.id).where(
                (NewsArticle.source_url == source_url)
                | (NewsArticle.content_hash == hash_value)
            )
        )
        if existing:
            await update_checkpoint(session, source_name)
            continue

        last_modified = parse_verified_datetime(record.get("last_modified_value"))
        session.add(
            NewsArticle(
                title=record["title"] or "Untitled",
                publisher=source_name,
                source_url=source_url,
                publication_date=published,
                last_modified=last_modified,
                full_text=full_text,
                content_hash=hash_value,
                collected_at=record["collected_at"],
                raw_metadata=record["raw_metadata"],
            )
        )
        try:
            await session.commit()
            count += 1
        except IntegrityError:
            await session.rollback()
        await update_checkpoint(session, source_name)
    return count


async def ingest_jobs(session: AsyncSession, now: datetime | None = None) -> int:
    count = 0
    crawler = AtsJobCrawler()
    resolver = EntityResolver()
    async for record in crawler.crawl():
        if record.get("_blocking"):
            await update_checkpoint(
                session,
                record["_source"],
                f"HTTP {record['_status']}",
            )
            continue

        source_name = record["source_name"]
        source_url = record["source_url"]
        published = parse_verified_datetime(record.get("published_value"))
        if published is None:
            await quarantine(
                session,
                "JOB",
                source_name,
                source_url,
                "Missing or unverifiable publication date",
                record["raw_metadata"],
            )
            await update_checkpoint(session, source_name)
            continue
        if not is_within_24_hours(published, now=now):
            await update_checkpoint(session, source_name)
            continue
        if not source_url:
            await quarantine(
                session,
                "JOB",
                source_name,
                source_url,
                "Missing source URL",
                record["raw_metadata"],
            )
            await update_checkpoint(session, source_name)
            continue

        hash_value = content_hash(
            record["company"],
            record["title"],
            record.get("description"),
            source_url,
        )
        existing = await session.scalar(
            select(Job.id).where(
                (Job.source_url == source_url) | (Job.content_hash == hash_value)
            )
        )
        if existing:
            await update_checkpoint(session, source_name)
            continue

        last_modified = parse_verified_datetime(record.get("last_modified_value"))
        session.add(
            Job(
                company=record["company"],
                title=record["title"] or "Untitled",
                role_family=record.get("role_family"),
                location=record.get("location"),
                is_remote=record.get("is_remote"),
                published_at=published,
                last_modified=last_modified,
                source_url=source_url,
                source_name=source_name,
                description=record.get("description"),
                content_hash=hash_value,
                collected_at=record["collected_at"],
                raw_metadata=record["raw_metadata"],
            )
        )
        try:
            await session.commit()
            count += 1
        except IntegrityError:
            await session.rollback()
        else:
            resolution = resolver.resolve(record["company"], "STARTUP")
            await resolver.persist_resolution(
                session,
                record["company"],
                "STARTUP",
                source_url,
                resolution,
            )
        await update_checkpoint(session, source_name)
    return count
