# Response to Reviewers — Gwyn Griffiths (G3ZIL), HamSCI critique

- **Review of:** manuscript v1.1.0, "Scale-dependent WSPR response to
  geomagnetic storms: frequency dependence and network-size effects on
  absolute loss" (Petrov & Petrov)
- **Reviewer:** Gwyn Griffiths, G3ZIL — 22 October 2026
  (`docs/reviews/gary_critique_v1.1.0.pdf`)
- **Response prepared:** 2026-10-30, against manuscript v1.5.0
- **Status:** all 15 comments triaged; 7 open items fixed in commit
  `3f68d55`; 6 were already solved in v1.5.0; 2 stale (contradicted by
  the new data).

Note: the reviewer's line numbers refer to the v1.1.0 PDF (lineno
markers), not the current source; comments were matched by content.

## Point-by-point table

| # | Comment (v1.1.0 lines) | Status in v1.5.0 | Action taken |
|---|---|---|---|
| A1 | Dense statistical jargon; invite a professional statistician familiar with WSPR to review the methods (a name was suggested) | **[ACTUAL — editorial]** | Outside the manuscript text: author will contact the suggested statistician before/at submission |
| A2 | Two key questions: intended readership and route to publication | **[ACTUAL — editorial]** | Route fixed: *Space Weather* (cover letter `docs/submission/Cover_Letter_SpaceWeather.tex` states the readership); audience named in the cover letter |
| L1 | Lines 13–14: Key Points too jargon-heavy — answer in the style of the Plain Language Summary ("Are 20 m and 15 m 'stable' or not?") | **[ACTUAL → FIXED]** | Key Points rewritten in plain language (EN+RU), all numbers preserved; the stability question is now answered directly: "Percentage drops remain the more stable metric" |
| L2 | Line 16: hypothesis and statistics are robust, but the causal (ionospheric) explanations are over-confident | **[PARTIALLY SOLVED]** | Two-mechanism discussion, explicit Limitations, and softened claims already in v1.5.0; the underlying decode-channel gap is now closed (see L4) |
| L3a | Lines 22–23: Kp is a quasi-logarithmic (exponential-like) scale, not linear | **[SOLVED]** | `main.tex` Geomagnetic indices: "$Kp$ is a 3-hourly planetary index on a quasi-logarithmic scale from 0 to 9" |
| L3b | Lines 22–23: conflating bins Kp 5–6 and ≥6 makes a messy comparison | **[ACTUAL → FIXED]** | New Limitations item "Index scaling and path diversity": quasi-log Kp ⇒ bins are not linearly spaced; bin-sparsity caveats kept in Key Points |
| L4a | Lines 26+: no justification for MUF as the cause | **[SOLVED]** | Dedicated MUF-suppression chain in Discussion with `davies1990`; 15 m sits at ~21 MHz ≈ daytime MUF |
| L4b | Lines 26+: **major weakness** — no discussion of why spots fail to decode during storms; Doppler spread (WSPR tones ~1.4 Hz) can kill decoding even at high SNR | **[ACTUAL → FIXED]** | New Discussion paragraph (EN+RU): storm-time Doppler spreading of the ~1.4 Hz WSPR tones as a decode-channel loss distinct from absorption; lead-in of "Physical mechanisms" updated to "two propagation mechanisms … (a third, decode-channel effect …)" |
| L4c | Lines 26+: number of hops matters (cumulative interaction) | **[ACTUAL → FIXED]** | New Limitations item: paths analysed without hop-count stratification; hop stratification listed as future work (path-distance bins already present) |
| L4d | Lines 26+: geomagnetic latitude and time of day of reflections matter | **[PARTIALLY SOLVED]** | Latitude-group analysis (−72.7 / −24.1 / −12.8 %) and UT-window decomposition in v1.5.0; reflection-point (not station) latitude remains future work |
| L4e | Lines 26+: a single number to three significant figures per band bundles all path types — no propagation conclusions without stratification | **[STALE]** | Superseded: stratification by latitude group, path distance (0–2 000 / 5 000–10 000 km), UT window, season and Kp bin now exists |
| L4f | Lines 26+: FT8 (Madrigal database) would give different results — larger tone spacing, higher Doppler tolerance | **[ACTUAL → FIXED]** | Added to the Limitations/future-work item: compare WSPR with FT8, which has higher Doppler tolerance |
| L5 | Line 53: it is F **region**, not layer (F1/F2 layers live inside it) — credit Steve Franke K9AN | **[ACTUAL → FIXED]** | EN: "F-layer" → "F-region" (Introduction + replication section); RU: "от слоя F" → "от области F" |
| L6 | Line 66: unclear how many paths are affected by auroral / polar-cap absorption — no latitude stratification | **[SOLVED]** | §Latitude-group analysis: pooled −72.7 / −24.1 / −12.8 % with PCA references (`reid1974`) |
| L7 | Line 87: "Absolutely true" | **[SOLVED]** | Agreement; no action required |
| L8 | Line 95: "density" is not needed | **[SOLVED]** | Term defined: "'spot density' is shorthand for this hourly aggregated spot count (spots per hour per band)" |
| L9 | Line 97: repeat of the Kp exponential-vs-linear point | **[SOLVED]** | Same as L3a: quasi-logarithmic scale stated in Methods |
| L10 | Line 105: "case not made" — where the paths actually lie | **[PARTIALLY SOLVED]** | Latitude + path-distance stratification added; station-longitude distribution addressed by the new "Station geography" Limitations item |
| L11 | Line 112: `avg(snr)` averages a logarithmic quantity → geometric mean of linear SNR; is that valid for the SNR ranges seen? | **[ACTUAL → FIXED]** | New note in Data section (EN+RU): `avg(snr)` is computed in the dB domain and is therefore a geometric mean of the linear SNR |
| L12 | Line 162: is the diurnal activity an artefact of station geography (Europe–N America, 125°W–30°E)? Station location not mentioned | **[ACTUAL → FIXED]** | New Limitations item "Station geography": the WSPR network is spatially non-uniform (predominantly Europe and North America); diurnal variation may be geography-driven |
| L13 | Line 256: all subsequent "why" deductions are questionable while all latitudes and hops are in one group | **[STALE / PARTIALLY SOLVED]** | Latitude groups, path-distance bins, UT windows and season splits now separate the sample; hop-level caveat recorded in Limitations |

Summary: **6 [SOLVED]** before this round · **2 [STALE]** (contradicted by
the new data) · **3 [PARTIALLY SOLVED]** · **7 [ACTUAL → FIXED]** ·
**2 editorial (A1, A2)** remain with the authors outside the manuscript.

## Reviewer statistics (unchanged, from the Q1 round)

- Estimate families separated: norm-tx headline (169 flare-free epochs,
  −23.9 / −22.5 / −30.1 %) vs. negative-binomial models (198 epochs,
  −33.6 / −27.1 / −39.8 %)
- Effective sample size via τ_int: 213 / 249 / 298
- Permutation p-floor: 2×10⁻⁵ (50 000 iterations)
- Latitude gradient: −72.7 % (auroral) vs. −12.8 % (equatorial), 5.7×
- Data: Zenodo v11, version DOI 10.5281/zenodo.23802881
