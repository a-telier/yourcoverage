"""SQLite database for persistent historical storage."""

import sqlite3
from datetime import date, datetime
from pathlib import Path


SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS competitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    website_url TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#888888',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id INTEGER NOT NULL REFERENCES competitors(id),
    week TEXT NOT NULL,          -- ISO week label: '2026-W12'
    collected_at TEXT NOT NULL,
    page_url TEXT NOT NULL,      -- final URL after redirects
    page_title TEXT,
    meta_description TEXT,
    screenshot_path TEXT,        -- relative path to screenshot file
    raw_html_length INTEGER,     -- size of the page HTML
    error TEXT,                  -- NULL if successful
    UNIQUE(competitor_id, week)
);

CREATE TABLE IF NOT EXISTS headlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    tag TEXT NOT NULL,           -- 'h1', 'h2', 'h3'
    text TEXT NOT NULL,
    position INTEGER NOT NULL    -- order on page
);

CREATE TABLE IF NOT EXISTS campaign_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    text TEXT NOT NULL,
    url TEXT NOT NULL,
    position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS nav_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    text TEXT NOT NULL,
    url TEXT,
    position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS promo_texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    text TEXT NOT NULL,
    position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS theme_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    kind TEXT NOT NULL,          -- 'color', 'material', 'category', 'campaign'
    label TEXT NOT NULL,
    match_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_collections_week ON collections(week);
