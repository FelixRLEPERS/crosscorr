# FAILURE — TASK 1 (Daily F10.7 check)

**Date:** 2026-10-11
**Status:** Premise failure (not a crash). No script written. No numbers produced.

## What the task required

Fetch daily F10.7 from:
`https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json`
→ restrict to 2024-04-01 .. 2026-03-31 → Spearman vs residuals (§5.5 check).

## What is actually at that URL

Verified by direct fetch (HTTP 200, 512 444 bytes, 3333 records):

```text
time-tag format: "1749-01", "1749-02", ..., "2026-09"   (YYYY-MM = MONTHLY)
records in 2024-04..2026-03: 24   (24 months, NOT ~730 days)
sample: 2024-04 f10.7=161.7 | 2024-05 f10.7=188.37 | 2024-08 f10.7=245.6
```

The data is **monthly**, not daily. The claim in `docs/HANDOFF_2026-10-11.md`
("Это JSON от NOAA SWPC с daily разрешением с 1957 года") is **incorrect**.

## Alternative sources probed (2 fix iterations, both insufficient)

1. `https://services.swpc.noaa.gov/text/daily-solar-indices.txt` — HTTP 200,
   truly daily (DSD.txt), BUT header says "Last 30 Days Daily Solar Data"
   (issued 11 Oct 2026) → covers only ~Sep–Oct 2026, NOT 2024-04..2026-03.
2. `https://services.swpc.noaa.gov/products/solar-and-geophysical-events.json`
   — HTTP 404.

## Why this was stopped instead of "just running it"

- Task title says **Daily** F10.7; the specified source is monthly.
- Running it anyway would produce a silently mislabeled statistic
  (24 monthly points presented as a daily check) → violates
  "never fabricate / correctness > speed".
- The R² gate (§5.5 sentence vs v1.1.0 track) depends on the real
  n: n=24 (monthly) has far less power than n≈550 (daily).

## Options for the user

- **(a)** Run the check with MONTHLY F10.7 from the specified URL,
  honestly labeled "monthly" (n ≈ 18 matched months of residuals,
  training window ends 2025-09). Note: Paper I §5.5 already states
  F10.7 is monthly — this would only quantify the existing limitation.
- **(b)** Authorize a real daily historical source (candidate: NGDC/NOAA
  daily F10.7 archive CSV, or SWPC FTP DSD files) → true daily check,
  n ≈ 550 days. Requires explicit URL approval per rules.
- **(c)** Use the 18 `f107` rows already inside `data/processed/unified.parquet`
  (monthly, no network at all) → weakest but zero external dependency.

## Current repo state

- No `scripts/f107_daily_check.py` created.
- No `results/f107_spearman.txt` created.
- No changes to any file other than this note.
