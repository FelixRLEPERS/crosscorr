# Preprint Outline

**Target journal:** Space Weather (AGU)
**Template:** AGU LaTeX (agu2019.cls)
**Target length:** 10–12 pages

---

## Title

**Scale-dependent WSPR response to geomagnetic storms:**
frequency dependence and baseline-invariant absolute loss

*Alternative:* WSPR as a distributed ionospheric sensor:
scale-dependent HF propagation response to geomagnetic storms

---

## Abstract (≤250 words)

[From `docs/first_result.md` Abstract, trimmed to 250 words]

---

## 1. Introduction (~1 page)

- HF radio propagation and the ionosphere
- Geomagnetic storms: Joule heating, particle precipitation, foF2 depletion
- D-layer absorption and MUF reduction as known mechanisms
- WSPR as a distributed ionospheric sensor (Frissell 2016, LaBelle 2023)
- Gap in literature: no quantitative, multi-band, scale-dependent characterisation
  of WSPR response to geomagnetic storms
- Our contributions:
  1. 18-month, 3-band WSPR analysis with Kp and Dst
  2. Scale-dependent effect (non-linear with Kp)
  3. Independent replication on held-out data
  4. Baseline-invariant absolute loss
  5. Day/night asymmetry consistent with intermittent particle precipitation

---

## 2. Data (~1 page)

### 2.1 WSPR
- wspr.live ClickHouse mirror
- 3 HF bands: 20m (14 MHz), 40m (7 MHz), 15m (21 MHz)
- Hourly aggregation: `toStartOfHour(time), count()`
- **Training:** April 2024 – September 2025 (548 days, 39 456 rows)
  - 198 storm hours (Kp ≥ 5) after merge
  - Quiet baseline: 73 718 (20m), 67 105 (40m), 13 386 (15m) spots/h
- **Held-out:** January–March 2026 (90 days, ~5 850 rows)
  - 31–39 storm hours after merge
  - Quiet baseline: 86 355 (20m), 92 694 (40m), 16 784 (15m) spots/h
  - +17–38% more stations relative to training

### 2.2 Geomagnetic indices
- Kp (GFZ Potsdam): 3-hourly planetary index, resampled to 1h forward-fill
- Dst (WDC Kyoto): 1-hourly provisional data
- F10.7 (NOAA SWPC): monthly means — too coarse for hourly analysis

---

## 3. Methods (~2 pages)

### 3.1 Residuals
- Baseline: `mean(spots | month, hour_of_day)`
- Residual: `spots − baseline`
- Removes diurnal (8× range) and seasonal confounders

### 3.2 Block permutation test
- Storm mask: Kp ≥ 5; Quiet mask: Kp < 3
- Non-overlapping 24h blocks, 10 000 iterations
- Accounts for ρ₁ ≈ 0.83 autocorrelation
- Effective sample size: ESS ≈ 82 (from N ≈ 482 for 20m)

### 3.3 Binned analysis
- Kp bins: <3, 3–4, 4–5, 5–6, 6–7, ≥7
- Monotonic gradient test: does drop scale with Kp?

### 3.4 Multiple testing correction
- Benjamini-Hochberg FDR on 6 primary tests (3 bands × {Kp, Dst})
- All six p_raw = 0.0 → all p_FDR = 0.0

### 3.5 Robustness checks
- n_active_tx control (spots per transmitter)
- Day-of-week confounder (r = −0.0087 with Kp)
- Kp vs Dst agreement (independent indices)
- Seasonal consistency (4 seasons)
- Dedup verification (740 duplicate rows removed; identical results)

---

## 4. Results (~3 pages)

### 4.1 Primary result
| Band | Drop (Kp ≥ 5) | p-value |
|------|--------------|---------|
| 20m  | −27.7%       | <0.0001 |
| 40m  | −27.2%       | <0.0001 |
| 15m  | −38.7%       | <0.0001 |

- Dst confirms: Δ(Dst<−50 vs Dst>−20) = −22 081 / −15 038 / −5 143, p<0.0001

### 4.2 Scale-dependent effect (novel)
- Monotonic gradient across Kp bins (Tables from §7.6)
- Kp 5–6 → −18 to −29%, Kp 6–7 → −34 to −51%, Kp ≥ 7 → −52 to −59%
- Non-linear: consistent with super-linear ionospheric response
- **Figure:** Binned Kp vs drop% (3 panels: 20m, 40m, 15m)

### 4.3 Frequency dependence
- 15m (−38.7%) > 20m (−27.7%) ≈ 40m (−27.2%)
- Two competing mechanisms: MUF drop (15m) + D-layer absorption (20m/40m)
- **Figure:** Frequency vs drop% (3 bars with error bars)

### 4.4 Day/night asymmetry
- 40m night > day in 9/10 training months with sufficient data
- Auroral absorption (Hargreaves 1969) + PCA (Reid 1974)
- Intermittent: requires specific storm morphology
- **Figure:** Day vs night drop per month (40m)

### 4.5 Independent replication
- Held-out Jan–Mar 2026: all bands p ≤ 0.014
- Scale-dependence replicates: Kp 6–7 drops within 0.85–0.95×
- Frequency dependence and day/night: not replicated in 3-month window
  (insufficient N_storm, intermittent mechanism)
- **Figure:** Training vs held-out side-by-side binned comparison

### 4.6 Baseline-invariant absolute loss
- 40m loses ~18 300 spots/h in both periods (1.00×)
- Despite 38% network growth, absolute propagation loss unchanged
- Strongest evidence for physical reality of the effect
- **Figure:** Absolute drop comparison (training vs held-out)

---

## 5. Discussion (~2 pages)

