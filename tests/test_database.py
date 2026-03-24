"""Tests for SQLite database."""

import pytest
from yourcoverage.database import Database


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    yield d
    d.close()


class TestCompetitors:
    def test_upsert_and_get(self, db):
        cid = db.upsert_competitor("zarahome", "Zara Home",
                                    "https://zarahome.com", "#c4a35a")
        comp = db.get_competitor("zarahome")
        assert comp["name"] == "Zara Home"
        assert comp["id"] == cid

    def test_upsert_updates_existing(self, db):
        db.upsert_competitor("test", "Old Name", "https://old.com", "#000")
        db.upsert_competitor("test", "New Name", "https://new.com", "#fff")
        comp = db.get_competitor("test")
        assert comp["name"] == "New Name"

    def test_list_competitors(self, db):
        db.upsert_competitor("a", "A Brand", "https://a.com", "#111")
        db.upsert_competitor("b", "B Brand", "https://b.com", "#222")
        comps = db.list_competitors()
        assert len(comps) == 2


class TestCollections:
    def test_save_and_load(self, db):
        cid = db.upsert_competitor("test", "Test", "https://test.com", "#000")
        page_data = {
            "collected_at": "2026-03-24T12:00:00",
            "page_url": "https://test.com",
            "page_title": "Test Page",
            "meta_description": "A test page",
            "screenshot_path": None,
            "raw_html_length": 5000,
            "error": None,
            "headlines": [
                {"tag": "h1", "text": "Welcome"},
                {"tag": "h2", "text": "New Collection"},
            ],
            "campaign_links": [
                {"text": "Spring Sale", "url": "/sale/spring"},
            ],
            "nav_categories": [
                {"text": "Bedding", "url": "/bedding"},
            ],
            "promo_texts": ["Discover our new spring collection"],
            "theme_tags": [
                {"kind": "campaign", "label": "seasonal", "match_count": 2},
                {"kind": "category", "label": "bedding", "match_count": 1},
            ],
        }
        db.save_collection(cid, "2026-W12", page_data)

        coll = db.get_collection(cid, "2026-W12")
        assert coll is not None
        assert coll["page_title"] == "Test Page"
        assert len(coll["headlines"]) == 2
        assert coll["headlines"][0]["text"] == "Welcome"
        assert len(coll["campaign_links"]) == 1
        assert coll["campaign_links"][0]["text"] == "Spring Sale"
        assert len(coll["theme_tags"]) == 2
        assert coll["promo_texts"] == ["Discover our new spring collection"]

    def test_recollect_replaces(self, db):
        cid = db.upsert_competitor("test", "Test", "https://test.com", "#000")
        data1 = {
            "page_url": "https://test.com", "headlines": [{"tag": "h1", "text": "Old"}],
            "campaign_links": [], "nav_categories": [], "promo_texts": [], "theme_tags": [],
        }
        data2 = {
            "page_url": "https://test.com", "headlines": [{"tag": "h1", "text": "New"}],
            "campaign_links": [], "nav_categories": [], "promo_texts": [], "theme_tags": [],
        }
        db.save_collection(cid, "2026-W12", data1)
        db.save_collection(cid, "2026-W12", data2)
        coll = db.get_collection(cid, "2026-W12")
        assert coll["headlines"][0]["text"] == "New"


class TestQueries:
    def test_list_weeks(self, db):
        cid = db.upsert_competitor("test", "Test", "https://test.com", "#000")
        for week in ["2026-W10", "2026-W11", "2026-W12"]:
            db.save_collection(cid, week, {
                "page_url": "https://test.com",
                "headlines": [], "campaign_links": [],
                "nav_categories": [], "promo_texts": [], "theme_tags": [],
            })
        weeks = db.list_weeks()
        assert weeks == ["2026-W10", "2026-W11", "2026-W12"]

    def test_resolve_latest(self, db):
        cid = db.upsert_competitor("test", "Test", "https://test.com", "#000")
        for week in ["2026-W10", "2026-W11", "2026-W12", "2026-W13"]:
            db.save_collection(cid, week, {
                "page_url": "https://test.com",
                "headlines": [], "campaign_links": [],
                "nav_categories": [], "promo_texts": [], "theme_tags": [],
            })
        result = db.resolve_week_range("latest-2")
        assert result == ["2026-W12", "2026-W13"]

    def test_resolve_all(self, db):
        cid = db.upsert_competitor("test", "Test", "https://test.com", "#000")
        for week in ["2026-W10", "2026-W11"]:
            db.save_collection(cid, week, {
                "page_url": "https://test.com",
                "headlines": [], "campaign_links": [],
                "nav_categories": [], "promo_texts": [], "theme_tags": [],
            })
        assert len(db.resolve_week_range("all")) == 2

    def test_resolve_empty(self, db):
        assert db.resolve_week_range("latest-4") == []
