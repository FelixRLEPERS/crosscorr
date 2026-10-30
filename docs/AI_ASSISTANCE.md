# AI Assistance

This project uses LLMs as programming and analysis assistants.
All scientific decisions, hypotheses, and conclusions are made
by the human authors.

## Models used

| Model | Role | Access |
|-------|------|--------|
| DeepSeek V4 Pro | Code generation, analysis scripts | Polza.ai |
| DeepSeek V4.1 Flash | Code generation, sensitivity analyses, internal audit support | OpenCode |
| MiMo V2.6 Flash | Test coverage, bug fixes, documentation, release preparation | Polza.ai (OpenCode) |
| Bonsai 2 27B (Ternary) | Local development, quick tasks | Local (RTX 3080 Ti) |
| Qwen 3.8 27B | Independent audit | Local (Bionic) |

## Scope of assistance

- **Code generation**: statistical scripts, data pipeline, tests
- **Uncertainty analyses**: bootstrap CIs, covariate adjustment,
  episode-level robustness, sensitivity checks
- **Documentation**: README, data pipeline docs, audit reports
- **Analysis review**: independent audit of methodology and results

## Human responsibility

All hypotheses, interpretations, physical mechanisms, and
conclusions are exclusively those of the human authors
(Alexey and Makar Petrov). AI tools are used as assistants
under human supervision — analogous to a calculator in
arithmetic or a spell-checker in writing.

## Session log

### 2026-10-30 — Data package v11 published on Zenodo

Data package v11 published on Zenodo. Version DOI: 10.5281/zenodo.23802881. Schema updated with goes_xray and n_unique_tx.

### 2026-10-30 — Q2 sync: paper (EN+RU) updated to the final flare-controlled and tx-normalized results

- **Task:** sync `paper/main.tex` + `paper/main_ru.tex` with the final
  Phase B numbers, scope "full sync + raw labels": headline results move to
  the tx-normalized, flare-excluded family; the NB model, bootstrap CIs,
  scale-dependence, UT-window, held-out, episode/monthly/distance and
  block-8 families keep their raw numbers but gain an explicit
  "raw spot counts" label; Methods gain the `eq:normtx` normalization
  paragraph; Limitations/Confounders revised.
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov (approved the scope beforehand, then
  the full unified diff `q2_sync.diff` in the Review pane BEFORE `--apply`)
- **Tooling (two-phase, AGENTS.md):**
  1. New `scripts/q2_extract_numbers.py` — read-only extractor of the
     final numbers from the result JSONs.
  2. New `scripts/update_paper_q2_sync.py` — `--check` / `--apply`
     updater: every `old` anchor must match exactly once per file
     (count == 1 guard; mismatch aborts without writing); all numbers
     interpolated from `results/perm_test_18mo_3band_norm_tx.json`,
     `results/spatial_lat_groups_norm_tx.json`,
     `results/spatial_lat_groups.json` (raw 15m low-lat cell) and
     `results/perm_test_18mo_3band.json` (raw flare-filtered drops
     -25.5 / -25.3 / -36.8) — nothing hardcoded; sanity checks pin the key
     values (169/2738, pooled -72.7/-24.1/-12.8, raw 15m low-lat -11.8,
     1325 flare hours); output guaranteed UTF-8 without BOM, LF, final
     newline. Per-band section anchors are asserted present, and both
     lists are matched file-wide (the count==1 guard is the uniqueness
     check, not the section slice).
- **Paper changes (both languages, mirrored):**
  - Abstract / keypoints / PLS / conclusions: headline = spots per active
    transmitter — 20m -23.9%, 40m -22.5%, 15m -30.1% (p=2.00e-05),
    sample 169 storm / 2738 quiet epochs (1325 GOES XRS flare hours
    excluded); raw-vs-norm wording corrected where the old text claimed
    the raw values were "conservative".
  - `sec:spatial`: norm prose (pooled -72.7 / -24.1 / -12.8, high/low
    ratio 5.7x), "significant in 8 of 9 band x latitude cells"
    (low-lat 15m p=9.07e-02 does not survive TX-normalization), the
    flare paragraph kept raw-vs-raw (73.1/72.1, 28.2/26.1, 22.8/20.0)
    with explicit labels, new Selection-bias paragraph (15m low-lat
    -11.8% p=5e-05 -> -0.8% p=0.0907), `tab:spatial` rows, caption and
    p-values (40m low-lat 2.4e-02, 15m low-lat 9.1e-02 not significant).
  - Methods: new `\paragraph{Selection-bias normalization.}` with
    `\begin{equation} \label{eq:normtx}` inserted before the existing
    subsection, so the `Section~3.3` / `разд.~3.3` cross-references stay
    valid; the paragraph states which analyses run on `S_norm` and which
    stay on raw counts (labeled as such).
  - Limitations: obsolete claim "normalisation ... is not available"
    removed — "Station activity" rewritten (tx normalization applied via
    `eq:normtx`, receivers/paths remain residual confounders); new item
    "Low-latitude 15m selection bias". Confounders: false claim "the
    permutation analyses retain all hours" corrected (both the headline
    permutation and the latitude-group analysis exclude the flare hours).
  - Raw-kept families carry explicit labels: tab:main raw run
    "(raw spot counts, flare-included training run)", UT-table all-hours
    rows, block-size sensitivity, scale/blocked-8 and distance/Kp-scheme
    captions, held-out raw comparisons.
- **Verification:** `ruff check .`, `mypy crosscorr_lib`,
  `pytest -m "not slow"` (369 passed, 2 deselected) green; BOM / CRLF /
  final-newline verified on both .tex files; full `git diff` reviewed;
  temporary diagnostic scripts removed from the repo root.

### 2026-10-30 — Phase B: selection-bias normalisation by active transmitters (`--norm-tx`)

- **Task:** Q1 audit, physical block — control for selection bias (human
  factor): normalise spot counts by the number of active transmitters
  (`n_unique_tx`, per hour+band, available in unified.parquet meta after the
  Phase F refetch) and test whether the storm/quiet effect survives.
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov (approved the script diff before the
  runs; approved the commit after seeing the comparison table)
