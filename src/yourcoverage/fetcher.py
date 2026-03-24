"""Fetch Instagram profile and post data using instaloader."""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import instaloader

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [60, 120, 300]
DELAY_BETWEEN_PROFILES = 5


@dataclass
class PostData:
    shortcode: str
    timestamp: datetime
    likes: int
    comments: int
    caption: str | None
    is_video: bool


@dataclass
class ProfileResult:
    username: str
    follower_count: int = 0
    following_count: int = 0
    is_private: bool = False
    posts: list[PostData] = field(default_factory=list)
    error: str | None = None


def fetch_profile(
    username: str, since: datetime, loader: instaloader.Instaloader
) -> ProfileResult:
    """Fetch a single Instagram profile and its posts since the given date."""
    for attempt in range(MAX_RETRIES):
        try:
            profile = instaloader.Profile.from_username(loader.context, username)

            result = ProfileResult(
                username=username,
                follower_count=profile.followers,
                following_count=profile.followees,
                is_private=profile.is_private,
            )

            if profile.is_private:
                result.error = "Profile is private"
                return result

            for post in profile.get_posts():
                if post.date_utc < since:
                    break
                result.posts.append(
                    PostData(
                        shortcode=post.shortcode,
                        timestamp=post.date_utc,
                        likes=post.likes,
                        comments=post.comments,
                        caption=post.caption,
                        is_video=post.is_video,
                    )
                )

            logger.info(
                "Fetched %s: %d posts, %d followers",
                username,
                len(result.posts),
                result.follower_count,
            )
            return result

        except instaloader.exceptions.TooManyRequestsException:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.warning(
                "Rate limited on %s, retrying in %ds (attempt %d/%d)",
                username,
                delay,
                attempt + 1,
                MAX_RETRIES,
            )
            time.sleep(delay)

        except instaloader.exceptions.ConnectionException as e:
            if attempt == 0:
                logger.warning("Connection error on %s, retrying in 10s: %s", username, e)
                time.sleep(10)
            else:
                return ProfileResult(username=username, error=str(e))

        except Exception as e:
            return ProfileResult(username=username, error=str(e))

    return ProfileResult(username=username, error="Max retries exceeded (rate limited)")


def fetch_all(usernames: list[str], months_back: int) -> list[ProfileResult]:
    """Fetch all competitor profiles."""
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
    )

    since = datetime.utcnow() - timedelta(days=months_back * 30)
    results = []

    for i, username in enumerate(usernames):
        logger.info("Fetching profile %d/%d: %s", i + 1, len(usernames), username)
        result = fetch_profile(username, since, loader)
        results.append(result)

        if i < len(usernames) - 1:
            time.sleep(DELAY_BETWEEN_PROFILES)

    return results
