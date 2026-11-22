import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.resolution.seeds import AI_STARTUP_SEEDS
from src.storage.models import (
    Entity,
    EntityMappingLog,
    EntityReviewQueue,
)

LEGAL_SUFFIXES = (
    r"\bincorporated\b",
    r"\bcorporation\b",
    r"\bcompany\b",
    r"\blimited\b",
    r"\bllc\b",
    r"\bltd\b",
    r"\binc\b",
    r"\bcorp\b",
)


def normalize_name(raw_name: str) -> str:
    value = unicodedata.normalize("NFKD", raw_name).lower()
    value = "".join(char for char in value if not unicodedata.combining(char))
    for suffix in LEGAL_SUFFIXES:
        value = re.sub(suffix, " ", value)
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@dataclass(frozen=True)
class Resolution:
    canonical_name: str | None
    canonical_id: str | None
    match_method: str
    confidence: float
    candidates: tuple[str, ...] = ()


class EntityResolver:
    FUZZY_THRESHOLD = 96.0

    def __init__(self, seeds: list[tuple[str, list[str]]] | tuple = AI_STARTUP_SEEDS):
        self.seeds = dict(seeds)

    def resolve(self, raw_name: str, entity_type: str = "STARTUP") -> Resolution:
        normalized = normalize_name(raw_name)
        if not normalized:
            return Resolution(None, None, "unmatched", 0.0)

        for canonical, aliases in self.seeds.items():
            names = [canonical, *aliases]
            if normalized in {normalize_name(name) for name in names}:
                if normalize_name(canonical) == normalized:
                    method = "exact"
                    confidence = 1.0
                else:
                    method = "alias"
                    confidence = 1.0
                return Resolution(
                    canonical,
                    f"{entity_type.lower()}:{normalize_name(canonical).replace(' ', '-')}",
                    method,
                    confidence,
                )

        ranked = [
            (canonical, fuzz.ratio(normalized, normalize_name(canonical)))
            for canonical in self.seeds
        ]
        ranked.sort(key=lambda item: item[1], reverse=True)
        strong = [item for item in ranked if item[1] >= self.FUZZY_THRESHOLD]

        if len(strong) == 1:
            canonical, score = strong[0]
            return Resolution(
                canonical,
                f"{entity_type.lower()}:{normalize_name(canonical).replace(' ', '-')}",
                "fuzzy",
                score / 100,
            )

        if len(strong) > 1:
            return Resolution(
                None,
                None,
                "ambiguous",
                strong[0][1] / 100,
                tuple(canonical for canonical, _ in strong),
            )

        return Resolution(None, None, "unmatched", ranked[0][1] / 100)

    async def persist_resolution(
        self,
        session: AsyncSession,
        raw_name: str,
        entity_type: str,
        source_url: str | None,
        resolution: Resolution,
    ) -> None:
        if resolution.canonical_name:
            existing = await session.scalar(
                select(Entity).where(Entity.canonical_id == resolution.canonical_id)
            )
            if existing is None:
                session.add(
                    Entity(
                        canonical_id=resolution.canonical_id,
                        canonical_name=resolution.canonical_name,
                        entity_type=entity_type,
                        source_url=source_url,
                    )
                )

        session.add(
            EntityMappingLog(
                raw_name=raw_name,
                canonical_name=resolution.canonical_name,
                entity_type=entity_type,
                match_method=resolution.match_method,
                confidence_score=resolution.confidence,
                source_url=source_url,
                timestamp=datetime.now(UTC),
            )
        )

        if resolution.match_method in ("ambiguous", "unmatched"):
            session.add(
                EntityReviewQueue(
                    raw_name=raw_name,
                    entity_type=entity_type,
                    candidates={"names": list(resolution.candidates)},
                    source_url=source_url,
                    status="pending",
                    created_at=datetime.now(UTC),
                )
            )
        await session.commit()
