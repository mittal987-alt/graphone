import logging
from datetime import UTC, datetime

import aiohttp
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.crawlers.github import GITHUB_PATH_RE, get_github_metrics
from src.crawlers.huggingface import (
    HuggingFaceOrganizationsCrawler,
    HuggingFaceSpacesCrawler,
)
from src.crawlers.research import ArxivCrawler
from src.resolution.resolver import EntityResolver
from src.storage.models import (
    GitHubRepository,
    Product,
    ResearchPaper,
    Startup,
)
from src.utils.http import AsyncHttpClient

logger = logging.getLogger(__name__)


async def ingest_startups(session: AsyncSession, max_pages: int = 100) -> int:
    count = 0
    crawler = HuggingFaceOrganizationsCrawler(max_pages=max_pages)
    resolver = EntityResolver()
    async for record in crawler.crawl():
        name = record.get("entityName")
        source_url = record.get("sourceUrl")
        if not name or not source_url:
            continue
        existing = await session.scalar(
            select(Startup.id).where(Startup.source_url == source_url)
        )
        if existing:
            continue
        session.add(
            Startup(
                entity_name=name,
                website=record.get("website"),
                description=record.get("description"),
                industry=record.get("industry"),
                employee_count=record.get("employeeCount"),
                source_name=record["sourceName"],
                source_url=source_url,
                collected_at=record["collectedAt"],
                raw_metadata={"pipeline": "phase1_startups"},
            )
        )
        try:
            await session.commit()
            resolution = resolver.resolve(name, "STARTUP")
            await resolver.persist_resolution(
                session,
                name,
                "STARTUP",
                source_url,
                resolution,
            )
            count += 1
        except IntegrityError:
            await session.rollback()
    return count


async def ingest_products(session: AsyncSession, max_pages: int = 100) -> int:
    count = 0
    crawler = HuggingFaceSpacesCrawler(max_pages=max_pages)
    async for record in crawler.crawl():
        name = record.get("name")
        source_url = record.get("sourceUrl")
        if not name or not source_url:
            continue
        existing = await session.scalar(
            select(Product.id).where(Product.source_url == source_url)
        )
        if existing:
            continue
        session.add(
            Product(
                name=name,
                description=record.get("description"),
                website=record.get("website"),
                startup_name=record.get("startupName"),
                pricing_model=record["pricingModel"],
                source_name=record["sourceName"],
                source_url=source_url,
                collected_at=record["collectedAt"],
                raw_metadata={"pipeline": "phase1_products"},
            )
        )
        try:
            await session.commit()
            count += 1
        except IntegrityError:
            await session.rollback()
    return count


async def ingest_research(
    session: AsyncSession,
    max_results: int = 2000,
    github_token: str | None = None,
) -> int:
    count = 0
    crawler = ArxivCrawler(max_results=max_results)
    github_client = AsyncHttpClient(requests_per_second=1.0) if github_token else None
    github_metrics_cache: dict[str, tuple[str | None, int | None]] = {}
    if not github_token:
        logger.info("GitHub star enrichment deferred because GITHUB_TOKEN is unset")

    async for record in crawler.crawl():
        paper_url = record["paper_url"]
        paper = await session.scalar(
            select(ResearchPaper).where(ResearchPaper.paper_url == paper_url)
        )
        is_new = paper is None
        github_url = record["github_url"]
        if paper is None:
            paper = ResearchPaper(
                title=record["title"],
                authors=record["authors"],
                abstract=record["abstract"],
                published_date=record["published_date"],
                paper_url=paper_url,
                github_url=github_url,
                source_name=record["source_name"],
                collected_at=record["collected_at"],
                raw_metadata=record["raw_metadata"],
            )
            session.add(paper)
        elif paper.github_stars is not None or not paper.github_url:
            continue

        if paper.github_url and github_token:
            github_url = paper.github_url
            if github_url not in github_metrics_cache:
                try:
                    github_metrics_cache[github_url] = await get_github_metrics(
                        github_url,
                        github_token,
                        client=github_client,
                    )
                except (aiohttp.ClientError, RuntimeError) as error:
                    logger.warning(
                        "GitHub metrics lookup failed for %s: %s", github_url, error
                    )
                    github_metrics_cache[github_url] = (github_url, None)
            resolved_url, github_stars = github_metrics_cache[github_url]
            if resolved_url:
                paper.github_url = resolved_url
            paper.github_stars = github_stars

        github_stars = None
        if paper.github_stars is not None:
            github_stars = paper.github_stars
        if paper.github_url and github_stars is not None:
            match = GITHUB_PATH_RE.search(paper.github_url)
            if match:
                owner, repo_name = match.groups()
                existing_repository = await session.scalar(
                    select(GitHubRepository).where(
                        GitHubRepository.repository_url == paper.github_url
                    )
                )
                if existing_repository:
                    existing_repository.stars = github_stars
                    existing_repository.last_seen_at = datetime.now(UTC)
                else:
                    session.add(
                        GitHubRepository(
                            repository_url=paper.github_url,
                            owner=owner,
                            name=repo_name,
                            stars=github_stars,
                            last_seen_at=datetime.now(UTC),
                        )
                    )
        try:
            await session.commit()
            if is_new:
                count += 1
        except IntegrityError:
            await session.rollback()
    return count
