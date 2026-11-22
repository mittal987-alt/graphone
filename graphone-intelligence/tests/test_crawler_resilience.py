import pytest

from src.crawlers.browser import PlaywrightBrowserFallback
from src.utils.resilience import (
    BrowserBlockedError,
    CircuitBreaker,
    CircuitOpenError,
    blocking_status,
)


def test_blocking_status_detects_cloudflare():
    assert blocking_status(200, "<html>cloudflare verification</html>")
    assert blocking_status(403, "access denied") == "ACCESS_DENIED_403"
    assert blocking_status(429, "rate limited") == "RATE_LIMITED_429"


def test_circuit_breaker_opens_after_threshold():
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=60)
    url = "https://fixture.example/page"
    breaker.record_failure(url)
    assert not breaker.is_open(url)
    breaker.record_failure(url)
    assert breaker.is_open(url)
    try:
        breaker.ensure_closed(url)
    except CircuitOpenError:
        assert True
    else:
        assert False


@pytest.mark.asyncio
async def test_disabled_browser_fallback_stops_safely():
    browser = PlaywrightBrowserFallback(enabled=False)
    try:
        await browser.fetch_text("https://fixture.example")
    except BrowserBlockedError:
        assert True
    else:
        assert False
