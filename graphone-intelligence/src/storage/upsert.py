from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_unique(
    session: AsyncSession,
    model: type,
    values: dict[str, Any],
    unique_field: str,
) -> tuple[Any, bool]:
    unique_value = values[unique_field]
    field = getattr(model, unique_field)
    existing = await session.scalar(select(model).where(field == unique_value))
    if existing is not None:
        for key, value in values.items():
            setattr(existing, key, value)
        await session.commit()
        return existing, False

    record = model(**values)
    session.add(record)
    try:
        await session.commit()
        return record, True
    except Exception:
        await session.rollback()
        raise
