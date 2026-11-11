# TimesFM MVP Report — 20m Band

**Date:** 2026-11-11
**Branch:** `experimental/timesfm-test`
**Status:** Phase 2 (MVP, 20m) + Phase 3a (3-band) + Phase 4 (frozen Jan–Mar 2026 confirmation) complete — forecasting confirmed at 1h (frozen skill_1h 20m = 0.435, pre-registered band met); 6–24h margins do not hold on frozen

---

## Revision note (2026-11-11, post-review)

An independent review of the first draft flagged two framing problems. Both are corrected here:

1. **Experiment A's 6h "−75% vs persistence" was a strawman.** Persistence MAE 51.82 at 6h is an artifact of the diurnal cycle (a 6h-ahead hold-last-value forecast is phase-shifted; at 24h the phase realigns, so persistence recovers to 15.06). A **seasonal-naive baseline** (same hour, previous day) is the honest comparison: it gives ~15 MAE at every horizon, so the true TimesFM margin at 6h is **−15%**, not −75%.
2. **Experiment B is a negative result, not a "partial" one.** The pre-registered recall band (0.3–0.6 → "partial") labels anything above 0.3 as partial by construction; it says nothing about precision. At the pre-registered 2σ point TimesFM flags 391 hours for 28 storms — **97% false positives** (precision 0.026). A post-hoc threshold sweep (2/3/4/5σ) confirms no usable operating point exists.

**Net:** forecasting is a narrow but real positive; detection is a negative. Two stories, not one.

---

## Executive Summary

Two experiments tested whether Google's TimesFM (a foundation model for time series) can either (A) forecast WSPR spot density or (B) detect geomagnetic storms without Kp in its input.

### Key Findings

| Experiment | Question | Result | Verdict |
|---|---|---|---|
| **A (baseline)** | How well does TimesFM forecast "normal" patterns? | MAE 8.03 / 12.83 / 13.32 (1/6/24h) vs seasonal-naive 15.13 / 15.08 / 15.06 | **Positive (narrow):** beats both naive baselines at every horizon, but the margin is modest beyond 1h |
| **Phase 3a (3-band)** | Does it hold across 20m/40m/15m? | skill_1h: 15m 0.603, 20m 0.572, 40m 0.505 — beats naive on all 3 bands | **Positive (narrow):** confirmed cross-band; ordering reflects physical predictability (15m easiest, 40m hardest) |
| **Phase 4 (frozen)** | Does it generalize to untouched Jan–Mar 2026? | skill_1h 20m **0.435** ∈ [0.34, 0.54]; 6–24h ≈0 (15m negative at 12/24h) | **Confirmed at 1h** (pre-registered band met); 6–24h margins **do not** generalize |
| **B (storm-aware)** | Can TimesFM detect storms WITHOUT Kp in its input? | precision 0.026, recall 0.357, F1 0.048; **97% of alerts are false** | **Negative:** not usable for operational detection at any tested threshold |

### Pre-registered interpretation thresholds (and why they are insufficient alone)

- **Recall ≥ 0.6**: TimesFM catches storms without Kp → useful for anomaly detection
- **Recall 0.3–0.6**: "Partial detection"
- **Recall < 0.3**: does NOT replace Kp-based detection

Recall = 0.357 formally lands in the "partial" band, **but these thresholds bound recall only**. A detector with precision 0.026 is unusable operationally regardless of recall: an operator would receive 391 alerts per quarter of which 10 are real. The honest reading (including precision, which the pre-registered band did not constrain) is **negative for operational detection**.

---

## Experiment A: Baseline (Forecast Quality)

**Train:** Apr 2024 – Sep 2025 (13,152 h, 198 storm hours — all included)
**Pseudo-test:** Jan – Mar 2025 (walk-forward, 2,160 h, 28 storm hours)
**Horizons:** 1h, 6h, 24h ahead
**Context:** 512 h (zero-shot, no fine-tuning)

### Results

