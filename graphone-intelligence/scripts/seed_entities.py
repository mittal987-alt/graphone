import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.resolution.resolver import normalize_name
from src.resolution.seeds import AI_STARTUP_SEEDS
from src.storage.database import init_db, session_factory
from src.storage.models import Entity, EntityAlias


async def main() -> None:
    await init_db()
    async with session_factory() as session:
        for canonical, aliases in AI_STARTUP_SEEDS:
            canonical_id = f"startup:{normalize_name(canonical).replace(' ', '-')}"
            existing = await session.scalar(
                select(Entity).where(Entity.canonical_id == canonical_id)
            )
            if existing is None:
                entity = Entity(
                    canonical_id=canonical_id,
                    canonical_name=canonical,
                    entity_type="STARTUP",
                )
                session.add(entity)
                await session.flush()
            else:
                entity = existing

            for alias in [canonical, *aliases]:
                normalized = normalize_name(alias)
                duplicate = await session.scalar(
                    select(EntityAlias).where(
                        EntityAlias.normalized_alias == normalized,
                        EntityAlias.entity_type == "STARTUP",
                    )
                )
                if duplicate is None:
                    session.add(
                        EntityAlias(
                            entity_id=entity.id,
                            alias=alias,
                            normalized_alias=normalized,
                            entity_type="STARTUP",
                        )
                    )
        await session.commit()

    print(f"Seeded {len(AI_STARTUP_SEEDS)} canonical AI startups.")


if __name__ == "__main__":
    asyncio.run(main())