- **Code changes (all behind `--norm-tx`, default off = legacy behaviour):**
  1. `scripts/perm_test_18mo_3band.py` — new `--norm-tx` flag; after the
     flare filter `value = value / n_unique_tx` parsed from the meta JSON
     (loud `SystemExit` if n_unique_tx is missing or <= 0, with the
     refetch/unify instructions); delta rounding/format switches to
     fractional spots-per-transmitter (3 decimals); `config.norm_tx` block
     added to the output JSON.
  2. `scripts/spatial_analysis.py` — new `--norm-tx` flag; Phase 1 gains two
     checks: n_unique_tx coverage in unified meta over the window (>= 99%,
     required for `--source local` where meta is the ONLY source) and a light
     API probe of `uniqExact(tx_sign) GROUP BY hour, band`. Phase 2: api
     source fetches a companion n_unique_tx query per chunk and merges on
     (hour, band); local source joins n_unique_tx from unified meta;
     `spots_norm = spots / n_unique_tx(hour,band)` with a loud guard before
     statistics; `block_perm_test`/`analyze_group` take a `value_col`
     parameter (raw `value` kept for n_storm_spots provenance);
     `params.norm_tx` recorded in the output JSON. NOTE: `--source local`
     was rejected for the actual run (spot CSVs are truncated at 100k rows
     per the module docstring), the run used `--source api`.
  3. New `scripts/compare_norm_tx.py` — read-only two-table reporter
     (perm per-band + spatial pooled/per-band, raw vs norm) with guards
     (flare filter active in all 4 inputs, norm flags as expected) and a
     verdict block (sign, significance count with `[WEAK]` cell listing,
     band/latitude gradient order comparison); exit 0 on guards + verdict.
- **Runs (2026-10-30, no flares, block=24, canonical defaults):**
  - `perm_test_18mo_3band.py --norm-tx --out results/perm_test_18mo_3band_norm_tx.json`
    -> 20m -23.9%, 40m -22.5%, 15m -30.1% (raw -25.5/-25.3/-36.8), all
    p=2.00e-05 (floor). n_tx min/median/max = 99/461/1023.
  - `spatial_analysis.py --source api --norm-tx --skip-crosscheck --apply
    --out results/spatial_lat_groups_norm_tx.json` -> Phase 1 all OK
    (n_unique_tx coverage 39456/39456 = 100%), 40 chunks + 40 companion
    queries, 106 328 cells normalised, Total spots 1 796 248 370 unchanged.
- **Comparison (`scripts/compare_norm_tx.py`, exit 0):**
  - Pooled lat groups: High -72.1 -> -72.7 (slightly STRONGER), Mid
    -26.1 -> -24.1, Low -20.0 -> -12.8; all p=5.00e-05 (floor) in both.
  - 14/15 cells significant after norm; sign negative everywhere; band
    gradient (15m > 20m > 40m) and latitude gradient (H > M > L) PRESERVED.
  - **One exception — 15m Low-lat: -11.8% (p=5.00e-05) -> -0.8%
    (p=9.07e-02)**: this secondary cell is explained by the active-
    transmitter population (selection bias), not by geomagnetic physics.
    40m Low-lat weakens 1.95e-03 -> 2.37e-02 but stays significant.
  - Interpretation for the manuscript: the MAIN effect (auroral/mid-lat
    drop, all pooled bands) is physical; the 15m low-lat cell is a
    candidate Limitations item for the Q2 sync (decided with the author).
- **Intentionally NOT changed:** the manuscript (Q2 sync will decide how to
  phrase the norm results), headline/abstract numbers, canonical JSONs
  (`results/perm_test_18mo_3band.json`, `results/spatial_lat_groups*.json`).
  Norm output JSONs live in gitignored `results/` next to the canonicals.
- **Verification:** `ruff check .`, `mypy crosscorr_lib`,
  `pytest -m "not slow"` green; `git diff` reviewed.

### 2026-10-30 — Phase F refetch, unified rebuild, Zenodo v11 refresh, block = 8 rerun (Q1 audit completion)

- **Task:** complete the Q1-audit data fixes: full re-pull of the 1701 WSPR
  hourly files with `n_unique_tx`, rebuild `unified.parquet`, refresh the
  Zenodo staging, rerun the spatial permutation with `block = 8` (no flares),
  and update the `sec:dropnorm` sentence accordingly.
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov (approved the `sec:dropnorm` diff before
  `--apply`)
- **Changes made:**
  1. **Phase F executed:** `python data/scripts/refetch_wspr_hourly.py
     --apply --workers 4` -> `[DONE] ok=1701 fail=0 of 1701`. spots_count
     drift WARNs on some files confirm the data changed since the first
     pull — the reason the full rerun campaign (Q2) was commissioned.
  2. **Rebuild `data/processed/unified.parquet`:**
     `python data/scripts/unify_schema.py` -> 121 591 rows x 9 cols,
     0 errors; per-row `meta` (`n_unique_tx`, `mean_snr`, `max_distance`)
     verified present.
  3. **Zenodo staging v11 refresh (two-phase):**
     `python scripts/prepare_zenodo_v11.py --check` then `--apply` ->
     `[OK] staged`; sha256
     `8ee0ac22eb48eb671fc5add881101ef1ae2670a39ea8c0c4d61d8250cc8031ba`,
     3 829 807 bytes. The actual Zenodo upload stays a manual author step.
  4. **Block = 8 rerun (no flares):**
     `python scripts/spatial_analysis.py --block 8 --out
     results/spatial_lat_groups_block8.json` — guards verified
     `flare_filter.exclude_flares=True` in both JSONs
     (`n_spots_total=1 796 248 370`, 1 325 flare hours excluded).
     Canonical `results/spatial_lat_groups.json` (block = 24) not touched.
  5. **New `scripts/compare_block8.py`:** builds the b=24 vs b=8 comparison
     table (12 cells), asserts conservativeness (p(b=8) <= p(b=24) in every
     cell — holds), floor counts 8/9 per-band (11/12 with pooled) identical
     in both runs, identical Drop% columns. 40m low-latitude:
     1.9499e-03 (b=24) -> 3.4998e-04 (b=8), i.e. still above the floor.
  6. **New `scripts/update_paper_block8.py`** (two-phase): regenerates the
     `sec:dropnorm` block-sensitivity sentence in `paper/main.tex` and
     `paper/main_ru.tex` from the two JSONs (values read, not hardcoded;
     RU comma decimal separator). `--check` reviewed, `--apply` run after
     explicit human approval:
     - EN: `... low-latitude 40\,m moves from $1.95 \times 10^{-3}$ to
       $3.5 \times 10^{-4}$).`
     - RU: `... низкоширотная 40\,м переходит от $1{,}95 \times 10^{-3}$ к
       $3{,}5 \times 10^{-4}$).`
     This replaces the stale claim `from $p = 1.5 \times 10^{-4}$ to the
     floor`, which matched neither JSON (b=24 = 1.95e-3, b=8 = 3.50e-4,
     both above the floor). The rest of the sentence (8/9 floor, uniform
     conservativeness) is unchanged and re-verified.
