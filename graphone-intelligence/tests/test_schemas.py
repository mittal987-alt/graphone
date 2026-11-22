from datetime import UTC, datetime

from pydantic import ValidationError

from src.extractors.schemas import PricingModel, StartupRecord


def test_startup_schema_accepts_missing_optional_data():
    record = StartupRecord(
        source={"name": "Example Directory", "url": "https://example.com/startup"},
        content={"entityName": "Example AI", "data": {"employeeCount": None}},
        collectedAt=datetime.now(UTC),
    )
    assert record.content.entityName == "Example AI"


def test_startup_schema_rejects_invalid_source_url():
    try:
        StartupRecord(
            source={"name": "Example Directory", "url": "not-a-url"},
            content={"entityName": "Example AI"},
            collectedAt=datetime.now(UTC),
        )
    except ValidationError:
        assert True
    else:
        assert False


def test_unknown_pricing_is_explicit():
    assert PricingModel.UNKNOWN.value == "UNKNOWN"
