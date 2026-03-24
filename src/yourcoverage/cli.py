"""CLI entry point for the Instagram competitor analyzer."""

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config


def cmd_collect(args, config):
    """Run weekly data collection."""
    from .collector import collect_all
    from .storage import cleanup_old_weeks, week_label

    week = args.week or week_label()
    print(f"Collecting data for week {week}...")
    print(f"Competitors: {', '.join(c.name for c in config.competitors)}")

    results = collect_all(
        competitors=config.competitors,
        settings=config.collection,
        week=week,
        login_user=args.ig_user,
        login_pass=args.ig_pass,
    )

    succeeded = sum(1 for r in results.values()
                    if not r.get("instagram", {}).get("error"))
    failed = len(results) - succeeded

    print(f"\nDone! {succeeded} profiles collected, {failed} failed.")
    for username, data in results.items():
        ig = data.get("instagram", {})
        error = ig.get("error")
        if error:
            print(f"  ✗ {username}: {error}")
        else:
            posts = ig.get("posts", [])
            summary = ig.get("content_summary", "")
            print(f"  ✓ {username}: {len(posts)} posts — {summary}")

    cleanup_old_weeks(config.collection.weeks_to_keep)


def cmd_report(args, config):
    """Generate HTML report from stored data."""
    from .reporter import write_report

    week_spec = args.weeks or config.report.default_weeks
    print(f"Generating report for weeks: {week_spec}")

    filepath = write_report(config, week_spec)
    print(f"Report written to: {filepath}")


def cmd_status(args, config):
    """Show status of stored data."""
    from .storage import list_weeks, load_snapshot

    weeks = list_weeks()
    if not weeks:
        print("No data collected yet. Run: yourcoverage collect")
        return

    print(f"Stored weeks: {len(weeks)}")
    print(f"Range: {weeks[0]} to {weeks[-1]}")
    print()

    for week in reversed(weeks[-8:]):
        print(f"  {week}:")
        for comp in config.competitors:
            snapshot = load_snapshot(comp.instagram_username, week)
            if snapshot:
                ig = snapshot.get("instagram", {})
                posts = ig.get("posts", [])
                error = ig.get("error")
                if error:
                    print(f"    {comp.name}: ERROR - {error}")
                else:
                    print(f"    {comp.name}: {len(posts)} posts")
            else:
                print(f"    {comp.name}: no data")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Instagram & Website Competitor Analyzer"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("competitors.yaml"),
        help="Path to competitors YAML config (default: competitors.yaml)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Collect command
    p_collect = subparsers.add_parser("collect", help="Collect weekly data from Instagram & websites")
    p_collect.add_argument("--week", help="Override week label (e.g., 2026-W12)")
    p_collect.add_argument("--ig-user", help="Instagram username for login (better rate limits)")
    p_collect.add_argument("--ig-pass", help="Instagram password for login")

    # Report command
    p_report = subparsers.add_parser("report", help="Generate HTML report from stored data")
    p_report.add_argument("--weeks", help="Week range: '9-12', 'latest-4', 'all', or '2026-W09:2026-W12'")

    # Status command
    p_status = subparsers.add_parser("status", help="Show status of stored data")

    # Legacy: no subcommand = old behavior (fetch + aggregate + export)
    parser.add_argument("--months", type=int, default=None, help="(legacy) Months back to analyze")
    parser.add_argument("--output", type=Path, default=None, help="(legacy) Output directory")
    parser.add_argument("--format", choices=["csv", "json", "both"], default="both", help="(legacy) Output format")

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
    elif args.command is None:
        # Legacy mode or show help
        if args.months is not None or args.output is not None:
            _legacy_run(args, config)
        else:
            parser.print_help()
            print("\nQuick start:")
            print("  yourcoverage collect          # Collect this week's data")
            print("  yourcoverage report            # Generate HTML dashboard")
            print("  yourcoverage status            # Show stored data status")
    else:
        parser.print_help()


def _legacy_run(args, config):
    """Legacy mode: fetch + aggregate + export (backwards compatible)."""
    from .aggregator import aggregate
    from .exporter import export_csv, export_errors, export_json
    from .fetcher import fetch_all

    if args.months is not None:
        months = args.months
    else:
        months = 6
    output_dir = args.output or Path("./output")

    print(f"Analyzing {len(config.usernames)} competitors over the last {months} months...")
    results = fetch_all(config.usernames, months)
    metrics = aggregate(results)

    succeeded = sum(1 for r in results if r.error is None)
    failed = sum(1 for r in results if r.error is not None)

    output_files = []
    if args.format in ("csv", "both"):
        path = export_csv(metrics, output_dir)
        output_files.append(path)
    if args.format in ("json", "both"):
        path = export_json(metrics, output_dir)
        output_files.append(path)

    error_path = export_errors(results, output_dir)

    print(f"\nDone! {succeeded} profiles fetched, {failed} failed.")
    for f in output_files:
        print(f"  Report: {f}")
    if error_path:
        print(f"  Errors: {error_path}")


if __name__ == "__main__":
    main()
