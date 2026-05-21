"""Playwright browser session — connects to existing Chrome via CDP."""

from __future__ import annotations

import asyncio
import random
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig
    from kdp_agent.db import KdpBook


class KdpSession:
    """
    Connects to an existing Chrome browser via CDP (port 9222 by default).
    The user MUST be logged in to KDP before calling fill_and_upload().
    """

    def __init__(self, config: "KdpConfig") -> None:
        self._cfg = config
        self._browser: Any = None
        self._page: Any = None

    async def connect(self) -> None:
        from playwright.async_api import async_playwright  # type: ignore
        port = self._cfg.publishing.playwright_cdp_port
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.connect_over_cdp(
            f"http://localhost:{port}"
        )
        contexts = self._browser.contexts
        if not contexts:
            raise RuntimeError("No browser context found. Make sure Chrome is open and logged in to KDP.")
        ctx = contexts[0]
        pages = ctx.pages
        self._page = pages[0] if pages else await ctx.new_page()

    async def disconnect(self) -> None:
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_pw"):
            await self._pw.stop()

    async def fill_and_upload(self, book: "KdpBook") -> None:
        """Navigate KDP and fill all form fields. Pause before Submit."""
        page = self._page
        cfg = self._cfg

        await page.goto(cfg.publishing.kdp_dashboard_url)
        await self._delay()

        # Click "Create" → Paperback
        await page.click('a[data-action="create-paperback"], [data-test="create-paperback"]')
        await self._delay()

        # Fill book details
        await self._fill_text("#data-print-book-title", book.metadata.title)
        await self._fill_text("#data-print-book-subtitle", book.metadata.subtitle)
        await self._fill_text('[name="author-first-name"]', "Author")
        await self._fill_text('[name="author-last-name"]', "Name")

        # Description (KDP uses a rich text editor)
        desc_sel = '#data-print-book-description, [name="description"]'
        await page.fill(desc_sel, book.metadata.description)
        await self._delay()

        # Keywords
        for i, kw in enumerate(book.metadata.keywords[:7]):
            await self._fill_text(f'#data-print-book-keywords-{i}', kw)

        # Save progress to DB
        book.publish_state["filled_details"] = True

        await self._delay()
        # Pause — human reviews and clicks Submit
        # (agent intentionally stops here, per ToS compliance boundary)

    async def _fill_text(self, selector: str, value: str) -> None:
        """Type text into a field with human-like delays."""
        page = self._page
        pub_cfg = self._cfg.publishing
        try:
            await page.wait_for_selector(selector, timeout=5000)
            await page.click(selector)
            await page.fill(selector, "")
            # Type character by character
            for char in value:
                await page.type(selector, char)
                delay_range = pub_cfg.typing_delay_ms
                await asyncio.sleep(
                    random.uniform(delay_range[0], delay_range[1]) / 1000
                )
        except Exception:
            pass  # Selector not found on this KDP page variant — skip

    async def _delay(self) -> None:
        """Random inter-action delay for anti-detection."""
        delay_range = self._cfg.publishing.playwright_action_delay_ms
        await asyncio.sleep(random.uniform(delay_range[0], delay_range[1]) / 1000)