| Horizon | TimesFM MAE | Persistence MAE | Seasonal-naive MAE | TimesFM vs seasonal-naive |
|---|---|---|---|---|
| 1h | **8.03** | 14.81 | 15.13 | **−47%** |
| 6h | **12.83** | 51.82 ⚠️ | 15.08 | **−15%** |
| 24h | **13.32** | 15.06 † | 15.06 † | **−12%** |

*Baselines computed on identical origins and actuals (`results/timesfm_mvp_20m_baselines.json`).
Persistence = hold the last observed value. Seasonal-naive = value from the same hour of
the previous day. ⚠️ = persistence at 6h is inflated by the diurnal phase mismatch and is
**not a fair comparison** — read the seasonal-naive column.*

*† = the two baselines are **identical by construction at 24h**, hence the bit-identical
15.06. Both are anchored at the prediction origin g, not at the target time g+h−1:
persistence uses `values[g−1]`, seasonal-naive uses `values[g−(25−h)]`. At h=24 that lag
is `25−24 = 1`, so seasonal-naive collapses to `values[g−1]` = persistence. At 1h and 6h
the lags differ (g−24 and g−19 vs g−1), so the two baselines genuinely differ there. This
is an arithmetic identity, not a data duplication bug; it does not affect any conclusion
(TimesFM 13.32 beats the single shared baseline either way).*

**Interpretation:**
- **1h (−47%):** the real, useful result. TimesFM clearly beats both naive baselines on
  the short horizon where autocorrelation is high. This supports operational use "one hour
  before degradation."
- **6h (−15%):** honest margin. Persistence's 51.82 is an artifact (diurnal phase); against
  the fair seasonal-naive baseline the gain is modest but positive.
- **24h (−12%):** seasonal-naive equals persistence here (both = value at origin−1, since
  lag 24h wraps to the previous hour), so the two baseline columns coincide; the margin is
  modest.
- Error grows then saturates (8.03 → 12.83 → 13.32): the model converges to the
  seasonal/quiet-time level rather than tracking storm excursions.

---

## Phase 3a: Extended Forecasting — 3 Bands (Jan–Sep 2025)

**Scope:** forecasting only (Experiment B detection closed as negative).
Extended pseudo-test to all available 2025 data (**Jan 1 – Sep 30 2025**, 6,552 h per
band — Oct–Dec 2025 has no data in `unified.parquet`), across **20m / 40m / 15m**.
Frozen Jan–Mar 2026 untouched (Phase 4 confirmation only). Zero-shot TimesFM 2.5-200m,
context 512h, horizons 1/6/12/24h, three baselines (persistence, seasonal-naive, mean-24h).

**Script:** `scripts/timesfm_forecast_phase3.py` (`--from-records` rebuilds metrics from
per-band records CSVs without reloading the model).

### Results (6,552 forecasts × 3 bands)

**skill = 1 − MAE_model / MAE_seasonal-naive**, computed *within* each band:

| Band | skill 1h | skill 6h | skill 12h | skill 24h | MAE 1h | naive-24h MAE |
|---|---|---|---|---|---|---|
| 15m | **+0.603** | +0.226 | +0.140 | +0.116 | 4.02 | 10.12 |
| 20m | +0.572 | +0.207 | +0.145 | +0.093 | 7.07 | 16.55 |
| 40m | +0.505 | +0.186 | +0.131 | +0.099 | 7.89 | 16.00 |

**TimesFM beats all three naive baselines on all three bands at every horizon.**

### Cross-band comparison: magnitude vs ordering (important caveat)

- **Skill MAGNITUDE is NOT cross-band comparable.** Each band's skill divides by its *own*
  seasonal-naive MAE (10.12 / 16.51 / 15.95 at 1h), so the denominators differ by ~1.6×.
  A direct "0.603 > 0.572" read across bands is not meaningful.
- **The ORDERING IS real, confirmed by two independent metrics.** Absolute MAE normalized
  by a *pooled* std (shared scale) gives the same order as skill at every horizon:

  | Band | skill 1h | MAE / pooled-std (1h) |
  |---|---|---|
  | 15m | 0.603 (best) | 0.127 (best) |
  | 20m | 0.572 | 0.223 |
  | 40m | 0.505 (worst) | 0.249 (worst) |

  If the skill ordering were a normalization artifact, the scale-free MAE/pooled would
  show a *different* order. It does not — both agree: **15m easiest → 40m hardest.**

