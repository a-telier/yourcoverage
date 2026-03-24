"""Aggregate post data into monthly metrics."""

from collections import defaultdict
from dataclasses import dataclass

from .fetcher import ProfileResult


@dataclass
class MonthlyMetrics:
    username: str
    year: int
    month: int
    post_count: int
    total_likes: int
    total_comments: int
    avg_likes: float
    avg_comments: float
    engagement_rate: float
    follower_count: int


def aggregate(results: list[ProfileResult]) -> list[MonthlyMetrics]:
    """Group posts by month and compute metrics for each profile."""
    metrics = []

    for result in results:
        if result.error and not result.posts:
            continue

        # Group posts by (year, month)
        monthly: dict[tuple[int, int], list] = defaultdict(list)
        for post in result.posts:
            key = (post.timestamp.year, post.timestamp.month)
            monthly[key].append(post)

        for (year, month), posts in sorted(monthly.items()):
            post_count = len(posts)
            total_likes = sum(p.likes for p in posts)
            total_comments = sum(p.comments for p in posts)

            avg_likes = total_likes / post_count
            avg_comments = total_comments / post_count

            if result.follower_count > 0 and post_count > 0:
                engagement_rate = (total_likes + total_comments) / (
                    post_count * result.follower_count
                )
            else:
                engagement_rate = 0.0

            metrics.append(
                MonthlyMetrics(
                    username=result.username,
                    year=year,
                    month=month,
                    post_count=post_count,
                    total_likes=total_likes,
                    total_comments=total_comments,
                    avg_likes=round(avg_likes, 2),
                    avg_comments=round(avg_comments, 2),
                    engagement_rate=round(engagement_rate, 6),
                    follower_count=result.follower_count,
                )
            )

    return sorted(metrics, key=lambda m: (m.username, m.year, m.month))
