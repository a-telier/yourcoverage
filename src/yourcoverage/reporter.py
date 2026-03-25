"""Generate HTML report from stored website content data."""

import html as html_mod
from datetime import date
from pathlib import Path

from .config import Config
from .database import Database
from .themes import summarize_themes, generate_summary


def _esc(text: str) -> str:
    return html_mod.escape(str(text)) if text else ""


def write_report(config: Config, db: Database,
                 week_spec: str | None = None) -> Path:
    """Generate and write the HTML report to disk."""
    spec = week_spec or config.report.default_weeks
    weeks = db.resolve_week_range(spec)

    if not weeks:
        weeks_data = {}
    else:
        slugs = [c.slug for c in config.competitors]
        weeks_data = db.get_weeks_data(weeks, slugs)

    html = _generate_html(config, weeks, weeks_data)
    output_dir = config.report.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "index.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


def _generate_html(config: Config, weeks: list[str],
                   weeks_data: dict) -> str:
    week_range = (f"{weeks[0]} to {weeks[-1]}" if len(weeks) > 1
                  else (weeks[0] if weeks else "No data"))
    generated = date.today().isoformat()

    # Build competitor sections
    comp_tabs = []
    comp_panels = []
    comp_cards = []

    for i, comp in enumerate(config.competitors):
        slug = comp.slug
        data = weeks_data.get(slug, {"competitor": {}, "weeks": {}})
        active = "active" if i == 0 else ""
        display = "block" if i == 0 else "none"

        comp_tabs.append(
            f'<div class="tab {active}" onclick="selectCompetitor(\'{slug}\', this)" '
            f'style="--comp-color: {comp.color}">{_esc(comp.name)}</div>'
        )

        # Aggregate themes across all weeks
        all_theme_tags = []
        all_headlines = []
        all_campaigns = []
        latest_screenshot = None
        n_weeks_with_data = 0

        for week in reversed(weeks):
            coll = data.get("weeks", {}).get(week)
            if not coll or coll.get("error"):
                continue
            n_weeks_with_data += 1
            all_theme_tags.extend(coll.get("theme_tags", []))
            all_headlines.extend(coll.get("headlines", []))
            all_campaigns.extend(coll.get("campaign_links", []))
            if not latest_screenshot and coll.get("screenshot_path"):
                latest_screenshot = coll["screenshot_path"]

        theme_summary = summarize_themes(all_theme_tags)
        summary_text = generate_summary(theme_summary)

        # --- Panel content ---
        panel_parts = []

        # Source link
        panel_parts.append(
            f'<a href="{_esc(comp.website_url)}" target="_blank" rel="noopener" '
            f'class="source-link">{_esc(comp.website_url)}</a>'
        )

        # Screenshot (if available)
        if latest_screenshot:
            panel_parts.append(
                f'<div class="screenshot-wrapper">'
                f'<img src="../../{_esc(latest_screenshot)}" alt="Homepage screenshot" '
                f'class="screenshot" loading="lazy">'
                f'</div>'
            )

        # Theme summary
        panel_parts.append(f'''
        <div class="content-summary">
            <div class="section-title">Content Themes</div>
            <div class="summary-text">{_esc(summary_text)}</div>
            <div class="theme-tags">
                {_render_theme_tags(theme_summary)}
            </div>
        </div>''')

        # Weekly content breakdown
        panel_parts.append(
            '<div class="section-title">Weekly Content</div>'
        )
        for week in reversed(weeks):
            coll = data.get("weeks", {}).get(week)
            panel_parts.append(_render_week_card(week, coll, comp))

        # Comparison card
        comp_cards.append(_render_comparison_card(
            comp, n_weeks_with_data, len(all_headlines),
            len(all_campaigns), theme_summary,
        ))

        comp_panels.append(
            f'<div class="competitor-panel" id="panel-{slug}" '
            f'style="display:{display}">'
            + "\n".join(panel_parts)
            + '</div>'
        )

    return _build_html(
        week_range=week_range,
        generated=generated,
        comp_tabs="\n".join(comp_tabs),
        comp_panels="\n".join(comp_panels),
        comp_cards="\n".join(comp_cards),
    )


def _render_theme_tags(theme_summary: dict) -> str:
    tags = []
    for c in theme_summary.get("top_colors", [])[:3]:
        tags.append(f'<span class="theme-tag color-tag">{_esc(c)}</span>')
    for m in theme_summary.get("top_materials", [])[:3]:
        tags.append(f'<span class="theme-tag material-tag">{_esc(m)}</span>')
    for c in theme_summary.get("top_categories", [])[:3]:
        tags.append(f'<span class="theme-tag category-tag">{_esc(c)}</span>')
    for c in theme_summary.get("campaigns", [])[:2]:
        tags.append(f'<span class="theme-tag campaign-tag">{_esc(c)}</span>')
    return "\n".join(tags)


