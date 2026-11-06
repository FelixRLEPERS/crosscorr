# CrossCorr 2.0 — Strategic Roadmap

**Created:** 2026-11-06 (after Paper 1 submission to *Space Weather*)
**Status:** planning; no implementation code in this file
**Scope:** future work after v1.6.4 (WSPR + geomagnetic storms)

## 0. Context

Paper 1 (v1.6.4, Zenodo 10.5281/zenodo.23895056) tests the WSPR response
to geomagnetic storms (Kp >= 5) over 18 months across 3 HF bands,
using block permutation, FDR, IAAFT surrogates, and held-out replication.

> Note: For the operational/family roadmap, see docs/roadmap.md. This file (ROADMAP_v2.0.md) is dedicated strictly to scientific plans (Papers 2A, 2B, 3).

CrossCorr 2.0 extends the same statistical engine to:

- **Paper 2A (Russell-McPherron effect):** Does solar geometry
  (declination, dipole tilt) explain seasonal variation in the WSPR
  storm response? *Space Weather* / *JGR: Space Physics*.
- **Paper 2B (Tidal triggering):** Do solid Earth tides (Moon + Sun)
  modulate seismicity? Planets are null-control. *BSSA* / *JGR: Solid Earth*.
- **Paper 3 (φ-layer):** Does any cross-correlation peak show a
  Fibonacci-lattice signature beyond what station geometry predicts?
  (High-risk, methodologically strict; only if 2A/2B succeed.)

**Core principle:** We do not search for correlations. We test physical
hypotheses with pre-registered nulls. A null result is a valid result.

## 1. Phase Overview

### Paper 2A — Russell-McPherron effect in WSPR data (2-3 months)
- Add solar_declination + dipole_tilt to the residual model (Eq. 1).
- Check whether the seasonal peak in WSPR response survives the control.
- Same engine: block permutation, FDR, held-out replication.
- Expected null: RM effect is ~30% of semiannual variation in Kp; WSPR
  response may or may not show it.

### Paper 2B — Tidal triggering of earthquakes (4-6 months)
- Data: USGS/IRIS earthquakes M>=4.5, >=18 months.
- Aggregate seismicity to daily bins (counts, energy).
- Compute tidal stress at each fault via quaternions (ECI -> ENU).
- Moon + Sun = signal; Venus/Jupiter = null-control (physical tidal
  acceleration is ~1e-6 and ~1e-7 of lunar; any signal would be spurious).
- Pre-registration required (docs/paper-2b-preregistration.md).
- Expected: positive for Moon/Sun, null for planets.

### Paper 3 — φ-layer (exploratory, only if 2A/2B succeed)
- Test whether cross-correlation peak positions on the sphere show
  Fibonacci-lattice structure beyond station-geometry null.
- Spherical Fibonacci lattice as null-geometry (F1 in catalog).
- This is the riskiest direction; do not start without 2A/2B success.

## 2. Spatial Models Catalog (Module 0)

To separate signals (WSPR -> Sun-Earth -> Seismology -> φ-layer),
the spatial structure of data must be explicitly modeled. Catalog
below is sorted by relevance to the pipeline.

### A. Ionospheric models (Paper 2A)
- **A1. TEC / foF2 / IRI:** IGS TEC maps, JPL/COSMIC, IRI-2020 (PyIRI).
  Integration: covariate "TEC along path" + "TEC gradient" in residual.
  Note: PyIRI = climatology (smooth), IGS TEC = observations (weather).
  Use PyIRI as baseline, IGS TEC as deviation covariate (see Note 2).
- **A2. Ray tracing / HF propagation:** Jones-Stephenson, IRI+ray tracing.
  Integration: nuisance covariate to separate path geometry from signal.
- **A3. Magnetospheric model:** Tsyganenko T01/T04, magnetopause, cusp,
  auroral oval (Python: geopack, aacgmv2).
  Integration: station weight by L-shell / MLT.

### B. Seismological / crustal models (Paper 2B)
- **B1. 3D velocity model:** PREM / AK135 / LLNL-G3D (nuisance covariate).
- **B2. Tectonic provinces & faults:** PB2002, GEM faults, WSM.
  Integration: categorical covariate for tidal stress at specific faults.
- **B3. Heat flow & gravity:** IHFC, EIGEN-6C4 (deep heterogeneity control).
- **B4. Sediment & Vs30:** CRUST1.0, USGS Vs30 (site response; baseline).

### C. Spatial-statistical models (shared layer)
- **C1. Variograms & kriging:** empirical variogram, Matérn/spherical,
  ordinary/universal kriging. Integration: baseline tool for K(Δ).
- **C2. Gaussian processes (GP) with anisotropic kernel:**
  K(x_i, x_j) = σ² M_ν(|x_i - x_j|_A). Integration: replace kernel
  regression; Bayesian model selection.
- **C3. Slepian functions / spherical harmonics:** localized bases.
  Integration: filter ephemeris response by scale.
- **C4. Spatial point process (ETAS / Hawkes):** background intensity
  model for earthquakes. Integration: **critical** for Paper 2B —
  declustering before tidal analysis (see Note 1).
