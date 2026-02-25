"""Transformation utilities for aggregating parking ticket data."""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


@dataclass
class AggregationResult:
    records_processed: int
    records_output: int
    output_path: Path


DAY_NAME_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _parse_datetime(issue_date: str | None, violation_time: str | None) -> Optional[datetime]:
    if not issue_date:
        return None

    try:
        # Issue date is formatted as YYYY-MM-DD (ISO)
        date_obj = datetime.strptime(issue_date, "%Y-%m-%d")
    except ValueError:
        return None

    time_obj: Optional[datetime] = None
    if violation_time:
        violation_time = violation_time.strip()
        # Remove potential trailing letters (A/P) representing AM/PM if present
        suffix = violation_time[-1]
        time_part = violation_time
        if suffix in {"A", "P"} and len(violation_time) >= 5:
            am_pm = "AM" if suffix == "A" else "PM"
            time_part = violation_time[:-1]
            try:
                time_obj = datetime.strptime(time_part, "%H%M")
                hour_24 = time_obj.hour
                if am_pm == "AM":
                    hour_24 = 0 if hour_24 == 12 else hour_24
                elif am_pm == "PM":
                    hour_24 = hour_24 if hour_24 == 12 else hour_24 + 12
                time_obj = time_obj.replace(hour=hour_24)
            except ValueError:
                time_obj = None
        else:
            try:
                time_obj = datetime.strptime(time_part, "%H%M")
            except ValueError:
                time_obj = None

    if time_obj:
        return date_obj.replace(hour=time_obj.hour, minute=time_obj.minute)
    return date_obj


def build_segment_identifier(row: pd.Series) -> str:
    components = [
        (row.get("violation_county") or "").strip().upper(),
        (row.get("street_name") or "").strip().upper(),
        (row.get("intersecting_street_1") or "").strip().upper(),
        (row.get("intersecting_street_2") or "").strip().upper(),
    ]
    return " | ".join(components)


def aggregate_ticket_counts(
    db_path: Path | str = config.DEFAULT_DATABASE_PATH,
    *,
    output_path: Path | str | None = None,
    min_samples_per_segment: int = 5,
) -> AggregationResult:
    db_path = Path(db_path)
    output_path = Path(output_path) if output_path else config.DERIVED_DATA_DIR / "segment_time_counts.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(db_path)) as conn:
        query = "SELECT * FROM raw_tickets"
        df = pd.read_sql_query(query, conn)

    if df.empty:
        logger.warning("No data found in raw_tickets table. Skipping aggregation.")
        return AggregationResult(records_processed=0, records_output=0, output_path=output_path)

    numeric_cols = ["latitude", "longitude", "fine_amount", "amount_due", "penalty_amount", "interest_amount", "reduction_amount", "payment_amount"]
    for column in numeric_cols:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["issue_datetime"] = df.apply(
        lambda row: _parse_datetime(row.get("issue_date"), row.get("violation_time")), axis=1
    )
    df = df.dropna(subset=["issue_datetime"])

    df["day_of_week"] = df["issue_datetime"].dt.day_name()
    df["hour_of_day"] = df["issue_datetime"].dt.hour
    df["segment_id"] = df.apply(build_segment_identifier, axis=1)

    # Filter to rows that have at least a street name and borough
    df = df[(df["segment_id"].str.strip() != "") & df["street_name"].notna() & df["violation_county"].notna()]

    grouped = (
        df.groupby(["segment_id", "day_of_week", "hour_of_day", "ticket_type"], dropna=False)
        .agg(
            ticket_count=("summons_number", "count"),
            avg_latitude=("latitude", "mean"),
            avg_longitude=("longitude", "mean"),
            street_name=("street_name", "first"),
            intersecting_street_1=("intersecting_street_1", "first"),
            intersecting_street_2=("intersecting_street_2", "first"),
            violation_county=("violation_county", "first"),
        )
        .reset_index()
    )

    grouped = grouped[grouped["ticket_count"] >= max(min_samples_per_segment, 1)]
    grouped = grouped.sort_values(
        by=["ticket_count"], ascending=False
    )

    grouped.to_parquet(output_path, index=False)
    logger.info("Wrote aggregated dataset to %s (%s rows)", output_path, len(grouped))
    return AggregationResult(
        records_processed=len(df),
        records_output=len(grouped),
        output_path=output_path,
    )


def build_segment_summary(
    aggregated_path: Path | str | None = None,
    *,
    output_path: Path | str | None = None,
) -> AggregationResult:
    aggregated_path = Path(aggregated_path) if aggregated_path else config.DERIVED_DATA_DIR / "segment_time_counts.parquet"
    summary_path = Path(output_path) if output_path else config.DERIVED_DATA_DIR / "segment_summary.parquet"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(aggregated_path)
    if df.empty:
        logger.warning("Aggregated dataset is empty. Skipping summary build.")
        return AggregationResult(records_processed=0, records_output=0, output_path=summary_path)

    summary = (
        df.groupby("segment_id")
        .agg(
            total_tickets=("ticket_count", "sum"),
            borough=("violation_county", "first"),
            street_name=("street_name", "first"),
            intersecting_street_1=("intersecting_street_1", "first"),
            intersecting_street_2=("intersecting_street_2", "first"),
            latitude=("avg_latitude", "mean"),
            longitude=("avg_longitude", "mean"),
            ticket_types=("ticket_type", lambda x: sorted(set(filter(None, x)))),
        )
        .reset_index()
    )

    summary["ticket_types"] = summary["ticket_types"].apply(lambda values: ", ".join(values) if values else "Unknown")
    summary.to_parquet(summary_path, index=False)
    logger.info("Wrote segment summary to %s (%s rows)", summary_path, len(summary))
    return AggregationResult(
        records_processed=len(summary),
        records_output=len(summary),
        output_path=summary_path,
    )


__all__ = [
    "aggregate_ticket_counts",
    "build_segment_summary",
    "AggregationResult",
]
