# TimesFM MVP Report — 20m Band

**Date:** 2026-11-11
**Branch:** `experimental/timesfm-test`
**Status:** Phase 2 complete (MVP) — actual metrics filled from run outputs

---

## Executive Summary

Two experiments tested whether Google's TimesFM (foundation model for time series) can either (A) forecast WSPR spot density or (B) detect geomagnetic storms without Kp index in training.

### Key Findings

| Experiment | Question | Result |
|---|---|---|
| **A (baseline)** | How well does TimesFM forecast "normal" patterns? | MAE 8.03 (1h) / 12.83 (6h) / 13.32 (24h); beats persistence at every horizon |
| **B (storm-aware)** | Can TimesFM detect storms WITHOUT Kp in training? | **recall = 0.357**, precision = 0.026, F1 = 0.048 |

### Interpretation Thresholds (pre-registered)

- **Recall ≥ 0.6**: TimesFM catches storms without Kp → useful for anomaly detection
- **Recall 0.3–0.6**: Partial detection → complementary to Kp, not replacement
- **Recall < 0.3**: TimesFM does NOT replace Kp-based detection → limited to forecasting

**Verdict: recall = 0.357 ∈ [0.3, 0.6) → partial detection.** TimesFM *partially* catches
storms from forecast residuals alone (no Kp in its input), but it does **not** replace
Kp-based detection. Precision is very low (0.026): 381 false positives vs 10 true positives
at the pre-registered 2σ threshold.

---

## Experiment A: Baseline (Forecast Quality)

**Train:** Apr 2024 – Sep 2025 (13,152 h, 198 storm hours — all included)
**Pseudo-test:** Jan – Mar 2025 (walk-forward, 2,160 h, 28 storm hours)
**Horizons:** 1h, 6h, 24h ahead
**Context:** 512 h (zero-shot, no fine-tuning)

### Results

| Horizon | MAE | RMSE | N samples | Persistence MAE | Persistence RMSE |
|---|---|---|---|---|---|
| 1h | **8.03** | 10.44 | 2160 | 14.81 | 18.92 |
| 6h | **12.83** | 16.61 | 2160 | 51.82 | 62.98 |
| 24h | **13.32** | 17.41 | 2160 | 15.06 | 19.84 |

*Persistence baseline (`results/timesfm_mvp_20m_persistence_baseline.json`): predict the
last observed value; same origins and same actuals, so numbers are directly comparable.*

**Interpretation:**
- TimesFM beats persistence at **every** horizon: −46% MAE at 1h, −75% at 6h, −12% at 24h.
- Error grows with horizon as expected (8.03 → 12.83 → 13.32) but saturates: the 6h→24h
  increase is small, i.e. the model converges to the seasonal/quiet-time level.
- The 6h persistence MAE of 51.82 (vs 15.06 at 24h) reflects the strong diurnal cycle:
  a 6h-ahead naive forecast is systematically out of phase, while at 24h the phase realigns.
- These are errors on the *normalized* density scale (`spots / n_unique_tx`).

---

## Experiment B: Storm-Aware Detection

**Train:** Apr 2024 – Sep 2025 (**storms EXCLUDED**: 198 storm hours removed → 12,954 h, 0 storms)
**Pseudo-test:** Jan – Mar 2025 (walk-forward, 2,160 h, 28 storm hours)
**Detection:** `|residual| > 2 × rolling_std(168h, center=True)`

> **Design note:** TimesFM is run zero-shot (no fine-tuning on our data), so its only
> "training" input is the context window. "Train without storms" is therefore implemented
> as *excluding storm epochs (Kp ≥ 5) from the context history* (`build_context()` via
> `nonstorm_idx`), not as a fine-tuning split. Kp is never an input to the model in either
> experiment — it only defines the ground-truth labels.

### Results

| Metric | Value |
|---|---|
| Precision | 0.0256 |
| **Recall** | **0.3571** |
| F1 | 0.0477 |
| TP / FP / FN / TN | 10 / 381 / 18 / 1751 |
| Total storms in test (Kp ≥ 5 hours) | 28 |
| Total anomalies detected | 391 |

**Interpretation:**
- **Recall 0.357 → "partial detection" band (0.3–0.6).** The residual-based detector finds
  10 of 28 storm hours with no Kp information at all — better than chance, but far from
  reliable.
- **Precision 0.026 is the weak point:** with a 2σ threshold on a 168h rolling band, 381 of
  391 flagged hours are not storms. The detector fires on many non-storm disturbances
  (quiet-time variability, diurnal misfit) — so as an *alerting* mechanism it is unusable
  without further tuning.
- Per the pre-registered thresholds: **TimesFM partially catches storms but does not
  replace Kp-based detection.**

---

## Comparison with Validated Core (Block Permutation)

The paper's validated results (block permutation, `results/perm_test_18mo_3band_norm_tx.json`):