- **Intentionally NOT changed (deferred to the Q2 rerun campaign):**
  permutation-test headline numbers, abstract N=198 / Drop% figures,
  bootstrap CIs and all other derived tables, plus CI config — they still
  describe the original with-flares runs, as documented in the 2026-10-30
  flare-control entry below.
- **Verification:** `ruff check .` OK; `mypy crosscorr_lib` OK;
  `pytest -m "not slow"` 369 passed, 2 deselected; `git diff` reviewed;
  committed and pushed via CLI.

### 2026-10-30 (Phase B Prep) — `n_unique_tx` in the WSPR hourly ETL

- **Task:** Selection-Bias (Phase B) groundwork, author instructions:
  add `uniqExact(tx_sign) AS n_unique_tx` to `fetch_wspr_hourly`, persist it
  in `meta` via `unify_schema.py`, and produce the re-pull plan (full
  18 months vs a single test band).
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov (approved Phase 1 + decisions: per-row
  meta, Phase T now / Phase F when API is up, re-pull BEFORE the Zenodo
  upload so published v11 already carries `n_unique_tx`)
- **Code changes:**
  1. `data/scripts/download_wspr.py::fetch_wspr_hourly` — SQL gains
     `uniqExact(tx_sign) AS n_unique_tx`; `hourly_cols` (positional
     DataFrame construction) and the return column list gain the field;
     docstring updated. CSV header becomes
     `timestamp,band,spots_count,mean_snr,max_distance,mean_frequency,n_unique_tx`.
  2. `data/scripts/unify_schema.py::load_wspr_hourly` — meta is now built
     **per row** (decision B1). This also fixes a latent bug: previously
     `mean_snr`/`max_distance` were taken via `.iloc[0]`, i.e. the first
     hour's values were replicated onto every row of the day, contradicting
     the README's "Per-row metadata" claim. Risk assessed as zero: grep
     shows no analysis code parses `meta["mean_snr"]`/`max_distance`
     (only download scripts and `snr_analysis_3band.py`, which queries the
     API directly). Missing columns (old CSVs) yield JSON `null`.
  3. New `data/scripts/refetch_wspr_hourly.py` — two-phase re-pull runner
     (default = plan + one-request probe; `--apply` = parallel re-fetch).
     Target universe = files that already exist in `data/raw/wspr/`
     (1701 = 548 days x 3 bands training + 19 days x 3 bands Jan-2026;
     span 2024-04-01..2026-01-19) - the date set never grows. Resume =
     skip files whose header already has `n_unique_tx` (unless `--force`).
     Per file: spots_count drift check against the old file (warn),
     atomic tmp -> replace, sha256 sidecar via `download_wspr._write_checksum`.
     `--workers 4` -> estimated 8-12 min for the full run.
  4. Two unit tests in `tests/test_unify_schema.py`: per-row meta with
     `n_unique_tx`/`mean_snr`/`max_distance`; missing columns -> null.
- **Phase T executed (2026-10-30):** probe 2024-04-01 15m
  (16 745 spots/h -> 258 unique tx) and 3-day x 20m apply
  (2025-06-01..03): 3/3 ok, header verified, values plausible
  (106 400 spots/h -> 710 unique tx). One fix during T: drift-merge
  needed `pd.to_datetime(..., utc=True)` normalisation of the old file's
  `timestamp` (str vs datetime64[us, UTC]).
- **Scope notes:** writers feeding `data/raw/wspr_hourly/`
  (`download_wspr_parallel.py`, `dload_2026.py`, `bg_dload_2026.py`,
  `fetch_heldout_2026h1.py`; schema `hour,spots,...`) are untouched -
  that directory is a separate cache that `unify_schema.LOADERS` never
  reads (only `data/raw/wspr/` is globbed).
- **Verification:** `ruff check .` OK; `mypy crosscorr_lib` OK;
  `pytest -m "not slow"` 367 passed, 2 deselected; targeted
  `pytest tests/test_unify_schema.py` 15 passed (incl. 2 new).
- **Next (author plan):** Phase F `--apply` (1701 files, API restored
  2026-10-30) -> `unify_schema.py` rebuild -> refresh the Zenodo v11
  staging (staging currently hash `18a3ee5e...`, NOT yet uploaded) ->
  manual upload. Still pending: block = 8 without-flares spatial rerun
  for the `sec:dropnorm` sensitivity sentence.

### 2026-10-30 (Data Release) — Zenodo v11 staged (unified.parquet with GOES X-ray)

- **Task:** refresh the Zenodo data staging after the GOES X-ray schema
  change (`detector_type += goes_xray`, `unit = W/m2`): new SHA-256/size/
  row counts/inventory in `zenodo_data/README.md`, new `checksums.txt`,
  parquet copied into the staging directory for manual upload (concept
  DOI 10.5281/zenodo.23285958).
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov (approved the Phase-1 diff before Apply)
- **Tooling:** `scripts/prepare_zenodo_v11.py` (house two-phase pattern:
  default run = report + unified diff, `--apply` = copy parquet with a
  post-copy SHA-256 assertion + rewrite README/checksums; exactly-once
  pattern verification aborts before writing on any mismatch; UTF-8 + LF;
  idempotent re-run prints `[SKIP]` and exits 0). Temp debug script used
  during the session was removed.
- **Result (v11 payload):** sha256
  `18a3ee5e0b7c09b8e68188141a674125e84633c1333fbb396d8d34c9f2ac1ecf`,
  2 687 068 bytes, 121 591 rows x 9 columns (v10 was 1 703 727 bytes /
  84 402 rows). Detector inventory deltas documented in README:
  `goes_xray` +13 143 rows (hourly max of the XRS 1-min mean, W/m2,
  2024-04-01 -> 2025-09-30); `wspr` 21 846 -> 44 524 rows (985 -> 1 206
  receiver callsigns, from earlier rebuilds); `wspr_hourly` 39 456 ->
  40 824 rows (period extended to 2026-01-19 23:00 by the held-out
  extension fetches); `dst`/`kp`/`f107`/`ephemeris` unchanged.
  README also documents the v11 header note, `goes_xray`/`W/m2` in the
  column vocabularies, and the new ETL step 4 (GOES download from NOAA
  NCEI via `download_space_weather.py`); the Notes-section receiver count
  was synced (985 -> 1 206) after it surfaced in review.
