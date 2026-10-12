# DIRTY Worktree Report — 2026-10-12

Read-only inspection. No removals.

| name           | dirty_count | files                                                    | last_commit         |
|----------------|-------------|----------------------------------------------------------|---------------------|
| brave-moon     | 2           | main.log, texput.log                                     | 2026-10-08 15:44    |
| clever-star    | 1           | nul                                                      | 2026-10-08 16:36    |
| crisp-rocket   | 4           | download_space_weather.py, fetch_all.py, 2025-08/, nul   | 2026-10-07 22:39    |
| kind-wolf      | 1           | nul                                                      | 2026-10-08 09:46    |
| playful-lagoon | 2           | audit/FINAL_REPORT.md, audit/PROJECT_BRIEF.md            | 2026-10-06 17:58    |
| proud-wizard   | 4           | AGENTS.md, HANDOFF_PROMPT.md, PROJECT_CONTEXT.md, TODO.md| 2026-10-08 18:41    |
| shiny-mountain | 3           | mutual_info.py, test_E_mutual_info.py, bench/results_v5_after.txt | 2026-10-06 17:58 |
| tidy-pixel     | 1           | cross_mfdfa.py                                           | 2026-10-06 17:58    |

## Categorization

- **Empty-ish (only `nul`):** clever-star, kind-wolf.
  `nul` is a Windows artifact (zero-byte file), safe to ignore or delete.
- **Logs only:** brave-moon (main.log, texput.log from pdflatex).
- **Real source edits:** crisp-rocket, shiny-mountain, tidy-pixel.
  These have MODIFIED tracked files — careful, may contain work.
- **Docs/notes:** playful-lagoon, proud-wizard.
- **Directory artifact:** crisp-rocket/2025-08.

## Recommendation (user decides)

- SAFE_TO_REMOVE (no meaningful content):
    clever-star, kind-wolf, brave-moon
- REVIEW_FIRST:
    crisp-rocket, shiny-mountain, tidy-pixel,
    playful-lagoon, proud-wizard

## Note
Generated read-only by Bonsai 2 27B (OpenCode) on 2026-10-12.
LastWriteTime intentionally skipped (PowerShell-from-bash quoting
too fragile for local model; git commit dates used instead).
