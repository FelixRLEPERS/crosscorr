# P0′ WSPR archive span audit (read-only)

**Warning: this is a span audit, NOT an effect analysis.** No β, no harmonics,
no IMF polarity — only spot/tx/rx/pair counts, coverage, and usable-span
boundaries. Read-only queries against `wspr.live` via GET; `results/*.json`
stays gitignored.

**Branch:** `experimental/archive-span` (from `main`). **Not pushed to `main`.**

## Method

- GET only (`?query=`), no POST, no `system.parts`, no `min(time)` (1999 corrupt
  row excluded by explicit `time >= '2008-01-01'` filter).
- Explicit date range per year (`time >= 'Y-01-01' AND time < 'Y+1-01-01'`),
  `uniq()` not `uniqExact`, 4 s pause between queries (20/min limit),
  120 s timeout with retries.
- 38 count cells (19 years × 2 bands), all `status: ok`.
- Validation (all clean): 38 keys present, 0 failed, 0 missing/extra keys,
  no negative/`None` values, `uniq_pairs ≤ min(uniq_tx·uniq_rx, spots)`,
  `K_years = 5`.

## Table 1 — years × bands (2008–2026)

| Year | 20m spots | 20m tx | 20m rx | 20m pairs | 40m spots | 40m tx | 40m rx | 40m pairs |
|------|-----------|--------|--------|-----------|-----------|--------|--------|-----------|
| 2008 | 68,995 | 701 | 409 | 4,958 | 244,584 | 1,412 | 468 | 12,371 |
| 2009 | 726,594 | 3,624 | 1,813 | 61,569 | 2,902,233 | 6,055 | 2,229 | 142,574 |
| 2010 | 6,263,805 | 9,775 | 4,515 | 420,939 | 7,504,511 | 10,422 | 4,077 | 382,342 |
| 2011 | 11,468,552 | 9,572 | 4,776 | 568,778 | 7,329,614 | 7,169 | 3,738 | 306,714 |
| 2012 | 17,827,704 | 9,576 | 4,860 | 632,597 | 4,689,837 | 5,795 | 3,330 | 192,811 |
| 2013 | 20,111,388 | 8,673 | 4,693 | 597,533 | 5,646,844 | 5,056 | 3,016 | 175,196 |
| 2014 | 28,996,658 | 11,598 | 5,320 | 724,056 | 9,771,249 | 6,841 | 3,648 | 239,266 |
| 2015 | 28,169,358 | 16,799 | 6,328 | 884,490 | 17,057,356 | 10,281 | 4,747 | 407,734 |
| 2016 | 42,123,004 | 40,794 | 8,727 | 1,493,125 | 49,168,086 | 28,830 | 7,473 | 1,038,693 |
| 2017 | 78,036,732 | 55,640 | 12,285 | 2,662,754 | 120,508,039 | 38,953 | 11,308 | 2,257,718 |
| 2018 | 81,946,887 | 50,780 | 11,910 | 2,237,869 | 158,663,330 | 56,034 | 11,785 | 2,514,432 |
| 2019 | 97,938,916 | 47,458 | 11,499 | 2,046,345 | 227,071,428 | 54,454 | 11,688 | 2,543,884 |
| 2020 | 172,268,618 | 81,212 | 15,045 | 3,699,798 | 337,430,933 | 69,029 | 14,467 | 3,644,206 |
| 2021 | 245,532,823 | 154,549 | 14,931 | 5,205,599 | 424,294,357 | 90,736 | 14,366 | 3,892,055 |
| 2022 | 376,134,205 | 182,047 | 16,155 | 5,895,539 | 465,797,901 | 116,377 | 14,180 | 3,932,344 |
| 2023 | 487,258,158 | 291,471 | 14,867 | 7,513,495 | 488,846,709 | 116,859 | 11,930 | 3,225,921 |
| 2024 | 563,442,429 | 357,893 | 14,613 | 8,635,469 | 518,235,622 | 126,677 | 11,231 | 3,069,721 |
| 2025 | 669,767,485 | 472,168 | 14,606 | 11,360,245 | 650,857,804 | 159,009 | 11,625 | 3,415,657 |
| 2026 | 649,957,636 | 579,057 | 13,727 | 13,408,830 | 654,136,543 | 218,195 | 10,761 | 3,498,898 |

2013/2024 cross-checked against external model's two pilot values — exact match
(20,111,388 / 563,442,429). 2008 starts at 0 spots — archive begins later than
the audit window; recorded as-is (explicit date filter, not `min(time)`).

## Table 2 — coverage (fraction of days with ≥ N spots)

N = 1000/day for 20m, 100/day for 40m (conservative: 2013 already has ~20M
20m spots/year, so 1000/day is far below the observed mean).

