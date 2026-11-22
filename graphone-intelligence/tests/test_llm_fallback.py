import pytest
from pydantic import BaseModel

from src.llm.errors import ErrorKind, LLMError
from src.llm.orchestrator import LLMOrchestrator
from src.llm.providers import LLMProvider


class FixtureExtraction(BaseModel):
    title: str
    count: int | None = None


class FixtureProvider(LLMProvider):
    context_window_tokens = 2000
    max_output_tokens = 100

    def __init__(self, name: str, outcome: str):
        self.name = name
        self.model = name
        self.outcome = outcome

    async def extract(self, prompt: str, timeout_seconds: float) -> str:
        if self.outcome == "429":
            raise LLMError(self.name, ErrorKind.RATE_LIMIT, "rate limited", 0)
        if self.outcome == "413":
            raise LLMError(self.name, ErrorKind.PAYLOAD_TOO_LARGE, "too large")
        if self.outcome == "auth":
            raise LLMError(self.name, ErrorKind.AUTHENTICATION, "bad key")
        if self.outcome == "invalid":
            return '{"title": "fixture", "count": "not-an-integer"}'
        return '{"title": "fixture", "count": 3}'


@pytest.mark.asyncio
async def test_fallback_moves_from_gemini_to_groq():
    orchestrator = LLMOrchestrator(
        [FixtureProvider("gemini", "429"), FixtureProvider("groq", "success")],
        max_retries=0,
    )
    results = await orchestrator.extract(
        "Source fixture text.",
        FixtureExtraction,
        record_type="TEST",
    )
    assert results[0].title == "fixture"
    assert results[0].count == 3


@pytest.mark.asyncio
async def test_payload_error_falls_back_without_database_row():
    orchestrator = LLMOrchestrator(
        [FixtureProvider("gemini", "413"), FixtureProvider("groq", "success")],
        max_retries=0,
    )
    results = await orchestrator.extract(
        "Source fixture text.",
        FixtureExtraction,
        record_type="TEST",
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_all_providers_failure_persists_when_session_supplied():
    from src.storage.database import init_db, session_factory

    await init_db()
    orchestrator = LLMOrchestrator(
        [FixtureProvider("gemini", "auth"), FixtureProvider("groq", "auth")],
        max_retries=0,
    )
    async with session_factory() as session:
        results = await orchestrator.extract(
            "Source fixture text.",
            FixtureExtraction,
            record_type="TEST",
            source_url="https://fixture.example/source",
            session=session,
        )
    assert results == []
