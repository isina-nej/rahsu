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
