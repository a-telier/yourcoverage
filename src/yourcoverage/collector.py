"""Weekly data collector: fetch Instagram posts and website homepage content."""

import hashlib
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import instaloader
import requests
from bs4 import BeautifulSoup

from .config import Competitor, CollectionSettings
from .storage import save_snapshot, thumbnails_dir, week_label
from .themes import analyze_post, analyze_week, generate_summary

logger = logging.getLogger(__name__)

DELAY_BETWEEN_PROFILES = 5
MAX_RETRIES = 3
RETRY_DELAYS = [60, 120, 300]


def _download_thumbnail(url: str, shortcode: str, week: str) -> str | None:
    """Download a post thumbnail image and return the local relative path."""
    try:
        tdir = thumbnails_dir(week)
        ext = ".jpg"
        filename = f"{shortcode}{ext}"
        filepath = tdir / filename
        if filepath.exists():
            return str(filepath.relative_to(Path("data")))

        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; YourCoverage/1.0)"
        })
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        return str(filepath.relative_to(Path("data")))
    except Exception as e:
        logger.warning("Failed to download thumbnail for %s: %s", shortcode, e)
        return None


def collect_instagram(
    competitor: Competitor,
    settings: CollectionSettings,
    loader: instaloader.Instaloader,
    week: str | None = None,
) -> dict:
    """Fetch Instagram posts for a single competitor."""
    week = week or week_label()
    username = competitor.instagram_username
    result = {
        "username": username,
        "name": competitor.name,
        "collected_at": datetime.utcnow().isoformat(),
        "week": week,
        "source": "instagram",
        "profile": {},
        "posts": [],
        "error": None,
    }

    for attempt in range(MAX_RETRIES):
        try:
            profile = instaloader.Profile.from_username(loader.context, username)
            result["profile"] = {
                "followers": profile.followers,
                "following": profile.followees,
                "posts_count": profile.mediacount,
                "biography": profile.biography,
                "is_private": profile.is_private,
                "profile_pic_url": str(profile.profile_pic_url),
            }

            if profile.is_private:
                result["error"] = "Profile is private"
                return result

            # Fetch recent posts
            count = 0
            for post in profile.get_posts():
                if count >= settings.posts_per_profile:
                    break

                post_data = {
                    "shortcode": post.shortcode,
                    "url": f"https://www.instagram.com/p/{post.shortcode}/",
                    "timestamp": post.date_utc.isoformat(),
                    "likes": post.likes,
                    "comments": post.comments,
                    "caption": post.caption,
                    "is_video": post.is_video,
                    "image_url": str(post.url),
                    "thumbnail_path": None,
                    "themes": analyze_post(post.caption or ""),
                }

                # Download thumbnail
                if settings.download_thumbnails and not post.is_video:
                    thumb_path = _download_thumbnail(str(post.url), post.shortcode, week)
                    post_data["thumbnail_path"] = thumb_path

                result["posts"].append(post_data)
                count += 1

            # Analyze themes across all posts
            result["theme_summary"] = analyze_week(result["posts"])
            result["content_summary"] = generate_summary(result["theme_summary"])

            logger.info(
                "Collected %s: %d posts, %d followers",
                username, len(result["posts"]), profile.followers,
            )
            return result

        except instaloader.exceptions.TooManyRequestsException:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.warning("Rate limited on %s, retrying in %ds", username, delay)
            time.sleep(delay)

        except instaloader.exceptions.ConnectionException as e:
            if attempt == 0:
                logger.warning("Connection error on %s, retrying: %s", username, e)
                time.sleep(10)
            else:
                result["error"] = str(e)
                return result

        except Exception as e:
            result["error"] = str(e)
            return result

    result["error"] = "Max retries exceeded (rate limited)"
    return result