- **C5. Non-stationary spatial models (SPDE-INLA):** extension.

### D. Network / graph models
- **D1. Spatial station graph:** centrality, community detection.
- **D2. Visibility graph / recurrence networks:** nonlinear coupling (low priority).

### E. Spectral-decomposed models
- **E1. EOF / PCA:** dominant modes φ_k(x), temporal coefficients a_k(t).
  Integration: correlate modes with ephemerides (instead of pairwise).
- **E2. 2D/3D wavelets (curvelets):** anisotropic coupling.
- **E3. Spherical wavelet / needlet:** localized spectral filtering (Paper 3).

### F. Fractal / φ-specific models (Paper 3)
- **F1. Spherical Fibonacci lattice:** ideal φ-lattice as null-geometry.
  Integration: discriminator in Module 0 (M_φ); aligned with Paper 3.
- **F2. Multifractal spatial fields:** α(x), f(α) for coherence fields.
- **F3. Cut-and-project / quasicrystal:** strict test for φ-signature (M5).

### G. ML spatial models (optional, only with pre-registration)
- **G1. GNN:** stations as nodes, coherence as edges.
- **G2. Spatial transformer / convolutional set models.**

## 3. Inclusion Rules (anti-p-hacking)

Models are included in analysis ONLY if:
- (a) data exists;
- (b) pre-registration exists;
- (c) null model exists;
- **(d) model is included in the hierarchy BEFORE results are seen.**

Without (d), criteria (a)-(c) can be satisfied post-hoc, and the rule
stops protecting against p-hacking.

**Hierarchy (do NOT include all at once — multiple comparisons and
power loss):**
- **Baseline set (mandatory):** B4, C1, C2, F1.
- **Contextual set:** A1-A3 (Paper 2A); B2, C4 (Paper 2B); E1, F3 (Paper 3).
- **Extensions (after first results):** B1, B3, C3, C5, D1, E2, F2, G.

**Forbidden:**
- Mixing ionospheric and crustal models in one conclusion without
  variance decomposition.
- ML models without pre-registration and interpretable baselines.
- Touching main, tags, or Zenodo until a new submission round begins.

## 4. Pre-registration Notes (for docs/paper-2a-preregistration.md
   and docs/paper-2b-preregistration.md)

### Note 1 (C4, ETAS): declustering changes the null hypothesis
C4 is not just "remove aftershocks". After declustering, background
intensity is no longer Poisson. In Paper 2B pre-registration, fix:
- which declusterer (ETAS with specific parameters, Reasenberg-Jones,
  Gardner-Knopoff);
- what counts as "background" (M threshold, window, regional aggregation).
Otherwise the tidal result depends on declusterer choice — a hidden
degree of freedom that reviewers will expose.

### Note 2 (A1): PyIRI vs IGS TEC — two different products, not "or"
PyIRI = climatological model (smooth, no space weather).
IGS TEC = observations (with weather and noise).
Correct scheme for Paper 2A:
- PyIRI -> baseline level (climatology);
- IGS TEC -> deviation covariate (observed variation).
Fix this distinction in pre-registration. Mixing levels into one
covariate produces false gradients.

### Note 3 (inclusion rule): add "stop-cock" (d)
See section 3 above: model must be included in hierarchy BEFORE
results are seen. Without (d), (a)-(c) can be met retroactively.

## 5. Technical Stack

- **Ephemerides:** astropy.coordinates (NASA/ESA standard).
- **Rotations:** scipy.spatial.transform.Rotation (quaternions, ECI -> ENU).
- **Geodesy:** pymap3d (clean API for local ENU/NED).
- **Statistics:** crosscorr_lib.analysis (block permutation, max-stat,
  FDR, IAAFT).
- **Branches:** paper-2a/russell-mcpherron, paper-2b/tidal-triggering,
  experimental/astro-seismology (umbrella for scaffolding).

## 6. Educational Component (Makar 13, Egor 11)

- **Paper 2A (Sun):** great topic for school conference. Visible physics
  (axial tilt, seasons), beautiful visualizations (polar projections of
  subsolar point, seasonal Kp plots).
- **Paper 2B (Seismology):** harder, but framed as "we tested the myth
  of planetary influence and found it null" — teaches the scientific method.

## 7. Anti-patterns (do NOT do)

- Do NOT start Paper 2B before Paper 2A submission.
- Do NOT include all spatial models in one analysis.
- Do NOT publish WSPR + seismology + φ-layer in a single paper.
- Do NOT skip pre-registration for Paper 2B.
- Do NOT touch main, tags, or Zenodo until a new submission round begins.
- Do NOT claim "confirmed" without out-of-sample replication.

## 8. Next Steps (after Paper 1 submission)

1. Update this file with actual pre-registration dates and thresholds.
2. Create branch paper-2a/russell-mcpherron from experimental/astro-seismology.
3. Add solar_declination + dipole_tilt to residual model (Paper 2A).
4. Run 18-month WSPR data through the updated model.
5. Draft Paper 2A (target: 2-3 months after Paper 1 submission).
6. Only after Paper 2A accepted: start Paper 2B pre-registration.
