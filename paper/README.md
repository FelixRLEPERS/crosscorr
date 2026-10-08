# CrossCorr Preprint -- Compilation Instructions

## Requirements

- LaTeX distribution: **MiKTeX** (Windows) or **TeX Live** (Linux/macOS)
- Required packages (MiKTeX will auto-install on first compile):
  - `amsmath`, `amssymb` -- AMS math
  - `graphicx` -- images
  - `siunitx` -- SI units
  - `natbib` -- author-year citations
  - `booktabs` -- professional tables
  - `hyperref` -- hyperlinks

## AGU Journal Class

The template uses `agujournal2019.cls` (AGU journals, including Space Weather).

### Option A: MiKTeX (Windows)
```
miktex-console  →  Packages  →  search "agu"  →  install "aguplus"
```
Or let MiKTeX auto-install on first `pdflatex` run (click "Install" in popup).

### Option B: Manual download
1. Go to https://www.agu.org/publish-with-agu/publish#1
2. Download the AGU LaTeX template
3. Copy `agujournal2019.cls` to `paper/`

### Option C: Overleaf (online, zero setup)
1. Go to https://www.overleaf.com
2. Use the AGU journal template: "Space Weather"
3. Upload `main.tex`, `references.bib`, and `figures/`

## Compile Locally

```bash
cd paper

# First pass (creates .aux)
pdflatex main.tex

# Process bibliography
bibtex main

# Second and third passes (resolve cross-references)
pdflatex main.tex
pdflatex main.tex
```

Or in one line:
```bash
cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## Files

```
paper/
├── main.tex          # 12-page LaTeX preprint
├── references.bib    # 30+ BibTeX references
├── figures/
│   ├── fig1_kp_timeseries.png        # Kp time series + WSPR overlay
│   ├── fig2_scale_dependence.png     # Binned Kp vs drop (scale)
│   ├── fig3_frequency_dependence.png # Band comparison (frequency)
│   ├── fig4_day_night_asymmetry.png  # Day/night decomposition
│   └── fig5_baseline_invariance.png  # Absolute loss invariance
└── README.md
```

## Notes

- Some references in `references.bib` are marked `[TODO: confirm in Google Scholar]`
  and need verification before final submission.
- The `fig4_day_night_asymmetry.png` and `fig5_baseline_invariance.png` currently use
  approximate placeholder plots; dedicated figures should be generated from
  `scripts/eda_18mo_3band.py`.
- The AGU class option `draft` is set; remove for final version (shows figures,
  enables hyperlinks).