CREATE INDEX IF NOT EXISTS idx_collections_competitor ON collections(competitor_id);
CREATE INDEX IF NOT EXISTS idx_headlines_collection ON headlines(collection_id);
CREATE INDEX IF NOT EXISTS idx_theme_tags_collection ON theme_tags(collection_id);
"""


class Database:
    """SQLite database wrapper for yourcoverage."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA_SQL)
        # Check/set version
        row = self.conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            self.conn.execute("INSERT INTO schema_version (version) VALUES (?)",
                              (SCHEMA_VERSION,))
        self.conn.commit()

    def close(self):
        self.conn.close()

    # --- Competitors ---

    def upsert_competitor(self, slug: str, name: str, website_url: str,
                          color: str) -> int:
        """Insert or update a competitor, return its ID."""
        self.conn.execute("""
            INSERT INTO competitors (slug, name, website_url, color)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name=excluded.name,
                website_url=excluded.website_url,
                color=excluded.color
        """, (slug, name, website_url, color))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM competitors WHERE slug=?", (slug,)
        ).fetchone()
        return row["id"]

    def get_competitor(self, slug: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM competitors WHERE slug=?", (slug,)
        ).fetchone()
        return dict(row) if row else None

    def list_competitors(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM competitors ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Collections ---

    def save_collection(self, competitor_id: int, week: str,
                        page_data: dict) -> int:
        """Save a weekly collection. Returns collection ID."""
        # Delete existing collection for this competitor+week (re-collect)
        existing = self.conn.execute(
            "SELECT id FROM collections WHERE competitor_id=? AND week=?",
            (competitor_id, week)
        ).fetchone()
        if existing:
            cid = existing["id"]
            for table in ("headlines", "campaign_links", "nav_categories",
                          "promo_texts", "theme_tags"):
                self.conn.execute(f"DELETE FROM {table} WHERE collection_id=?",
                                  (cid,))
            self.conn.execute("DELETE FROM collections WHERE id=?", (cid,))

        self.conn.execute("""
            INSERT INTO collections
                (competitor_id, week, collected_at, page_url, page_title,
                 meta_description, screenshot_path, raw_html_length, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            competitor_id, week,
            page_data.get("collected_at", datetime.utcnow().isoformat()),
            page_data.get("page_url", ""),
            page_data.get("page_title"),
            page_data.get("meta_description"),
            page_data.get("screenshot_path"),
            page_data.get("raw_html_length"),
            page_data.get("error"),
        ))
        cid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Headlines
        for i, h in enumerate(page_data.get("headlines", [])):
            self.conn.execute(
                "INSERT INTO headlines (collection_id, tag, text, position) "
                "VALUES (?, ?, ?, ?)",
                (cid, h["tag"], h["text"], i)
            )

        # Campaign links
        for i, cl in enumerate(page_data.get("campaign_links", [])):
            self.conn.execute(
                "INSERT INTO campaign_links (collection_id, text, url, position) "
                "VALUES (?, ?, ?, ?)",
                (cid, cl["text"], cl["url"], i)
            )

        # Nav categories
        for i, nc in enumerate(page_data.get("nav_categories", [])):
            self.conn.execute(
                "INSERT INTO nav_categories (collection_id, text, url, position) "
                "VALUES (?, ?, ?, ?)",
                (cid, nc["text"], nc.get("url", ""), i)
            )

        # Promo texts
        for i, pt in enumerate(page_data.get("promo_texts", [])):
            self.conn.execute(
                "INSERT INTO promo_texts (collection_id, text, position) "
                "VALUES (?, ?, ?)",
                (cid, pt, i)
            )

        # Theme tags
        for tag in page_data.get("theme_tags", []):
            self.conn.execute(
                "INSERT INTO theme_tags (collection_id, kind, label, match_count) "
                "VALUES (?, ?, ?, ?)",
                (cid, tag["kind"], tag["label"], tag.get("match_count", 1))
            )

        self.conn.commit()
        return cid

    def get_collection(self, competitor_id: int, week: str) -> dict | None:
        """Load a single collection with all related data."""
        row = self.conn.execute(
            "SELECT * FROM collections WHERE competitor_id=? AND week=?",
            (competitor_id, week)
        ).fetchone()
        if not row:
            return None
        return self._hydrate_collection(dict(row))

    def _hydrate_collection(self, coll: dict) -> dict:
        """Load related data for a collection."""
        cid = coll["id"]

        coll["headlines"] = [dict(r) for r in self.conn.execute(
            "SELECT tag, text FROM headlines WHERE collection_id=? ORDER BY position",
            (cid,)
        ).fetchall()]

        coll["campaign_links"] = [dict(r) for r in self.conn.execute(
            "SELECT text, url FROM campaign_links WHERE collection_id=? ORDER BY position",
            (cid,)
        ).fetchall()]

        coll["nav_categories"] = [dict(r) for r in self.conn.execute(
            "SELECT text, url FROM nav_categories WHERE collection_id=? ORDER BY position",
            (cid,)
        ).fetchall()]

        coll["promo_texts"] = [r["text"] for r in self.conn.execute(
            "SELECT text FROM promo_texts WHERE collection_id=? ORDER BY position",
            (cid,)
        ).fetchall()]

        coll["theme_tags"] = [dict(r) for r in self.conn.execute(
            "SELECT kind, label, match_count FROM theme_tags "
            "WHERE collection_id=? ORDER BY match_count DESC",
            (cid,)
        ).fetchall()]

        return coll

    # --- Queries ---

    def list_weeks(self) -> list[str]:
        """List all weeks that have data, sorted chronologically."""
        rows = self.conn.execute(
            "SELECT DISTINCT week FROM collections ORDER BY week"
        ).fetchall()
        return [r["week"] for r in rows]

    def resolve_week_range(self, spec: str) -> list[str]:
        """Resolve a week range spec into a list of week labels."""
        all_weeks = self.list_weeks()
        if not all_weeks:
            return []

        spec = spec.strip()

        if spec == "all":
            return all_weeks

        if spec.startswith("latest"):
            n = int(spec.split("-")[1]) if "-" in spec else 4
            return all_weeks[-n:]

        # Explicit ISO range: "2026-W09:2026-W12"
        if "W" in spec:
            sep = ":" if ":" in spec else None
            if sep:
                start, end = spec.split(sep)
                return [w for w in all_weeks if start <= w <= end]
            return [w for w in all_weeks if w == spec]

        # Short: "9-12" or "9:12"
        sep = ":" if ":" in spec else "-"
        parts = spec.split(sep)
        if len(parts) == 2:
            year = date.today().isocalendar()[0]
            start = f"{year}-W{int(parts[0]):02d}"
            end = f"{year}-W{int(parts[1]):02d}"
            return [w for w in all_weeks if start <= w <= end]

        return all_weeks

    def get_weeks_data(self, weeks: list[str],
                       competitor_slugs: list[str] | None = None
                       ) -> dict[str, dict[str, dict]]:
        """Load all data for given weeks, grouped by competitor slug.

        Returns: {slug: {week: collection_dict}}
        """
        if competitor_slugs:
            placeholders = ",".join("?" for _ in competitor_slugs)
            comps = self.conn.execute(
                f"SELECT * FROM competitors WHERE slug IN ({placeholders})",
                competitor_slugs
            ).fetchall()
        else:
            comps = self.conn.execute("SELECT * FROM competitors").fetchall()

        result = {}
        for comp in comps:
            slug = comp["slug"]
            result[slug] = {"competitor": dict(comp), "weeks": {}}
            for week in weeks:
                coll = self.get_collection(comp["id"], week)
                if coll:
                    result[slug]["weeks"][week] = coll

        return result

    def get_month_data(self, year: int, month: int,
                       competitor_slug: str | None = None
                       ) -> list[dict]:
        """Get all collections for a specific month (for historical queries)."""
        # ISO weeks that fall in this month
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)

        # Get all weeks in range
        all_weeks = self.list_weeks()
        target_weeks = []
        for w in all_weeks:
            # Parse week label to get the Monday of that week
            parts = w.split("-W")
            if len(parts) == 2:
                wy, wn = int(parts[0]), int(parts[1])
                monday = date.fromisocalendar(wy, wn, 1)
                if start <= monday < end:
                    target_weeks.append(w)

        if not target_weeks:
            return []

        query = """
            SELECT c.*, comp.slug, comp.name as competitor_name
            FROM collections c
            JOIN competitors comp ON c.competitor_id = comp.id
            WHERE c.week IN ({})
        """.format(",".join("?" for _ in target_weeks))
        params = list(target_weeks)

        if competitor_slug:
            query += " AND comp.slug = ?"
            params.append(competitor_slug)

        query += " ORDER BY c.week, comp.name"

        rows = self.conn.execute(query, params).fetchall()
        return [self._hydrate_collection(dict(r)) for r in rows]
