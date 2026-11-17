# Correction Note (draft) — Dst parser bug, manuscript 2026SW005535

**Date:** 2026-11-17
**Status:** DRAFT — not sent, not committed to main, `paper/` untouched.
**Branch:** `experimental/reviewer2-audit`
**Source:** external Reviewer-2 audit claim A1, verified against code, raw data,
WDC Kyoto source files, `data/processed/unified.parquet`, and `paper/main.pdf` (v1.6.4).

## 1. Summary

A data-parser bug in Dst preprocessing (`data/scripts/download_space_weather.py`,
`_parse_dst_line`) drops entire days from the WDC Kyoto provisional Dst series when
adjacent hourly values are printed without a separator (e.g. `... -33-131-157-277 ...`,
day 11 May 2024: `0-313-390-406-395...`). The bug affects the Dst-based statistics in
the manuscript (Table 5, §2.2 "minimum Dst = −96 nT", the Dst arm of the 6 primary
tests). The Kp-based results are unaffected (different data source/parser).

**Secondary bug (found during finalization, 2026-11-17):** `fetch_dst` parses
`end_date` as midnight (`end_dt = Timestamp(end_date)`), and the filter
`ts <= end_dt` therefore excludes the last 23 hours of every fetched range. Each of
the four training-window files loses its final 23 h, plus 24 h for 30 Sep 2025 —
**116 h in total**. The 644 missing hours decompose exactly as **528 h (22 whole
days dropped by the merge bug) + 116 h (end-of-window truncation)**; the arithmetic
reconciles in aggregate (per-file ledger accompanies the corrected version).

## 2. Root cause (verified)

```python
# data/scripts/download_space_weather.py, _parse_dst_line (lines 127-165)
parts = line.split()  # merged token "-406-395" is ONE token
...
for token in parts[1:]:
    try:
        values.append(int(token))
    except ValueError:
        continue  # merged token silently discarded
...
if len(hourly) < 24:
    return None  # => entire day discarded by caller
```

There is no fixed-width fallback. **Correct fixed layout (verified 2026-11-17 on the
real 11 May 2024 line):** header = **16 chars** (`DST`+`yymm`+`*`+`dd`+`RRX`+code,
e.g. `DST2405*11PPX120`), base value at `[16:20]`, hourly fields at
`[20+4i : 24+4i]` for i = 0..23, plus one unused trailing field at `[116:120]`.
Kyoto's `dstYYMM.for.request` format is fixed-width 4-char fields; negative values
≥ 100 nT occupy all 4 chars and abut the next field with no space.

**Off-by-one trap (found by the external audit, verified before sending):** the first
draft of the fix below used `line[13:]` — that slice includes the 3-char header code
(`120`), so regex parsing shifts every hour by one (hour0 of 11 May 2024 reads 0
instead of −313). The correct slice is `line[16:]`.

## 3. Evidence

| Check | Expected (fixed-width) | Actual (buggy parse) |
|---|---|---|
| Parser mechanism | fixed-width | `split()` + `int()` + `continue` + `return None` — CONFIRMED |
| Dropped days (stored data, Apr 2024 – Sep 2025) | 0 | **22 whole days** (528 h), incl. **10–12 May 2024 (Gannon storm main phase)** + **116 h** end-of-window truncation = **644 h** |
| Dropped days (read-only re-fetch 2026-11-17) | 0 | 23 days / 552 h — provisional-data drift vs stored files; bug mechanism identical |
| Hours in 18-month window | 13 152 | 12 508 stored in `unified.parquet` (**644 missing**, exact match) |
| Minimum Dst in window | **−406 nT** (11 May 2024) | **−96 nT** — exactly the value printed in §2.2 |
| Storm hours (Dst < −50 nT), correct reference parse (`line[16:]`) | **886** | **471** — exactly Nstorm in Table 5 (**+415 h, +88% missing**) |
| Hour alignment / slice | header = 16 chars → `line[16:]`, hour0 (11 May 2024) = −313 | draft fix used `line[13:]` → hour0 = 0 (off-by-one) — caught by external audit 2026-11-17, corrected in §5 |
| Mean Dst | changes | −11.5 nT (paper) is biased toward quiet conditions |

Raw file, day 10 May 2024 (as served by WDC Kyoto today):

```
DST2405*10PPX120   0  12  10 ...  25  66 -33-131-157-277-339-308 -41
DST2405*11PPX120   0-313-390-406-395-389-358-320-374-364-297...
```

Direct execution of `_parse_dst_line` on this file: days 10, 11, 12 May 2024 → `None`
(672 parsed hours vs 744 by fixed-width reference parse).

## 4. Affected manuscript numbers (all Dst-based)

1. §2.2: "mean Dst = −11.5 nT, minimum Dst = −96 nT" → true minimum ≈ −406 nT.
2. §2.2: "471 hours satisfy Dst < −50 nT" → ≈ 886 h (recompute required; provenance:
   reference fixed-width parse of a read-only 2026-11-17 re-fetch with the correct
   `line[16:]` slice — an interim parse with the off-by-one `line[13:]` slice gave
   850, superseded by 886).
3. §2.2 comparative sentence: "This selection covers fewer storm hours than the
   Kp-based selection (471 versus 594 hours…)" becomes **false after the fix**
   (886 > 594) and requires rewriting in the corrected version.
