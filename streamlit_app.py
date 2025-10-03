"""Interactive heatmap for NYC parking tickets."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
import pydeck as pdk
import streamlit as st

from parking_ticket_map import config


def load_aggregated_data(path: Optional[str] = None) -> pd.DataFrame:
    dataset_path = Path(path) if path else config.DERIVED_DATA_DIR / "segment_time_counts.parquet"
    if not dataset_path.exists():
        st.warning(
            "Aggregated dataset not found. Run `python -m parking_ticket_map.cli aggregate` to build it first."
        )
        return pd.DataFrame()
    return pd.read_parquet(dataset_path)


def main() -> None:
    st.set_page_config(page_title="NYC Parking Ticket Heatmap", layout="wide")

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }
        .heatmap-header {
            padding: 0.75rem 1rem;
            border-radius: 0.75rem;
            background: linear-gradient(120deg, rgba(24,74,123,0.85), rgba(9,30,66,0.95));
            color: #f5f7fb;
        }
        .heatmap-header h1 {
            font-size: 2.4rem;
            margin-bottom: 0.2rem;
        }
        .heatmap-header p {
            margin-bottom: 0;
            opacity: 0.85;
        }
        [data-testid="stMetricValue"] {
            font-size: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="heatmap-header">
            <h1>NYC Parking Ticket Explorer</h1>
            <p>Discover when and where parking tickets are issued across New York City. Use the filters to uncover hotspots by day, hour, and ticket type.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mapbox_token = None
    try:
        mapbox_token = st.secrets.get("mapbox_token")  # type: ignore[attr-defined]
    except Exception:
        mapbox_token = None
    mapbox_token = mapbox_token or os.environ.get("MAPBOX_API_KEY")
    if mapbox_token:
        pdk.settings.mapbox_api_key = mapbox_token
        map_style = "mapbox://styles/mapbox/dark-v11"
    else:
        map_style = None
        st.info(
            "Using OpenStreetMap tiles. Add MAPBOX_API_KEY or Streamlit secret `mapbox_token` to enable Mapbox basemaps."
        )

    data = load_aggregated_data()
    if data.empty:
        st.stop()

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_lookup = {day: index for index, day in enumerate(day_order)}
    unique_days = data["day_of_week"].dropna().unique().tolist()
    unique_days.sort(key=lambda day: day_lookup.get(day, len(day_order)))
    day_options = ["All"] + unique_days
    hour_min, hour_max = int(data["hour_of_day"].min()), int(data["hour_of_day"].max())

    with st.sidebar:
        st.header("Filters")
        st.caption("Refine the dataset before exploring the map.")
        day_selected = st.selectbox("Day of Week", options=day_options, index=0)
        hour_range = st.slider(
            "Hour of Day", min_value=hour_min, max_value=hour_max, value=(hour_min, hour_max)
        )
        ticket_types = ["All"] + sorted(filter(None, data["ticket_type"].dropna().unique().tolist()))
        ticket_type_selected = st.selectbox("Ticket Type", options=ticket_types, index=0)
        min_tickets = st.slider(
            "Minimum tickets per segment", min_value=1, max_value=500, value=10, help="Hide rarely-used segments"
        )
        st.divider()
        st.caption(
            "Ticket counts are aggregated by street segment, day of week, hour of day, and ticket type."
        )

    filtered = data.copy()
    if day_selected != "All":
        filtered = filtered[filtered["day_of_week"] == day_selected]
    filtered = filtered[(filtered["hour_of_day"] >= hour_range[0]) & (filtered["hour_of_day"] <= hour_range[1])]
    if ticket_type_selected != "All":
        filtered = filtered[filtered["ticket_type"] == ticket_type_selected]
    filtered = filtered[filtered["ticket_count"] >= min_tickets]
    filtered = filtered.dropna(subset=["avg_latitude", "avg_longitude"])

    if filtered.empty:
        st.warning("No data matches the selected filters.")
        st.stop()

    total_tickets = int(filtered["ticket_count"].sum())
    segment_count = int(filtered["segment_id"].nunique())
    peak_hour = (
        filtered.groupby("hour_of_day")["ticket_count"].sum().idxmax() if not filtered.empty else None
    )
    peak_day = (
        filtered.groupby("day_of_week")["ticket_count"].sum().idxmax() if not filtered.empty else None
    )

    st.markdown("### Filtered Snapshot")
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("Tickets in view", f"{total_tickets:,}")
    with metric_cols[1]:
        st.metric("Segments", f"{segment_count:,}")
    with metric_cols[2]:
        if peak_day is not None:
            st.metric("Busiest day", peak_day)
        else:
            st.metric("Busiest day", "–")
    with metric_cols[3]:
        if peak_hour is not None:
            st.metric("Busiest hour", f"{int(peak_hour):02d}:00")
        else:
            st.metric("Busiest hour", "–")

    top_segments = (
        filtered.sort_values("ticket_count", ascending=False)
        .head(3)
        .loc[:, ["street_name", "ticket_count", "violation_county"]]
    )
    if not top_segments.empty:
        segments_text = []
        for row in top_segments.itertuples():
            street = row.street_name if isinstance(row.street_name, str) else "Unknown"
            borough = row.violation_county if isinstance(row.violation_county, str) else "NYC"
            segments_text.append(
                f"{street.title()} ({borough} • {int(row.ticket_count):,} tickets)"
            )
        st.markdown("**Top street segments:** " + ", ".join(segments_text))

    st.divider()

    midpoint_lat = filtered["avg_latitude"].mean()
    midpoint_lon = filtered["avg_longitude"].mean()
    if pd.isna(midpoint_lat) or pd.isna(midpoint_lon):
        midpoint_lat, midpoint_lon = 40.7128, -74.0060

    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=filtered,
        get_position="[avg_longitude, avg_latitude]",
        get_weight="ticket_count",
        radiusPixels=60,
        opacity=0.9,
    )

    layers = []
    if mapbox_token:
        layers.append(heatmap_layer)
    else:
        tile_layer = pdk.Layer(
            "TileLayer",
            data="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            min_zoom=0,
            max_zoom=19,
            tile_size=256,
        )
        layers.extend([tile_layer, heatmap_layer])

    deck = pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=float(midpoint_lat),
            longitude=float(midpoint_lon),
            zoom=11.2,
            pitch=40,
            bearing=20,
        ),
        layers=layers,
        tooltip={
            "html": "<b>{street_name}</b><br />{ticket_count} tickets<br />{day_of_week} @ {hour_of_day}:00",
            "style": {"backgroundColor": "rgba(15,23,42,0.85)", "color": "white", "fontSize": "14px"},
        },
    )

    map_tab, table_tab = st.tabs(["Interactive Map", "Segment Table"])

    with map_tab:
        st.pydeck_chart(deck, use_container_width=True)
        st.caption(
            "Heatmap intensities scale with ticket volume for the selected filters. Drag or zoom to inspect individual corridors."
        )

    with table_tab:
        st.dataframe(
            filtered[
                [
                    "segment_id",
                    "street_name",
                    "intersecting_street_1",
                    "intersecting_street_2",
                    "violation_county",
                    "day_of_week",
                    "hour_of_day",
                    "ticket_type",
                    "ticket_count",
                ]
            ]
            .sort_values("ticket_count", ascending=False)
            .rename(
                columns={
                    "segment_id": "Segment ID",
                    "street_name": "Street",
                    "intersecting_street_1": "From",
                    "intersecting_street_2": "To",
                    "violation_county": "Borough",
                    "day_of_week": "Day",
                    "hour_of_day": "Hour",
                    "ticket_type": "Ticket Type",
                    "ticket_count": "Tickets",
                }
            ),
            use_container_width=True,
        )
        st.caption("Sort columns to identify notable street segments and ticket types.")

    st.divider()
    with st.expander("How this dataset is built"):
        st.markdown(
            """
            Ticket counts are sourced from the NYC Open Parking and Camera Violations dataset. The ingestion
            pipeline aggregates tickets by street segment, day of week, hour of day, and ticket type, then derives
            representative coordinates to visualize trends on the map.
            """
        )


if __name__ == "__main__":
    main()