- **Git scope:** `zenodo_data/` is gitignored except `README.md`
  (tracked); `unified.parquet` + `checksums.txt` remain local staging
  artifacts for the manual Zenodo upload.
- **Verification:** `ruff check .` / `ruff format --check` clean for the
  new script; staging re-run idempotent (`[SKIP] ... agree`, exit 0);
  README/checksums byte-verified (no BOM, no CR, final newline LF).

### 2026-10-30 (Paper Sync) — Manuscript switched to flare-controlled spatial numbers

- **Task:** Q1 audit follow-up: update `paper/main.tex` and `paper/main_ru.tex`
  to the flare-controlled (canonical, without-flares) latitude-group results
  and add the Methods/Limitations text on the GOES flare control.
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov (approved the Phase-1 diff before Apply)
- **Tooling:** `scripts/update_paper_flare_numbers.py` (house two-phase
  pattern: default run prints the unified diff and changes nothing; `--apply`
  writes). All new values are read from `results/spatial_lat_groups.json`
  (flare-controlled run); old values are cross-validated against
  `results/spatial_lat_groups_with_flares.json` *and* the literal .tex text
  (15 JSON sanity assertions; every pattern must match exactly once inside its
  scope - the spatial slice `sec:spatial -> Discussion` or the whole file -
  otherwise the script aborts before writing). The script refuses BOM/CRLF/
  missing final newline and writes UTF-8 + LF only.
- **Changes (identical set in both languages):**
  1. `sec:spatial` prose: pooled drop 73.1/28.2/22.8 -> **72.1/26.1/20.0 %**,
     high/low ratio 3.2x -> 3.6x; 15 m 85.3/14.0 -> 84.2/11.8 %
     (6.1x -> 7.1x); window "1.98 billion spots / 13 152 h" -> **1.80 billion
     / 11 827 h**; significance summary p <= 1.5e-4 -> **p <= 1.95e-3**
     (8/9 cells still at the 5e-5 floor).
  2. `tab:spatial`: all 12 cells (pooled/40/20/15 m x high/mid/low) to the
     flare-controlled values; caption N_storm 198 -> **169**; per-group and
     per-band `N_storm,spots` (e.g. pooled high-lat 90 669 -> 80 673); low-lat
     40 m p 1.5e-4 -> 1.95e-3.
  3. `sec:dropnorm`: T_storm/T_quiet 198/3035 -> **169/2738 h**, raw ratio
     1.75 -> 1.72 %, quiet window 15.3x -> 16.2x, normalization 169/2738.
  4. Limitations "One sampled hour per Kp epoch": 198/3035 -> 169/2738
     sampled hours, full 594/9105 -> 507/8214 h.
  5. Confounders SID sentence rewritten: flare effects ARE controlled in the
     latitude-group analysis (1 325 h, 10.1 %, shifts pooled drops by
     1-2 pp); the permutation-based analyses retain all hours (citation kept).
  6. Two new notes: (i) `sec:spatial` Methods-style sentence - values are
     flare-controlled, the flare-included run differs by 1-2 pp per group
     (73.1 vs 72.1, 28.2 vs 26.1, 22.8 vs 20.0), p at the permutation floor
     in both runs, so the gradient is not a flare (SID) artifact; (ii) a new
     Limitations item "Solar-flare control / Контроль солнечных вспышек":
     1 325 flare hours remove the sampled hour of 326 of 4 349 covered epochs
     (N_storm 198 -> 169, N_quiet 3035 -> 2738), pooled drops shift 1-2 pp,
     all p stay at the floor, and the smaller epoch sample lowers power for
     secondary pairwise Kp-bin contrasts.
