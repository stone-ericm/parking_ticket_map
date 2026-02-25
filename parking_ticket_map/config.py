"""Configuration constants for the parking ticket data pipeline."""
from __future__ import annotations

from pathlib import Path

# Base URL for the NYC Open Parking and Camera Violations API
BASE_URL: str = "https://data.cityofnewyork.us/resource/nc67-uf89.json"

# Default batch size for Socrata API pagination
DEFAULT_PAGE_SIZE: int = 50000

# Default path for the SQLite database that stores raw ticket data
DEFAULT_DATABASE_PATH: Path = Path("data/parking_tickets.db")

# Directory for derived datasets (aggregations, geojson, etc.)
DERIVED_DATA_DIR: Path = Path("data/derived")

# Directory for raw API responses (newline-delimited JSON snapshots)
RAW_DATA_DIR: Path = Path("data/raw")

# Timeout (seconds) for HTTP requests to the Socrata endpoint
HTTP_TIMEOUT: int = 60

# Default sleep duration between API requests (seconds)
DEFAULT_SLEEP_SECONDS: float = 0.25

# Accepted ticket types that qualify as parking violations.
# Camera violations are filtered out by excluding known camera-related types.
PARKING_TICKET_TYPES = {
    "P": "Parking",
    "PK": "Parking",
    "PARK": "Parking",
    "PARKING": "Parking",
}

CAMERA_TICKET_TYPES = {
    "SPEED CAMERA",
    "BUS LANE CAMERA",
    "RED LIGHT CAMERA",
    "BUS LANE",
    "SCHOOL ZONE SPEED CAMERA",
}

# Fields that are extracted from the API responses and persisted to the database.
# The API field names match the database column names 1:1.
RAW_FIELDS: tuple[str, ...] = (
    "summons_number",
    "issue_date",
    "violation_time",
    "violation",
    "violation_description",
    "violation_county",
    "house_number",
    "street_name",
    "intersecting_street_1",
    "intersecting_street_2",
    "violation_precinct",
    "violation_status",
    "vehicle_make",
    "vehicle_color",
    "vehicle_body_type",
    "vehicle_expiration_date",
    "vehicle_year",
    "registration_state",
    "street_code1",
    "street_code2",
    "street_code3",
    "latitude",
    "longitude",
    "community_board",
    "fine_amount",
    "amount_due",
    "penalty_amount",
    "interest_amount",
    "reduction_amount",
    "payment_amount",
    "precinct",
    "law_section",
    "issuing_agency",
    "summons_image",
    "violation_code",
    "time_first_observed",
    "ticket_type",
)
