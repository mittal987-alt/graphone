from datetime import UTC, datetime, timedelta
from hashlib import sha256

import dateparser

UTC = UTC


def parse_verified_datetime(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    parsed = dateparser.parse(
        value,
        settings={
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": "UTC",
            "TO_TIMEZONE": "UTC",
        },
    )
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def is_within_24_hours(
    publication_date: datetime,
    *,
    now: datetime | None = None,
) -> bool:
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    else:
        reference = reference.astimezone(UTC)
    published = publication_date
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    else:
        published = published.astimezone(UTC)
    return reference - timedelta(hours=24) <= published <= reference


def content_hash(*parts: str | None) -> str:
    normalized = "\n".join((part or "").strip().lower() for part in parts)
    return sha256(normalized.encode("utf-8")).hexdigest()
