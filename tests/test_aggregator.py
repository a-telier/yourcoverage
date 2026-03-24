"""Tests for monthly aggregation logic."""

from datetime import datetime

from yourcoverage.aggregator import aggregate
from yourcoverage.fetcher import PostData, ProfileResult


def _make_post(year: int, month: int, day: int, likes: int, comments: int) -> PostData:
    return PostData(
        shortcode=f"post_{year}_{month}_{day}",
        timestamp=datetime(year, month, day),
        likes=likes,
        comments=comments,
        caption=None,
        is_video=False,
    )


def test_basic_aggregation():
    result = ProfileResult(
        username="testuser",
        follower_count=1000,
        posts=[
            _make_post(2025, 1, 10, likes=100, comments=10),
            _make_post(2025, 1, 20, likes=200, comments=20),
            _make_post(2025, 2, 5, likes=300, comments=30),
        ],
    )
    metrics = aggregate([result])

    assert len(metrics) == 2

    jan = metrics[0]
    assert jan.username == "testuser"
    assert jan.year == 2025
    assert jan.month == 1
    assert jan.post_count == 2
    assert jan.total_likes == 300
    assert jan.total_comments == 30
    assert jan.avg_likes == 150.0
    assert jan.avg_comments == 15.0
    assert jan.engagement_rate == round((300 + 30) / (2 * 1000), 6)

    feb = metrics[1]
    assert feb.month == 2
    assert feb.post_count == 1
    assert feb.total_likes == 300
    assert feb.total_comments == 30


def test_skips_errored_profiles():
    result = ProfileResult(username="broken", error="Profile is private")
    metrics = aggregate([result])
    assert metrics == []


def test_zero_followers_engagement():
    result = ProfileResult(
        username="newuser",
        follower_count=0,
        posts=[_make_post(2025, 3, 1, likes=10, comments=5)],
    )
    metrics = aggregate([result])
    assert len(metrics) == 1
    assert metrics[0].engagement_rate == 0.0


def test_multiple_profiles():
    r1 = ProfileResult(
        username="alpha",
        follower_count=500,
        posts=[_make_post(2025, 1, 1, likes=50, comments=5)],
    )
    r2 = ProfileResult(
        username="beta",
        follower_count=1000,
        posts=[_make_post(2025, 1, 15, likes=100, comments=10)],
    )
    metrics = aggregate([r1, r2])
    assert len(metrics) == 2
    assert metrics[0].username == "alpha"
    assert metrics[1].username == "beta"
