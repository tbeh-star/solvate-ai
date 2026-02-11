"""
Knowde marketplace taxonomy scraper.

Uses Playwright to render the SPA and intercept API responses
containing category/taxonomy data.

Usage:
    scraper = KnowdeTaxonomyScraper()
    result = await scraper.run_full_extraction()

Dependencies:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

# Base URL
MARKETPLACE_URL = "https://www.knowde.com/marketplace"


class KnowdeTaxonomyScraper:
    """
    Extracts taxonomy from Knowde marketplace.

    Strategy:
    1. Load marketplace page with Playwright headless Chrome
    2. Intercept XHR/API responses containing category JSON
    3. Navigate category pages to extract subcategory trees
    4. Extract product attribute schemas from sample product pages
    5. Store raw JSON for audit trail
    """

    def __init__(
        self,
        output_dir: str = "data/knowde_taxonomy",
        delay_seconds: float = 2.0,
        headless: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay_seconds
        self.headless = headless
        self._intercepted_responses: list[dict] = []

    async def _setup_browser(self):
        """Initialize Playwright browser."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "playwright is required for scraping. "
                "Install with: pip install playwright && playwright install chromium"
            )

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            )
        )
        self._page = await self._context.new_page()

        # Intercept API responses
        self._page.on("response", self._on_response)

    async def _on_response(self, response) -> None:
        """Capture API responses that may contain taxonomy data."""
        url = response.url
        if any(
            keyword in url.lower()
            for keyword in ["categor", "taxonomy", "marketplace", "filter", "facet"]
        ):
            try:
                if "application/json" in (response.headers.get("content-type", "")):
                    body = await response.json()
                    self._intercepted_responses.append({
                        "url": url,
                        "status": response.status,
                        "body": body,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    logger.info("intercepted_api_response", url=url, status=response.status)
            except Exception:
                pass

    async def _teardown_browser(self) -> None:
        """Clean up Playwright resources."""
        if hasattr(self, "_browser"):
            await self._browser.close()
        if hasattr(self, "_pw"):
            await self._pw.stop()

    async def extract_marketplace_categories(self) -> list[dict]:
        """
        Load the marketplace page and extract top-level categories
        from the rendered DOM.
        """
        logger.info("navigating_to_marketplace", url=MARKETPLACE_URL)
        await self._page.goto(MARKETPLACE_URL, wait_until="networkidle")
        await asyncio.sleep(self.delay)

        # Try to extract categories from the page structure
        categories = await self._page.evaluate("""
            () => {
                const results = [];
                // Look for category links in the marketplace navigation
                const links = document.querySelectorAll('a[href*="/marketplace/"]');
                links.forEach(link => {
                    const href = link.getAttribute('href');
                    const text = link.textContent.trim();
                    if (href && text && !href.includes('?')) {
                        results.push({
                            name: text,
                            url: href,
                            slug: href.split('/').pop(),
                        });
                    }
                });
                return results;
            }
        """)

        logger.info("extracted_marketplace_categories", count=len(categories))
        return categories

    async def extract_subcategories(self, category_url: str) -> list[dict]:
        """
        Navigate to a category page and extract its subcategory tree
        from the sidebar/filter navigation.
        """
        full_url = f"https://www.knowde.com{category_url}" if category_url.startswith("/") else category_url

        logger.info("extracting_subcategories", url=full_url)
        await self._page.goto(full_url, wait_until="networkidle")
        await asyncio.sleep(self.delay)

        subcategories = await self._page.evaluate("""
            () => {
                const results = [];
                // Look for subcategory elements in the filter sidebar
                const filterSections = document.querySelectorAll(
                    '[data-testid*="filter"], [class*="filter"], [class*="category"]'
                );
                filterSections.forEach(section => {
                    const links = section.querySelectorAll('a');
                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        const text = link.textContent.trim();
                        if (href && text) {
                            results.push({
                                name: text,
                                url: href,
                                slug: href.split('/').pop(),
                            });
                        }
                    });
                });
                return results;
            }
        """)

        logger.info("extracted_subcategories", url=full_url, count=len(subcategories))
        return subcategories

    async def extract_product_attributes(self, product_url: str) -> dict:
        """
        Navigate to a product page and extract the attribute schema
        (what fields/groups are used).
        """
        full_url = f"https://www.knowde.com{product_url}" if product_url.startswith("/") else product_url

        logger.info("extracting_product_attributes", url=full_url)
        await self._page.goto(full_url, wait_until="networkidle")
        await asyncio.sleep(self.delay)

        attributes = await self._page.evaluate("""
            () => {
                const result = {};
                // Look for attribute sections on the product page
                const sections = document.querySelectorAll(
                    '[class*="attribute"], [class*="property"], [class*="specification"]'
                );
                sections.forEach(section => {
                    const heading = section.querySelector('h2, h3, h4, [class*="title"]');
                    const groupName = heading ? heading.textContent.trim() : 'unknown';
                    const items = [];
                    const rows = section.querySelectorAll('tr, [class*="row"], [class*="item"]');
                    rows.forEach(row => {
                        const key = row.querySelector('th, [class*="label"], [class*="key"]');
                        const value = row.querySelector('td, [class*="value"]');
                        if (key && value) {
                            items.push({
                                key: key.textContent.trim(),
                                value: value.textContent.trim(),
                            });
                        }
                    });
                    if (items.length > 0) {
                        result[groupName] = items;
                    }
                });
                return result;
            }
        """)

        logger.info("extracted_product_attributes", url=full_url, groups=len(attributes))
        return attributes

    def _save_raw_data(self, filename: str, data: object) -> Path:
        """Save extracted data as JSON for audit trail."""
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info("saved_raw_data", path=str(filepath))
        return filepath

    async def run_full_extraction(self) -> dict:
        """
        Orchestrate complete taxonomy extraction.

        Returns summary dict with extraction results and file paths.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        result = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "categories": [],
            "intercepted_apis": [],
            "files": [],
        }

        try:
            await self._setup_browser()

            # Step 1: Extract marketplace top-level categories
            categories = await self.extract_marketplace_categories()
            result["categories"] = categories
            result["files"].append(
                str(self._save_raw_data(f"categories_{timestamp}.json", categories))
            )

            # Step 2: Extract subcategories for each top-level category
            for cat in categories[:20]:  # Limit to prevent excessive scraping
                url = cat.get("url", "")
                if url:
                    subcats = await self.extract_subcategories(url)
                    cat["subcategories"] = subcats
                    await asyncio.sleep(self.delay)

            result["files"].append(
                str(self._save_raw_data(f"categories_with_subs_{timestamp}.json", categories))
            )

            # Step 3: Save intercepted API responses
            result["intercepted_apis"] = self._intercepted_responses
            if self._intercepted_responses:
                result["files"].append(
                    str(self._save_raw_data(
                        f"intercepted_apis_{timestamp}.json",
                        self._intercepted_responses,
                    ))
                )

            result["status"] = "completed"
            result["finished_at"] = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error("scraper_failed", error=str(e))

        finally:
            await self._teardown_browser()

        # Save final summary
        self._save_raw_data(f"extraction_summary_{timestamp}.json", result)

        return result