### 5.1 Physical mechanisms
- MUF reduction: storm heating → recombination → foF2 ↓ → MUF below 21 MHz
- D-layer absorption: energetic particle precipitation → D-region ionisation → non-deviative absorption
- Why 20m ≈ 40m in total: daytime MUF penalty on 20m compensates nighttime D-layer penalty on 40m

### 5.2 Scale-dependence interpretation
- Non-linear ionospheric response to geomagnetic forcing
- Joule heating ∝ Σ_P × E² → super-linear
- foF2 depletion saturates at strong storms (Kp ≥ 6)
- Practical: Kp ≥ 6 needed for substantial HF disruption, Kp ≥ 7 for severe

### 5.3 Baseline-invariance significance
- WSPR network grows over time → percentage-based metrics are unstable
- Absolute spot loss is a physically meaningful metric
- Implication for operational forecasting: real-time monitoring possible
  even with growing/fluctuating station counts

### 5.4 Comparison with literature
- Frissell et al. (2016): qualitative WSPR-ionosphere coupling →
  we add quantitative, multi-band, scale-dependent characterisation
- Themens et al. (2021): modelled foF2/MUF response →
  we provide observational confirmation via citizen-science data
- Hargreaves (1969), Reid (1974): auroral absorption and PCA →
  we invoke these mechanisms to explain observed day/night asymmetry
- Limitations of previous WSPR studies: single-band, short-period, no
  scale-dependence, no independent replication

### 5.5 Future work
- Expand to 4+ bands (30m, 17m, 12m, 10m) to better constrain MUF threshold
- Full 11-year solar cycle analysis (2024–2035)
- Per-path geographic analysis (polar vs equatorial paths)
- SNR-based analysis (not just spot count)
- Flare-separated analysis (solar flares vs storms)
- Machine learning: real-time Kp → WSPR drop prediction

---

## 6. Conclusions (~0.5 page)

1. Geomagnetic storms (Kp ≥ 5) cause statistically significant WSPR spot
   reduction on 20m, 40m, and 15m (p < 0.0001).
2. The effect is **scale-dependent**: −18% to −59% depending on Kp.
3. Scale-dependence replicates on independent held-out data.
4. Baseline-invariant absolute loss confirms physical reality.
5. Frequency dependence suggests two competing mechanisms:
   MUF drop (15m) and D-layer absorption (20m/40m).
6. Day/night asymmetry (40m night > day) is consistent with
   intermittent auroral/PCA absorption.
7. WSPR is a viable distributed ionospheric sensor for monitoring
   geomagnetic storm effects on HF propagation.

---

## 7. Limitations (~0.5 page)

[List from `docs/first_result.md` §6 — 8 items, plus:]
- Replication limited to 3 months (6 months planned, wspr.live server
  throughput limits not yet resolved)
- Block permutation assumes stationarity within blocks (24h); storms
  can last >24h
- No per-path SNR analysis (only aggregate spot count)
- Correlation, not causation — physical mechanism inferred from
  frequency and time-of-day patterns
- F10.7 monthly data too coarse; daily F10.7 not available from
  NOAA SWPC API for the full period

---

## 8. Acknowledgments

- wspr.live operators for public ClickHouse mirror
- GFZ Potsdam for real-time Kp API
- WDC Kyoto for Dst data
- NOAA SWPC for F10.7
- AI assistance disclosure: DeepSeek V4 Pro (code and statistics),
  Bonsai 27B (hypothesis), Qwen 3.8 27B (audit). All scientific
  decisions by human authors.
- Mama Petrov for communications support

---

## 9. References

[To be filled from Google Scholar / SAO/NASA ADS]

Core references to confirm:
1. Frissell et al. (2016) — WSPR as distributed ionospheric sensor
2. LaBelle et al. (2023) — WSPR network statistics
3. Themens et al. (2021) — ionospheric storm response modelling
4. Hargreaves (1969) — auroral absorption
5. Reid (1974) — Polar Cap Absorption (PCA)
6. Røyrvik and Davis (1982) — auroral absorption morphology
7. [TODO: Rodger et al.] — HF absorption during storms
8. [TODO: Kavanagh et al.] — D-region modelling
9. [TODO: solar flare / SID literature]
10. [TODO: sporadic-E literature]
11. [TODO: F10.7 / solar cycle correlation]

---

## 10. Figures (5 main + supplementary)

| Fig | Title | Panels | Data source |
|-----|-------|--------|-------------|
| 1 | Kp time series with WSPR response overlay | 1 panel | `eda_18mo_3band.py` |
| 2 | Scale-dependent effect: binned Kp vs drop% | 3 panels (20m/40m/15m) | §7.6 tables |
| 3 | Frequency dependence: drop% vs band | 1 panel (3 bars, training + held-out) | §7.5 |
| 4 | Day/night asymmetry: per-month 40m | 1 panel | §7.5.1 |
| 5 | Baseline-invariance: absolute spot loss, training vs held-out | 1 panel | §11.2 |

**Supplementary:**
- S1: Full binned analysis (all Kp bins, all bands)
- S2: Seasonal decomposition
- S3: Dst-based replication
- S4: Per-transmitter normalisation check

---

## 11. Data availability statement

All data are publicly available:
- WSPR: wspr.live (ClickHouse mirror, no authentication)
- Kp: GFZ Potsdam (JSON API)
- Dst: WDC Kyoto (HTTP)
- Unified parquet + analysis scripts: Zenodo (DOI pending)
- Full code: GitHub (https://github.com/FelixRLEPERS/crosscorr)

---

## 12. Author contributions

- **Alexey Petrov** — concept, methodology, literature review, code review
- **Makar Petrov** (13 y.o.) — data pipeline, EDA, statistical analysis
- AI tools used as programming/audit assistants; all scientific
  decisions made by human authors