import asyncio
import random
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.storage.models import (
    EntityMappingLog,
    ExportCheckpoint,
    Job,
    NewsArticle,
    Product,
    ResearchPaper,
    Startup,
)


class SheetsService(Protocol):
    def ensure_tabs(self, tab_names: list[str]) -> None: ...

    def batch_update(
        self,
        tab_name: str,
        headers: list[str],
        rows: list[list[Any]],
        *,
        clear_existing: bool = False,
    ) -> int: ...


TAB_HEADERS = {
    "Startups": [
        "ID",
        "Entity Name",
        "Website",
        "Description",
        "Industry",
        "Employee Count",
        "Source Name",
        "Source URL",
        "Collected At",
    ],
    "Products": [
        "ID",
        "Name",
        "Description",
        "Website",
        "Startup Name",
        "Pricing Model",
        "Source Name",
        "Source URL",
        "Collected At",
    ],
    "Research Papers": [
        "ID",
        "Title",
        "Authors",
        "Abstract",
        "Publication Date",
        "Paper URL",
        "GitHub URL",
        "GitHub Stars",
        "Source Name",
        "Collected At",
    ],
    "Jobs": [
        "ID",
        "Company",
        "Title",
        "Role Family",
        "Location",
        "Is Remote",
        "Published At",
        "Last Modified",
        "Source URL",
        "Source Name",
        "Collected At",
    ],
    "News": [
        "ID",
        "Title",
        "Publisher",
        "URL",
        "Publication Date",
        "Last Modified",
        "Full Text",
        "Collected At",
        "Content Hash",
    ],
    "Entity Mapping Log": [
        "ID",
        "Raw Name",
        "Canonical Name",
        "Entity Type",
        "Match Method",
        "Confidence Score",
        "Source URL",
        "Timestamp",
    ],
}


def utc_text(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat()
    return value.astimezone(UTC).isoformat()


class GoogleSheetsExporter:
    def __init__(self, sheets: SheetsService | None = None, batch_size: int = 500):
        self.sheets = sheets
        self.batch_size = batch_size

    async def export_table(
        self,
        session: AsyncSession,
        tab_name: str,
        model: type,
        headers: list[str],
        row_builder,
    ) -> int:
        checkpoint = await session.scalar(
            select(ExportCheckpoint).where(ExportCheckpoint.tab_name == tab_name)
        )
        if checkpoint is None:
            checkpoint = ExportCheckpoint(
                tab_name=tab_name,
                status="pending",
                raw_metadata={
                    "duplicate_keys": "database_primary_key",
                    "initialized": False,
                },
            )
            session.add(checkpoint)
            await session.commit()

        query = select(model).order_by(model.id)
        if checkpoint.last_record_id:
            query = query.where(model.id > checkpoint.last_record_id)
        records = (await session.scalars(query.limit(self.batch_size))).all()

        if self.sheets is None:
            checkpoint.status = "not_configured" if records else "complete"
            checkpoint.raw_metadata = {
                **checkpoint.raw_metadata,
                "reason": "Google Sheets service account is not configured",
            }
            await session.commit()
            return 0

        initialize = not checkpoint.raw_metadata.get("initialized", False)
        if not records and not initialize:
            checkpoint.status = "complete"
            await session.commit()
            return 0

        rows = [row_builder(record) for record in records]
        written = 0
        for attempt in range(5):
            try:
                written = self.sheets.batch_update(
                    tab_name,
                    headers,
                    rows,
                    clear_existing=initialize,
                )
                break
            except Exception as error:
                status = getattr(error, "status_code", None)
                error_name = type(error).__name__
                is_transient = (
                    status in (429, 500, 502, 503, 504)
                    or "TransportError" in error_name
                    or "ServerNotFoundError" in error_name
                    or "socket" in error_name.lower()
                    or "timeout" in error_name.lower()
                )
                if not is_transient:
                    checkpoint.status = "failed"
                    checkpoint.raw_metadata = {
                        **checkpoint.raw_metadata,
                        "error": str(error),
                    }
                    await session.commit()
                    raise
                await asyncio.sleep(min(2**attempt + random.random(), 60))
        else:
            checkpoint.status = "failed"
            await session.commit()
            return 0

        if records:
            checkpoint.last_record_id = records[-1].id
        checkpoint.last_row_count = written
        checkpoint.last_exported_at = datetime.now(UTC)
        checkpoint.status = "complete"
        checkpoint.raw_metadata = {
            **checkpoint.raw_metadata,
            "initialized": True,
        }
        await session.commit()
        return written

    async def export_all(self, session: AsyncSession) -> dict[str, int]:
        if self.sheets is None:
            settings = get_settings()
            if not settings.google_sheets_spreadsheet_id:
                return {tab: 0 for tab in TAB_HEADERS}
            raise RuntimeError(
                "Google Sheets service account implementation is not configured"
            )

        self.sheets.ensure_tabs(list(TAB_HEADERS))
        exporters = [
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
                "Research Papers",
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
                "Entity Mapping Log",
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

        counts: dict[str, int] = {}
        for tab_name, model, row_builder in exporters:
            total = 0
            while True:
                written = await self.export_table(
                    session,
                    tab_name,
                    model,
                    TAB_HEADERS[tab_name],
                    row_builder,
                )
                total += written
                if written < self.batch_size:
                    break
            counts[tab_name] = total
        return counts


class GoogleSheetsService:
    def __init__(
        self,
        spreadsheet_id: str,
        credentials_file: str | None = None,
    ):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_file = credentials_file
        self._service = None

    def _build_service(self):
        if self._service is not None:
            return self._service
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        if not self.credentials_file:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not configured")
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self._service = build("sheets", "v4", credentials=credentials)
        return self._service

    def ensure_tabs(self, tab_names: list[str]) -> None:
        service = self._build_service()
        spreadsheet = (
            service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        )
        existing = {
            sheet["properties"]["title"] for sheet in spreadsheet.get("sheets", [])
        }
        requests = [
            {"addSheet": {"properties": {"title": tab_name}}}
            for tab_name in tab_names
            if tab_name not in existing
        ]
        if requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": requests},
            ).execute()

    def batch_update(
        self,
        tab_name: str,
        headers: list[str],
        rows: list[list[Any]],
        *,
        clear_existing: bool = False,
    ) -> int:
        service = self._build_service()
        values = ([headers] if clear_existing else []) + rows
        if not values:
            return 0
        body: dict[str, Any] = {"values": values}
        range_name = f"{tab_name}!A1"
        if clear_existing:
            service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f"{tab_name}!A:{chr(65 + len(headers) - 1)}",
            ).execute()
        service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return max(0, len(rows))
