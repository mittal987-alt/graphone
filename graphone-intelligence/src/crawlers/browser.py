from typing import Any

from src.config.settings import get_settings
from src.utils.resilience import BrowserBlockedError, blocking_status


class PlaywrightBrowserFallback:
    def __init__(self, enabled: bool | None = None, proxy_url: str | None = None):
        settings = get_settings()
        self.enabled = settings.playwright_enabled if enabled is None else enabled
        self.proxy_url = proxy_url if proxy_url is not None else settings.proxy_url

    async def fetch_text(self, url: str, wait_selector: str | None = None) -> str:
        if not self.enabled:
            raise BrowserBlockedError("Playwright fallback is disabled")

        try:
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise BrowserBlockedError("Playwright package is unavailable") from error

        async with async_playwright() as playwright:
            launch_args: dict[str, Any] = {}
            if self.proxy_url:
                launch_args["proxy"] = {"server": self.proxy_url}
            browser = await playwright.chromium.launch(
                headless=True,
                **launch_args,
            )
            context = await browser.new_context(
                locale="en-US",
                user_agent=(
                    "Mozilla/5.0 (compatible; GraphOneIntelligence/1.0; "
                    "+https://example.invalid/contact)"
                ),
            )
            try:
                page = await context.new_page()
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                if response is None:
                    raise BrowserBlockedError("No browser response")
                status = response.status
                html = await page.content()
                block_status = blocking_status(status, html)
                if block_status:
                    raise BrowserBlockedError(block_status)
                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=10000)
                return await page.locator("body").inner_text()
            finally:
                await context.close()
                await browser.close()
