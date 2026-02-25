"""Persistence utilities for parking ticket data."""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Iterable, List, Mapping

from . import config

logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw_tickets (
    summons_number TEXT PRIMARY KEY,
    issue_date TEXT,
    violation_time TEXT,
    violation TEXT,
    violation_description TEXT,
    violation_county TEXT,
    house_number TEXT,
    street_name TEXT,
    intersecting_street_1 TEXT,
    intersecting_street_2 TEXT,
    violation_precinct TEXT,
    violation_status TEXT,
    vehicle_make TEXT,
    vehicle_color TEXT,
    vehicle_body_type TEXT,
    vehicle_expiration_date TEXT,
    vehicle_year TEXT,
    registration_state TEXT,
    street_code1 TEXT,
    street_code2 TEXT,
    street_code3 TEXT,
    latitude REAL,
    longitude REAL,
    community_board TEXT,
    fine_amount REAL,
    amount_due REAL,
    penalty_amount REAL,
    interest_amount REAL,
    reduction_amount REAL,
    payment_amount REAL,
    precinct TEXT,
    law_section TEXT,
    issuing_agency TEXT,
    summons_image TEXT,
    violation_code TEXT,
    time_first_observed TEXT,
    ticket_type TEXT,
    raw_payload TEXT NOT NULL
);
"""


class TicketDatabase:
    """A thin wrapper around SQLite operations for ticket persistence."""

    def __init__(self, path: Path | str = config.DEFAULT_DATABASE_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()

    def upsert_records(self, records: Iterable[Mapping[str, object]]) -> int:
        if not records:
            return 0

        columns = list(config.RAW_FIELDS)
        placeholders = ", ".join(["?"] * (len(columns) + 1))
        sql = f"INSERT OR REPLACE INTO raw_tickets ({', '.join(columns)}, raw_payload) VALUES ({placeholders})"

        to_insert: List[List[object]] = []
        for record in records:
            row: List[object] = [record.get(field) for field in config.RAW_FIELDS]
            row.append(json.dumps(record))
            to_insert.append(row)

        with self.connect() as conn:
            conn.executemany(sql, to_insert)
            conn.commit()
        logger.debug("Inserted %s records", len(to_insert))
        return len(to_insert)

    def stream_raw_records(self, limit: int | None = None) -> Iterable[sqlite3.Row]:
        query = "SELECT * FROM raw_tickets"
        params: List[object] = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self.connect() as conn:
            cursor = conn.execute(query, params)
            yield from cursor


__all__ = ["TicketDatabase"]