### Physical interpretation (consistent with the paper)

The ordering reflects intrinsic predictability, not model favoritism:

- **15m** is the most predictable — dominated by MUF / foF2 suppression, essentially a
  **single dominant mechanism**, so a quiet-time forecast tracks it well.
- **40m** is the least predictable — **D-layer absorption** depends on particle flux,
  flares, multiple competing mechanisms → physically noisier → lower skill.
- **20m** sits between them.

This matches the paper's mechanism split (15m ≈ MUF suppression; 40m ≈ D-layer
absorption). More complex physics → lower ceiling on naive-forecast skill.

### Note on the pre-registered stop condition

A stop condition ("flag if 15m skill > 20m skill") was set on the premise that 15m is the
*noisiest* band. Diagnosis showed the premise is false: **15m is the *least* variable**
(std 25.89 vs 33.45/35.59), hence easiest to forecast. Band-swap (H1) and data leakage
(H3) were both explicitly ruled out (records `actual_1h` std matches raw band bit-for-bit;
all origins strictly in 2025, context strictly before origin). The stop condition was a
**false positive from an incorrect premise**; the ordering it flagged is a genuine result,
not a bug or artifact.

### Honest assessment (Phase 3a)

- Positive, narrow: TimesFM beats naive baselines on all 3 bands; the margin is large at
  1h (skill 0.51–0.60) and modest at 6–24h (0.09–0.23).
- Cross-band *skill magnitude* is not comparable; cross-band *ordering* is, and it is
  confirmed independently (MAE/pooled).
- Does **not** establish "foundation models solve HF forecasting" — only "beats naive
  baselines on 1–6h WSPR density across 3 bands."

---

## Phase 4 — Frozen Confirmation (Jan–Mar 2026)

**One pre-registered run, no new experiments.** Same code path as Phase 3a
(`scripts/timesfm_forecast_phase3.py --frozen`), same 3 bands × 4 horizons, same
baselines, same metrics. Frozen window: **2026-01-01 → 2026-04-01**; actual frozen data
ends **2026-01-19** (456 h available → 433 forecast origins after dropping the 24h tail).
Frozen Jan–Mar 2026 was untouched by Phase 2/3a.

**Pre-registered confirmation threshold:** frozen skill_1h 20m ∈ [0.34, 0.54]
(±0.10 around the Phase-2 MVP value 0.44) → confirmation; < 0.34 → record
"generalizes partially" and stop.

### Results (433 forecasts × 3 bands)

skill = 1 − MAE_model / MAE_seasonal-naive; **Phase 3a value in parentheses:**

| Band | skill 1h | skill 6h | skill 12h | skill 24h |
|---|---|---|---|---|
| 20m | **+0.435** (0.572) | +0.012 (0.207) | +0.017 (0.145) | +0.056 (0.093) |
| 40m | +0.469 (0.505) | +0.174 (0.186) | +0.190 (0.131) | +0.221 (0.099) |
| 15m | +0.388 (0.603) | +0.015 (0.226) | −0.032 (0.140) | −0.098 (0.116) |

### Verdict against the pre-registered threshold

- **CONFIRMED at 1h:** frozen skill_1h 20m = **0.435**, inside [0.34, 0.54].
  All 3 bands are positive at 1h (0.39–0.47) on held-out data.
- **6–24h does NOT hold:** 20m skill at 6/12h collapses to ≈0 (0.012/0.017),
  15m turns **negative** at 12h/24h (−0.032/−0.098 — worse than seasonal-naive).
  Only 40m retains a modest positive margin at every horizon (0.17–0.22).
- **Difficulty ordering preserved:** MAE/pooled at 1h gives **15m < 20m < 40m**,
  identical to Phase 3a — the physical ordering (15m/MUF easiest, 40m/D-layer
  hardest) survives held-out data.