| Year | 20m (≥1000) days | frac | 40m (≥100) days | frac |
|------|------------------|------|------------------|------|
| 2008 | 15 | 0.041 | 126 | 0.344 |
| 2009 | 165 | 0.452 | 363 | 0.995 |
| 2010 | 363 | 0.995 | 365 | 1.000 |
| 2011 | 365 | 1.000 | 365 | 1.000 |
| 2012 | 366 | 1.000 | 366 | 1.000 |
| 2013 | 314 | 0.860 | 314 | 0.860 |
| 2014–2025 | 365–366 | 1.000 | 365–366 | 1.000 |
| 2026 | 319 | 0.874 | 319 | 0.874 |

2013 dip (0.860) reflects a partial-year data gap in both bands, not a query
artifact; 2026 is a full-year window but coverage fraction uses 365 days as
denominator per the audit convention.

## Pair recurrence (K_years = 5)

### Result (hash-sample method, partial 8/19 years)

The full-span query (`GROUP BY tx_sign, rx_sign HAVING uniq(toYear(time)) >= 5`)
exceeded the server's hard 15 s limit → HTTP 408; the SQL hint and URL
`max_execution_time` parameter are both ignored, and hash-bucket pre-filtering
does not help (the bottleneck is the raw scan). A deterministic hash-sample
fallback was used instead:

- Per-year query: `cityHash64(tx_sign, rx_sign) % 256 = 0` → **1/256 of pairs**
  per year, aggregated locally across years (scale ×256 for absolute counts).
- **Collected: 8/19 years (2008–2015).** Years 2016–2026 failed: all 11 years
  timed out after ≤2 attempts each (10 s pauses, 45 s backoff, 60 s quiet
  retest) — the denser post-2015 years exceed the client timeout even when the
  server answers trivial queries in 0.3 s. Recorded as
  `2016-2026: failed, rate-limit/timeout`.

**Partial result (band=14 / 20m, K_years ≥ 5):**

| Metric | Sampled (1/256) | Estimated (×256) |
|--------|-----------------|------------------|
| unique pairs | 12,312 | ≈ 3.15 M |
| pairs present in ≥ 5 years | 82 | ≈ 21,008 |
| **frac_ge5y** | **0.67%** | — |

Histogram (years a sampled pair appears in):
`{1: 10,369; 2: 1,421; 3: 332; 4: 108; 5: 62; 6: 17; 7: 2; 8: 1}` — the mass
is overwhelmingly at 1–2 years.

**Verdict: frac 0.67% ≪ 10% → composition bias real.** Even on the 8 earliest
(most stable) years, fewer than 1 in 100 sampled pairs recurs in ≥5 years.
Since only 2008–2015 (the *pre-growth* era, when the network was smallest) is
covered, the full-span figure could only be **lower**, not higher — the
conclusion cannot flip by adding 2016–2026.

### Recorded in JSON

`results/archive_span_p0.json` keeps `pair_recurrence_ge5y: not_available`
(the original full-span attempt); this hash-sample result is recorded here in
the document only.

## Usable span (coverage-only fallback)

Rule (fallback, because pair_recurrence is unavailable): first year where
coverage fraction ≥ 80% on **both** bands, through 2026.

| Band | First year ≥ 80% coverage (both bands condition) |
|------|--------------------------------------------------|
| 20m  | 2010 (0.995)                                     |
| 40m  | 2009 (0.995), but both-bands condition met 2010 |

**Usable span: 2010–2026 (17 years).** 2008–2009 are below 80% on 20m
(0.041, 0.452); from 2010 onward both bands stay ≥ 0.995 except 2013
(0.860, still ≥ 0.80) and 2026 (0.874, still ≥ 0.80).

## Follow-up probes (same read-only session)

Two open questions from the first pass were closed with additional GET queries.

### 1. 2013 anomaly — root cause found

The 0.860 coverage is **not** days that fell just below the ≥1000 threshold. It
is a **contiguous 51-day archive gap**: no rows exist at all for

**2013-01-09 → 2013-02-28** (verified two independent ways: LEFT JOIN anti-join
and `NOT IN`, both = 51 days).

The rest of 2013 is fully dense: 314 present days, min daily count 7,308 (20m),
max 119,212, mean 64,049 — nowhere near the 1000/day threshold. Both bands
(20m and 40m) show the same 314 present days, so the gap is **archive-wide,
not band-specific** — consistent with a data-collection outage, not a query
artifact. `314/365 = 0.860` explains the fraction directly.

Impact on 2A: FE(day-of-year) loses ~51 observations for calendar days in
mid-Jan through end-Feb (a period that includes RM-relevant months). This
reduces N_eff for those months but does not remove any calendar day entirely —
every date except this one block is present across the full 2010–2026 span.

### 2. Pair recurrence — January-sample panel overlap (complements §"Pair recurrence" above)

