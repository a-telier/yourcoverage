"""Weekly website content collector.

Uses Playwright (headless browser) when available, falls back to
requests + BeautifulSoup for environments without browser binaries.
"""

import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin

from .config import Competitor, CollectionSettings
from .themes import analyze_text

logger = logging.getLogger(__name__)

# Campaign-related URL path keywords
_CAMPAIGN_URL_KEYWORDS = [
    "collection", "campaign", "new", "sale", "promo",
    "kollektion", "nouveau", "nueva", "nyhet", "erbjudande",
    "solde", "tendance", "inspiration", "jardin", "garden",
    "outdoor", "exterieur", "seasonal", "spring", "summer",
    "canape", "sofa", "decoration", "mobilier", "furniture",
]

# Campaign-related link TEXT keywords (multilingual)
_CAMPAIGN_TEXT_KEYWORDS = [
    # French
    "decouvrez", "nouvelle", "collection", "jardin", "canape",
    "decoration", "exterieur", "mobilier", "tendance", "promo",
    "solde", "offre", "nouveaute",
    # English
    "discover", "new", "collection", "garden", "outdoor",
    "furniture", "campaign", "sale", "offer", "shop now",
    "explore", "see all", "view all",
    # Swedish
    "upptack", "kollektion", "tradgard", "utomhus", "mobel",
    "kampanj", "erbjudande", "nyheter",
    # Spanish
    "descubr", "coleccion", "jardin", "mueble", "oferta",
]

_PROMO_KEYWORDS = [
    "collection", "new", "sale", "free", "offer", "discover",
    "shop", "explore", "kampanj", "nouveau", "decouvr", "solde",
    "printemps", "spring", "summer", "sommar", "jardin", "garden",
    "canape", "sofa", "outdoor", "exterieur", "decoration",
    "mobilier", "furniture", "tendance",
]

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Full browser-like headers to avoid 403s
_HTTP_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,sv;q=0.8,fr;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Minimum image dimensions (pixels in src URL or attributes) to count as hero
_MIN_IMAGE_WIDTH = 300


def _empty_result(competitor: Competitor) -> dict:
    return {
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
        "hero_images": [],
    }


def _dedup(items: list[dict], key_field: str, max_items: int) -> list[dict]:
    """Deduplicate list of dicts by a field, preserving order."""
    seen = set()
    out = []
    for item in items:
        k = item[key_field].lower() if isinstance(item[key_field], str) else item[key_field]
        if k not in seen:
            seen.add(k)
            out.append(item)
            if len(out) >= max_items:
                break
    return out


def _run_theme_analysis(result: dict) -> None:
    """Run theme analysis on all extracted text and store in result."""
    all_text = " ".join(
        [h["text"] for h in result["headlines"]]
        + [cl["text"] for cl in result["campaign_links"]]
        + result["promo_texts"]
        + [img.get("alt", "") for img in result["hero_images"] if img.get("alt")]
        + ([result["meta_description"]] if result["meta_description"] else [])
    )
    result["theme_tags"] = analyze_text(all_text)


def _normalize(text: str) -> str:
    """Lowercase and strip accents for keyword matching."""
    import unicodedata
    text = text.lower()
    # Decompose accented chars and remove combining marks
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _resolve_url(href: str, base_url: str) -> str:
    """Resolve a relative URL against the base URL."""
    if not href:
        return ""
    if href.startswith(("http://", "https://")):
        return href
    if href.startswith("//"):
        return "https:" + href
    return urljoin(base_url, href)


def _is_hero_image(src: str, alt: str, width=None, height=None) -> bool:
    """Check if an image is likely a hero/campaign image (not an icon)."""
    if not src:
        return False
    src_lower = src.lower()
    # Skip tiny images, icons, tracking pixels, svgs
    skip_patterns = [
        ".svg", "icon", "logo", "pixel", "track", "spacer",
        "1x1", "blank", "spinner", "loading", "arrow", "chevron",
        "data:image", "base64",
    ]
    if any(p in src_lower for p in skip_patterns):
        return False
    # Check explicit dimensions
    try:
        if width and str(width).isdigit() and int(width) < _MIN_IMAGE_WIDTH:
            return False
        if height and str(height).isdigit() and int(height) < 100:
            return False
    except (ValueError, TypeError):
        pass
    return True


# ---------------------------------------------------------------------------
# Playwright-based collector (preferred)
# ---------------------------------------------------------------------------

