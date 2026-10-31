# Legacy FDR artifact — reproducibility note

`perm_test_18mo_3band_fdr.json` (2026-10-08) was generated with
`n_iter=5000` and no add-one correction. It is superseded by:

- `perm_test_18mo_3band.json` — main permutation test, 5000 iter, add-one
- `round3_merge_sensitivity.json` — 50000 iter, add-one, Kp, flare-included
- `perm_test_dst_50k.json` — 50000 iter, add-one, Dst

§3.6 of the manuscript cites 50000 iterations and p ≤ 2×10⁻⁵;
those values are supported by the three files above, not by this artifact.

**Note on reproducibility.** The stored values in this artifact (and
in `round3_merge_sensitivity.json`, committed 2026-10-20) were
computed on an earlier version of `unified.parquet`. The snapshot
was rebuilt on 2026-10-30 (current sha256 `8ee0ac22…`, matching
Zenodo v11). Re-running the analysis on the current snapshot gives
values shifted by ~1e-6 relative — well below the 0.1 pp reporting
precision of the manuscript, but not bit-identical. This is the same
database-mutability effect documented as finding #3 in the paper;
it applies to all committed analysis artifacts, not only this one.
The artifact is kept for provenance only.