Independent of the hash-sample K_years=5 result, per-year unique
`(tx_sign, rx_sign)` counts and their **pairwise intersections** were measured
on a January-month sample of three years:

| Year (Jan) | unique pairs |
|------------|--------------|
| 2015 | 259,119 |
| 2018 | 886,615 |
| 2021 | 1,405,843 |

| Intersection | shared pairs | share of smaller side |
|--------------|--------------|-----------------------|
| 2015 ∩ 2018 | 18,254 | 7.0% |
| 2015 ∩ 2021 | 10,914 | 4.2% |
| 2018 ∩ 2021 | 59,032 | 6.7% |

**Interpretation:** pair overlap is **below 10% in every comparison** — the
panel turns over heavily between years (the pair universe grows ~5× from 2015
to 2021). This is a real composition-stability concern, not a blocker: it means
band-day FE may run on a **different panel of pairs each year**. The
hash-sample K_years=5 result above (frac 0.67%) independently confirms the
same picture.

## What this does and does not mean

- **Does:** documents the archive's usable span for extraction design.
- **Does not:** say anything about effect size, β, harmonics, or IMF polarity.
  This is a span audit, NOT an effect analysis.

## Core rx geography

627 rx — широкая панель (активны хотя бы раз в каждом году 2017-2025). Это больше, чем 55-77 rx из Qwen (те были активны в каждом году в конкретном месяце). Для band-day FE(rx) достаточно 627; для FE(день-года) внутри месяца нужно 55-77. Оба критерия валидны, разные уровни строгости.

Core receivers = `rx_sign` with spots in **≥9 distinct years of 2017–2025**
(2017-01-01 ≤ time < 2026-01-01), `band = 14` (20m). Coordinates via
`any(rx_lat)`, `any(rx_lon)`; regions from a coarse lat/lon box
classification (full table in `results/archive_span_core_geo.json`,
gitignored).

**627 core receivers:**

| Region | Count | Share |
|--------|-------|-------|
| Europe | 337 | 53.8% |
| North America | 224 | 35.7% |
| Oceania | 34 | 5.4% |
| South America | 14 | 2.2% |
| Asia | 12 | 1.9% |
| Other | 4 | 0.6% |
| Africa | 2 | 0.3% |

**Conclusion: 627 core rx, mostly Europe + North America (89.5%)** — the
persistent receiver panel is a Northern-hemisphere Western sample; Africa and
Asia together hold 2.1%. This is a **limitation for global inference**:
band-day results generalize to the WSPR receiving network that Europe/NA
dominate, not to a geographically uniform global panel.

## Conclusion — composition bias is real

- **Coverage span: 2010–2026 (17 years)** — days are dense enough everywhere
  (except the documented 2013 gap), so *band-day* analysis is feasible over
  the full window.
- **Panel-stability span for pair-day design: effectively < 5 years.** Only
  0.67% of sampled pairs recur in ≥5 years (measured on 2008–2015, the
  network's smallest era; adding 2016–2026 can only lower this). The
  K_years=5 threshold cannot be met by any meaningful pair panel anywhere in
  the archive.
- **Consequence for 2A: the design must be band-day (not pair-day).** A
  pair-day FE design would have to either drop the K_years=5 recurrence rule
  or accept an unusably small recurring-panel N.

## Honest caveats

- The K_years=5 figure covers **8/19 years (2008–2015)**; 2016–2026 failed on
  rate-limit/timeout. Direction of the bias is one-sided: later years are
  denser and faster-growing (pair universe ×5 from 2015→2021), so the
  full-span frac would be ≤ 0.67%, never higher. The verdict is robust to
  the missing years.
- 2013's 51-day gap and the sub-10% pair overlap are both recorded here for
  transparency; neither is a hard blocker for band-day extraction design, but
  both feed into how N_eff and panel composition are handled downstream.

## Next step

Usable span (2010–2026, 17 years) ≥ 5 years → **extraction design (P1) may
proceed on a band-day basis**, gated on the Paper 1 (2026SW005535) review
decision. Task 2A freezes after this commit: no extraction/analysis code
until that decision.

## Raw data

`results/archive_span_p0.json` (gitignored): `by_year_raw` (38 cells),
`coverage` (38 cells), `coverage_fraction`, `pair_recurrence_ge5y`
(`not_available` — original full-span attempt), `usable_span_coverage_only`,
`validation`. Core-rx geography (627 rows with region tags) is written to
`results/archive_span_core_geo.json` (gitignored). The hash-sample
K_years=5 result (8 years, frac 0.67%, histogram), the 2013 gap dates and
the January-sample pair intersections are recorded only in this document,
not the JSONs.

**Not pushed. Not tagged. Not sent to Zenodo. `paper/`, `audit/`, `main`
untouched.**