- **Intentionally NOT changed (author decisions, 2026-10-30):**
  - Permutation-test headline numbers (abstract 198 storm epochs, -27.7 /
    -27.2 / -38.7 %, bootstrap CIs, episode/monthly/UT-window/pairwise/
    held-out tables and the remaining 198/3035 mentions) still describe the
    original WITH-flares runs. The author commissioned a **full re-run
    campaign** (all derived analyses without flare hours + full manuscript
    sync) as a separate task; the interim hybrid state is explicitly
    documented by the rewritten SID sentence and the new Limitations item.
  - "Storm-slot independence: The 198 Kp >= 5 epochs ..." kept: it is a
    statement about the Kp epoch universe of the window (true regardless of
    the flare filter); the new Limitations item covers the 198 -> 169
    reduction of the analyzed sample.
  - `sec:dropnorm` block-size-sensitivity sentence ("8/9 at the p-floor under
    both settings; low-lat 40 m p = 1.5e-4 -> floor") **not yet updated**: the
    block = 8 rerun WITHOUT flare hours is pending -
    `python scripts/spatial_analysis.py --block 8 --out
    results/spatial_lat_groups_block8.json` failed its Phase-1 API
    reachability check on 2026-10-30 (wspr.live connection reset after 3
    attempts). Re-run when the endpoint is reachable, then patch the sentence
    via script (fresh 9-cell p-values for block = 8 vs 24).
- **Verification:** `ruff check .` OK; `mypy crosscorr_lib` OK;
  `pytest -m "not slow"` 367 passed, 2 deselected; both .tex files verified
  BOM-free, CRLF-free, final newline = LF; `git diff` reviewed.

### 2026-10-30 — Solar flare control via GOES X-ray (Q1 audit, physical block, Phase A)

- **Task:** Q1 audit physical block: control for solar flares (GOES X-ray) and
  regenerate affected results with a with-flares vs without-flares comparison.
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov
- **Date:** 2026-10-30
- **Changes made:**
  1. **ETL: new source `goes_xray`:**
     - `data/scripts/download_space_weather.py`: new `fetch_goes_xray(start, end, out_dir)` —
       NOAA NCEI GOES-R XRS Level-2, daily NetCDF (1-minute means, ~290 KB/day),
       URL `data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/<sat>/l2/data/xrsf-l2-avg1m/`.
       Multi-satellite fallback `GOES_SATS = ("goes18", "goes16", "goes19")` (goes18 covers the full
       2024-04..2025-10 window; goes16 stops at 2025-04, goes19 starts at 2025-01). Days with no file
       on any satellite are skipped, not zero-filled. Requires `netCDF4` — declared as optional
       extra `etl = ["netCDF4>=1.6"]` in `pyproject.toml` (lazy import, CI unaffected).
     - `data/scripts/fetch_all.py`: `goes_xray` added to `KNOWN_SOURCES` and the space-weather router.
     - `data/scripts/config.yaml`: `space_weather.indices += "goes_xray"`.
     - `data/scripts/unify_schema.py`: `load_goes_xray()` + `_route_sw()` branch
       (`detector_id = "goes_xray_1_8a"`, `detector_type = "goes_xray"`, `meta.granularity = "hourly"`).
     - `crosscorr_lib/analysis/residuals.py`: `DETECTOR_UNITS["goes_xray"] = "W/m2"`.
     - `data/schema/unified_schema.json`: `detector_type` enum `+= "goes_xray"` (kept in sync with
       `DETECTOR_UNITS` by `test_detector_units_cover_schema_enum`).
  2. **Aggregation is hourly MAX, not mean (explicit decision):**
     - `download_space_weather.py:_hourly_max_from_nc()` groups the 1-minute XRS-B (1–8 Å) flux by
       hour and takes `max()`. A 10-minute M-class flare diluted by hourly `mean()` would fall below
       the M1.0 threshold. Empirical check on the 2024-05-10 super-flare day (AR 3664): threshold
       1e-5 W/m2 flags **16 hours by max but only 11 by mean — 5 flare hours lost**, including the
       06:00 UTC peak (max 3.98e-4 vs mean 9.9e-5). Minutes with `flag != 0` or non-finite flux are
       dropped; hours with zero valid minutes are absent from the CSV (a gap, not a zero).
  3. **Flare filter is an `isin()` index, not merge + dropna:**
     - `scripts/perm_test_18mo_3band.py:73` — `wspr[~wspr["hour"].isin(flare_hours)]`
     - `scripts/spatial_analysis.py:686` — `counts[~counts["hour"].isin(flare_hours)]`
     - Missing GOES data therefore never drops WSPR hours: an hour with no GOES row is not in
       `flare_hours` and stays in the analysis ("no data = no flare"), with no `fillna(0)` that
       could mask a real zero background. The filter reads `value` (raw flux), not `residual`, so
       NaNs from the OLS residual stage cannot affect it. `spatial_analysis.py verify()` FAILS
       loudly if `goes_xray` rows are missing or hourly coverage < 90%, so the run can never
       silently degrade to the uncontrolled analysis.
  4. **CLI flags (no hardcoded parameters):**
     - `scripts/perm_test_18mo_3band.py`, `scripts/spatial_analysis.py`: `--exclude-flares`
       (default on, `BooleanOptionalAction` → `--no-exclude-flares`), `--flare-threshold`
       (default `1e-5` W/m2 = M1.0), `--out`. Both JSONs record a `flare_filter` block
       (threshold, flare hours in period, hours excluded).
     - `scripts/flare_control_compare.py` (new): builds the with-flares vs without-flares
       comparison table (drop%, p-value, N_storm deltas) from the two result JSONs.
  5. **Docs:** `docs/DATA_PIPELINE.md` (GOES source section + limitations),
     `docs/PIPELINE.md` §9b, `docs/methodology.md` item 9, `data/README.md`.
  6. **Zenodo v11 required:** the unified schema changed (`detector_type` enum gained `goes_xray`,
     `unit` gained `W/m2`), so a new data package version must be published. Raw observations are
     unchanged; the `unified.parquet` structure/values are. `paper/` not touched.
- **Comparison results (with flares vs without flares):**
  - 18-month permutation (2024-04-01..2025-10-01), 50 000 permutations, seed 42:

    | Band | Drop% with flares | Drop% without flares | Δ (pp) | p with | p without | N_storm |
    |------|-------------------|----------------------|--------|--------|-----------|---------|
    | 15m  | −38.7 | −36.8 | 1.9 | 2.00e-05 | 2.00e-05 | 198 → 169 |
    | 20m  | −27.7 | −25.5 | 2.2 | 2.00e-05 | 2.00e-05 | 198 → 169 |
    | 40m  | −27.2 | −25.3 | 1.9 | 2.00e-05 | 2.00e-05 | 198 → 169 |

  - hours excluded: **1325 of 13152 (10.1%)** flare hours (hourly GOES XRS-B max
    flux ≥ 1e-5 W/m2, M1.0+); 29 of them were storm epochs (198 → 169, −14.6%).
  - verification: the `--no-exclude-flares` run reproduces the pre-flare-control
    canonical JSON exactly (0 differing values across all 66 shared keys — only the
    `config.flare_filter` block was added), so the pipeline regeneration is bit-for-bit
    neutral for the baseline.
  - **Verdict: robust physics.** All three bands kept p at the floor (2.00e-05 =
    1/50000), the latitude/frequency gradient order (15m > 20m > 40m) is unchanged,
    and the drop% attenuated by only ~2 pp after removing 10% of the hours — flare
    (SID) contamination explains only a small share of the suppression.
  - **Power caveat:** pairwise Kp-bin tests lost significance on 15m (all 3 pairs)
    and on 40m Kp5-6 vs Kp6-7, driven by N_storm 198 → 169 rather than by effect
    reversal (effect sizes stay negative). The main three-band result and the Kp7+
    pairs on 20m/40m remain significant. Recorded in `docs/first_result.md` §6.
  - spatial (High/Mid/Low), 20 000 iterations, seed 42 — completed 2026-10-30
    after the API became reachable (`--sample-n 500`; the default 5000 exceeds
    the endpoint's ~19 s long-request budget in this region, see `docs/LESSONS.md`):

    | Group | Drop% with flares | Drop% without flares | Δ (pp) | p with | p without | N_storm |
    |-------|-------------------|----------------------|--------|--------|-----------|---------|
    | High-lat (>60)  | −73.1 | −72.1 | 1.0 | 5.00e-05 | 5.00e-05 | 198 → 169 |
    | Mid-lat (30–60) | −28.2 | −26.1 | 2.1 | 5.00e-05 | 5.00e-05 | 198 → 169 |
    | Low-lat (<30)   | −22.8 | −20.0 | 2.8 | 5.00e-05 | 5.00e-05 | 198 → 169 |

    Per band (without flares): 15m −84.2/−38.6/−11.8, 20m −70.3/−24.9/−22.2,
    40m −67.2/−25.2/−21.6 (high/mid/low); all p = 5.00e-05 except 40m low-lat
    p = 1.95e-03 (q = 1.95e-03, was 1.50e-04 with flares — power loss only).
  - **spatial verdict: the auroral gradient survives flare control.**
    High > Mid > Low holds in the pooled table and in every band; attenuation
    is 0.8–3.1 pp across all 12 group/band cells while p stays at the
    permutation floor in 11/12 of them. The high-lat effect (−72.1%) is an
    order of magnitude above the low-lat one — flare (SID) hours cannot
    explain the latitude structure.
  - the `--no-exclude-flares` spatial run reproduces the pre-control canonical
    JSON exactly (148/148 shared keys identical apart from the `generated`
    timestamp; only `params.flare_filter` was added).
  - tables: `results/flare_control_comparison_perm.csv`,
    `results/flare_control_comparison_spatial.csv`; run JSONs:
    `results/*_with_flares.json` (with flares) vs the canonical paths (without).

### 2026-10-30 — Statistical audit fixes (Phase 2: Apply)

- **Task:** Apply Q1 audit feedback: switch to IAAFT surrogates, remove Fisher double-counting in Max-stat, unify ESS to τ_int.
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov
- **Date:** 2026-10-30
- **Changes made:**
  1. **IAAFT surrogates (default):**
     - `crosscorr_lib/analysis/surrogate.py`: `surrogate_method="phase"` → `"iaaft"` (line 452), `surrogate_test` now calls `iaaft_surrogate` (line 122)
     - `crosscorr_lib/pairs.py`: `method="phase"` → `"iaaft"` (line 201), docstring updated
  2. **Removed Fisher double-counting:**
     - `crosscorr_lib/analysis/surrogate.py`: `fisher=True` → `False` (line 373), `fisher_weighted_max_stat` branches: `fisher=True` uses `|arctanh(r)|*sqrt(n-3)`, `fisher=False` uses raw `|r|`; docstring explains double-counting issue
  3. **Unified ESS to τ_int:**
     - `docs/first_result.md`: §3.4 AR(1) formula replaced with τ_int + threshold rule (5 consecutive lags < 1.96/√n)
     - `README.md`: "AR(1)" → "integrated autocorrelation time, tau_int"
     - `crosscorr_lib/analysis/effective_sample.py`: docstring updated, references `integrated_autocorrelation_time()`
  4. **Documentation updates:**
     - `docs/PIPELINE.md` §4.2: description → raw max|r| (Fisher disabled)
     - `docs/methodology.md` lines 20-21: raw max|r|, `fisher=False`
  5. **Tests updated:**
     - `tests/test_statistical_reference.py`: lines 142-167 rewritten to expect raw `|r|` (default `fisher=False`)
- **Rationale:** Q1 audit feedback — IAAFT more conservative null, remove double-counting of `n-3` in Fisher transform on empirical surrogates, τ_int model-agnostic ESS.
- **Files modified:** `crosscorr_lib/analysis/surrogate.py`, `crosscorr_lib/pairs.py`, `crosscorr_lib/analysis/effective_sample.py`, `docs/first_result.md`, `README.md`, `docs/PIPELINE.md`, `docs/methodology.md`, `tests/test_statistical_reference.py`.
- **Methodology impact:** Yes — T_obs values change (raw |r| vs Fisher Z), p-values recomputed with IAAFT surrogates.
- **Paper impact:** Potentially — if Results reports specific T_obs values, regenerate from `results/*.json`.
- **Reproducibility:** Yes — same seeds, same pipeline, deterministic.

---

### 2026-10-30 — IAAFT Audit Verification

2026-10-30 — IAAFT Audit Verification: Confirmed that core paper results (spatial & 18mo) rely on block permutation, not surrogate phase randomization. IAAFT fix applied only to library defaults; JSON results remain valid. Determinism smoke-test passed.

- **Task:** Verify whether IAAFT surrogate fix affected persisted results.
- **AI model:** MiMo V2.6 Flash (OpenCode)
- **Human reviewer:** Alexey Petrov
- **Findings:**
  - `spatial_analysis.py` and `perm_test_18mo_3band.py` use block permutation (`rng.permutation`), not surrogate tests — unaffected by IAAFT default.
  - All 26 `results/*.json` files generated by block-permutation or deterministic scripts — no IAAFT dependency.
  - `simulate_network.py` / `simulate_snapshots.py` (only scripts calling `cross_correlation_pairs_with_max_stat`) hardcode `method="phase"` — unaffected.
  - SHA256 of `results/spatial_lat_groups.json` and `results/perm_test_18mo_3band.json` identical before/after full rerun (seed=42).
- **Conclusion:** Core paper results (spatial & 18mo) are deterministic and independent of IAAFT fix. IAAFT change applies only to future surrogate-based analyses.
- **Files modified:** `docs/AI_ASSISTANCE.md` only.
- **Reproducibility:** Yes — byte-identical outputs on rerun.

---

### 2026-10-27 (Paper Update) — Limitations note on high autocorrelation

2026-10-27 (Paper Update): Added a note to the Limitations section in both main.tex and main_ru.tex regarding the drop in statistical power at AR(1) ≈ 0.95, based on the experimental findings from power_curve.py verification.

### 2026-10-27 (Update) — Power-curve figure check after the `ar` fix

- **Task requested:** regenerate the power-curve figures in `paper/` after
  the `ar`-propagation fix in `power_curve.py` and review figure captions.
- **Finding 1: no such figures exist.** `paper/figures/` contains only
  fig1–fig5 (kp timeseries, scale dependence, frequency dependence,
  day–night asymmetry, baseline invariance) plus `lstid_pilot_may2024.png`;
  neither `main.tex` nor `main_ru.tex` includes a power-curve figure, and
  `git log --all -S "power_curve" -- paper/` shows none ever existed. The
  only generator is the module CLI (`python -m
  crosscorr_lib.analysis.power_curve --plot`); no script in `scripts/`
  produces manuscript figures from it.
- **Finding 2: the fix does not change default runs.** The CLI `--ar`
  default (0.85) equals the `benchmark()` default that was used implicitly
  before the fix. An explicit equivalence check (same seeds, pre- vs
  post-fix argument paths, `tmp_plots/verify_default_equivalence.py`)
  returned identical `p_value` and `detected_lag` for every tested
  coupling (`EQUIVALENT`).
- **Quick comparison runs** (fast flags: 4–5 couplings, 3–5 seeds,
  n=400/4000, 20–50 surrogates; output kept in the untracked `tmp_plots/`)
  show a difference only for non-default `ar`: with `--ar 0.95` the median
  detected lag shifts from 9 to 14–15 (true lag 6) and power falls from
  0.20 to 0.00, since `hit` requires `|detected_lag − true_lag| ≤ 1`.
- **No changes were made to `paper/`:** there are no power-curve figures to
  regenerate, and no caption mentions `ar=0.85` (the only `0.85` occurrences
  are `width=0.85\textwidth` and p-values such as 0.8547), so captions need
  no review. All steps were performed on explicit human instruction; after
  the requested regeneration turned out to be a no-op, the human author
  chose this factual reporting variant instead of the pre-drafted text.

### 2026-10-29 — Spatial latitude-group analysis added to `paper/main.tex` (methods, limitations, disclosure)

- **Seven text fragments drafted by the AI assistant and approved by the
  human author against a numeric checklist** (every figure re-derived from
  `results/spatial_lat_groups.json`): Main result, Discussion implication,
  Methods time-normalization, Limitations sampling, endpoint disclosure,
  table caption, block-sensitivity statement.
- **New Results subsection (Table `tab:spatial`)** reports the pooled drop
  gradient 73.1 / 28.2 / 22.8 % and the per-band cells; `N_storm_spots`
  is captioned per cell (high-lat 15 m = 7 665 flagged as the grey-zone
  value requiring the caption).
- **Author-caught correction before insertion:** the Kp join exposes 198
  storm / 3035 quiet *sampled hours* (one hour per 3-h epoch), not the
  full 594 / 9105 h; the initial fragment carrying 594 h was rejected and
  the Limitations item records the design fact. Drop% itself is invariant
  because the ratio is unchanged.
- **Terminology check before insertion:** the existing Methods already fix
  "block = 24 epochs = 72 h"; the block-sensitivity fragment reuses that
  terminology (block = 8 = 24 h variant; uniformly conservative across all
  nine band x latitude cells, no cell less significant).
- **`paper/main_ru.tex` intentionally not updated** — the Russian set
  requires a separate review round per the author's protocol. One wording
  deviation was introduced and reported for post-insertion review: the
  internal version tag was removed from the Implication sentence (the
  paper does not otherwise reference release versions).
- **Selective staging:** this entry and the `paper/main.tex` insertions
  were committed while the author's separate uncommitted held-out-2026h1
  changes to the same files were deliberately left in the working tree
  (awaiting the author's OK, per the 2026-10-27 entry).
- **Exact run command documented in `paper/main.tex` (Data):** the
  disclosure paragraph now states
  `python scripts/spatial_analysis.py --source api --skip-crosscheck --apply`
  with `\verb` so that `--` and `_` render literally (2026-10-29,
  explicit human instruction; selective staging, held-out untouched).
### 2026-10-29 — RU spatial translation synchronized (`paper/main_ru.tex`, sec:spatial/sec:dropnorm)

- **Five RU fragments drafted by the AI assistant and approved by the
  human author against a terminology checklist**, then inserted into
  `paper/main_ru.tex`: endpoint disclosure (Data), `sec:dropnorm`
  subsection (Methods), `sec:spatial` subsection + `tab:spatial` table
  (Results), implication lead (Discussion), Limitations item.
- **Critical catch before insertion:** a double negation in the
  block-sensitivity sentence ("не делает ... неизменной") inverted the
  meaning of the English "leaves every band x latitude cell unchanged
  or more significant"; corrected to "оставляет каждую ячейку
  неизменной или более значимой".
- **Terminology fixed by the author:** time-normalized drop ->
  "нормированное по времени снижение"; midpoint-latitude -> "широта
  середины трассы"; add-one -> "поправка на единицу (add-one)";
  p-floor -> "нижняя граница $p$"; epoch universe -> "множество эпох
  общее"; auroral -> "авроральная" (kept).
- **Grammar fix:** "отобранную час" -> "отобранный час" (2x).
- **RU-only commit:** `paper/main.tex` (EN) untouched in this commit;
  labels `sec:spatial`/`sec:dropnorm`/`tab:spatial` are identical across
  EN/RU files, which is normal (independent documents).

### 2026-10-29 — Data package v10 published on Zenodo

- **Data package v10 published on Zenodo.** Version DOI:
  10.5281/zenodo.23769556. Concept DOI: 10.5281/zenodo.23285958.
- **`CITATION.cff`:** the previous DOI
  10.5281/zenodo.23495246 was replaced with the Concept DOI
  (author instruction: always cite the concept, not a version).


### 2026-10-27 - Extended held-out window (Jan-Jun 2026) prepared for revision; `paper/` untouched

- **All steps on explicit human instruction; no commit made (awaiting author's OK).**
- **New `data/scripts/fetch_heldout_2026h1.py`** (two-phase verify -> apply;
  CLI `--start/--end/--bands/--apply/--workers/--timeout/--out-dir/--skip-band-check`,
  no hardcoded dates). Phase 1 is read-only: inventories the union of
  `data/raw/wspr/` and `data/raw/wspr_hourly/` (the 2026 hourly data actually
  lives in `wspr_hourly/`, not `wspr/` — deviation from the literal spec;
  both directories are scanned) and validates band indices via
  `SELECT DISTINCT band FROM wspr.rx` (15m=21, 20m=14, 40m=7 confirmed).
  Phase 2 downloads only the missing day-band series from
  `http://db1.wspr.live/` (ClickHouse `wspr.rx`, GET, `JSONCompact`, retry
  backoff 5/15/30 s, sha256 sidecars) and normalises both observed JSON
  shapes (`array[4]` = `[hour, spots, mean_snr, max_dist]`, `array[2]` =
  `[hour, spots]`, dict rows) into canonical
  `wspr_hourly_YYYY-MM-DD_<band>.csv`; existing legacy JSON days are read
  as-is by the builder (no materialisation rewrite).
- **Fetched the Apr 25/Jun 30 gap: 199 day-band files, ok=199 failed=0
  (309.7 s)** — 15m Apr 25-Jun 30 = 67 days, 20m and 40m Apr 26-Jun 30 =
  66 days each; 253 722 bytes total, 24 hourly rows per file. Full
  Jan 1 - Jun 30 re-verify: 0 missing tasks; canonical CSV count 138 -> 337.
- **New `scripts/build_heldout_extract.py`** (two-phase; CLI `--start/--end/
  --suffix/--bands/--apply`): joins hourly spot counts with Kp epochs from
  `data/raw/space_weather/kp_*.csv` (one hourly count per native 3-h epoch;
  storm kp>=5 / quiet kp<3 / unsettled excluded) — the exact frozen-extract
  construction; reads canonical CSV + legacy `wspr_2026_*` JSON. Writes
  `results/heldout_3band_<band>_2026h1.parquet` (1441 rows; 24 283 / 24 954 /
  24 770 bytes for 15m / 20m / 40m); the frozen `*_2026-10-15.parquet` files
  are never overwritten. Refuses to write on coverage gaps or Jan-Mar
  inconsistency.
- **Checks passed:** coverage 181/181 days per band, 0 missing/empty days;
  epochs 1441 per band (expected 1448 — 7 Kp epochs absent upstream in late
  Jun; the Kp file has 1441 rows and ends 2026-06-30 00:00); Jan-Mar
  720 epochs, N_storm=47, N_quiet=439 per band (matches frozen); value
  cross-check vs frozen 2026-10-15 extracts: **720/720 hours exact per
  band**; Apr-Jun N_storm=23, N_quiet=563, 721 epochs; **Jan-Jun N_storm=70,
  N_quiet=1002, N_total=1441** (was 47 / 439 / 720).
- **`scripts/recompute_heldout_residual.py` and `scripts/abs_loss_ratio_ci.py`
  gained backward-compatible CLI** (`--src-suffix`, `--out`; recompute also
  `--period`): defaults reproduce the frozen Jan-Mar run, and the Phase-0
  `EXPECT_P` verification now runs only for `--src-suffix 2026-10-15`.
  Extended outputs: `results/heldout_resid_2026h1.json`,
  `results/abs_loss_ratio_ci_2026h1.json`. Frozen JSONs untouched.
- **Residual p-values (Jan-Jun 2026) vs frozen Jan-Mar** (n_iter=50000,
  block=24, seed=42 unchanged; obs_resid in parentheses):
  20m 3.99992e-04 (19/50000 exceed, obs -12827.9) vs 1.99996e-05;
  40m 7.99984e-05 (3, obs -10128.9) vs 1.99996e-04;
  15m 4.7599e-03 (237, obs -3098.5) vs 7.99984e-05 — all three remain
  significant at p<0.01. Raw Drop% Jan-Jun: 20m -22.39, 40m -21.84,
  15m -9.96 (Jan-Mar: -26.73, -29.0, -22.13).
- **Absolute-loss ratio (Jan-Jun held-out / Apr-2024..Sep-2025 training):**
  20m 0.9839 [0.1384, 1.8916] (was 1.1009 [0.1764, 1.9363]); 40m 1.0784
  [0.4795, 1.9010] (was 1.4377 [0.6498, 2.3336]); 15m 0.2634 [0.0189,
  0.9830] (was 0.7005 [0.0467, 1.5748]) — the 15m CI now lies entirely
  below 1 (it crossed 1 in the frozen Jan-Mar run). Held-out point estimate:
  20m 20093, 40m 19718, 15m 1364 (heldout n_epochs 1441; n_valid=1000).
  Training series and method (1000 block bootstraps, seed 42) unchanged.
- **`scripts/provenance_manifest.py` updated:** the dataset/artifact/script
  lists now include the 3 `*_2026h1.parquet`, both `*_2026h1.json` and the
  4 held-out pipeline scripts; `heldout_window` is now
  `["2026-01-01", "2026-07-01"]` with `heldout_window_frozen` retained;
  new `--out` flag. Run with
  `--out results/provenance_manifest_2026-10-27.json` — the tracked frozen
  `results/provenance_manifest_2026-10-20.json` was NOT overwritten.
- **`.gitignore`:** negation lines added for the 5 new `results/*` artifacts
  (`heldout_3band_{15m,20m,40m}_2026h1.parquet`,
  `heldout_resid_2026h1.json`, `abs_loss_ratio_ci_2026h1.json`).
- **Documentation:** this entry plus `docs/AUDIT_START_NEXT_SESSION.md`
  record that the extended held-out extract exists but `paper/main.tex` and
  `paper/main_ru.tex` were NOT updated (revision task for the author).
- **Verification:** `ruff check .`, `mypy crosscorr_lib` and
  `pytest -m "not slow"` all pass (367 passed, 2 deselected).

### 2026-10-27 — Bug fixes in `power_curve.py`, expanded test suite, release v1.5.0

- **Fixed a bug in `crosscorr_lib/analysis/power_curve.py`:** `measure_point()`
  did not forward the `ar` parameter to `benchmark()`, so the `--ar` flag was
  silently ignored. The parameter is now propagated; regression test:
  `test_measure_point_forwards_ar_and_records_effective_model`.
- **Fixed related bugs in `crosscorr_lib/analysis/benchmark_utils.py`:**
  `benchmark()` now passes `null_model_name` to
  `max_lag_surrogate_pvalue(..., surrogate_method=...)` — previously `--null`
  had no effect and phase randomisation was always used — and the *actually
  used* null model is recorded in `PowerPoint.null_model` (unknown names such
  as `block` are normalised to `phase`, matching the surrogate implementation).
  Regression tests: `test_benchmark_passes_null_model_to_surrogate`,
  `test_benchmark_normalizes_unknown_null_model`.
- **Fixed `crosscorr_lib/analysis/mantel.py`:** `build_dist_matrix()` now fills
  the diagonal with zeros as promised by its docstring (previously NaN).
- **Tests added/extended in the same session:** `tests/test_power_curve.py`,
  `tests/test_stationarity.py`, `tests/test_mfdfa.py`, `tests/test_safe_exec.py`
  (new files) plus `tests/test_mantel.py`, `tests/test_distance_analysis.py`
  (extended). Test suite 290 → 369 tests, statement coverage 58% → 85%,
  CI gate raised from `--cov-fail-under=45` to `=70`.
- **Paper consistency check:** `paper/main.tex` and `paper/main_ru.tex` were
  searched for `power_curve`, `null_model`, `--null`, `block`, `surrogate`,
  `autocorrelation` and coverage claims. The manuscript makes no statement
  about the power-curve runs or the surrogate null-model choice (all "block"
  references are the block permutation/bootstrap test, a different procedure),
  therefore **no changes were made to the manuscript**.
- All changes above were made on explicit human instruction, reviewed and
  committed by the human author (commits `f6989f8` … `v1.5.0`).