def _playwright_available() -> bool:
    """Check if Playwright and a browser binary are available."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def _collect_playwright(
    competitor: Competitor,
    settings: CollectionSettings,
    week: str,
    screenshots_dir: Path | None,
    result: dict,
) -> None:
    """Scrape using Playwright headless browser."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-SE",
            user_agent=_USER_AGENT,
        )
        page = context.new_page()

        logger.info("Loading %s (Playwright) ...", competitor.website_url)
        page.goto(competitor.website_url, timeout=settings.timeout,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Cookie banners
        for selector in [
            'button:has-text("Accept")', 'button:has-text("Acceptera")',
            'button:has-text("Accepter")', 'button:has-text("Accept all")',
            '[id*="cookie"] button', '[class*="cookie"] button',
            '[id*="consent"] button',
        ]:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(1000)
                    break
            except Exception:
                continue

        result["page_url"] = page.url
        result["page_title"] = page.title()

        meta = page.query_selector('meta[name="description"]')
        if meta:
            result["meta_description"] = meta.get_attribute("content")

        html = page.content()
        result["raw_html_length"] = len(html)

        # Headlines
        for tag in ["h1", "h2", "h3"]:
            for el in page.query_selector_all(tag):
                text = (el.inner_text() or "").strip()
                if text and 3 < len(text) < 200:
                    result["headlines"].append({"tag": tag, "text": text})
        result["headlines"] = _dedup(result["headlines"], "text", 30)

        # Campaign links + their images — match by URL path OR text
        for link in page.query_selector_all("a[href]"):
            href = link.get_attribute("href") or ""
            text = (link.inner_text() or "").strip()
            if not text or len(text) < 3 or len(text) > 150:
                continue
            href_lower = href.lower()
            text_lower = _normalize(text)
            url_match = any(kw in href_lower for kw in _CAMPAIGN_URL_KEYWORDS)
            text_match = any(kw in text_lower for kw in _CAMPAIGN_TEXT_KEYWORDS)
            if url_match or text_match:
                campaign = {
                    "text": text,
                    "url": _resolve_url(href, result["page_url"]),
                }
                result["campaign_links"].append(campaign)
                # Grab image inside this campaign link
                img = link.query_selector("img[src], img[data-src]")
                if img:
                    src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                    alt = (img.get_attribute("alt") or text).strip()
                    if src and _is_hero_image(src, alt):
                        result["hero_images"].append({
                            "src": _resolve_url(src, result["page_url"]),
                            "alt": alt,
                        })
        result["campaign_links"] = _dedup(result["campaign_links"], "text", 20)

        # Also grab images from hero/banner/carousel sections
        for selector in [
            "[class*='hero'] img", "[class*='banner'] img",
            "[class*='carousel'] img", "[class*='slider'] img",
            "[class*='slide'] img", "[class*='swiper'] img",
        ]:
            for img in page.query_selector_all(selector):
                src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                alt = (img.get_attribute("alt") or "").strip()
                if src and _is_hero_image(src, alt):
                    result["hero_images"].append({
                        "src": _resolve_url(src, result["page_url"]),
                        "alt": alt,
                    })
        result["hero_images"] = _dedup(result["hero_images"], "src", 12)

        # Nav categories
        nav = page.query_selector("nav") or page.query_selector('[role="navigation"]')
        if nav:
            seen_nav = set()
            for a in nav.query_selector_all("a"):
                text = (a.inner_text() or "").strip()
                href = a.get_attribute("href") or ""
                if text and 2 < len(text) < 50 and text.lower() not in seen_nav:
                    seen_nav.add(text.lower())
                    result["nav_categories"].append({
                        "text": text,
                        "url": _resolve_url(href, result["page_url"]),
                    })
            result["nav_categories"] = result["nav_categories"][:25]

        # Promo texts
        seen_promos = set()
        for el in page.query_selector_all(
            "p, [class*='promo'], [class*='banner'], [class*='hero'], "
            "[class*='campaign'], [class*='collection']"
        ):
            text = (el.inner_text() or "").strip()
            if not text or len(text) < 20 or len(text) > 300:
                continue
            if any(kw in text.lower() for kw in _PROMO_KEYWORDS):
                if text not in seen_promos:
                    seen_promos.add(text)
                    result["promo_texts"].append(text)
                    if len(result["promo_texts"]) >= 10:
                        break

        # Screenshot
        if settings.screenshot and screenshots_dir:
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{competitor.slug}_{week}.png"
            screenshot_path = screenshots_dir / filename
            page.screenshot(path=str(screenshot_path), full_page=True)
            result["screenshot_path"] = str(
                screenshot_path.relative_to(screenshots_dir.parent.parent)
            )

        browser.close()


# ---------------------------------------------------------------------------
# HTTP fallback collector (requests + BeautifulSoup)
# ---------------------------------------------------------------------------

def _collect_http(
    competitor: Competitor,
    settings: CollectionSettings,
    result: dict,
) -> None:
    """Scrape using requests + BeautifulSoup (no browser needed)."""
    import requests
    from bs4 import BeautifulSoup

    logger.info("Loading %s (HTTP fallback) ...", competitor.website_url)
    timeout_sec = settings.timeout / 1000

    session = requests.Session()
    session.headers.update(_HTTP_HEADERS)

    resp = session.get(
        competitor.website_url,
        timeout=timeout_sec,
        allow_redirects=True,
    )
    resp.raise_for_status()

    result["page_url"] = resp.url
    result["raw_html_length"] = len(resp.text)

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title_tag = soup.find("title")
    if title_tag:
        result["page_title"] = title_tag.get_text(strip=True)

    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        result["meta_description"] = meta["content"]

    # Headlines
    base_url = result["page_url"]
    for tag in ["h1", "h2", "h3"]:
        for el in soup.find_all(tag):
            text = el.get_text(strip=True)
            if text and 3 < len(text) < 200:
                result["headlines"].append({"tag": tag, "text": text})
    result["headlines"] = _dedup(result["headlines"], "text", 30)

    # Campaign links + their images
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not text or len(text) < 3 or len(text) > 150:
            continue
        href_lower = href.lower()
        text_lower = _normalize(text)
        url_match = any(kw in href_lower for kw in _CAMPAIGN_URL_KEYWORDS)
        text_match = any(kw in text_lower for kw in _CAMPAIGN_TEXT_KEYWORDS)
        if url_match or text_match:
            result["campaign_links"].append({
                "text": text,
                "url": _resolve_url(href, base_url),
            })
            # Grab image inside this campaign link
            img = a.find("img")
            if img:
                src = img.get("src") or img.get("data-src") or ""
                alt = (img.get("alt") or text).strip()
                if src and _is_hero_image(src, alt):
                    result["hero_images"].append({
                        "src": _resolve_url(src, base_url),
                        "alt": alt,
                    })
            # Also check picture > source inside link
            source = a.find("source", srcset=True)
            if source and not img:
                srcset = source.get("srcset", "")
                parts = srcset.split(",")
                if parts:
                    src = parts[-1].strip().split(" ")[0]
                    if _is_hero_image(src, ""):
                        result["hero_images"].append({
                            "src": _resolve_url(src, base_url),
                            "alt": text,
                        })
    result["campaign_links"] = _dedup(result["campaign_links"], "text", 20)

    # Also grab images from hero/banner/carousel sections
    for class_kw in ["hero", "banner", "carousel", "slider", "slide", "swiper"]:
        for container in soup.find_all(
            attrs={"class": lambda c: c and class_kw in " ".join(c).lower()
                   if isinstance(c, list) else class_kw in str(c).lower()
                   if c else False}
        ):
            for img in container.find_all("img"):
                src = img.get("src") or img.get("data-src") or ""
                alt = (img.get("alt") or "").strip()
                if src and _is_hero_image(src, alt):
                    result["hero_images"].append({
                        "src": _resolve_url(src, base_url),
                        "alt": alt,
                    })
    result["hero_images"] = _dedup(result["hero_images"], "src", 12)

    # Nav categories
    nav = soup.find("nav") or soup.find(attrs={"role": "navigation"})
    if nav:
        seen_nav = set()
        for a in nav.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if text and 2 < len(text) < 50 and text.lower() not in seen_nav:
                seen_nav.add(text.lower())
                result["nav_categories"].append({
                    "text": text,
                    "url": _resolve_url(href, base_url),
                })
        result["nav_categories"] = result["nav_categories"][:25]

    # Promo texts
    seen_promos = set()
    for el in soup.find_all(["p", "div", "span"]):
        classes = el.get("class", [])
        class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
        has_promo_class = any(
            kw in class_str.lower()
            for kw in ["promo", "banner", "hero", "campaign", "collection"]
        )
        is_p = el.name == "p"
        if not has_promo_class and not is_p:
            continue
        text = el.get_text(strip=True)
        if not text or len(text) < 20 or len(text) > 300:
            continue
        if any(kw in text.lower() for kw in _PROMO_KEYWORDS):
            if text not in seen_promos:
                seen_promos.add(text)
                result["promo_texts"].append(text)
                if len(result["promo_texts"]) >= 10:
                    break


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def collect_website(
    competitor: Competitor,
    settings: CollectionSettings,
    week: str,
    screenshots_dir: Path | None = None,
    use_playwright: bool | None = None,
) -> dict:
    """Scrape a competitor's homepage.

    Tries Playwright first (handles JS sites, takes screenshots).
    Falls back to requests+BeautifulSoup if Playwright unavailable.
    """
    result = _empty_result(competitor)

    try:
        if use_playwright is True or (use_playwright is None and _pw_ok):
            _collect_playwright(competitor, settings, week,
                                screenshots_dir, result)
        else:
            _collect_http(competitor, settings, result)

        _run_theme_analysis(result)

        logger.info(
            "Collected %s: %d headlines, %d images, %d campaigns, %d themes",
            competitor.name, len(result["headlines"]),
            len(result["hero_images"]),
            len(result["campaign_links"]), len(result["theme_tags"]),
        )

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


# Check Playwright availability once at import time
logger.info("Checking Playwright availability...")
_pw_ok = _playwright_available()
if _pw_ok:
    logger.info("Playwright available - using headless browser")
else:
    logger.info("Playwright unavailable - using HTTP fallback")
