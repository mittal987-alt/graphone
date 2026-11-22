import asyncio
import random
import time
from dataclasses import dataclass
from urllib.parse import urlparse


class CircuitOpenError(RuntimeError):
    pass


class BrowserBlockedError(RuntimeError):
    pass


@dataclass
class CircuitState:
    failure_count: int = 0
    opened_at: float | None = None


class DomainRateLimiter:
    def __init__(self, requests_per_second: float = 1.0):
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self.interval = 1.0 / requests_per_second
        self._next_allowed: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, url: str) -> None:
        domain = urlparse(url).netloc.lower()
        async with self._lock:
            now = time.monotonic()
            allowed = max(now, self._next_allowed.get(domain, now))
            self._next_allowed[domain] = allowed + self.interval
            delay = max(0.0, allowed - now)
        if delay:
            await asyncio.sleep(delay)


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_seconds: float = 60):
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._states: dict[str, CircuitState] = {}

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    def ensure_closed(self, url: str) -> None:
        domain = self._domain(url)
        state = self._states.setdefault(domain, CircuitState())
        if state.opened_at is None:
            return
        if time.monotonic() - state.opened_at >= self.reset_seconds:
            state.failure_count = 0
            state.opened_at = None
            return
        raise CircuitOpenError(f"Circuit open for {domain}")

    def record_success(self, url: str) -> None:
        domain = self._domain(url)
        state = self._states.setdefault(domain, CircuitState())
        state.failure_count = 0
        state.opened_at = None

    def record_failure(self, url: str) -> None:
        domain = self._domain(url)
        state = self._states.setdefault(domain, CircuitState())
        state.failure_count += 1
        if state.failure_count >= self.failure_threshold:
            state.opened_at = time.monotonic()

    def is_open(self, url: str) -> bool:
        domain = self._domain(url)
        state = self._states.get(domain)
        return bool(state and state.opened_at is not None)


def blocking_status(status_code: int, text: str) -> str | None:
    if status_code in (401, 403):
        return f"ACCESS_DENIED_{status_code}"
    if status_code == 429:
        return "RATE_LIMITED_429"
    lower = text.lower()
    if "captcha" in lower or "cloudflare" in lower or "datadome" in lower:
        return "BOT_PROTECTION"
    return None


async def polite_delay(
    base_seconds: float = 0.25,
    jitter_seconds: float = 0.25,
) -> None:
    await asyncio.sleep(base_seconds + random.random() * jitter_seconds)
