import asyncio
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from src.exporters.google_sheets import TAB_HEADERS, utc_text
from src.storage.database import init_db, session_factory
from src.storage.models import (
    EntityMappingLog,
    Job,
    NewsArticle,
    Product,
    ResearchPaper,
    Startup,
)

EXPORT_DIR = ROOT / "data" / "exports"


async def export_to_csv() -> None:
    await init_db()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    async with session_factory() as session:
        tables = [
            (
                "Startups",
                Startup,
                lambda item: [
                    item.id,
                    item.entity_name,
                    item.website or "",
                    item.description or "",
                    item.industry or "",
                    item.employee_count if item.employee_count is not None else "",
                    item.source_name,
                    item.source_url,
                    utc_text(item.collected_at),
                ],
            ),
            (
                "Products",
                Product,
                lambda item: [
                    item.id,
                    item.name,
                    item.description or "",
                    item.website or "",
                    item.startup_name or "",
                    item.pricing_model,
                    item.source_name,
                    item.source_url,
                    utc_text(item.collected_at),
                ],
            ),
            (
                "Research_Papers",
                ResearchPaper,
                lambda item: [
                    item.id,
                    item.title,
                    ", ".join(item.authors or []),
                    item.abstract or "",
                    utc_text(item.published_date),
                    item.paper_url,
                    item.github_url or "",
                    item.github_stars if item.github_stars is not None else "",
                    item.source_name,
                    utc_text(item.collected_at),
                ],
            ),
            (
                "Jobs",
                Job,
                lambda item: [
                    item.id,
                    item.company,
                    item.title,
                    item.role_family or "",
                    item.location or "",
                    item.is_remote if item.is_remote is not None else "",
                    utc_text(item.published_at),
                    utc_text(item.last_modified),
                    item.source_url,
                    item.source_name,
                    utc_text(item.collected_at),
                ],
            ),
            (
                "News",
                NewsArticle,
                lambda item: [
                    item.id,
                    item.title,
                    item.publisher,
                    item.source_url,
                    utc_text(item.publication_date),
                    utc_text(item.last_modified),
                    item.full_text or "",
                    utc_text(item.collected_at),
                    item.content_hash,
                ],
            ),
            (
                "Entity_Mapping_Log",
                EntityMappingLog,
                lambda item: [
                    item.id,
                    item.raw_name,
                    item.canonical_name or "",
                    item.entity_type,
                    item.match_method,
                    item.confidence_score,
                    item.source_url or "",
                    utc_text(item.timestamp),
                ],
            ),
        ]

        print(f"Exporting tables to {EXPORT_DIR.resolve()}...")
        for name, model, row_fn in tables:
            query = select(model).order_by(model.id)
            records = (await session.scalars(query)).all()
            csv_path = EXPORT_DIR / f"{name}.csv"
            header_key = name.replace("_", " ")
            headers = TAB_HEADERS[header_key]

            with open(csv_path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                for record in records:
                    writer.writerow(row_fn(record))

            print(f"  [OK] {csv_path.name}: {len(records)} rows written.")

    print("\nCSV export complete! Files can be directly uploaded to Google Sheets tabs.")


if __name__ == "__main__":
    asyncio.run(export_to_csv())
