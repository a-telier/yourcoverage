"""Generate HTML report from stored weekly data."""

import json
import html as html_mod
from datetime import date
from pathlib import Path

from .config import Config, Competitor
from .storage import load_snapshot, resolve_week_range, list_weeks
from .themes import generate_summary


def _esc(text: str) -> str:
    """HTML-escape text."""
    return html_mod.escape(str(text)) if text else ""


def _fmt_number(n: int | float) -> str:
    """Format large numbers: 1200000 -> 1.2M, 45000 -> 45K."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


def load_report_data(config: Config, week_spec: str | None = None) -> dict:
    """Load all stored data for the specified week range."""
    spec = week_spec or config.report.default_weeks
    weeks = resolve_week_range(spec)

    if not weeks:
        return {"weeks": [], "competitors": {}}

    data = {"weeks": weeks, "competitors": {}}

    for comp in config.competitors:
        username = comp.instagram_username
        comp_data = {
            "config": {
                "name": comp.name,
                "username": username,
                "color": comp.color,
                "website_url": comp.website_url,
            },
            "weekly": {},
        }

        for week in weeks:
            snapshot = load_snapshot(username, week)
            if snapshot:
                comp_data["weekly"][week] = snapshot

        data["competitors"][username] = comp_data

    return data


def _render_theme_tags(theme_summary: dict) -> str:
    """Render theme analysis as colored tag badges."""
    tags = []
    for color in theme_summary.get("top_colors", [])[:3]:
        tags.append(f'<span class="theme-tag color-tag">{_esc(color)}</span>')
    for mat in theme_summary.get("top_materials", [])[:3]:
        tags.append(f'<span class="theme-tag material-tag">{_esc(mat)}</span>')
    for cat in theme_summary.get("top_categories", [])[:3]:
        tags.append(f'<span class="theme-tag category-tag">{_esc(cat)}</span>')
    for camp in theme_summary.get("campaigns", [])[:2]:
        tags.append(f'<span class="theme-tag campaign-tag">{_esc(camp)}</span>')
    return "\n".join(tags)


def _render_post_grid(posts: list[dict], max_posts: int = 9) -> str:
    """Render a grid of Instagram post thumbnails."""
    html_parts = ['<div class="post-grid">']
    for post in posts[:max_posts]:
        shortcode = post.get("shortcode", "")
        post_url = post.get("url", f"https://www.instagram.com/p/{shortcode}/")
        image_url = post.get("image_url", "")
        thumbnail = post.get("thumbnail_path", "")
        likes = post.get("likes", 0)
        comments = post.get("comments", 0)
        caption = (post.get("caption") or "")[:120]
        is_video = post.get("is_video", False)

        # Use local thumbnail if available, else Instagram image URL
        img_src = f"../../data/{thumbnail}" if thumbnail else image_url

        # Post theme tags
        themes = post.get("themes", {})
        theme_parts = []
        for c in themes.get("categories", [])[:2]:
            theme_parts.append(c)
        for c in themes.get("colors", [])[:1]:
            theme_parts.append(c)
        theme_line = " · ".join(theme_parts) if theme_parts else ""

        html_parts.append(f'''
        <a href="{_esc(post_url)}" target="_blank" class="post-card" rel="noopener">
            <div class="post-img" style="background-image: url('{_esc(img_src)}')">
                {"<div class='video-badge'>▶</div>" if is_video else ""}
            </div>
            <div class="post-stats">
                <span>♥ {_fmt_number(likes)}</span>
                <span>💬 {_fmt_number(comments)}</span>
            </div>
            {f'<div class="post-theme">{_esc(theme_line)}</div>' if theme_line else ""}
            {f'<div class="post-caption">{_esc(caption)}</div>' if caption else ""}
        </a>''')

    html_parts.append('</div>')
    return "\n".join(html_parts)


def _render_website_section(web_data: dict) -> str:
    """Render website homepage analysis section."""
    if not web_data or web_data.get("error"):
        error = web_data.get("error", "No data") if web_data else "No data"
        return f'<div class="web-notice">Website: {_esc(error)}</div>'

    parts = ['<div class="website-info">']

    hero_texts = web_data.get("hero_texts", [])
    if hero_texts:
        parts.append('<div class="web-heroes">')
        parts.append('<div class="web-label">Homepage Headlines</div>')
        for text in hero_texts[:5]:
            parts.append(f'<div class="web-hero-text">{_esc(text)}</div>')
        parts.append('</div>')

    campaigns = web_data.get("campaign_banners", [])
    if campaigns:
        parts.append('<div class="web-campaigns">')
        parts.append('<div class="web-label">Active Campaigns</div>')
        for camp in campaigns[:5]:
            parts.append(f'<div class="web-campaign">{_esc(camp["text"])}</div>')
        parts.append('</div>')

    promos = web_data.get("promo_texts", [])
    if promos:
        parts.append('<div class="web-promos">')
        parts.append('<div class="web-label">Promotional Content</div>')
        for promo in promos[:3]:
            parts.append(f'<div class="web-promo-text">{_esc(promo)}</div>')
        parts.append('</div>')

    parts.append('</div>')
    return "\n".join(parts)


def generate_report(config: Config, week_spec: str | None = None) -> str:
    """Generate the full HTML report."""
    data = load_report_data(config, week_spec)
    weeks = data["weeks"]
    competitors = data["competitors"]

    week_range_label = f"{weeks[0]} to {weeks[-1]}" if len(weeks) > 1 else (weeks[0] if weeks else "No data")
    generated_at = date.today().isoformat()

    # Build competitor tabs and panels
    comp_tabs = []
    comp_panels = []

    for i, (username, comp_data) in enumerate(competitors.items()):
        cfg = comp_data["config"]
        name = cfg["name"]
        color = cfg["color"]
        active = "active" if i == 0 else ""

        comp_tabs.append(
            f'<div class="tab {active}" onclick="selectCompetitor(\'{username}\', this)" '
            f'style="--comp-color: {color}">{_esc(name)}</div>'
        )

        # Aggregate data across weeks
        all_posts = []
        total_likes = 0
        total_comments = 0
        total_posts = 0
        followers = 0
        theme_summaries = []
        website_data = None

        for week in reversed(weeks):  # Most recent first
            snapshot = comp_data["weekly"].get(week)
            if not snapshot:
                continue

            ig = snapshot.get("instagram", {})
            prof = ig.get("profile", {})
            if prof.get("followers"):
                followers = max(followers, prof["followers"])

            posts = ig.get("posts", [])
            all_posts.extend(posts)
            total_likes += sum(p.get("likes", 0) for p in posts)
            total_comments += sum(p.get("comments", 0) for p in posts)
            total_posts += len(posts)

            if ig.get("theme_summary"):
                theme_summaries.append(ig["theme_summary"])

            web = snapshot.get("website")
            if web and not web.get("error"):
                website_data = web  # Use most recent

        avg_likes = total_likes / total_posts if total_posts else 0
        engagement = (total_likes + total_comments) / (total_posts * followers) if (total_posts and followers) else 0

        # Merge theme summaries
        merged_themes = {
            "top_colors": [], "top_materials": [], "top_categories": [], "campaigns": [],
            "color_detail": {}, "material_detail": {}, "category_detail": {}, "campaign_detail": {},
        }
        if theme_summaries:
            from collections import Counter
            color_c, mat_c, cat_c, camp_c = Counter(), Counter(), Counter(), Counter()
            for ts in theme_summaries:
                color_c.update(ts.get("color_detail", {}))
                mat_c.update(ts.get("material_detail", {}))
                cat_c.update(ts.get("category_detail", {}))
                camp_c.update(ts.get("campaign_detail", {}))
            merged_themes["top_colors"] = [c for c, _ in color_c.most_common(5)]
            merged_themes["top_materials"] = [m for m, _ in mat_c.most_common(5)]
            merged_themes["top_categories"] = [c for c, _ in cat_c.most_common(5)]
            merged_themes["campaigns"] = [c for c, _ in camp_c.most_common(3)]

        content_summary = generate_summary(merged_themes)

        # Build weekly breakdown for table
        weekly_rows = []
        for week in reversed(weeks):
            snapshot = comp_data["weekly"].get(week)
            if not snapshot:
                weekly_rows.append(f'''
                <tr><td>{_esc(week)}</td><td colspan="5" class="no-data">No data collected</td></tr>''')
                continue
            ig = snapshot.get("instagram", {})
            posts = ig.get("posts", [])
            w_likes = sum(p.get("likes", 0) for p in posts)
            w_comments = sum(p.get("comments", 0) for p in posts)
            w_followers = ig.get("profile", {}).get("followers", 0)
            w_eng = (w_likes + w_comments) / (len(posts) * w_followers) if (posts and w_followers) else 0

            eng_class = "eng-high" if w_eng > 0.03 else "eng-mid" if w_eng > 0.01 else "eng-low"
            weekly_rows.append(f'''
                <tr>
                    <td>{_esc(week)}</td>
                    <td>{len(posts)}</td>
                    <td>{_fmt_number(w_likes)}</td>
                    <td>{_fmt_number(w_comments)}</td>
                    <td><span class="eng-badge {eng_class}">{w_eng:.2%}</span></td>
                    <td>{_esc(ig.get("content_summary", ""))}</td>
                </tr>''')

        display = "block" if i == 0 else "none"
        panel = f'''
    <div class="competitor-panel" id="panel-{username}" style="display:{display}">
        <!-- Summary stats -->
        <div class="overview">
            <div class="stat-card">
                <div class="label">Followers</div>
                <div class="value">{_fmt_number(followers)}</div>
            </div>
            <div class="stat-card">
                <div class="label">Posts ({len(weeks)}w)</div>
                <div class="value">{total_posts}</div>
            </div>
            <div class="stat-card">
                <div class="label">Avg Likes</div>
                <div class="value">{_fmt_number(avg_likes)}</div>
            </div>
            <div class="stat-card">
                <div class="label">Engagement</div>
                <div class="value">{engagement:.2%}</div>
            </div>
        </div>

        <!-- Content summary -->
        <div class="content-summary">
            <div class="section-title">Content Themes</div>
            <div class="summary-text">{_esc(content_summary)}</div>
            <div class="theme-tags">
                {_render_theme_tags(merged_themes)}
            </div>
        </div>

        <!-- Post grid -->
        <div class="section-title">Recent Posts</div>
        {_render_post_grid(all_posts)}

        <!-- Website insights -->
        <div class="section-title">Website Homepage</div>
        {_render_website_section(website_data)}

        <!-- Weekly breakdown table -->
        <div class="section-title" style="margin-top: 20px;">Weekly Breakdown</div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Week</th>
                        <th>Posts</th>
                        <th>Likes</th>
                        <th>Comments</th>
                        <th>Eng.</th>
                        <th>Theme</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(weekly_rows)}
                </tbody>
            </table>
        </div>
    </div>'''
        comp_panels.append(panel)

    # Comparison cards
    comp_cards = []
    for username, comp_data in competitors.items():
        cfg = comp_data["config"]
        all_posts = []
        followers = 0
        for week in weeks:
            snapshot = comp_data["weekly"].get(week)
            if not snapshot:
                continue
            ig = snapshot.get("instagram", {})
            prof = ig.get("profile", {})
            if prof.get("followers"):
                followers = max(followers, prof["followers"])
            all_posts.extend(ig.get("posts", []))

        total_likes = sum(p.get("likes", 0) for p in all_posts)
        total_comments = sum(p.get("comments", 0) for p in all_posts)
        eng = (total_likes + total_comments) / (len(all_posts) * followers) if (all_posts and followers) else 0
        eng_class = "eng-high" if eng > 0.03 else "eng-mid" if eng > 0.01 else "eng-low"

        comp_cards.append(f'''
        <div class="comp-card" style="border-left: 3px solid {cfg["color"]}">
            <div class="comp-header">
                <span class="comp-name">{_esc(cfg["name"])}</span>
                <span class="comp-followers">{_fmt_number(followers)} followers</span>
            </div>
            <div class="comp-metrics">
                <div class="comp-metric">
                    <div class="val">{len(all_posts)}</div>
                    <div class="lbl">Posts</div>
                </div>
                <div class="comp-metric">
                    <div class="val">{_fmt_number(total_likes)}</div>
                    <div class="lbl">Likes</div>
                </div>
                <div class="comp-metric">
                    <div class="val"><span class="eng-badge {eng_class}">{eng:.2%}</span></div>
                    <div class="lbl">Engagement</div>
                </div>
            </div>
        </div>''')

    return _build_html(
        week_range_label=week_range_label,
        generated_at=generated_at,
        comp_tabs="\n".join(comp_tabs),
        comp_panels="\n".join(comp_panels),
        comp_cards="\n".join(comp_cards),
        weeks=weeks,
    )


def _build_html(
    week_range_label: str,
    generated_at: str,
    comp_tabs: str,
    comp_panels: str,
    comp_cards: str,
    weeks: list[str],
) -> str:
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YourCoverage — Competitor Analysis</title>
    <style>
        :root {{
            --bg: #0d1117;
            --card: #161b22;
            --border: #30363d;
            --text: #e6edf3;
            --muted: #8b949e;
            --accent: #58a6ff;
            --green: #3fb950;
            --red: #f85149;
            --orange: #d29922;
            --purple: #bc8cff;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 16px;
            padding-bottom: 80px;
            -webkit-font-smoothing: antialiased;
        }}

        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .header h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
        .header p {{ font-size: 13px; color: var(--muted); }}
        .badge {{
            display: inline-block;
            background: rgba(88, 166, 255, 0.15);
            color: var(--accent);
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 12px;
            margin-top: 8px;
        }}

        /* Tabs */
        .tabs {{
            display: flex; gap: 8px; margin-bottom: 20px;
            overflow-x: auto; -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }}
        .tabs::-webkit-scrollbar {{ display: none; }}
        .tab {{
            flex-shrink: 0; padding: 8px 16px; border-radius: 8px;
            border: 1px solid var(--border); background: var(--card);
            color: var(--muted); font-size: 14px; font-weight: 500;
            cursor: pointer; transition: all 0.2s;
        }}
        .tab.active {{
            background: var(--comp-color, var(--accent));
            color: #fff; border-color: var(--comp-color, var(--accent));
        }}

        /* View toggle */
        .view-toggle {{
            display: flex; gap: 0; margin-bottom: 20px;
            border-radius: 8px; overflow: hidden; border: 1px solid var(--border);
        }}
        .view-btn {{
            flex: 1; padding: 10px; text-align: center;
            background: var(--card); color: var(--muted);
            font-size: 13px; font-weight: 500; cursor: pointer;
            border: none; transition: all 0.2s;
        }}
        .view-btn.active {{ background: var(--accent); color: #fff; }}
        .view-btn + .view-btn {{ border-left: 1px solid var(--border); }}

        .view-section {{ display: none; }}
        .view-section.active {{ display: block; }}

        /* Stats grid */
        .overview {{
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 10px; margin-bottom: 20px;
        }}
        .stat-card {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 14px;
        }}
        .stat-card .label {{
            font-size: 11px; color: var(--muted);
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
        }}
        .stat-card .value {{ font-size: 22px; font-weight: 700; }}

        /* Content summary & themes */
        .content-summary {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 16px; margin-bottom: 20px;
        }}
        .summary-text {{
            font-size: 14px; color: var(--text); margin-bottom: 10px;
            line-height: 1.5;
        }}
        .theme-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
        .theme-tag {{
            display: inline-block; font-size: 11px; font-weight: 600;
            padding: 3px 10px; border-radius: 12px;
        }}
        .color-tag {{ background: rgba(188,140,255,0.15); color: var(--purple); }}
        .material-tag {{ background: rgba(210,153,34,0.15); color: var(--orange); }}
        .category-tag {{ background: rgba(63,185,80,0.15); color: var(--green); }}
        .campaign-tag {{ background: rgba(248,81,73,0.15); color: var(--red); }}

        /* Post grid */
        .post-grid {{
            display: grid; grid-template-columns: repeat(3, 1fr);
            gap: 8px; margin-bottom: 20px;
        }}
        .post-card {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 10px; overflow: hidden;
            text-decoration: none; color: var(--text);
            transition: transform 0.2s;
        }}
        .post-card:active {{ transform: scale(0.97); }}
        .post-img {{
            width: 100%; padding-bottom: 100%;
            background-size: cover; background-position: center;
            background-color: var(--border); position: relative;
        }}
        .video-badge {{
            position: absolute; top: 6px; right: 6px;
            background: rgba(0,0,0,0.7); color: #fff;
            font-size: 10px; padding: 2px 6px; border-radius: 4px;
        }}
        .post-stats {{
            display: flex; justify-content: space-between;
            padding: 6px 8px; font-size: 11px; color: var(--muted);
        }}
        .post-theme {{
            padding: 0 8px 4px; font-size: 10px; color: var(--accent);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .post-caption {{
            padding: 0 8px 8px; font-size: 10px; color: var(--muted);
            display: -webkit-box; -webkit-line-clamp: 2;
            -webkit-box-orient: vertical; overflow: hidden;
            line-height: 1.3;
        }}

        /* Website section */
        .website-info {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 16px; margin-bottom: 20px;
        }}
        .web-label {{
            font-size: 11px; color: var(--accent); text-transform: uppercase;
            letter-spacing: 0.5px; margin-bottom: 8px; font-weight: 600;
        }}
        .web-hero-text {{
            font-size: 13px; color: var(--text); padding: 4px 0;
            border-bottom: 1px solid var(--border);
        }}
        .web-heroes, .web-campaigns, .web-promos {{ margin-bottom: 12px; }}
        .web-campaign {{
            font-size: 12px; color: var(--orange); padding: 3px 0;
        }}
        .web-promo-text {{
            font-size: 12px; color: var(--muted); padding: 4px 0;
            line-height: 1.4;
        }}
        .web-notice {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 16px; margin-bottom: 20px;
            color: var(--muted); font-size: 13px;
        }}

        /* Table */
        .table-wrapper {{
            overflow-x: auto; -webkit-overflow-scrolling: touch;
            margin-bottom: 24px; border-radius: 12px;
            border: 1px solid var(--border);
        }}
        table {{
            width: 100%; border-collapse: collapse;
            font-size: 13px; min-width: 550px;
        }}
        thead th {{
            background: var(--card); padding: 10px 12px;
            text-align: left; font-weight: 600; color: var(--muted);
            font-size: 11px; text-transform: uppercase;
            letter-spacing: 0.5px; position: sticky; top: 0;
        }}
        tbody td {{
            padding: 10px 12px; border-top: 1px solid var(--border);
        }}
        tbody tr:nth-child(even) {{ background: rgba(255,255,255,0.02); }}
        .no-data {{ color: var(--muted); font-style: italic; }}

        .eng-badge {{
            display: inline-block; padding: 2px 8px;
            border-radius: 10px; font-weight: 600; font-size: 12px;
        }}
        .eng-high {{ background: rgba(63,185,80,0.15); color: var(--green); }}
        .eng-mid {{ background: rgba(210,153,34,0.15); color: var(--orange); }}
        .eng-low {{ background: rgba(248,81,73,0.15); color: var(--red); }}

        /* Comparison cards */
        .comparison-cards {{ display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }}
        .comp-card {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 16px;
        }}
        .comp-header {{
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 12px;
        }}
        .comp-name {{ font-size: 16px; font-weight: 700; }}
        .comp-followers {{ font-size: 12px; color: var(--muted); }}
        .comp-metrics {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }}
        .comp-metric {{ text-align: center; }}
        .comp-metric .val {{ font-size: 16px; font-weight: 700; }}
        .comp-metric .lbl {{
            font-size: 10px; color: var(--muted); text-transform: uppercase;
        }}

        .section-title {{
            font-size: 15px; font-weight: 600;
            margin-bottom: 12px; color: var(--muted);
        }}

        .footer {{
            text-align: center; padding: 20px 0;
            color: var(--muted); font-size: 12px;
            border-top: 1px solid var(--border); margin-top: 20px;
        }}

        /* Week selector */
        .week-selector {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 12px 16px; margin-bottom: 20px;
        }}
        .week-selector label {{
            font-size: 12px; color: var(--muted); margin-right: 8px;
        }}
        .week-selector select {{
            background: var(--bg); color: var(--text);
            border: 1px solid var(--border); border-radius: 6px;
            padding: 6px 10px; font-size: 13px;
        }}
    </style>
</head>
<body>

<div class="header">
    <h1>YourCoverage</h1>
    <p>Instagram & Website Competitor Analysis</p>
    <span class="badge">{_esc(week_range_label)} — Generated {_esc(generated_at)}</span>
</div>

<!-- View Toggle -->
<div class="view-toggle">
    <button class="view-btn active" onclick="switchView('overview')">Overview</button>
    <button class="view-btn" onclick="switchView('compare')">Compare</button>
</div>

<!-- OVERVIEW VIEW -->
<div id="view-overview" class="view-section active">
    <div class="tabs" id="comp-tabs">
        {comp_tabs}
    </div>
    {comp_panels}
</div>

<!-- COMPARE VIEW -->
<div id="view-compare" class="view-section">
    <div class="section-title">Competitor Comparison ({_esc(week_range_label)})</div>
    <div class="comparison-cards">
        {comp_cards}
    </div>
</div>

<div class="footer">
    YourCoverage — Data collected {_esc(week_range_label)}
</div>

<script>
function switchView(view) {{
    document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('view-' + view).classList.add('active');
    event.target.classList.add('active');
}}

function selectCompetitor(username, el) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    document.querySelectorAll('.competitor-panel').forEach(p => p.style.display = 'none');
    document.getElementById('panel-' + username).style.display = 'block';
}}
</script>

</body>
</html>'''


def write_report(config: Config, week_spec: str | None = None) -> Path:
    """Generate and write the HTML report to disk."""
    html = generate_report(config, week_spec)
    output_dir = config.report.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "index.html"
    with open(filepath, "w") as f:
        f.write(html)
    return filepath
