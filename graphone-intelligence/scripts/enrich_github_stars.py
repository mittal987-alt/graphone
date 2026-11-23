import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from src.config.settings import get_settings
from src.crawlers.github import GITHUB_PATH_RE, get_github_metrics
from src.storage.database import init_db, session_factory
from src.storage.models import GitHubRepository, ResearchPaper
from src.utils.http import AsyncHttpClient
from src.utils.observability import configure_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    configure_logging("INFO")
    await init_db()
    settings = get_settings()
    token = settings.github_token

    if token:
        print("Using configured GITHUB_TOKEN for accelerated star lookup.")
    else:
        print("GITHUB_TOKEN not found in .env; using polite public GitHub API pacing.")

    async with session_factory() as session:
        papers = (
            await session.scalars(
                select(ResearchPaper)
                .where(ResearchPaper.github_url.is_not(None))
                .where(ResearchPaper.github_stars.is_(None))
            )
        ).all()

        print(f"Found {len(papers)} papers with GitHub URLs pending star enrichment.")
        if not papers:
            print("No papers pending enrichment.")
            return

        client = AsyncHttpClient(requests_per_second=1.0 if token else 0.5)
        enriched_count = 0

        for paper in papers:
            if not paper.github_url:
                continue
            canonical_url, stars = await get_github_metrics(
                paper.github_url, token=token, client=client
            )
            if canonical_url:
                paper.github_url = canonical_url
            if stars is not None:
                paper.github_stars = stars
                enriched_count += 1
                match = GITHUB_PATH_RE.search(canonical_url or paper.github_url)
                if match:
                    owner, repo_name = match.groups()
                    existing_repo = await session.scalar(
                        select(GitHubRepository).where(
                            GitHubRepository.repository_url == paper.github_url
                        )
                    )
                    if existing_repo:
                        existing_repo.stars = stars
                        existing_repo.last_seen_at = datetime.now(UTC)
                    else:
                        session.add(
                            GitHubRepository(
                                repository_url=paper.github_url,
                                owner=owner,
                                name=repo_name,
                                stars=stars,
                                last_seen_at=datetime.now(UTC),
                            )
                        )
                await session.commit()
                print(f"Enriched: {paper.title[:40]}... -> {stars} stars")

        print(f"Enrichment complete: {enriched_count}/{len(papers)} repositories updated.")


if __name__ == "__main__":
    asyncio.run(main())