def _render_week_card(week: str, coll: dict | None, comp) -> str:
    if not coll:
        return (f'<div class="week-card empty">'
                f'<div class="week-label">{_esc(week)}</div>'
                f'<div class="no-data">No data collected</div></div>')

    if coll.get("error"):
        return (f'<div class="week-card error">'
                f'<div class="week-label">{_esc(week)}</div>'
                f'<div class="error-text">Error: {_esc(coll["error"])}</div>'
                f'</div>')

    parts = [f'<div class="week-card">',
             f'<div class="week-header">',
             f'<span class="week-label">{_esc(week)}</span>',
             f'<span class="week-meta">{_esc(coll.get("page_title", ""))}</span>',
             f'</div>']

    # Headlines
    headlines = coll.get("headlines", [])
    if headlines:
        parts.append('<div class="week-headlines">')
        for h in headlines[:8]:
            tag_class = f"htag-{h['tag']}"
            parts.append(
                f'<div class="headline {tag_class}">'
                f'<span class="htag">{h["tag"]}</span> {_esc(h["text"])}</div>'
            )
        if len(headlines) > 8:
            parts.append(
                f'<div class="more-count">+{len(headlines) - 8} more</div>'
            )
        parts.append('</div>')

    # Campaign links
    campaigns = coll.get("campaign_links", [])
    if campaigns:
        parts.append('<div class="week-campaigns">')
        parts.append('<div class="subsection-label">Campaigns & Collections</div>')
        for cl in campaigns[:6]:
            parts.append(
                f'<a href="{_esc(cl["url"])}" target="_blank" rel="noopener" '
                f'class="campaign-link">{_esc(cl["text"])}</a>'
            )
        parts.append('</div>')

    # Promo texts
    promos = coll.get("promo_texts", [])
    if promos:
        parts.append('<div class="week-promos">')
        parts.append('<div class="subsection-label">Promotional Messages</div>')
        for p in promos[:3]:
            parts.append(f'<div class="promo-text">{_esc(p)}</div>')
        parts.append('</div>')

    # Theme tags for this week
    tags = coll.get("theme_tags", [])
    if tags:
        summary = summarize_themes(tags)
        parts.append('<div class="week-themes">')
        parts.append(_render_theme_tags(summary))
        parts.append('</div>')

    parts.append('</div>')
    return "\n".join(parts)


def _render_comparison_card(comp, n_weeks, n_headlines, n_campaigns,
                            theme_summary) -> str:
    summary = generate_summary(theme_summary)
    return f'''
    <div class="comp-card" style="border-left: 3px solid {comp.color}">
        <div class="comp-header">
            <span class="comp-name">{_esc(comp.name)}</span>
            <a href="{_esc(comp.website_url)}" target="_blank" rel="noopener"
               class="comp-url">{_esc(comp.website_url)}</a>
        </div>
        <div class="comp-metrics">
            <div class="comp-metric">
                <div class="val">{n_weeks}</div>
                <div class="lbl">Weeks</div>
            </div>
            <div class="comp-metric">
                <div class="val">{n_headlines}</div>
                <div class="lbl">Headlines</div>
            </div>
            <div class="comp-metric">
                <div class="val">{n_campaigns}</div>
                <div class="lbl">Campaigns</div>
            </div>
        </div>
        <div class="comp-summary">{_esc(summary)}</div>
        <div class="comp-themes">{_render_theme_tags(theme_summary)}</div>
    </div>'''


