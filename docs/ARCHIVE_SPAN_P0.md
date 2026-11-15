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

- Full-span query (`GROUP BY tx_sign, rx_sign HAVING uniq(toYear(time)) >= 5`)
  exceeded the 60 s limit → HTTP 408.
- Split-by-year fallback (per-year `DISTINCT tx_sign, rx_sign`, union in Python)
  also timed out on every year (120 s) → **not available**.
- Recorded as `pair_recurrence: not_available` in `results/archive_span_p0.json`
  per the fallback rule. Usable span below therefore uses **coverage only**.

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

## What this does and does not mean

- **Does:** documents the archive's usable span for extraction design.
- **Does not:** say anything about effect size, β, harmonics, or IMF polarity.
  This is a span audit, NOT an effect analysis.

## Next step

Usable span (2010–2026, 17 years) ≥ 5 years → proceed to extraction design.
Had it been < 5 years, task 2A would close here.

## Raw data

`results/archive_span_p0.json` (gitignored): `by_year_raw` (38 cells),
`coverage` (38 cells), `coverage_fraction`, `pair_recurrence_ge5y`
(`not_available` + reason), `usable_span_coverage_only`, `validation`.

**Not pushed. Not tagged. Not sent to Zenodo. `paper/`, `audit/`, `main`
untouched.**
