# Finding: Held-out numbers not reproducible from live wspr.live

**Date:** 2026-10-13
**Investigator:** session 7 (paper audit response, Finding 1.3)
**Status:** OPEN — needs decision (not a code bug)

## Summary

Held-out absolute loss for 40m reported in paper (tab:baseline
= -18304 spots/h; tab:heldout N=648, N_storm=38) is NOT
reproducible from live wspr.live as of 2026-10-13. Both HTTP and
HTTPS endpoints return identical fresh counts today:
N_total=720, N_storm=47, N_quiet=439, point=26287.

Training numbers (parquet) reproduce exactly: 18285.

## Evidence

| Run | N_total | N_storm | point | vs hardcode 18304 |
|---|---|---|---|---|
| Paper (historical) | 648 | 38 | 18304 | 0 |
| heldout_abs_loss_40m.py (HTTPS, today) | 720 | 47 | 26287 | +7983 |
| diag_heldout_orig_logic.py (HTTP, today) | 720 | 47 | 26287 | +7983 |

## Diagnosis

HTTP vs HTTPS — ruled out (byte-identical).
Logic — reproduced identically (3-state labels, value metric).
Kp — unchanged (parquet).
Root cause — **data revision on wspr.rx**: live database has
gained additional hourly slots since original run.

## Implication

- If live revision is authoritative: training 18285 vs held-out
  26287 → ratio 1.44, NOT 1.00. Central claim of "baseline-invariant
  absolute loss" at risk.
- If historical snapshot is authoritative: numbers in paper are
  correct for the archival version; live reproduction will
  diverge. Needs explicit caveat in §5.5 and Code Availability.
- Either way: **training is frozen in parquet (good), held-out
  is not (bad, by design of replication_2026.py).**

## Options (do NOT decide in this session)

A. Add §5.5 limitation: "held-out numbers from wspr.live snapshot
   of [DATE]; live database has since been revised. Archival
   reproduction available at v1.1.0 tag." — minimal, keeps claim.
B. Recompute all held-out numbers from current live DB and update
   paper. Risk: 26287 breaks invariance claim. Requires broader
   discussion.
C. Contact wspr.live maintainers re: data availability snapshots
   / archival access. Long-term.

## Recommendation

Pause. Discuss with family (Alexey + Makar). Decision affects
not just Finding 1.3 but potentially the whole §4.6 claim.

Do NOT commit paper changes until this is resolved.
