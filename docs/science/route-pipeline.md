# Scientific route pipeline

## Implementation scope

1. Request coordinates must be within a bounded Tehran box.
2. OSRM provides true route geometry and named navigation steps. No synthetic route is generated if the route service is unavailable.
3. A PostGIS spatial bounding-box filter selects candidate OSM/manual obstacles.
4. Obstacles are projected onto route geometry. Nearby OSM data is **display-only**. Fuel effects are applied only after a moderator has confirmed a manual obstacle with named road and bidirectional relevance, and the OSRM step name matches.
5. A stop sign is modeled as a 2-second stop; a speed bump slows to 3 m/s; crossings to 4.5 m/s. Those are **configurable engineering assumptions**, not measured Pride calibration.
6. For confirmed signals, the engine evaluates all-green and all-red driving scenarios with a default unvalidated red probability of 0.5. Central estimates are an interpolation; the returned range covers the two scenarios.
7. If a self-hosted OpenTopoData-compatible `ELEVATION_BASE_URL` is configured, up to 70 sample points per route are queried. Median-smoothed SRTM gradients enter wheel power. Provider failures return explicit warning and no grade correction.
8. Constant engine efficiency and default Pride mass/rolling coefficients are not a laboratory characterization. All outputs remain research estimates.

## Core safety limits

- No arbitrary URL is accepted from end users.
- No live traffic or exact signal phases are claimed.
- Unknown obstacle direction or road affiliation is never silently treated as a stop.
- Opposite carriageway may share street name; human-confirmed direction still cannot replace a network-edge topology match in a production routing system.
- Raw origin/destination coordinates are not sent to application logs.
- This MVP does not guarantee the globally minimum-fuel route; only candidates returned by OSRM are compared.

## Road-network topology via OSRM annotations

When `annotations=nodes` is enabled, the OSRM Route API supplies OpenStreetMap
node IDs traversed by each leg of a route (see
https://project-osrm.org/docs/v26.6.1/http.html). These IDs are parsed as Python
integers to preserve 64-bit identifiers.

The current **automatic** obstacle rule applies only to:
- OSM `node` with `traffic_calming=bump|hump|table`, imported with its OSM ID
- Exactly matching `annotation.nodes` membership for this OSRM route
- Confirmed nearby location within the 12m geometric tolerance

Traffic signals, stop signs and crossings are displayed but not automatically
treated as mandatory slowdowns: shared intersection nodes cannot determine the
travel direction or the actual signal phase. Reviewed/manual obstacles remain
subject to separate bidirectional street-name matching and are still a
*conservative prototype*, not rigorous lane-level topology.

The API reports `topology_matched_osm_calming` separately from
`reviewed_applied` and `total_applied`. No guarantee of OSM completeness or
per-trip fuel accuracy is made. If annotations are missing, automatic effects
fail closed (evidence-only). OSRM data and OSM obstacle data must refer to a
compatible dated extract; otherwise ID membership may be stale.
