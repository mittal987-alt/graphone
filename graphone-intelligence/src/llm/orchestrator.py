import asyncio
import json
import random
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.chunking import chunk_text
from src.llm.errors import ErrorKind, LLMError
from src.llm.providers import LLMProvider
from src.storage.models import ExtractionTask, FailedTask
from src.utils.observability import log_event, metrics

T = TypeVar("T", bound=BaseModel)


class LLMOrchestrator:
    def __init__(
        self,
        providers: list[LLMProvider],
        *,
        timeout_seconds: float = 60,
        max_retries: int = 3,
        overlap_tokens: int = 100,
    ):
        if not providers:
            raise ValueError("At least one LLM provider is required")
        self.providers = providers
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.overlap_tokens = overlap_tokens

    async def _extract_with_provider(
        self,
        provider: LLMProvider,
        prompt: str,
    ) -> str:
        for attempt in range(self.max_retries + 1):
            try:
                metrics.increment("llm_requests")
                return await provider.extract(prompt, self.timeout_seconds)
            except LLMError as error:
                metrics.increment("llm_retries")
                log_event(
                    30,
                    "llm_provider_error",
                    event="provider_error",
                    provider=provider.name,
                    retryCount=attempt,
                    errorKind=error.kind.value,
                )
                if error.kind in (
                    ErrorKind.AUTHENTICATION,
                    ErrorKind.INVALID_REQUEST,
                    ErrorKind.PAYLOAD_TOO_LARGE,
                    ErrorKind.PERMANENT,
                ):
                    raise
                if attempt >= self.max_retries:
                    raise
                base_delay = 2**attempt + random.random()
                if error.kind == ErrorKind.RATE_LIMIT and error.retry_after_seconds:
                    base_delay = error.retry_after_seconds
                await asyncio.sleep(min(base_delay, 60))

        raise RuntimeError("Provider retry loop exited unexpectedly")

    async def extract(
        self,
        text: str,
        schema: type[T],
        *,
        record_type: str,
        source_url: str | None = None,
        session: AsyncSession | None = None,
        extra_prompt: str = "",
    ) -> list[T]:
        now = datetime.now(UTC)
        task = ExtractionTask(
            source_url=source_url,
            record_type=record_type,
            status="running",
            chunk_count=0,
            retry_count=0,
            input_payload={"text": text, "extra_prompt": extra_prompt},
            provider_usage={},
            created_at=now,
            updated_at=now,
        )
        if session is not None:
            session.add(task)
            await session.commit()

        max_tokens = min(provider.context_window_tokens for provider in self.providers)
        chunks = chunk_text(
            text,
            max_tokens=max(256, max_tokens - 1500),
            overlap_tokens=self.overlap_tokens,
        )
        task.chunk_count = len(chunks)

        results: list[T] = []
        total_retries = 0
        for chunk in chunks:
            prompt = (
                "Extract only information explicitly supported by the source content.\n"
                "Never invent missing values. Use null for unavailable fields.\n"
                "Return one valid JSON object only.\n"
                f"{extra_prompt}\n\nSource content:\n{chunk.text}"
            )
            provider_errors: list[LLMError] = []
            chunk_result: T | None = None

            for provider in self.providers:
                try:
                    raw_response = await self._extract_with_provider(provider, prompt)
                    payload = json.loads(raw_response)
                    chunk_result = schema.model_validate(payload)
                    task.provider = provider.name
                    task.provider_usage.setdefault(provider.name, 0)
                    task.provider_usage[provider.name] += 1
                    break
                except json.JSONDecodeError as error:
                    provider_errors.append(
                        LLMError(
                            provider.name,
                            ErrorKind.INVALID_REQUEST,
                            f"Invalid JSON response: {error}",
                        )
                    )
                except ValidationError as error:
                    provider_errors.append(
                        LLMError(
                            provider.name,
                            ErrorKind.INVALID_REQUEST,
                            f"Pydantic validation failed: {error}",
                        )
                    )
                except LLMError as error:
                    provider_errors.append(error)
                    total_retries += 1

            if chunk_result is None:
                final_error = (
                    provider_errors[-1]
                    if provider_errors
                    else LLMError(
                        "llm",
                        ErrorKind.UNKNOWN,
                        "No provider returned a result",
                    )
                )
                task.status = "failed"
                task.retry_count = total_retries
                task.error_payload = {
                    "kind": final_error.kind.value,
                    "message": str(final_error),
                }
                task.updated_at = datetime.now(UTC)
                if session is not None:
                    session.add(
                        FailedTask(
                            task_type=record_type,
                            provider=final_error.provider,
                            source_url=source_url,
                            error_kind=final_error.kind.value,
                            error_message=str(final_error),
                            retry_count=total_retries,
                            payload={"text": chunk.text, "extra_prompt": extra_prompt},
                            created_at=datetime.now(UTC),
                            next_retry_at=datetime.now(UTC) + timedelta(minutes=15),
                        )
                    )
                    await session.commit()
                return []

            results.append(chunk_result)

        task.status = "completed"
        task.retry_count = total_retries
        task.result_payload = {
            "results": [item.model_dump(mode="json") for item in results]
        }
        task.updated_at = datetime.now(UTC)
        if session is not None:
            await session.commit()
        return results
