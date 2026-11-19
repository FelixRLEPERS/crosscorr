# Response to Editor — Manuscript 2026SW005535 (Reject & Resubmit)

**Journal:** Space Weather (AGU)
**Editor:** Jiaojiao Zhang
**Date:** 2026-11-19
**Branch:** `fix/dst-parser` (files prepared, not yet committed — per instruction)

---

Dear Dr. Zhang,

Thank you for your assessment of our manuscript and for inviting a resubmission.

## Editor's decision comment (quoted)

> "I have received 0 reviews … key points and abstract are clearly too long …
> I am rejecting it now so as not to put a time constraint on your revision …
> Once the revisions are complete, I would like to encourage you to resubmit
> the paper."

*(Ellipses mark elided text; the full decision letter is available in the
submission portal under manuscript 2026SW005535.)*

The decision was a **format-only desk rejection with zero reviews**: the
scientific content has not yet been evaluated. Below we address each
requirement from your letter and the submission checklist.

## Response to the formatting requirements

### 1. Key Points shortened to ≤140 characters each

Both manuscripts now contain exactly three Key Points. Lengths were verified
programmatically with Python `len()` on the rendered text of each item
(English and Russian counted separately, spaces included):

| Item | English (chars) | Russian (chars) |
|---|---|---|
| KP1 — storm suppression per active transmitter | 102 | 108 |
| KP2 — equatorial-to-auroral drop gradient | 113 | 103 |
| KP3 — normalisation removes the low-latitude 15 m drop | 128 | 133 |
| **Limit** | **≤ 140** | **≤ 140** |

### 2. Abstract shortened to compliance

The Abstract in both manuscripts is now **207 words (English)** and
**210 words (Russian)** — within the 200–220 word target. The shortened
abstract retains the core methodology (18-month wspr.live dataset, flare
exclusion via GOES XRS, normalisation by active transmitters,
block-permutation and negative-binomial inference) and all headline numbers
(−23.9 % / −22.5 % / −30.1 %, gradient −72.7 % vs −12.8 %, held-out 19–23 %,
negative-binomial model on all 198 storm epochs). The previously ≈600-word
abstracts were cut to roughly one third of their length.

### 3. Marked copy produced (letter item 2)

A copy of the manuscript with all changes marked (strikethrough for deleted
text, underline for added text) was generated with `latexdiff` against the
version submitted on 6 November 2026 (tag `v1.6.4`, commit `f04dc4f`):

- `paper/main_marked.pdf` (English; 210 additions / 243 deletions marked)
- `paper/main_ru_marked.pdf` (Russian; 246 additions / 308 deletions marked)

Both marked PDFs build without errors or undefined references.

### 4. Conflict of Interest statement added (letter item 4)

A dedicated section was added to both Article Files, after Acknowledgments:

- English: **Conflict of Interest Statement** — "The authors declare no
  conflicts of interest."
- Russian: **Заявление о конфликте интересов** — "Авторы заявляют об
  отсутствии конфликта интересов."

### 5. Data and code cited in References (submission checklist)

Both the dataset and the analysis code are now cited **in text** in the
Open Research section (`\citep`) **and** carry full records in References:

- Petrov, A., and M. Petrov (2026a), *CrossCorr: scale-dependent WSPR
  response to geomagnetic storms — analysis code*,
  https://doi.org/10.5281/zenodo.23895056 (version DOI, v1.6.4, MIT).
- Petrov, A., and M. Petrov (2026b), *CrossCorr unified dataset: WSPR spots,
  Kp and Dst indices (April 2024 – September 2025)*,
  https://doi.org/10.5281/zenodo.23802881 (version DOI of the data record).

The concept DOI 10.5281/zenodo.23285958 remains in place for the code
repository.

## Disclosures

### Dst parser correction (carried over from the previous report)

The Dst parser bug reported previously has been fixed in this version: the
parser now reads the WDC Kyoto provisional Dst file with the correct
fixed-width format, restoring 644 missing hourly values (hourly record count
12 508 → 13 152; storm hours 471 → 886; minimum −96 → −406 nT). The
corrected statistics and the corresponding manuscript text (Table 5 and the
Dst-based results) are included in the resubmitted PDFs. All Dst-dependent
figures were rerun after the fix.

### Key Point 2 direction correction

During final proofreading we found that the direction of the latitude
gradient in KP2 had been inverted in a working draft ("grows from auroral to
equatorial"). It now correctly reads "grows from equatorial to auroral
latitudes: −72.7 % near the auroral zone vs. −12.8 % near the equator"
(Russian: "растёт от экватора к авроральным широтам"), consistent with the
numbers quoted. The marked copies show this change explicitly.

### Flare-included clarification in the Abstract

To remove an ambiguity between the flare-free headline permutation result
(169 storm epochs) and the negative-binomial model, the Abstract now states
explicitly that the NB estimates are confirmed "on all 198 storm epochs"
("на всех 198 штормовых эпохах"), matching the Table 4 caption in the body.

## What was NOT changed

- No mathematical results, statistical conclusions, or the structure of the
  manuscript were modified beyond the items listed above.
- The revision is limited to: Key Points and Abstract compliance, the already
  reported Dst parser correction, the COI statement, data/code citations, and
  the marked copies.

We confirm that the revised manuscript conforms to the journal's formatting
requirements and look forward to peer review.

Sincerely,
The Authors
