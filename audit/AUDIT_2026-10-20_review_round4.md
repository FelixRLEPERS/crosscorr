# Audit 2026-10-20 — round 4 (paper + presentation)

## Source

External scientific audit of `paper/main.pdf` and
`docs/presentations/hamsci_2026-11-05/slides.pdf`, provided 2026-10-20.
Focus: primary claims, statistical inference, physical interpretation,
reproducibility, internal consistency, and slide caveats.

## Verdict

The audit found no numerical disagreement between the paper and the
slides. The primary effect, held-out direction, and absolute-loss
numbers are reported consistently. It identified one factual wording
error in the held-out ordering and several places where the
presentation compresses caveats.

## Accepted and fixed

1. **Held-out adjusted ordering.** The text said the adjusted held-out
   ordering was "closer to" training `15 > 20 > 40 m`. The actual
   adjusted held-out order is `15 > 40 > 20 m`: 15 m is restored as the
   most affected band, but the 20/40 m order remains reversed. The text
   now states this explicitly.
2. **Table 3 UTC-hour levels.** Added a caption note that the eight
   levels are the 3-hourly Kp sectors (00, 03, ..., 21 UTC).
3. **Trend tests and multiple testing.** The three Kp-bin trend tests
   are now explicitly secondary/supportive and outside the primary BH
   family.
4. **Absolute-loss comparison.** Added that the training/held-out CI
   comparison is a point comparison; the intervals overlap, so it is not
   a formal test of equality.
5. **Limitations.** Added an explicit frequency-ordering limitation:
   raw held-out order inverts, adjusted 15 m is again largest, but
   20/40 m remain reversed with overlapping CIs.
6. **Figure 2 caption.** Added that error bars are iid bootstrap
   intervals and episode-clustered intervals are wider (Appendix
   Table 13).
7. **Abstract.** Marked the UT-window pattern as exploratory.
8. **Slides.**
   - Dst check now says same sign/significance, magnitudes not
     comparable.
   - Scale-dependence bullet adds "not all pairwise contrasts
     resolved".
   - UT slide renamed "Exploratory result 2 — UT-sector asymmetry";
     inequality notation replaced with "largest drop first"; mechanism
     wording softened to "consistent with".
   - Held-out slide now states that the frequency ordering does not
     replicate (15 m is the smallest raw drop).
   - Conclusions say "primary effect replicates" and describe the
     dual-mechanism attribution as hypothesis-generating.
   - Slide 6 title changed to "scaling unresolved".
   - Speaker notes and Q&A synchronized with all of the above.

## Considered but not changed

- **Episode-clustered CI as the main Table 6/Figure 2 interval.** The
  paper already discloses iid intervals and reports cluster intervals in
  Appendix Table 13. Making cluster CI primary would require rebuilding
  the main table/figure and is a separate methodological decision.
- **Adding a BH-adjusted p column to Table 7.** The caption already
  reports that 5 of 9 comparisons survive and lists the four exceptions.
- **Path-resolved, local-time, riometer, ionosonde, or TEC analyses.**
  These remain future work and are already listed in Limitations.
- **"September 22, 2025" artifact.** Not present in the manuscript;
  the abstract says "September 2025".

## Verification

- Paper: 34 pages, 0 errors, 0 undefined references/citations, 3
  pre-existing overfull hboxes below 7 pt.
- Slides: 10 pages, 0 errors, 0 undefined references, 0 overfull boxes.
- No headline numbers were changed.