- **Skill-magnitude ordering flipped** (frozen 1h: 40m > 20m > 15m vs 3a:
  15m > 20m > 40m) — consistent with the Phase 3a caveat: cross-band skill
  *magnitude* depends on the band's own (shifting) baseline and is not a stable
  cross-band quantity. The frozen window was far more volatile (std: 40m 81.4 vs
  33.4 in 3a; 20m 46.7 vs 35.6), so denominators moved per band.
- **24h identity holds** (persistence == seasonal-naive on all 3 bands, bit-exact).

### Caveats (frozen-specific)

- The frozen window is **harder than 2025**: higher volatility on every band
  (40m std 2.4× Phase 3a) — confirmation was earned on a more active period, not an easy one.
- **Context gap:** Oct–Dec 2025 has no data in `unified.parquet`, so every frozen
  origin's 512h context crosses a 3-month gap (last pre-gap row: 2025-09-30 23:00).
  This affects all bands/horizons equally and does not favor the model.
- n = 433 origins per band — small; 1h margins are stable across bands, long-horizon
  margins are not.

### Honest assessment (Phase 4)

- **The headline claim survives held-out confirmation:** TimesFM beats
  persistence and seasonal-naive at **1h** on frozen Jan–Mar 2026 (skill 0.39–0.47,
  20m 0.435 within the pre-registered band).
- **The 6–24h claim does not:** what Phase 3a showed as modest positive margins
  (0.09–0.23) is ≈0 or negative on frozen for 20m/15m. Final framing must say
  "**beats naive baselines at 1h; no usable margin at 6–24h**" (40m a partial exception).
- Quantile/interval forecasts: **not run** (deferred as a separate task).
- This closes the forecasting branch: positive at 1h (narrow, confirmed), no
  longer-horizon generalization. Not a claim that foundation models solve HF forecasting.

---

## Experiment B: Storm-Aware Detection

**Train:** Apr 2024 – Sep 2025 (**storms EXCLUDED from context**: 198 storm hours removed → 12,954 h, 0 storms)
**Pseudo-test:** Jan – Mar 2025 (walk-forward, 2,160 h, 28 storm hours)
**Pre-registered detector:** `|residual| > 2 × rolling_std(168h, center=True)`

> **Design note (important):** TimesFM runs zero-shot (no fine-tuning), so its only
> "training" input is the context window. "Train without storms" is therefore implemented
> as *excluding storm epochs (Kp ≥ 5) from the context history* (`build_context()` via
> `nonstorm_idx`), **not** as a fine-tuning split. Kp is never an input to the model — it
> only defines ground-truth labels. Consequently this experiment does **not** test "can
> TimesFM learn a storm-free baseline"; it tests "**given a non-storm context, does the
> model flag a storm as an anomaly?**" The answer is: weakly, and with overwhelming noise.

### Pre-registered result (2σ)

| Metric | Value |
|---|---|
| Precision | 0.0256 |
| Recall | 0.3571 |
| F1 | 0.0477 |
| TP / FP / FN / TN | 10 / 381 / 18 / 1751 |
| Storm hours in test (Kp ≥ 5) | 28 |
| Alerts fired | 391 |
| **False-positive share of alerts** | **97.4%** |

**Interpretation:** TimesFM, given a non-storm context, flags storms weakly (recall 0.36)
but with a **97% false-positive rate**. No operational deployment could absorb 391 alerts
per quarter where 10 are real. **Kp-based detection remains the appropriate method.**

The model does carry a weak storm-correlated signal: precision 0.026 is ~2× the base rate
(28/2160 = 1.3%), i.e. a small lift over random. But a 2× lift at 2% precision is not a
detector.

### Post-hoc threshold sweep (sanity check, not pre-registered)

To confirm the negative rather than rest on a single operating point, the σ threshold was
swept on the same records (`results/timesfm_mvp_20m_threshold_sweep.json`):

