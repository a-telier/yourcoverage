"""CLI entry point for the Instagram competitor analyzer."""

import argparse
import logging
import sys
from pathlib import Path

from .aggregator import aggregate
from .config import load_config
from .exporter import export_csv, export_errors, export_json
from .fetcher import fetch_all


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Instagram competitor profiles by month"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("competitors.yaml"),
        help="Path to competitors YAML config (default: competitors.yaml)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=None,
        help="Months back to analyze (overrides config)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (overrides config)",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

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

    if args.months is not None:
        config.months_back = args.months
    if args.output is not None:
        config.output_dir = args.output

    print(f"Analyzing {len(config.usernames)} competitors over the last {config.months_back} months...")
    print(f"Profiles: {', '.join(config.usernames)}")

    results = fetch_all(config.usernames, config.months_back)
    metrics = aggregate(results)

    succeeded = sum(1 for r in results if r.error is None)
    failed = sum(1 for r in results if r.error is not None)

    output_files = []
    if args.format in ("csv", "both"):
        path = export_csv(metrics, config.output_dir)
        output_files.append(path)

    if args.format in ("json", "both"):
        path = export_json(metrics, config.output_dir)
        output_files.append(path)

    error_path = export_errors(results, config.output_dir)

    print(f"\nDone! {succeeded} profiles fetched, {failed} failed.")
    print(f"Total monthly data points: {len(metrics)}")
    for f in output_files:
        print(f"  Report: {f}")
    if error_path:
        print(f"  Errors: {error_path}")


if __name__ == "__main__":
    main()