| Metric | Block Permutation (paper) | TimesFM (MVP) |
|---|---|---|
| **Method** | Statistical hypothesis test | Time series forecasting |
| **Question** | "Is the storm effect real?" | "What happens next N hours?" |
| **20m effect size** | −23.9% drop (p=2e-5) | MAE 8.03 / 12.83 / 13.32 (1/6/24h) |
| **Ground truth** | Kp ≥ 5 (external) | Self-supervised forecast + Kp labels only for scoring |
| **Interpretation** | Storm causes drop | Model predicts normal pattern |

### Key Insight

**Block permutation and TimesFM answer different questions:**

- **Block permutation** proves causality: "Storms cause spot density drop (p < 2e-5)"
- **TimesFM** forecasts: "Based on history, spot density will be X in N hours"

They are **complementary, not competing**. This MVP does not show TimesFM is better or
worse than block permutation — the methods are incommensurable. What the MVP establishes:

- Forecasting the quiet-time baseline works (beats persistence at all horizons).
- Storm *detection* from residuals alone is partial (recall 0.357) and noisy
  (precision 0.026) → Kp remains essential for detection.

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

TimesFM is a foundation model trained on diverse time series. It may:
1. Learn storm patterns during training → predict them well (low residual)
2. Not generalize to geomagnetic storms → predict poorly (high residual)

**Experiment A** tests (1): if MAE is low, model captures storm dynamics.
**Experiment B** tests (2): by removing storms from the context, we force the model to
predict "normal" patterns. If residual spikes during unseen storms → anomaly detection works.

**Outcome:** A works as a forecaster (beats persistence); B is *partial* — residuals carry
some storm signal (recall 0.357) but the 2σ detector is dominated by false positives.

---

## Files

- **Script:** `scripts/timesfm_mvp_20m.py`
- **Results A:** `results/timesfm_mvp_20m_expA.json`
- **Results B:** `results/timesfm_mvp_20m_expB.json`
- **Per-hour forecasts:** `results/timesfm_mvp_20m_expA_records.csv`,
  `results/timesfm_mvp_20m_expB_records.csv`
- **Persistence baseline:** `results/timesfm_mvp_20m_persistence_baseline.json`
- **Visualization:** `results/timesfm_mvp_20m_visualization.png`
- **Venv:** `.venv-timesfm/` (Python 3.11, timesfm 3.0.2, torch CPU)

---

## What's Next (Phase 3)

**Recommendation: proceed to Phase 3 selectively** — the forecasting result (A) is solid
and worth confirming; the detection result (B) is partial and needs threshold work before
any "Kp-free detection" claim.

1. **Full pseudo-test:** Jan – Dec 2025 (12 months, walk-forward)
2. **All 3 bands:** 20m, 40m, 15m
3. **Frozen confirmation:** Jan – Mar 2026 (untouched so far)
4. **Detection tuning (B):** sweep the σ threshold (2σ → 3σ) and band length; report the
   precision–recall trade-off instead of a single operating point. If recall cannot be
   pushed ≥ 0.6 at usable precision, document the negative result.
5. **Comparison with paper:** does the forecast degradation align with the −23.9% drop?

If detection stays below the bar:

1. **Document negative result:** "Foundation models don't replace domain-specific detection"
2. **Focus on forecasting:** use TimesFM for predicting baseline (quiet-time) patterns
3. **CrossCorr 2.0:** TimesFM as feature extractor, not detector

---

## Honest Assessment

**What we learned:**
- TimesFM zero-shot forecasts 20m spot density better than persistence at 1/6/24h
  (MAE 8.03 / 12.83 / 13.32 vs 14.81 / 51.82 / 15.06).
- Storm detection from context-excluded residuals is **partial**: recall 0.357
  (pre-registered band: "complementary to Kp, not replacement"), precision 0.026.
- A 2σ / 168h rolling threshold produces 391 alerts for 28 storm hours — the threshold,
  not the model, may be the binding limitation; this was a single pre-registered operating
  point, not a tuned detector.

**What we didn't test:**
- Frozen held-out (Jan–Mar 2026) — reserved for Phase 3
- Multi-band generalization — Phase 3
- Fine-tuning / adaptation to geophysics — zero-shot only
- Threshold sweep for detection — single point (2σ) only
- Causal interpretation — block permutation already proves this

**Limitations:**
- Pseudo-test is only 3 months (2,160 hours, 28 storm hours) → recall CI is wide
  (10/28 detected; a couple of hours swing moves recall by ~0.07).
- Pseudo-test lies inside the train window (walk-forward by timestamp, but same year) —
  possible temporal leakage; the frozen 2026 window is the real check.
- TimesFM pretrained on generic time series, not geophysics; CPU-only inference limited
  us to a single config (context 512h, batch 8).
- Experiment B's "no storms in train" is context exclusion, not retraining — an honest
  limitation of the zero-shot design.

**Both outcomes are publishable:**
- **Success (forecasting):** "Foundation models forecast quiet-time WSPR density baselines"
- **Partial/failure (detection):** "Foundation models don't replace Kp-based storm
  detection at pre-registered thresholds" — the current evidence points here for
  detection, while forecasting is a positive result.

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
- ✅ Frozen Jan–Mar 2026 window untouched

---

**Prepared by:** MiMo (OpenCode agent)
**Reviewed by:** [Pending]
**Status:** Awaiting Phase 3 decision
