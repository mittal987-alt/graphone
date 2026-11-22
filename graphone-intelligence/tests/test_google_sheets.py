import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.exporters.google_sheets import TAB_HEADERS, GoogleSheetsExporter, utc_text
from src.storage.models import Base, Startup


class FixtureSheets:
    def __init__(self):
        self.calls = []
        self.values = {}

    def ensure_tabs(self, tab_names):
        self.calls.append(("ensure", tab_names))

    def batch_update(self, tab_name, headers, rows, *, clear_existing=False):
        self.calls.append(("batch", tab_name, headers, rows, clear_existing))
        if clear_existing:
            self.values[tab_name] = [headers]
        self.values.setdefault(tab_name, []).extend(rows)
        return len(rows)


@pytest.mark.asyncio
async def test_export_batches_without_duplicate_checkpoint():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    fixture = FixtureSheets()
    exporter = GoogleSheetsExporter(sheets=fixture, batch_size=1)
    async with session_factory() as session:
        startup = Startup(
            entity_name="Fixture AI",
            source_name="Fixture",
            source_url=f"https://fixture.example/startups/fixture-ai-{uuid.uuid4()}",
            collected_at=datetime.now(UTC),
        )
        session.add(startup)
        await session.commit()

        def row_builder(item):
            return [
                item.id,
                item.entity_name,
                item.website or "",
                item.description or "",
                item.industry or "",
                item.employee_count if item.employee_count is not None else "",
                item.source_name,
                item.source_url,
                utc_text(item.collected_at),
            ]

        written = await exporter.export_table(
            session, "Startups Test", Startup, TAB_HEADERS["Startups"], row_builder
        )
        assert written == 1
        assert fixture.calls[0] == (
            "batch",
            "Startups Test",
            TAB_HEADERS["Startups"],
            [row_builder(startup)],
            True,
        )
        assert fixture.values["Startups Test"] == [
            TAB_HEADERS["Startups"],
            row_builder(startup),
        ]
    await engine.dispose()


@pytest.mark.asyncio
async def test_export_all_writes_all_batches_and_initializes_empty_tabs():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    fixture = FixtureSheets()
    exporter = GoogleSheetsExporter(sheets=fixture, batch_size=1)
    async with session_factory() as session:
        session.add_all(
            [
                Startup(
                    entity_name=f"Fixture AI {index}",
                    source_name="Fixture",
                    source_url=f"https://fixture.example/startups/{index}",
                    collected_at=datetime.now(UTC),
                )
                for index in range(2)
            ]
        )
        await session.commit()

        counts = await exporter.export_all(session)

    assert counts["Startups"] == 2
    for tab_name, headers in TAB_HEADERS.items():
        assert fixture.values[tab_name][0] == headers
        assert fixture.values[tab_name].count(headers) == 1
    startup_calls = [call for call in fixture.calls if call[1] == "Startups"]
    assert [call[4] for call in startup_calls] == [True, False]
    await engine.dispose()


def test_export_headers_are_preserved():
    assert "Startups" in TAB_HEADERS
    assert "Entity Mapping Log" in TAB_HEADERS
    assert len(TAB_HEADERS) == 6


def test_batch_export_accepts_missing_credentials():
    settings_exporter = GoogleSheetsExporter(sheets=None)
    assert settings_exporter.sheets is None