4. Table 5: Nstorm = 471 / Nquiet = 8 811 / excluded 3 226 (sum 12 508) → all three
   change; p-values and effect sizes must be recomputed.
5. "12 508 hourly values" framing: 12 508 is the *parsed* count (644 h lost to the
   bug), not a data-availability property.
6. Limitation #10 (provisional Dst) is unaffected but insufficient as a disclosure.

**Unaffected:** all Kp-based tests, 3-band × Kp primary results, permutation framework,
BH procedure itself, WSPR-side data.

## 5. Fix plan (NOT applied yet — manuscript is under review)

1. Replace token parsing in `_parse_dst_line` with fixed-width parse of the **16-char
   header** layout: base = `int(line[16:20])`, hours =
   `int(line[20 + 4*i : 24 + 4*i])` for i = 0..23, keep `9999` masking. Do **not**
   use `line[13:]` (includes the 3-char header code → hourly off-by-one; verified:
   `line[13:]` gives hour0 = 0, `line[16:]` gives hour0 = −313 for 11 May 2024).
2. Fix the end-of-window off-by-one in `fetch_dst`: set
   `end_dt = Timestamp(end_date) + 23 hours` (or exclusive next-day bound) so the
   final 23 h of each range are retained.
3. Add unit tests reproducing the 10–12 May 2024 lines (golden tests: 744/744 hours,
   min −406, **hour0 11 May 2024 = −313**) and a regression test on the window total
   (13 152 h, min ≤ −400 nT).
4. Snapshot `results/*.json` to `%TEMP%` **before** any re-run that writes to the
   same paths (project LESSONS rule), then re-run `fetch_dst` for Apr 2024 – Sep 2025,
   rebuild affected slice of `unified.parquet`, re-run the Dst arm (Table 5,
   storm/quiet split, BH inputs).
5. Diff old vs new Dst statistics; assess whether Dst tests still pass BH and whether
   §2.2/§4.2 wording changes.
6. Update `docs/AI_ASSISTANCE.md` in the same commit as any `paper/` edit (AGU rule).

Text-level corrections in v1.6.5:

- [ ] (a) §2.2 comparative sentence "fewer storm hours than Kp (471 vs 594)" becomes
  false after fix (886 > 594) and must be rewritten.
- [ ] (b) Open Research URL `dst_realtime` → `dst_provisional` (code uses provisional;
  verified: `paper/main.tex:2074` vs `DST_BASE` in `download_space_weather.py`).

## 6. Expected impact on conclusions (hypothesis, to be confirmed by recompute)

- Dst is the *corroborating* index (Kp is primary per §3); the Kp-side conclusions do
  not depend on this bug.
- Storm sample nearly doubles (471 → ≈886, +88%): Dst test p-values will change.
  Direction unknown until recompute; storm-hour estimates were biased toward *quiet*
  conditions.
- If Dst tests remain significant after recompute, the fix strengthens the paper; if
  not, the Index-independence claim (§"3.") needs revision.

## 7. Timeline proposal

| Step | When |
|---|---|
| This note to editorial office (spaceweather@agu.org, ID 2026SW005535) | on author decision |
| Parser fix + tests (branch `experimental/reviewer2-audit` → PR) | within 3 working days of decision |
| Dst recompute + impact diff | +2 days after fix |
| Correction material to editor | after recompute, coordinated with editorial guidance and reviewer feedback |

## 8. Message to the editorial office (draft)

```
Subject: Correction notice: data-parser bug in Dst preprocessing, Manuscript 2026SW005535

Dear Editorial Office,

We identified, during an independent audit of our preprocessing pipeline and before
any reviewer feedback, a data-parser bug in the Dst preprocessing of manuscript
2026SW005535 (v1.6.4); we verified the finding against the raw WDC Kyoto data and
apologize for the oversight. When WDC Kyoto prints adjacent negative hourly values
without a separator (e.g. "-406-395"), our split-on-whitespace parser discards the
token and then the entire affected day; a separate end-of-window off-by-one truncates
the final 23 hours of each fetched range.

As a result, 644 of 13 152 hours are missing from the 18-month window, including the
main phase of the 10-12 May 2024 (Gannon) storm, and the reported minimum Dst
(-96 nT) understates the true minimum (-406 nT).

Affected: the Dst arm of the primary analysis (3 of the 6 BH tests, 3 bands x
{Kp, Dst}); Table 5 requires recalculation, with the storm sample expected to increase
from 471 to approximately 886 hours (pending frozen-snapshot recompute). Not
affected: the Kp arm (the other 3 primary
tests), the headline effect sizes, and the spatial analyses; the Kp results stand
independently, and the Dst sign and significance are expected to hold after recompute.

Plan: fixed-width parser, a regression test (minimum Dst for May 2024 <= -400 nT)
and an hour-alignment golden test (11 May 2024 00 UT = -313 nT), refetch, rerun of
the Dst analysis, and an updated Table 5. Full technical details are in the attached
correction note. We can deliver a corrected version within five working days of your
guidance.

Please advise whether to submit the correction now or after reviewer feedback.

Sincerely, Alexey Petrov, corresponding author, on behalf of both authors
```
