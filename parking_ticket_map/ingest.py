"""Utilities to ingest parking ticket data from the NYC Open Data API."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional

import requests

from . import config
from .storage import TicketDatabase

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Capture summary statistics for an ingestion run."""

    records_fetched: int = 0
    records_inserted: int = 0
    pages_fetched: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> Dict[str, int]:
        return {
            "records_fetched": self.records_fetched,
            "records_inserted": self.records_inserted,
            "pages_fetched": self.pages_fetched,
            "duration_seconds": int((datetime.now(timezone.utc) - self.start_time).total_seconds()),
        }


class ParkingTicketIngestor:
    """Fetches parking ticket data and writes it to the local database."""

    def __init__(
        self,
        db: TicketDatabase,
        *,
        app_token: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.db = db
        self.session = session or requests.Session()
        self.app_token = app_token

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.app_token:
            headers["X-App-Token"] = self.app_token
        return headers

    def fetch_page(
        self,
        *,
        limit: int,
        offset: int,
        issue_date_from: Optional[str] = None,
        issue_date_to: Optional[str] = None,
        ticket_type_filter: bool = True,
    ) -> List[dict]:
        params: Dict[str, str] = {
            "$limit": str(limit),
            "$offset": str(offset),
        }

        where_clauses: List[str] = []
        if issue_date_from:
            where_clauses.append(f"issue_date >= '{issue_date_from}'")
        if issue_date_to:
            where_clauses.append(f"issue_date <= '{issue_date_to}'")

        if ticket_type_filter:
            camera_filters = " AND ".join(
                [f"upper(ticket_type) NOT LIKE '{value.upper()}%'" for value in config.CAMERA_TICKET_TYPES]
            )
            where_clauses.append(f"({camera_filters} OR ticket_type IS NULL)")

        if where_clauses:
            params["$where"] = " AND ".join(where_clauses)

        response = self.session.get(
            config.BASE_URL,
            headers=self._build_headers(),
            params=params,
            timeout=config.HTTP_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected payload from Socrata API")
        return data

    def fetch_all(
        self,
        *,
        page_size: int = config.DEFAULT_PAGE_SIZE,
        issue_date_from: Optional[str] = None,
        issue_date_to: Optional[str] = None,
        sleep_seconds: float = config.DEFAULT_SLEEP_SECONDS,
    ) -> Iterator[List[dict]]:
        offset = 0
        while True:
            page = self.fetch_page(
                limit=page_size,
                offset=offset,
                issue_date_from=issue_date_from,
                issue_date_to=issue_date_to,
            )
            if not page:
                break
            yield page
            offset += page_size
            if sleep_seconds:
                time.sleep(sleep_seconds)

    def ingest(
        self,
        *,
        issue_date_from: Optional[str] = None,
        issue_date_to: Optional[str] = None,
        page_size: int = config.DEFAULT_PAGE_SIZE,
        dry_run: bool = False,
        snapshot_path: Optional[str] = None,
        sleep_seconds: float = config.DEFAULT_SLEEP_SECONDS,
    ) -> IngestionStats:
        stats = IngestionStats()
        snapshot_handle = open(snapshot_path, "w", encoding="utf-8") if snapshot_path else None
        try:
            for page in self.fetch_all(
                page_size=page_size,
                issue_date_from=issue_date_from,
                issue_date_to=issue_date_to,
                sleep_seconds=sleep_seconds,
            ):
                stats.pages_fetched += 1
                stats.records_fetched += len(page)
                logger.info("Fetched %s records (page %s)", len(page), stats.pages_fetched)

                if snapshot_handle:
                    for record in page:
                        snapshot_handle.write(json.dumps(record))
                        snapshot_handle.write("\n")

                if dry_run:
                    continue

                inserted = self.db.upsert_records(page)
                stats.records_inserted += inserted
        finally:
            if snapshot_handle:
                snapshot_handle.close()

        logger.info("Ingestion completed: %s", stats.as_dict())
        return stats


def run_ingestion(
    *,
    db_path: Optional[str] = None,
    app_token: Optional[str] = None,
    issue_date_from: Optional[str] = None,
    issue_date_to: Optional[str] = None,
    page_size: int = config.DEFAULT_PAGE_SIZE,
    dry_run: bool = False,
    snapshot_path: Optional[str] = None,
    sleep_seconds: float = config.DEFAULT_SLEEP_SECONDS,
) -> IngestionStats:
    db = TicketDatabase(db_path or config.DEFAULT_DATABASE_PATH)
    db.initialize()
    ingestor = ParkingTicketIngestor(db, app_token=app_token)
    return ingestor.ingest(
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        page_size=page_size,
        dry_run=dry_run,
        snapshot_path=snapshot_path,
        sleep_seconds=sleep_seconds,
    )


__all__ = ["ParkingTicketIngestor", "IngestionStats", "run_ingestion"]