def _build_html(week_range, generated, comp_tabs, comp_panels,
                comp_cards) -> str:
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YourCoverage — Competitor Content Analysis</title>
    <style>
        :root {{
            --bg: #0d1117; --card: #161b22; --border: #30363d;
            --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
            --green: #3fb950; --red: #f85149; --orange: #d29922;
            --purple: #bc8cff;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg); color: var(--text);
            padding: 16px; padding-bottom: 80px;
            -webkit-font-smoothing: antialiased;
        }}

        .header {{ text-align: center; margin-bottom: 24px; }}
        .header h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
        .header p {{ font-size: 13px; color: var(--muted); }}
        .badge {{
            display: inline-block; background: rgba(88,166,255,0.15);
            color: var(--accent); font-size: 11px; font-weight: 600;
            padding: 3px 8px; border-radius: 12px; margin-top: 8px;
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
            display: flex; margin-bottom: 20px; border-radius: 8px;
            overflow: hidden; border: 1px solid var(--border);
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

        /* Source link */
        .source-link {{
            display: block; font-size: 12px; color: var(--accent);
            margin-bottom: 16px; text-decoration: none;
        }}
        .source-link:hover {{ text-decoration: underline; }}

        /* Screenshot */
        .screenshot-wrapper {{
            margin-bottom: 20px; border-radius: 12px; overflow: hidden;
            border: 1px solid var(--border);
        }}
        .screenshot {{
            width: 100%; height: auto; display: block;
            max-height: 400px; object-fit: cover; object-position: top;
        }}

        /* Content summary */
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

        .section-title {{
            font-size: 15px; font-weight: 600;
            margin-bottom: 12px; color: var(--muted);
        }}

        /* Week cards */
        .week-card {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 16px; margin-bottom: 12px;
        }}
        .week-card.empty, .week-card.error {{
            opacity: 0.5; padding: 12px 16px;
        }}
        .week-header {{
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 12px;
            padding-bottom: 8px; border-bottom: 1px solid var(--border);
        }}
        .week-label {{
            font-size: 14px; font-weight: 700; color: var(--accent);
        }}
        .week-meta {{
            font-size: 11px; color: var(--muted); max-width: 60%;
            text-align: right; overflow: hidden; text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .no-data {{ font-size: 12px; color: var(--muted); font-style: italic; }}
        .error-text {{ font-size: 12px; color: var(--red); }}

        /* Headlines */
        .week-headlines {{ margin-bottom: 12px; }}
        .headline {{
            font-size: 13px; padding: 3px 0; line-height: 1.4;
        }}
        .htag {{
            display: inline-block; font-size: 9px; font-weight: 700;
            color: var(--muted); background: rgba(255,255,255,0.05);
            padding: 1px 4px; border-radius: 3px; margin-right: 4px;
            vertical-align: middle;
        }}
        .htag-h1 .htag {{ color: var(--accent); }}
        .htag-h2 .htag {{ color: var(--green); }}
        .more-count {{ font-size: 11px; color: var(--muted); margin-top: 4px; }}

        /* Campaigns */
        .week-campaigns {{ margin-bottom: 12px; }}
        .subsection-label {{
            font-size: 11px; font-weight: 600; color: var(--orange);
            text-transform: uppercase; letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}
        .campaign-link {{
            display: inline-block; font-size: 12px; color: var(--accent);
            text-decoration: none; margin-right: 12px; margin-bottom: 4px;
        }}
        .campaign-link:hover {{ text-decoration: underline; }}
        .campaign-link::before {{ content: "→ "; color: var(--muted); }}

        /* Promos */
        .week-promos {{ margin-bottom: 12px; }}
        .promo-text {{
            font-size: 12px; color: var(--muted); padding: 4px 0;
            line-height: 1.4; border-left: 2px solid var(--border);
            padding-left: 8px; margin-bottom: 4px;
        }}

        /* Week themes */
        .week-themes {{ margin-top: 8px; }}

        /* Comparison */
        .comparison-cards {{
            display: flex; flex-direction: column; gap: 12px;
            margin-bottom: 24px;
        }}
        .comp-card {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 16px;
        }}
        .comp-header {{
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 12px;
        }}
        .comp-name {{ font-size: 16px; font-weight: 700; }}
        .comp-url {{
            font-size: 11px; color: var(--accent); text-decoration: none;
        }}
        .comp-url:hover {{ text-decoration: underline; }}
        .comp-metrics {{
            display: grid; grid-template-columns: 1fr 1fr 1fr;
            gap: 8px; margin-bottom: 12px;
        }}
        .comp-metric {{ text-align: center; }}
        .comp-metric .val {{ font-size: 18px; font-weight: 700; }}
        .comp-metric .lbl {{
            font-size: 10px; color: var(--muted); text-transform: uppercase;
        }}
        .comp-summary {{
            font-size: 13px; color: var(--text); margin-bottom: 8px;
            line-height: 1.4;
        }}
        .comp-themes {{ margin-top: 8px; }}

        .footer {{
            text-align: center; padding: 20px 0; color: var(--muted);
            font-size: 12px; border-top: 1px solid var(--border);
            margin-top: 20px;
        }}
    </style>
</head>
<body>

<div class="header">
    <h1>YourCoverage</h1>
    <p>Competitor Website Content Analysis</p>
    <span class="badge">{_esc(week_range)} — Generated {_esc(generated)}</span>
</div>

<div class="view-toggle">
    <button class="view-btn active" onclick="switchView('overview')">Overview</button>
    <button class="view-btn" onclick="switchView('compare')">Compare</button>
</div>

<div id="view-overview" class="view-section active">
    <div class="tabs" id="comp-tabs">
        {comp_tabs}
    </div>
    {comp_panels}
</div>

<div id="view-compare" class="view-section">
    <div class="section-title">Competitor Comparison ({_esc(week_range)})</div>
    <div class="comparison-cards">
        {comp_cards}
    </div>
</div>

<div class="footer">
    YourCoverage — Website content collected {_esc(week_range)}
</div>

<script>
function switchView(view) {{
    document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('view-' + view).classList.add('active');
    event.target.classList.add('active');
}}
function selectCompetitor(slug, el) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    document.querySelectorAll('.competitor-panel').forEach(p => p.style.display = 'none');
    document.getElementById('panel-' + slug).style.display = 'block';
}}
</script>

</body>
</html>'''