| σ | Alerts | TP | FP | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| 2 | 391 | 10 | 381 | 0.026 | 0.357 | 0.048 |
| 3 | 124 | 3 | 121 | 0.024 | 0.107 | 0.040 |
| 4 | 35 | 1 | 34 | 0.029 | 0.036 | 0.032 |
| 5 | 15 | 1 | 14 | 0.067 | 0.036 | 0.047 |

**No usable operating point exists.** Raising σ buys no precision (0.024 → 0.067 across
2σ→5σ, always < 7%) while recall collapses (0.357 → 0.036). Even at 5σ, 14 of 15 alerts
are false. **Threshold tuning cannot rescue detection — the result is negative.**

---

## Comparison with Validated Core (Block Permutation)

The paper's validated results (block permutation, `results/perm_test_18mo_3band_norm_tx.json`):

| Metric | Block Permutation (paper) | TimesFM (MVP) |
|---|---|---|
| **Method** | Statistical hypothesis test | Time series forecasting |
| **Question** | "Is the storm effect real?" | "What happens next N hours?" |
| **20m effect size** | −23.9% drop (p=2e-5) | MAE 8.03 / 12.83 / 13.32 (1/6/24h) |
| **Ground truth** | Kp ≥ 5 (external) | Self-supervised forecast; Kp only for labels |
| **Interpretation** | Storm causes drop | Model predicts normal pattern |

### Key Insight

**Block permutation and TimesFM answer different questions:**

- **Block permutation** proves causality: "Storms cause spot density drop (p < 2e-5)"
- **TimesFM** forecasts: "Based on history, spot density will be X in N hours"

They are **complementary, not competing, and not rankable** — this MVP does not and cannot
show TimesFM is "better or worse." What the MVP establishes:

- Forecasting the quiet-time baseline works: TimesFM beats persistence *and*
  seasonal-naive at 1/6/24h, with a large margin only at 1h.
- Storm detection from residual anomalies **fails**: 97% false positives at every tested
  threshold. Kp remains essential.

---

## Technical Details

### Data
- **Source:** `data/processed/unified.parquet` (full span 2024-04 → 2026-01)
- **Band:** 20m (13,608 hourly epochs after normalization/dropna)
- **Metric:** `value_norm = spots / n_unique_tx` (selection-bias control)
- **Ground truth:** Kp ≥ 5 (from `detector_type == "kp"`)

### Validation Protocol
- **Train:** 13,152 hours (Apr 2024 – Sep 2025)
- **Pseudo-test:** 2,160 hours (Jan – Mar 2025, 3 months) — lies *inside* the train
  window, so prediction origins are indexed by timestamp, not by `len(train)`
- **Frozen test (Jan–Mar 2026):** NOT used in Phase 2 — reserved for Phase 3 confirmation

### Model Configuration
- **TimesFM:** 3.0.2 package, checkpoint `google/timesfm-2.5-200m-pytorch` (200M params)
- **API:** `TimesFM_2p5_200M_torch.from_pretrained(..., torch_compile=False)` →
  `compile(ForecastConfig(max_context=512, max_horizon=24, per_core_batch_size=8))` →
  batched `forecast()` (64 contexts per call, ~98 ms/forecast)
- **Context window:** 512 hours; **Horizons:** 1, 6, 24 hours
- **Device:** CPU (venv torch 2.15.0+cpu — CUDA unavailable in this venv;
  `torch_compile=False` required on Windows since torch.compile needs triton)
- **Runtime:** ~3.5 min inference per experiment (2,160 origins, batched)

### Experiment Design

**Why two experiments?**

TimesFM may (1) learn storm patterns → predict them well (low residual), or (2) fail to
generalize → predict poorly (high residual). **A** tests (1); **B** tests (2) by removing
storms from the context so the model must predict "normal" patterns, then checking whether
residual spikes flag unseen storms.

**Outcome:** A works as a modest forecaster (beats both baselines, big margin only at 1h);
B fails as a detector (97% FP at every tested threshold).

---

## Files

