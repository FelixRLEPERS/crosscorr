# CrossCorr data package — unified.parquet

**Project:** CrossCorr — reproducible analysis of ionospheric storm
effects on the WSPR (Weak Signal Propagation Reporter) network,
cross-checked against independent space-weather indices.

**Package prepared:** 2026-10-28 (audit round v1.5.0, task "publish
unified.parquet on Zenodo"). Upload to Zenodo is a manual step
(performed by the maintainer); this directory is the staging area.

**Zenodo concept DOI:** 10.5281/zenodo.23285958
(the dataset lands as a new version under this concept)

## Files

| File | Size | SHA-256 (see `checksums.txt`) |
|---|---|---|
| `unified.parquet` | 1 703 727 bytes | `0a746f033c7492243d88874968a271f2020fa7631eb7dae75b1f0449d6cfadc2` |
| `README.md` | this file | — |
| `checksums.txt` | sha256 sums | — |

## What is in `unified.parquet`

Single long-format table (Apache Parquet, snappy): **84 402 rows ×
9 columns**, one row per (detector, timestamp) observation.

It serves two roles: (i) replication of the v1.5.0 analysis; (ii) the
Kp epoch series consumed by the spatial permutation run
(`spatial_analysis.py:load_kp` reads `UNIFIED_PATH`; `--source api`
fetches spot aggregates server-side but takes Kp from this file).

### Columns

| Column | Type | Description |
|---|---|---|
| `timestamp_utc` | timestamp (UTC) | Observation start (hourly grid, except `wspr` = 3-hourly epochs) |
| `detector_id` | string | Unique detector identifier, e.g. `wspr_hourly_20m`, `kp_index`, or a WSPR receiver callsign |
| `detector_type` | string | Detector family: `wspr_hourly`, `wspr`, `kp`, `dst`, `f107`, `ephemeris` |
| `value` | float | Raw measured/derived value (see `unit`) |
| `residual` | float | Residual after the OLS geomagnetic model (`residual_method`) |
| `residual_method` | string | `ols_geomagnetic` for every row in this release |
| `unit` | string | `count` (WSPR hourly spot counts), `dB` (spot SNR), `AU` (ephemeris distances), `unknown` (Kp/Dst/F10.7 as delivered by upstream services) |
| `quality_flag` | float | Quality marker; `0.0` = OK for all rows in this release |
| `meta` | string (JSON) | Per-row metadata: band/band_index/mean_snr/max_distance for `wspr_hourly`; granularity for indices; source URLs/objects elsewhere |

### Detector inventory (this release)

| `detector_type` | Rows | `detector_id`s | Period (UTC) | Unit |
|---|---|---|---|---|
| `wspr_hourly` | 39 456 | 3 (`15m`, `20m`, `40m`) | 2024-04-01 → 2025-09-30 23:00 | count |
| `kp` | 5 912 | `kp_index` (GFZ Potsdam) | 2024-04-01 → 2026-09-15 | — (nT-free index) |
| `dst` | 17 095 | `dst_index` (WDC Kyoto, provisional) | 2024-04-01 → 2026-09-15 | nT (stored as `unknown`) |
| `f107` | 18 | `f107_index` (NOAA SWPC, monthly sample) | 2024-04-15 → 2026-09-15 | sfu (stored as `unknown`) |
| `wspr` | 21 846 | 985 receiver callsigns (individual spot SNR, 2–6 min cadence, sampled subset) | 2025-01-15 → 2026-09-01 | dB |
| `ephemeris` | 75 | JPL Horizons sun/moon (hourly step) | 2026-08-01 → 2026-09-02 | AU |

Cadence note: `kp` rows are 3-hourly, `dst` hourly, `f107` monthly;
`wspr_hourly` is hourly per band. The stored `unit` field keeps raw
upstream values (`unknown` for index detectors); the table above gives
the physical unit for reading convenience.

### Analysis windows

- **Training period:** 2024-04-01 → 2025-10-01 (main statistics,
  permutation tests, figures).
- **Held-out period (primary):** Jan–Mar 2026; **sensitivity window:**
  Jan–Jun 2026 (see `docs/AI_ASSISTANCE.md`, Appendix table
  `tab:heldout_sensitivity`).

## How the data were obtained

ETL pipeline in `data/scripts/` (Python 3.10+, pandas/pyarrow):

1. **WSPR spot counts** — hourly aggregates per band pulled from the
   ClickHouse public endpoint `http://db1.wspr.live/`
   (`download_wspr.py`, orchestrated by `fetch_all.py`); raw CSVs live
   under `data/raw/wspr/` (gitignored, sha256 sidecars alongside).
2. **Space-weather indices** — `download_space_weather.py`:
   Kp from GFZ Potsdam JSON API, Dst from WDC Kyoto (provisional),
   F10.7 from NOAA SWPC JSON.
3. **Ephemeris** — `download_horizons.py` (JPL Horizons REST).
4. **Unification** — `unify_schema.py` merges all raw sources into the
   long schema above and fits the OLS geomagnetic residual model
   (`crosscorr_lib.analysis.residuals.fit_residual_model`,
   method `ols_geomagnetic`).

Provenance/retrieval dates are recorded in the paper's Data
Provenance table (`paper/main.tex`, `tab:provenance`) and in
`results/provenance_manifest_2026-10-27.json`.

## How to load

```python
import pandas as pd

df = pd.read_parquet("unified.parquet")
wspr = df[df["detector_type"] == "wspr_hourly"]  # hourly spot counts
kp = df[df["detector_type"] == "kp"]  # geomagnetic index
```

Reproduce headline statistics:

```bash
python scripts/perm_test_18mo_3band.py     # block permutation test
```

## Spatial analysis (paper v2.0, `sec:spatial`)

The published spatial latitude analysis is reproducible from this
package (plus public endpoints) with:

```bash
python scripts/spatial_analysis.py --source api --skip-crosscheck --apply
```

Data dependencies:

- `unified.parquet` (this package) — Kp epoch series
  (`load_kp()` reads `UNIFIED_PATH`).
- `wspr.rx` public endpoint (`http://db1.wspr.live/`) — Phase-2 spot
  aggregates (`GROUP BY hour, band, latbin`; 40 chunks × ~1.2 s).
- The alternative `--source local` run additionally requires
  `stations_geo.csv` (38.5 MB, tracked in the code repository, not
  included here) and the local raw spot CSVs (`data/raw/wspr/`,
  gitignored, re-downloadable from wspr.live). It was not used in the
  published run: the Phase-1 API cross-check was skipped due to the
  endpoint budget (see below). `--source local` remains an alternative
  reproducibility path.

`--skip-crosscheck` skips only the deferred Phase-1 heavy sample
(`ORDER BY id LIMIT 5000` with server-side `radians()`; exceeds the
60-s request budget after ~3.6k requests). Phase 2 is unaffected.
Endpoint disclosure (wspr.tx absent, unbounded DISTINCT not viable,
cross-check deferral): see the paper, Section "Data" — the manuscript
is the authoritative version.

## Integrity

Verify before use:

```bash
sha256sum -c checksums.txt      # Linux/macOS
# Windows (PowerShell):
Get-FileHash unified.parquet -Algorithm SHA256
```

## License & citation

- Data sources: WSPR (wspr.live, community data), GFZ Potsdam (Kp),
  WDC Kyoto (Dst), NOAA SWPC (F10.7), JPL Horizons (ephemeris) —
  redistributed as merged aggregates with attribution.
- Cite this dataset via the Zenodo concept DOI
  **10.5281/zenodo.23285958** and the accompanying paper
  (see `CITATION.cff` in the code repository).

## Notes / limitations

- `unified.parquet` contains hourly aggregates and a sampled subset of
  receiver-side individual SNR records (`wspr` detector, 985 callsigns);
  it contains no full per-spot records with transmitter callsigns and
  no station coordinates. Station reference: `stations_geo.csv` —
  38.5 MB / 1 745 681 data rows, tracked in the public code repository
  (github.com/FelixRLEPERS/crosscorr, commit 053d42d) but not included
  in this data package. It is required only for the alternative
  `--source local` run; the published spatial analysis uses `--source api`.
- The held-out window Jan–Mar 2026 has N_storm = 23 storm hours
  (Kp ≥ 5): statistical power there is limited by construction
  (acknowledged in the paper's Limitations).
- Raw WSPR CSVs are intentionally not part of this package
  (size/licensing); they are re-downloadable from wspr.live.
