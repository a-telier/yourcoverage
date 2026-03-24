"""CLI entry point for the website competitor content analyzer."""

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config


def cmd_collect(args, config):
    """Run weekly website content collection."""
    from .collector import collect_all
    from .database import Database
    from .storage import week_label, screenshots_dir_for_week

    week = args.week or week_label()
    db = Database(config.database)

    print(f"Collecting website content for week {week}...")
    print(f"Competitors: {', '.join(c.name for c in config.competitors)}")
    print(f"Database: {config.database}")
    print()

    # Ensure competitors exist in DB
    comp_ids = {}
    for comp in config.competitors:
        comp_ids[comp.slug] = db.upsert_competitor(
            slug=comp.slug, name=comp.name,
            website_url=comp.website_url, color=comp.color,
        )

    # Screenshots directory
    screenshots_dir = screenshots_dir_for_week(
        config.database.parent, week
    ) if config.collection.screenshot else None

    # Collect
    results = collect_all(
        competitors=config.competitors,
        settings=config.collection,
        week=week,
        screenshots_dir=screenshots_dir,
    )

    # Save to database
    for slug, data in results.items():
        db.save_collection(comp_ids[slug], week, data)
        error = data.get("error")
        if error:
            print(f"  x {slug}: {error}")
        else:
            n_headlines = len(data.get("headlines", []))
            n_campaigns = len(data.get("campaign_links", []))
            n_themes = len(data.get("theme_tags", []))
            print(f"  + {slug}: {n_headlines} headlines, "
                  f"{n_campaigns} campaigns, {n_themes} themes")
            if data.get("screenshot_path"):
                print(f"    screenshot: {data['screenshot_path']}")

    db.close()
    print(f"\nDone! Data saved to {config.database}")


def cmd_report(args, config):
    """Generate HTML report from stored data."""
    from .reporter import write_report
    from .database import Database

    db = Database(config.database)
    week_spec = args.weeks or config.report.default_weeks

    print(f"Generating report for weeks: {week_spec}")
    filepath = write_report(config, db, week_spec)
    db.close()
    print(f"Report written to: {filepath}")


def cmd_status(args, config):
    """Show status of stored data."""
    from .database import Database

    db = Database(config.database)
    weeks = db.list_weeks()
    competitors = db.list_competitors()

    if not weeks:
        print("No data collected yet.")
        print("Run: yourcoverage collect")
        db.close()
        return

    print(f"Database: {config.database}")
    print(f"Competitors: {len(competitors)}")
    print(f"Weeks collected: {len(weeks)}")
    print(f"Range: {weeks[0]} to {weeks[-1]}")
    print()

    for week in reversed(weeks[-8:]):
        print(f"  {week}:")
        for comp in competitors:
            coll = db.get_collection(comp["id"], week)
            if coll:
                if coll.get("error"):
                    print(f"    {comp['name']}: ERROR - {coll['error']}")
                else:
                    n_h = len(coll.get("headlines", []))
                    n_c = len(coll.get("campaign_links", []))
                    print(f"    {comp['name']}: {n_h} headlines, {n_c} campaigns")
            else:
                print(f"    {comp['name']}: no data")

    db.close()


def cmd_query(args, config):
    """Query historical data."""
    from .database import Database

    db = Database(config.database)

    if args.month:
        # Parse month: "2026-06" or "6"
        if "-" in args.month:
            year, month = args.month.split("-")
            year, month = int(year), int(month)
        else:
            from datetime import date
            year = date.today().year
            month = int(args.month)

        data = db.get_month_data(year, month, args.competitor)
        if not data:
            print(f"No data for {year}-{month:02d}")
            db.close()
            return

        print(f"Data for {year}-{month:02d}:")
        for coll in data:
            name = coll.get("competitor_name", coll.get("slug", "?"))
            print(f"\n  {name} — {coll['week']}:")
            for h in coll.get("headlines", [])[:5]:
                print(f"    [{h['tag']}] {h['text']}")
            for cl in coll.get("campaign_links", [])[:3]:
                print(f"    -> {cl['text']} ({cl['url']})")
    else:
        # Default: show latest week
        weeks = db.list_weeks()
        if weeks:
            week = weeks[-1]
            competitors = db.list_competitors()
            print(f"Latest collection: {week}\n")
            for comp in competitors:
                coll = db.get_collection(comp["id"], week)
                if coll and not coll.get("error"):
                    print(f"{comp['name']} ({comp['website_url']}):")
                    for h in coll.get("headlines", [])[:10]:
                        print(f"  [{h['tag']}] {h['text']}")
                    if coll.get("campaign_links"):
                        print("  Campaigns:")
                        for cl in coll["campaign_links"][:5]:
                            print(f"    {cl['text']} -> {cl['url']}")
                    print()

    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Website Competitor Content Analyzer"
    )
    parser.add_argument(
        "--config", type=Path, default=Path("competitors.yaml"),
        help="Path to competitors YAML config (default: competitors.yaml)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Collect
    p_collect = subparsers.add_parser(
        "collect", help="Collect this week's website content")
    p_collect.add_argument(
        "--week", help="Override week label (e.g., 2026-W12)")

    # Report
    p_report = subparsers.add_parser(
        "report", help="Generate HTML report from stored data")
    p_report.add_argument(
        "--weeks", help="Week range: 'latest-4', '9-12', 'all'")

    # Status
    subparsers.add_parser("status", help="Show stored data status")

    # Query
    p_query = subparsers.add_parser(
        "query", help="Query historical data")
    p_query.add_argument(
        "--month", help="Month to query: '2026-06' or '6'")
    p_query.add_argument(
        "--competitor", help="Filter by competitor slug")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        config = load_config(args.config)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == "collect":
        cmd_collect(args, config)
    elif args.command == "report":
        cmd_report(args, config)
    elif args.command == "status":
        cmd_status(args, config)
    elif args.command == "query":
        cmd_query(args, config)
    else:
        parser.print_help()
        print("\nQuick start:")
        print("  yourcoverage collect    # Scrape competitor websites this week")
        print("  yourcoverage report     # Generate HTML dashboard")
        print("  yourcoverage status     # Show stored data")
        print("  yourcoverage query      # Query historical data")
        print("  yourcoverage query --month 6 --competitor zarahome")


if __name__ == "__main__":
    main()
