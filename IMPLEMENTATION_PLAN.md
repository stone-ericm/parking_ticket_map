# NYC Parking Ticket Heatmap Implementation Plan

## 1. Requirements & Scope Alignment
- **Dataset coverage:** Process the full Open Parking and Camera Violations dataset, ingesting historical records and staying current with new entries.
- **Violation focus:** Filter to parking tickets while preserving the violation description/type to enable optional ticket-type filtering in the UI.
- **Spatial granularity:** Target street-segment resolution (e.g., "41st St between 8th Ave & 7th Ave"). Where exact segment mapping is not feasible, fall back to closest available precision such as blockface or intersection-level, while flagging those cases for transparency.
- **Cost constraints:** Favor free/open-source tooling and hosting (Socrata API, open geospatial datasets, static hosting + serverless/cron for updates).
- **User experience:** Provide day-of-week and hour-of-day filters, along with ticket-type filters. Support borough or neighborhood filtering if technically practical within cost limits.

## 2. Data Acquisition Strategy
1. **API exploration**
   - Review Socrata API schema for `nc67-uf89` to confirm parking violation identification fields (`violation_code`, `violation_description`, `violation_location`, etc.).
   - Determine pagination and throttling requirements (Socrata limit 1000 records per request; respect app token rate limits).
2. **Full historical pull**
   - Implement a batch extractor that walks the dataset chronologically (e.g., by `issue_date`).
   - Store raw responses in object storage (e.g., local parquet/CSV in repo for prototype, migrate to cloud storage if needed).
3. **Incremental updates**
   - Persist the timestamp/ID of the last ingested record to resume daily/hourly updates.
   - Schedule a no-cost GitHub Actions workflow or serverless cron (e.g., AWS Lambda Free Tier) to rerun the ingest and append new records.

## 3. Data Normalization & Enrichment
1. **Parsing & standardization**
   - Normalize date/time fields to timezone-aware UTC and derive day-of-week, hour-of-day attributes.
   - Harmonize borough and street naming (uppercase, trimmed).
2. **Parking-only filtration**
   - Define classification logic using `violation_code`, `violation_description`, or `violation_category` to isolate parking tickets; retain original fields for UI filters.
3. **Location enrichment**
   - Join with NYC Street Centerline (LION) dataset to map tickets to street segments.
   - Use address interpolation/geocoding (NYC GeoSupport API or Pelias via OpenStreetMap) when coordinates are absent.
   - Track confidence levels; flag tickets with ambiguous or missing segment mapping for potential exclusion or aggregated fallback.
4. **Data quality handling**
   - Deduplicate on unique ticket identifier (`summons_number`).
   - Manage missing timestamps/locations with explicit rules (e.g., drop, impute to nearest known value, or bucket into "Unknown").

## 4. Storage & Data Modeling
- **Raw layer:** Append-only Parquet/CSV files partitioned by year/month for reproducibility.
- **Curated layer:** Structured table with columns: `segment_id`, `borough`, `street_name`, `cross_from`, `cross_to`, `ticket_type`, `issue_datetime`, `day_of_week`, `hour_of_day`, `ticket_count`, etc.
- **Aggregations:** Precompute counts per `(segment_id, day_of_week, hour_of_day, ticket_type)` and maintain summary metrics (total tickets per segment, distribution across boroughs).
- **Tools:** Use pandas + DuckDB or sqlite for local processing; upgrade to Postgres if scaling demands.

## 5. Analytics & Visualization Preparation
- Create GeoJSON for each street segment with linked `segment_id`.
- Calculate normalized intensity metrics (e.g., tickets per hour, z-score) for color scaling.
- Generate supporting datasets for charts: top segments per borough, ticket-type distribution over time.

## 6. Application & UI Design
1. **Tech stack**
   - Frontend: React with Mapbox GL JS or Leaflet + MapLibre (free tier), bundled via Vite.
   - Data delivery: Host aggregated JSON/GeoJSON on static storage (e.g., GitHub Pages, Netlify free tier) or a lightweight API (Cloudflare Workers free tier).
2. **Features**
   - Interactive map with heatmap or choropleth representing ticket intensity by segment.
   - Filters: day-of-week selector, hour-of-day slider, ticket-type multi-select, optional borough dropdown.
   - Tooltips/popups showing segment details, counts, and recent trends.
   - Supplementary charts (bar chart of busiest hours/days, ticket-type breakdown) using Recharts or Vega-Lite.
3. **Performance considerations**
   - Implement lazy loading or tiling if GeoJSON is large; consider vector tiles generated via tippecanoe for scale.
   - Cache aggregated data client-side with service workers for offline resilience.

## 7. Infrastructure & Deployment
- **Data pipeline automation:** GitHub Actions workflow to run ingestion + aggregation scripts, commit artifacts to a `data/` branch or upload to storage.
- **Frontend deployment:** Deploy static site to GitHub Pages or Netlify (both free) triggered on main branch updates.
- **Secrets management:** Store Socrata app token and geocoding API keys as encrypted GitHub secrets.
- **Monitoring:** Add alerts for pipeline failures via GitHub Actions notifications and simple health checks for data freshness.

## 8. Validation & Testing
- Compare aggregated counts against random raw samples to verify accuracy.
- Unit test parsing, classification, and aggregation functions.
- Validate geocoding matches using spot checks on known addresses.
- Perform UI usability testing focusing on filter interactions and map legibility.

## 9. Documentation & Handoff
- Document pipeline architecture, data schema, and deployment steps in `README.md` and `docs/`.
- Provide runbooks for rerunning ingestion locally and troubleshooting geocoding issues.
- Include user guide explaining interpretation of the heatmap and limitations (e.g., segments with low confidence geocoding).

## 10. Next Steps / Open Items
- Confirm preferred fallback behavior for tickets that cannot be mapped to precise segments.
- Decide cadence for data refresh (daily vs. weekly) balancing completeness and free-tier limits.
- Assess whether additional filters (e.g., violation code) are required beyond ticket type, day, and hour.
