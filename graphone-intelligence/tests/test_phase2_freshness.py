from datetime import UTC, datetime, timedelta

from src.processors.freshness import (
    content_hash,
    is_within_24_hours,
    parse_verified_datetime,
)


def test_freshness_accepts_exact_24_hour_boundary():
    now = datetime(2026, 11, 21, 19, 0, tzinfo=UTC)
    boundary = now - timedelta(hours=24)
    assert is_within_24_hours(boundary, now=now)


def test_freshness_rejects_older_than_24_hours():
    now = datetime(2026, 11, 21, 19, 0, tzinfo=UTC)
    old = now - timedelta(hours=24, seconds=1)
    assert not is_within_24_hours(old, now=now)


def test_missing_or_relative_publication_date_is_unverified():
    assert parse_verified_datetime(None) is None
    assert parse_verified_datetime("") is None


def test_verified_iso_date_normalizes_to_utc():
    parsed = parse_verified_datetime("2026-11-21T10:00:00+05:30")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.isoformat() == "2026-11-21T04:30:00+00:00"


def test_content_hash_is_deterministic():
    first = content_hash("Example", "Full text")
    second = content_hash("Example", "Full text")
    assert first == second
    assert len(first) == 64