- **Script:** `scripts/timesfm_mvp_20m.py`
- **Results A:** `results/timesfm_mvp_20m_expA.json`
- **Results B:** `results/timesfm_mvp_20m_expB.json`
- **Baselines (persistence + seasonal-naive):** `results/timesfm_mvp_20m_baselines.json`
- **Threshold sweep (post-hoc):** `results/timesfm_mvp_20m_threshold_sweep.json`
- **Per-hour forecasts:** `results/timesfm_mvp_20m_expA_records.csv`,
  `results/timesfm_mvp_20m_expB_records.csv`
- **Visualization:** `results/timesfm_mvp_20m_visualization.png`
- **Phase 3a script:** `scripts/timesfm_forecast_phase3.py`
- **Phase 3a results:** `results/timesfm_phase3_forecast.json` (3 bands)
- **Phase 3a raw records:** `results/timesfm_phase3_{20m,40m,15m}_records.csv` —
  raw records on disk, not committed (2.5MB each, intermediate artifact)
- **Phase 3a visualization:** `results/timesfm_phase3_visualization.png`
- **Phase 4 (frozen) results:** `results/timesfm_phase4_frozen.json`
- **Phase 4 raw records:** `results/timesfm_phase4_frozen_{20m,40m,15m}_records.csv` —
  raw records on disk, not committed (intermediate artifact, same as Phase 3a)
- **Phase 4 visualization:** `results/timesfm_phase4_frozen_visualization.png`
- **Venv:** `.venv-timesfm/` (Python 3.11, timesfm 3.0.2, torch CPU)

---

## Publication Framing (two stories, not one)

**Forecasting — positive at 1h, confirmed on frozen; no margin beyond:**
> *"Foundation models for HF propagation forecasting: TimesFM beats persistence and
> seasonal-naive baselines at 1h for WSPR spot density (skill 0.39–0.47 across
> 20m/40m/15m), confirmed on frozen Jan–Mar 2026."*
- Useful for HamSCI operations (one-hour-ahead baseline prediction).
- Honest scope: **1h confirmed** (frozen 20m skill 0.435, within pre-registered
  [0.34, 0.54]); **6–24h does not hold** on frozen (≈0 for 20m/15m, negative 15m at
  12–24h; only 40m keeps 0.17–0.22).
- Cross-band: difficulty ordering is physical and survives held-out (15m/MUF easiest,
  40m/D-layer hardest by MAE/pooled); skill *magnitude* is not cross-band comparable
  (band-specific, shifting baselines — frozen ordering even flipped while MAE/pooled
  ordering held).
- Does **not** claim storm detection or causal insight.

**Detection — negative, publishable as a bounded negative result:**
> *"Foundation models do not replace Kp-based storm detection at pre-registered or
> swept thresholds: 97% false positives across 2σ–5σ."*
- The value is the boundary: it tells the community where foundation models stop helping.

**This MVP does NOT support** the claim "foundation models are useful for the ionosphere"
in general. It supports the narrow claim: **for 1h forecasting, TimesFM beats naive
baselines across 3 bands on held-out data; at 6–24h it does not.** For CrossCorr 2.0,
TimesFM is a *1h forecasting supplement* to block permutation, never a replacement for
Kp-based detection.

---

## What's Next (branch closed)

**Forecasting — all phases complete:**
1. ✅ Seasonal-naive baseline everywhere (Phase 2 onward).
2. ✅ Extended pseudo-test, all available 2025 data (Jan–Sep, 6,552 h).
3. ✅ All 3 bands: 20m, 40m, 15m (Phase 3a).
4. ✅ **Frozen Jan–Mar 2026 confirmation (Phase 4):** pre-registered 1h threshold met;
   6–24h margins recorded as not generalizing.
5. ✅ Final framing: "beats naive baselines at 1h; no usable 6–24h margin."
6. Quantile / interval forecasts — **deferred**, separate task (1–2 days of tuning +
   calibration), not a blocker for CrossCorr 2.0.

**Detection — closed (confirmed negative):**
- The 2σ→5σ sweep confirms no usable operating point (see table). No further threshold search.
- **Do not** fine-tune TimesFM on storms — leaves the pre-registered frame, turns discovery into fitting.
- Documented as a bounded negative result.

