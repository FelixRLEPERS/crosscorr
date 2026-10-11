# LSTID Pilot Report — 2026-10-11

## Data
- Storm: 2024-05-10 (G5, onset ~17:00 UTC)
- Quiet: 2024-05-05..07 (avg; Sun/Mon/Tue)
- Band: 20 m (14 MHz)
- Region: US East Coast (rx_lon -100..-60, rx_lat 25..60)
- Source: db1.wspr.live, server-side GROUP BY (hour × lat_bin × lon_bin)

## Row counts
- Storm: 3 218 agg rows / 1 314 301 spots (regional: 502 301)
- Quiet (3-day total): 10 346 agg rows / 3 876 001 spots
  (regional avg/day: 450 956)
- Delta (storm - quiet avg): +51 345 spots (full day, all hours)

## Result
- Pattern: **INCONCLUSIVE / leaning VERTICAL**
- First-drop hours by latitude (threshold -30%, 15–23 UTC):
  - 48N → 19 UTC, 46N → 17 UTC, 44N → 19 UTC, 42N → 18 UTC,
    40N → 18 UTC, 38N → 21 UTC, 30N → 15 UTC, 26N → 16 UTC
- The script's automated check reported "DIAGONAL" (15–21 UTC,
  est. 113 m/s), but this is an artifact of min/max fitting across
  a non-monotonic scatter — not a physical wave front.

## Observations
- Synchronous drop on 38–48N in 17–19 UTC — consistent with storm
  onset + terminator, not with LSTID.
- Direction is opposite to LSTID expectation: southern latitudes
  (26–30N) drop *earlier* than northern ones; auroral-origin LSTID
  must propagate pole → equator.
- Order along 38–48N is non-monotonic (17, 19, 18, 19, 18, 21 UTC),
  i.e. ±2 h scatter around ~19 UTC ≈ vertical front with noise.
- Deepening to −88…−100% at 46–48N by 21–23 UTC — likely nighttime
  D-layer absorption + storm-time activity peak.
- Strong baseline artifact in 04–11 UTC (+200…+860%): storm day =
  Friday vs quiet = weekend/early week; small nighttime denominators
  amplify it. F10.7 was also elevated (AR3664 aftermath).
- Southern rows (26–30N) are erratic — few stations, small numbers.

## Interpretation
- LSTID does not resolve on 20 m in this region for this event:
  the global chemical / D-layer absorption response dominates.
- Negative result: the pipeline works (GROUP BY on server, ~30 s
  per full pilot, no timeouts); the physics is simply not separable
  at this band/region/resolution with this baseline.

## Artifacts
- `lstid_pilot_may2024.png` — heatmap (delta spots, storm vs quiet avg)
- `storm_day_agg.parquet`, `quiet_all_agg.parquet` — aggregates
- Scripts: `scripts/weekend_pilot_lstid.py`, `scripts/inspect_heatmap.py`

## Next steps (Paper II)
- Baseline: quiet days of the same weekday (Friday vs Friday), or a
  control window ±2 weeks.
- Restrict analysis window to 15–23 UTC (around storm onset ~17 UTC).
- Lag detection: cross-correlation between latitude bands instead of
  "first drop < -30%".
- AACGM MLAT instead of geographic latitude.
- Try 15 m (21 MHz) — closer to MUF, potentially cleaner signal.

## Status
- NOT committed. To be discussed on HamSCI list (Frissell) first.