def collect_website(competitor: Competitor, week: str | None = None) -> dict:
    """Scrape the homepage of a competitor's website for campaign/collection info."""
    week = week or week_label()
    result = {
        "url": competitor.website_url,
        "collected_at": datetime.utcnow().isoformat(),
        "week": week,
        "source": "website",
        "title": "",
        "meta_description": "",
        "hero_texts": [],
        "campaign_banners": [],
        "navigation_categories": [],
        "promo_texts": [],
        "error": None,
    }

    if not competitor.website_url:
        result["error"] = "No website URL configured"
        return result

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "en-US,en;q=0.9,sv;q=0.8,fr;q=0.7",
        }
        resp = requests.get(competitor.website_url, timeout=30, headers=headers)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Page title
        if soup.title:
            result["title"] = soup.title.string.strip() if soup.title.string else ""

        # Meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            result["meta_description"] = meta["content"].strip()

        # Hero/banner texts (large heading elements, promo banners)
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(strip=True)
            if text and len(text) > 3 and len(text) < 200:
                result["hero_texts"].append(text)

        # Links that look like campaign/collection pages
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            text = a.get_text(strip=True)
            if any(kw in href for kw in [
                "collection", "campaign", "new", "sale", "promo",
                "kollektion", "nouveau", "nuevo",
            ]):
                if text and len(text) > 2 and len(text) < 100:
                    result["campaign_banners"].append({
                        "text": text,
                        "url": a["href"],
                    })

        # Navigation categories (main nav items)
        nav = soup.find("nav") or soup.find(attrs={"role": "navigation"})
        if nav:
            for a in nav.find_all("a"):
                text = a.get_text(strip=True)
                if text and len(text) > 2 and len(text) < 50:
                    result["navigation_categories"].append(text)

        # Promotional text blocks
        for tag in soup.find_all(["p", "span", "div"]):
            text = tag.get_text(strip=True)
            if text and 20 < len(text) < 300:
                text_lower = text.lower()
                if any(kw in text_lower for kw in [
                    "collection", "new", "sale", "free", "offer", "discover",
                    "shop", "explore", "kampanj", "nouveau", "découvr",
                ]):
                    if text not in result["promo_texts"]:
                        result["promo_texts"].append(text)
                        if len(result["promo_texts"]) >= 10:
                            break

        # Deduplicate
        result["hero_texts"] = list(dict.fromkeys(result["hero_texts"]))[:15]
        result["campaign_banners"] = result["campaign_banners"][:10]
        result["navigation_categories"] = list(dict.fromkeys(result["navigation_categories"]))[:20]

        logger.info("Scraped website %s: %d hero texts, %d campaigns",
                     competitor.website_url,
                     len(result["hero_texts"]),
                     len(result["campaign_banners"]))

    except Exception as e:
        result["error"] = str(e)
        logger.warning("Failed to scrape %s: %s", competitor.website_url, e)

    return result


def collect_all(
    competitors: list[Competitor],
    settings: CollectionSettings,
    week: str | None = None,
    login_user: str | None = None,
    login_pass: str | None = None,
) -> dict[str, dict]:
    """Collect data for all competitors and save weekly snapshots."""
    week = week or week_label()

    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
    )

    # Optional Instagram login for better rate limits
    if login_user and login_pass:
        try:
            loader.login(login_user, login_pass)
            logger.info("Logged in to Instagram as %s", login_user)
        except Exception as e:
            logger.warning("Instagram login failed: %s", e)

    results = {}

    for i, competitor in enumerate(competitors):
        logger.info("Collecting %d/%d: %s", i + 1, len(competitors), competitor.name)

        # Collect Instagram data
        ig_data = collect_instagram(competitor, settings, loader, week)

        # Collect website data
        web_data = collect_website(competitor, week)

        # Combine and save
        snapshot = {
            "competitor": {
                "name": competitor.name,
                "instagram_username": competitor.instagram_username,
                "instagram_url": competitor.instagram_url,
                "website_url": competitor.website_url,
                "color": competitor.color,
            },
            "week": week,
            "collected_at": datetime.utcnow().isoformat(),
            "instagram": ig_data,
            "website": web_data,
        }

        save_snapshot(competitor.instagram_username, snapshot, week)
        results[competitor.instagram_username] = snapshot

        # Rate limiting between profiles
        if i < len(competitors) - 1:
            time.sleep(DELAY_BETWEEN_PROFILES)

    return results
