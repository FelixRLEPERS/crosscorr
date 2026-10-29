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
