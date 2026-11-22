import asyncio
import random
from typing import Any

import aiohttp

from src.utils.resilience import (
    CircuitBreaker,
    DomainRateLimiter,
    blocking_status,
    polite_delay,
)


class AsyncHttpClient:
    def __init__(
        self,
        timeout: float = 30,
        concurrency: int = 8,
        max_retries: int = 4,
        requests_per_second: float = 1.0,
        failure_threshold: int = 5,
        reset_seconds: float = 60,
    ):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.semaphore = asyncio.Semaphore(concurrency)
        self.max_retries = max_retries
        self.rate_limiter = DomainRateLimiter(requests_per_second)
        self.circuit_breaker = CircuitBreaker(failure_threshold, reset_seconds)
        self.blocked_domains: set[str] = set()

    async def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        async with self.semaphore:
            self.circuit_breaker.ensure_closed(url)
            await self.rate_limiter.wait(url)
            for attempt in range(self.max_retries + 1):
                try:
                    await polite_delay()
                    async with aiohttp.ClientSession(timeout=self.timeout) as session:
                        async with session.get(
                            url, headers=headers, params=params
                        ) as response:
                            if response.status == 429:
                                body = await response.text()
                                status = blocking_status(response.status, body)
                                self.blocked_domains.add(status or "BLOCKED")
                                retry_after = response.headers.get("Retry-After")
                                delay = (
                                    float(retry_after)
                                    if retry_after and retry_after.isdigit()
                                    else min(2**attempt + random.random(), 60)
                                )
                                self.circuit_breaker.record_failure(url)
                                await asyncio.sleep(delay)
                                continue
                            if response.status >= 500:
                                self.circuit_breaker.record_failure(url)
                                await asyncio.sleep(
                                    min(2**attempt + random.random(), 30)
                                )
                                continue
                            body = await response.text()
                            status = blocking_status(response.status, body)
                            if status:
                                self.circuit_breaker.record_failure(url)
                                raise RuntimeError(status)
                            response.raise_for_status()
                            self.circuit_breaker.record_success(url)
                            return await response.json()
                except aiohttp.ClientError:
                    if attempt >= self.max_retries:
                        self.circuit_breaker.record_failure(url)
                        raise
                    await asyncio.sleep(min(2**attempt + random.random(), 30))
            raise RuntimeError(f"Request failed after retries: {url}")
