"""Command line interface for the parking ticket data pipeline."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from . import config
from .ingest import run_ingestion
from .transform import aggregate_ticket_counts, build_segment_summary


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NYC parking ticket heatmap data pipeline")
    parser.add_argument("command", choices=["ingest", "aggregate", "summary"], help="Pipeline stage to execute")
    parser.add_argument("--db", dest="db_path", default=str(config.DEFAULT_DATABASE_PATH), help="SQLite database path")
    parser.add_argument("--app-token", dest="app_token", default=None, help="NYC Open Data app token (optional)")
    parser.add_argument("--issue-date-from", dest="issue_date_from", default=None, help="Inclusive issue date lower bound (YYYY-MM-DD)")
    parser.add_argument("--issue-date-to", dest="issue_date_to", default=None, help="Inclusive issue date upper bound (YYYY-MM-DD)")
    parser.add_argument("--page-size", dest="page_size", type=int, default=config.DEFAULT_PAGE_SIZE, help="Number of records per API page")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Fetch data without writing to the database")
    parser.add_argument("--snapshot", dest="snapshot_path", default=None, help="Optional path to write newline-delimited JSON snapshot")
    parser.add_argument("--sleep", dest="sleep_seconds", type=float, default=config.DEFAULT_SLEEP_SECONDS, help="Sleep duration between API requests")
    parser.add_argument("--output", dest="output_path", default=None, help="Output path for the generated dataset")
    parser.add_argument("--input", dest="input_path", default=None, help="Input path when running the summary stage")
    parser.add_argument(
        "--min-samples",
        dest="min_samples_per_segment",
        type=int,
        default=5,
        help="Minimum observations per segment/day/hour combination",
    )
    parser.add_argument("--verbose", dest="verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    _configure_logging(args.verbose)

    if args.command == "ingest":
        run_ingestion(
            db_path=args.db_path,
            app_token=args.app_token,
            issue_date_from=args.issue_date_from,
            issue_date_to=args.issue_date_to,
            page_size=args.page_size,
            dry_run=args.dry_run,
            snapshot_path=args.snapshot_path,
            sleep_seconds=args.sleep_seconds,
        )
        return 0

    if args.command == "aggregate":
        aggregate_ticket_counts(
            db_path=args.db_path,
            output_path=args.output_path,
            min_samples_per_segment=args.min_samples_per_segment,
        )
        return 0

    if args.command == "summary":
        build_segment_summary(
            aggregated_path=args.input_path or args.output_path,
            output_path=args.output_path or args.snapshot_path,
        )
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
