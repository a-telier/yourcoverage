"""Weekly website content collector using Playwright."""

import logging
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

from .config import Competitor, CollectionSettings
from .themes import analyze_text

logger = logging.getLogger(__name__)

# Campaign-related URL keywords (multilingual)
_CAMPAIGN_KEYWORDS = [
    "collection", "campaign", "new", "sale", "promo",
    "kollektion", "nouveau", "nueva", "nyhet", "erbjudande",
    "solde", "tendance", "inspiration",
]


def collect_website(
    competitor: Competitor,
    settings: CollectionSettings,
    week: str,
    screenshots_dir: Path | None = None,
) -> dict:
    """Scrape a competitor's homepage using a real browser.

    Returns a dict ready for database.save_collection().
    """
    result = {
        "collected_at": datetime.utcnow().isoformat(),
        "page_url": competitor.website_url,
        "page_title": None,
        "meta_description": None,
        "screenshot_path": None,
        "raw_html_length": 0,
        "error": None,
        "headlines": [],
        "campaign_links": [],
        "nav_categories": [],
        "promo_texts": [],
        "theme_tags": [],
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="en-SE",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            # Navigate
            logger.info("Loading %s ...", competitor.website_url)
            page.goto(competitor.website_url, timeout=settings.timeout,
                      wait_until="domcontentloaded")

            # Wait for content to render (JS-heavy sites)
            page.wait_for_timeout(3000)

            # Accept cookie banners (common patterns)
            _dismiss_cookie_banner(page)
            page.wait_for_timeout(1000)

            # Final URL after redirects
            result["page_url"] = page.url

            # Page title
            result["page_title"] = page.title()

            # Meta description
            meta = page.query_selector('meta[name="description"]')
            if meta:
                result["meta_description"] = meta.get_attribute("content")

            # Raw HTML size
            html = page.content()
            result["raw_html_length"] = len(html)

            # --- Extract headlines ---
            for tag in ["h1", "h2", "h3"]:
                elements = page.query_selector_all(tag)
                for el in elements:
                    text = (el.inner_text() or "").strip()
                    if text and 3 < len(text) < 200:
                        result["headlines"].append({"tag": tag, "text": text})

            # Deduplicate headlines preserving order
            seen = set()
            unique_headlines = []
            for h in result["headlines"]:
                if h["text"] not in seen:
                    seen.add(h["text"])
                    unique_headlines.append(h)
            result["headlines"] = unique_headlines[:30]

            # --- Extract campaign/collection links ---
            links = page.query_selector_all("a[href]")
            for link in links:
                href = link.get_attribute("href") or ""
                text = (link.inner_text() or "").strip()
                href_lower = href.lower()

                if not text or len(text) < 3 or len(text) > 100:
                    continue

                if any(kw in href_lower for kw in _CAMPAIGN_KEYWORDS):
                    result["campaign_links"].append({
                        "text": text,
                        "url": _resolve_url(href, result["page_url"]),
                    })

            # Deduplicate campaign links
            seen_campaigns = set()
            unique_campaigns = []
            for cl in result["campaign_links"]:
                key = cl["text"].lower()
                if key not in seen_campaigns:
                    seen_campaigns.add(key)
                    unique_campaigns.append(cl)
            result["campaign_links"] = unique_campaigns[:15]

            # --- Extract navigation categories ---
            nav = page.query_selector("nav") or page.query_selector('[role="navigation"]')
            if nav:
                nav_links = nav.query_selector_all("a")
                seen_nav = set()
                for a in nav_links:
                    text = (a.inner_text() or "").strip()
                    href = a.get_attribute("href") or ""
                    if text and 2 < len(text) < 50 and text.lower() not in seen_nav:
                        seen_nav.add(text.lower())
                        result["nav_categories"].append({
                            "text": text,
                            "url": _resolve_url(href, result["page_url"]),
                        })
                result["nav_categories"] = result["nav_categories"][:25]

            # --- Extract promotional text blocks ---
            all_text_elements = page.query_selector_all(
                "p, [class*='promo'], [class*='banner'], [class*='hero'], "
                "[class*='campaign'], [class*='collection']"
            )
            promo_keywords = [
                "collection", "new", "sale", "free", "offer", "discover",
                "shop", "explore", "kampanj", "nouveau", "découvr", "solde",
                "printemps", "spring", "summer", "sommar",
            ]
            seen_promos = set()
            for el in all_text_elements:
                text = (el.inner_text() or "").strip()
                if not text or len(text) < 20 or len(text) > 300:
                    continue
                text_lower = text.lower()
                if any(kw in text_lower for kw in promo_keywords):
                    if text not in seen_promos:
                        seen_promos.add(text)
                        result["promo_texts"].append(text)
                        if len(result["promo_texts"]) >= 10:
                            break

            # --- Screenshot ---
            if settings.screenshot and screenshots_dir:
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{competitor.slug}_{week}.png"
                screenshot_path = screenshots_dir / filename
                page.screenshot(path=str(screenshot_path), full_page=True)
                result["screenshot_path"] = str(
                    screenshot_path.relative_to(screenshots_dir.parent.parent)
                )
                logger.info("Screenshot saved: %s", screenshot_path)

            # --- Theme analysis ---
            # Combine all extracted text for theme analysis
            all_text = " ".join(
                [h["text"] for h in result["headlines"]]
                + [cl["text"] for cl in result["campaign_links"]]
                + result["promo_texts"]
                + ([result["meta_description"]] if result["meta_description"] else [])
            )
            themes = analyze_text(all_text)
            result["theme_tags"] = themes

            browser.close()

            logger.info(
                "Collected %s: %d headlines, %d campaigns, %d themes",
                competitor.name,
                len(result["headlines"]),
                len(result["campaign_links"]),
                len(result["theme_tags"]),
            )

    except PwTimeout as e:
        result["error"] = f"Page load timeout: {e}"
        logger.warning("Timeout for %s: %s", competitor.website_url, e)
    except Exception as e:
        result["error"] = str(e)
        logger.warning("Failed to scrape %s: %s", competitor.website_url, e)

    return result


def collect_all(
    competitors: list[Competitor],
    settings: CollectionSettings,
    week: str,
    screenshots_dir: Path | None = None,
) -> dict[str, dict]:
    """Collect website data for all competitors."""
    results = {}
    for i, competitor in enumerate(competitors):
        logger.info("Collecting %d/%d: %s", i + 1, len(competitors),
                     competitor.name)
        data = collect_website(competitor, settings, week, screenshots_dir)
        results[competitor.slug] = data
    return results


def _dismiss_cookie_banner(page):
    """Try to dismiss common cookie consent banners."""
    selectors = [
        'button:has-text("Accept")',
        'button:has-text("Acceptera")',
        'button:has-text("Accepter")',
        'button:has-text("Accept all")',
        'button:has-text("Godkänn")',
        '[id*="cookie"] button',
        '[class*="cookie"] button',
        '[id*="consent"] button',
        '[class*="consent"] button',
    ]
    for selector in selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                return
        except Exception:
            continue


def _resolve_url(href: str, base_url: str) -> str:
    """Resolve a relative URL against the base URL."""
    if href.startswith(("http://", "https://")):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{href}"
    return href
