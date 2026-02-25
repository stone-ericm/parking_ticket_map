# parking_ticket_map

An end-to-end data pipeline that pulls NYC parking and camera violation data, processes it, and visualizes ticket density on an interactive heatmap.

## What It Does

Street parking in NYC is a gamble. Some blocks get ticketed heavily at certain hours or days of the week, but that information is buried in millions of rows of city data. This tool surfaces those patterns by ingesting violation records from the NYC Open Data API, transforming them into street-segment-level aggregates, and rendering the results on an interactive map. The goal is simple: see where and when tickets cluster so you can make better parking decisions.

## Pipeline Architecture

The pipeline runs in three stages:

1. **Ingest** (`ingest.py`) -- Pulls raw violation records from the NYC Open Parking and Camera Violations API and writes them to a local SQLite database via `storage.py`.
2. **Transform** (`transform.py`) -- Reads from SQLite, cleans, and aggregates the raw data by street segment, day of week, and hour of day. Results are written to Parquet files.
3. **Visualize** (`streamlit_app.py`) -- A Streamlit app that reads Parquet files and renders a pydeck heatmap showing ticket density. Supports both Mapbox and OpenStreetMap tile layers.

```
NYC Open Data API
      |
      v
  ingest.py --> storage.py --> SQLite
      |
      v
 transform.py --> Parquet files
      |
      v
 streamlit_app.py --> interactive heatmap (pydeck)
```

## Tech Stack

- **Python** -- Core language for the entire pipeline
- **pandas / pyarrow** -- Data manipulation and Parquet I/O
- **requests** -- API client for NYC Open Data
- **SQLite** -- Lightweight local storage for transformed data
- **Streamlit** -- Web app framework for the visualization layer
- **pydeck** -- Map rendering (WebGL-powered, Mapbox or OSM tiles)

## Getting Started

### Prerequisites

Python 3.10+ is required. A Mapbox API token is optional (falls back to OpenStreetMap).

### Install

```sh
git clone https://github.com/stone-ericm/parking_ticket_map.git
cd parking_ticket_map
pip install -r requirements.txt
```

### Run the Pipeline

Pull violation data from the NYC Open Data API:

```sh
python -m parking_ticket_map ingest
```

Transform and aggregate into Parquet:

```sh
python -m parking_ticket_map aggregate
```

### Launch the Map

```sh
streamlit run streamlit_app.py
```

The app will open in your browser with an interactive heatmap of ticket density by street segment, filterable by day of week and hour of day.

## Configuration

Pipeline settings (API endpoints, file paths, batch sizes) are defined in `config.py`.

## Project Structure

```
parking_ticket_map/
    __init__.py
    __main__.py
    config.py
    ingest.py
    transform.py
    storage.py
data/
    .gitkeep
streamlit_app.py
requirements.txt
```
