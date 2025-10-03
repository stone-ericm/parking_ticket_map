"""NYC Parking Ticket Heatmap data pipeline."""

from .cli import main as cli_main
from .ingest import ParkingTicketIngestor, IngestionStats, run_ingestion
from .transform import aggregate_ticket_counts, build_segment_summary

__all__ = [
    "cli_main",
    "ParkingTicketIngestor",
    "IngestionStats",
    "run_ingestion",
    "aggregate_ticket_counts",
    "build_segment_summary",
]
