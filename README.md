# NYC Parking Ticket Heatmap

This repository implements the end-to-end pipeline proposed in `IMPLEMENTATION_PLAN.md` for exploring New York City parking tickets. It includes:

- **Data ingestion** from the NYC Open Parking and Camera Violations API into a local SQLite database.
- **Transformation and aggregation** jobs to derive per-street-segment ticket counts by day of week and hour of day.
- **An interactive Streamlit application** that renders a heatmap using the aggregated dataset.

The stack relies solely on open-source tooling and can be executed locally with no recurring infrastructure costs.

## Getting Started

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Ingest data

Fetch parking ticket records into the local SQLite database. You can provide optional issue date bounds to limit the dataset during initial testing.

```bash
python -m parking_ticket_map ingest --issue-date-from 2023-01-01 --issue-date-to 2023-01-31 --page-size 5000 --sleep 0.5
```

> **Tip:** Provide your NYC Open Data App Token with `--app-token YOUR_TOKEN` for higher throughput.

### 3. Build aggregates

Create the per-segment, per-day/hour dataset and overall segment summary.

```bash
python -m parking_ticket_map aggregate --min-samples 5
python -m parking_ticket_map summary
```

This writes the following files:

- `data/derived/segment_time_counts.parquet`
- `data/derived/segment_summary.parquet`

### 4. Launch the heatmap UI

```bash
streamlit run streamlit_app.py
```

Use the sidebar controls to filter by day of week, hour range, ticket type, and minimum ticket counts per segment. The dashboard
highlights the busiest corridors, surfaces quick summary metrics, and renders the heatmap on top of a New York City basemap for
better context.

> Without credentials the app automatically falls back to OpenStreetMap tiles. Set the `MAPBOX_API_KEY` environment variable (or
> add a `mapbox_token` secret in Streamlit Cloud) to unlock Mapbox styles.

## Repository Layout

```
parking_ticket_map/
├── parking_ticket_map/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── ingest.py
│   ├── storage.py
│   └── transform.py
├── streamlit_app.py
├── IMPLEMENTATION_PLAN.md
├── README.md
├── requirements.txt
└── project idea.txt
```

## Notes & Future Work

- The aggregation pipeline approximates street segments using the borough, street name, and cross streets reported on the ticket. Integrating NYC Street Centerline data would yield richer geometries for map rendering.
- The Streamlit heatmap uses ticket centroids for weighting. Replacing this with true segment geometries would further align the visualization with the original vision.
- Consider scheduling the ingestion job (e.g., via GitHub Actions or a local cron job) to keep the dataset fresh.