**No further TimesFM experiments planned on this branch** — the exploration question
("does a foundation model help?") is answered: **at 1h, yes, confirmed; beyond 1h, no.**

---

## Honest Assessment

**What we learned:**
- TimesFM zero-shot forecasts 20m spot density **better than both naive baselines** at
  1/6/24h on the 2025 pseudo-test: MAE 8.03/12.83/13.32 vs seasonal-naive 15.13/15.08/15.06.
- **Phase 3a confirms it across 3 bands** (6,552 h each): skill_1h 0.505–0.603. The
  cross-band difficulty ordering (15m easiest → 40m hardest) is **physical** (MUF
  single-mechanism vs D-layer multi-mechanism), confirmed by two independent metrics.
- **Phase 4 confirms the 1h claim on frozen Jan–Mar 2026** (pre-registered threshold met:
  20m skill_1h 0.435 ∈ [0.34, 0.54]) — and **refutes the 6–24h extension**: margins that
  were 0.09–0.23 in Phase 3a collapse to ≈0 (20m/15m), negative for 15m at 12–24h; only
  40m holds (0.17–0.22). Difficulty ordering by MAE/pooled survived unchanged.
- Storm detection from context-excluded residuals **fails operationally**: precision 0.026
  (97% FP) at 2σ; the post-hoc sweep never exceeds 6.7% precision while recall collapses.
  The model has a ~2× lift over base rate — a real but useless storm-correlated signal.
- The pre-registered recall band alone would have labelled this "partial"; **precision was
  the binding constraint the band did not capture.** Recorded as a lesson for
  pre-registering detector metrics (register precision, or F1, not recall alone).

**What we didn't test:**
- Fine-tuning / adaptation to geophysics — zero-shot only (and deliberately so for detection)
- Quantile / interval forecasts — deferred as a separate task
- Context across the Oct–Dec 2025 data gap (frozen contexts unavoidably span it)

**Limitations:**
- Pseudo-test is only 3 months (2,160 hours, 28 storm hours) → recall CI is wide
  (10/28 detected; ±1 storm hour moves recall by ~0.036).
- Pseudo-test lies inside the train window (walk-forward by timestamp, same year) —
  possible temporal leakage; the frozen 2026 window was the real check — Phase 4
  confirmed the 1h margin but not 6–24h (see Phase 4).
- TimesFM pretrained on generic time series, not geophysics; CPU-only inference limited
  us to a single config (context 512h, batch 8).
- Experiment B's "no storms in train" is context exclusion, not retraining — an inherent
  property of the zero-shot design, now explicit.

**Both outcomes are publishable, and they are two different papers/sections:**
- **Forecasting (positive):** "Foundation models forecast HF/WSPR baselines better than
  naive methods on 1–6h horizons."
- **Detection (negative):** "Foundation models don't replace Kp-based storm detection —
  97% false positives across all tested thresholds."

---

## Guardrails Respected

- ✅ `paper/` untouched (manuscript under review)
- ✅ `audit/` untouched
- ✅ Validated `results/*.json` untouched (only added new files)
- ✅ Tags, Zenodo, `main` untouched
- ✅ `G:\stageforge` untouched
- ✅ Branch: `experimental/timesfm-test` (isolated)
- ✅ No synthetic data (real WSPR data only)
- ✅ No math MCP for main statistics (computed in the run scripts, reported verbatim from JSON)
- ✅ Frozen Jan–Mar 2026 window used **only once**, for the pre-registered Phase 4
  confirmation run — never for tuning or exploration

---

**Prepared by:** MiMo (OpenCode agent)
**Reviewed by:** [independent review incorporated 2026-11-11; Phase 3a cross-band review same day; Phase 4 run per user's pre-registered protocol]
**Status:** Forecasting → **branch closed**: 1h confirmed on frozen (skill_1h 20m 0.435, band met), 6–24h margins do not generalize; quantile deferred. Detection → closed as negative result.
