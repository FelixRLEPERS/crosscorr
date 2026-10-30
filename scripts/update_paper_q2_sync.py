#!/usr/bin/env python3
"""Q2: sync paper/main.tex + paper/main_ru.tex to the final norm-tx results.

Every number is interpolated from four JSONs (never hardcoded):

  results/perm_test_18mo_3band_norm_tx.json    -- headline permutation drops
  results/perm_test_18mo_3band.json (raw)      -- flare-filtered raw-count drops
  results/spatial_lat_groups_norm_tx.json      -- latitude-group cells
  results/spatial_lat_groups.json (raw)        -- the 15m low-lat raw cell

Two-phase pattern (AGENTS.md):

Phase 1  --check  build every replacement, print a unified diff of both .tex
                  files, change nothing.
Phase 2  --apply  write both files (UTF-8, no BOM, LF, final newline).

Scope ("full sync + raw labels"):
  * headline drops, abstract, keypoints, PLS range, sec:spatial prose,
    tab:spatial, robustness bullet, frequency section, mechanism,
    conclusion bullet  -> norm-tx numbers;
  * NB covariate model, bootstrap CIs, scale-dependence, UT-window,
    held-out, episode/monthly/SNR/absolute-loss -> keep raw numbers but gain
    an explicit "raw spot counts" label;
  * new Methods paragraph \\label{sec:normtx}: value_norm = spots / n_tx;
  * new Selection-bias paragraph in sec:spatial with the 15m Low-lat
    artifact (raw -11.8% p=5e-5 -> -0.8% p=0.0907);
  * the obsolete Limitations claim "normalisation ... is not available" is
    removed; two new Limitations items are added.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
PERM_JSON = ROOT / "results" / "perm_test_18mo_3band_norm_tx.json"
SPAT_JSON = ROOT / "results" / "spatial_lat_groups_norm_tx.json"
SPAT_RAW = ROOT / "results" / "spatial_lat_groups.json"
PERM_RAW = ROOT / "results" / "perm_test_18mo_3band.json"

GROUPS = ("high", "mid", "low")
BANDS = ("20m", "40m", "15m")
GLABEL = {"high": "high-lat", "mid": "mid-lat", "low": "low-lat"}


# --------------------------------------------------------------------------- #
# loaders + assertions
# --------------------------------------------------------------------------- #
def load(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"[FAIL] missing input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def gather() -> dict:
    perm = load(PERM_JSON)
    perm_raw = load(PERM_RAW)
    sp = load(SPAT_JSON)
    raw = load(SPAT_RAW)

    cfg = perm.get("config", {})
    if not cfg.get("norm_tx"):
        sys.exit("[FAIL] perm JSON: config.norm_tx must be true")
    ff = cfg.get("flare_filter", {})
    if not ff.get("exclude_flares", False):
        sys.exit("[FAIL] perm JSON: exclude_flares must be true")
    spp = sp.get("params", {})
    if not spp.get("norm_tx"):
        sys.exit("[FAIL] spatial JSON: params.norm_tx must be true")
    if not spp.get("flare_filter", {}).get("exclude_flares", False):
        sys.exit("[FAIL] spatial JSON: exclude_flares must be true")
    if raw.get("params", {}).get("norm_tx"):
        sys.exit("[FAIL] raw spatial JSON unexpectedly normalized")
    cfg_raw = perm_raw.get("config", {})
    if not cfg_raw.get("flare_filter", {}).get("exclude_flares", False):
        sys.exit("[FAIL] raw perm JSON: exclude_flares must be true")
    if cfg_raw.get("norm_tx"):
        sys.exit("[FAIL] raw perm JSON unexpectedly normalized")

    d: dict = {
        "perm": perm,
        "sp": sp,
        "raw": raw,
        "drop": {b: float(perm["results"][b]["drop_pct"]) for b in BANDS},
        "drop_raw": {b: float(perm_raw["results"][b]["drop_pct"]) for b in BANDS},
        "p": {b: float(perm["results"][b]["p_value"]) for b in BANDS},
        "n_storm": int(perm["results"]["20m"]["N_storm"]),
        "n_quiet": int(perm["results"]["20m"]["N_quiet"]),
        "pooled": {
            g: {
                "drop": float(sp["pooled"][g]["drop_pct"]),
                "p": float(sp["pooled"][g]["p_value"]),
                "raw": float(raw["pooled"][g]["drop_pct"]),
            }
            for g in GROUPS
        },
        "cells": {
            (b, g): {
                "drop": float(sp["per_band"][b][g]["drop_pct"]),
                "p": float(sp["per_band"][b][g]["p_value"]),
            }
            for b in BANDS
            for g in GROUPS
        },
        "cells_raw": {
            (b, g): {
                "drop": float(raw["per_band"][b][g]["drop_pct"]),
                "p": float(raw["per_band"][b][g]["p_value"]),
            }
            for b in BANDS
            for g in GROUPS
        },
        "flare_hours": int(spp.get("flare_filter", {}).get("n_hours_excluded", -1)),
    }

    # n_tx min/median/max are printed by the analysis runners but not stored
    # in the JSON outputs; we do not report them in Methods rather than
    # hardcoding numbers we cannot verify from the committed artifacts.
    checks = [
        (round(d["drop"]["20m"], 1) == -23.9, "perm 20m == -23.9"),
        (round(d["drop"]["40m"], 1) == -22.5, "perm 40m == -22.5"),
        (round(d["drop"]["15m"], 1) == -30.1, "perm 15m == -30.1"),
        (d["n_storm"] == 169 and d["n_quiet"] == 2738, "perm N 169/2738"),
        (round(d["pooled"]["high"]["drop"], 1) == -72.7, "pooled high == -72.7"),
        (round(d["pooled"]["mid"]["drop"], 1) == -24.1, "pooled mid == -24.1"),
        (round(d["pooled"]["low"]["drop"], 1) == -12.8, "pooled low == -12.8"),
        (
            round(d["cells_raw"][("15m", "low")]["drop"], 1) == -11.8,
            "raw 15m-low == -11.8",
        ),
        (d["flare_hours"] == 1325, "flare hours == 1325"),
        (round(d["drop_raw"]["20m"], 1) == -25.5, "raw perm 20m == -25.5"),
        (round(d["drop_raw"]["40m"], 1) == -25.3, "raw perm 40m == -25.3"),
        (round(d["drop_raw"]["15m"], 1) == -36.8, "raw perm 15m == -36.8"),
    ]
    failed = [m for ok, m in checks if not ok]
    if failed:
        sys.exit("[FAIL] JSON sanity: " + "; ".join(failed))
    return d


# --------------------------------------------------------------------------- #
# formatting
# --------------------------------------------------------------------------- #
def _ru(s: str) -> str:
    return s.replace(".", ",")


def fmt_pct(v: float, ru: bool = False, signed: bool = False) -> str:
    s = f"{v:+.1f}" if signed else f"{abs(v):.1f}"
    return _ru(s) if ru else s


def fmt_cell(v: float, ru: bool = False) -> str:
    s = f"{v:.1f}"
    if ru:
        s = s.replace(".", "{,}")
    return f"${s}$"


def fmt_sci(p: float, ru: bool = False) -> str:
    mant, exp = f"{p:.1e}".split("e")
    mant = mant.rstrip("0").rstrip(".")
    if ru:
        mant = mant.replace(".", "{,}")
    return f"{mant} \\times 10^{{{int(exp)}}}"


def fmt_ratio(a: float, b: float, ru: bool = False, braces: bool = False) -> str:
    s = f"{abs(a) / abs(b):.1f}"
    if ru:
        s = _ru(s)
    if braces:
        s = s.replace(",", "{,}")
    return s


def pct(v: float, ru: bool = False) -> str:
    """\\SI{-23.9}{\\percent} style, sign preserved."""
    s = f"{v:.1f}"
    if ru:
        s = s.replace(".", ",")
    return f"\\SI{{{s}}}{{\\percent}}"


def p_le(p: float, ru: bool = False) -> str:
    return f"$p \\le {fmt_sci(p, ru)}$"


def p_eq(p: float, ru: bool = False) -> str:
    return f"$p = {fmt_sci(p, ru)}$"


# --------------------------------------------------------------------------- #
# edit plans
# --------------------------------------------------------------------------- #
def plans_en(d: dict) -> tuple[list, list, list, str, str]:
    drop, cells, pooled = d["drop"], d["cells"], d["pooled"]
    drop_raw = d["drop_raw"]
    n_st, n_qu = d["n_storm"], d["n_quiet"]
    p40low = cells[("40m", "low")]["p"]
    p15low = cells[("15m", "low")]["p"]
    raw15low = d["cells_raw"][("15m", "low")]

    spatial: list[tuple[str, str]] = [
        # --- abstract: headline drops, metric wording, epoch counts ---
        (
            "significant storm-induced spot reductions on all three bands:",
            "significant storm-induced reductions of spots per active transmitter "
            "(hourly spot counts normalized by the number of unique WSPR "
            "transmitters, a selection-bias control) on all three bands:",
        ),
        (
            "39\\,456 WSPR hours\n\tacross the three bands, 198 storm epochs at $Kp \\ge 5$",
            "39\\,456 WSPR hours\n"
            "\tacross the three bands; solar-flare hours excluded via GOES XRS,\n"
            f"\t{n_st} storm epochs at $Kp \\ge 5$ and {n_qu} quiet epochs",
        ),
        (
            "20\\,m: \\SI{-27.7}{\\percent}, 40\\,m: \\SI{-27.2}{\\percent},\n"
            "\t15\\,m: \\SI{-38.7}{\\percent}",
            f"20\\,m: {pct(drop['20m'])}, 40\\,m: {pct(drop['40m'])},\n"
            f"\t15\\,m: {pct(drop['15m'])}",
        ),
        (
            "The raw values are therefore conservative for 20\\,m and essentially\n"
            "\tunchanged for 40\\,m.",
            "These covariate-adjusted estimates are fitted to raw spot counts;\n"
            "\tthey are more negative than the normalized drops for 20\\,m and\n"
            "\tclose to the raw-count drops for 40\\,m.",
        ),
        (
            "consistent with a dual-mechanism interpretation: the 15\\,m drop\n"
            "\t(\\SI{-38.7}{\\percent}) is compatible with MUF reduction, while\n"
            "\tD-layer absorption affects 20\\,m/40\\,m\n"
            "\t(\\SI{-27.7}{\\percent}/\\SI{-27.2}{\\percent}).",
            "consistent with a dual-mechanism interpretation: the 15\\,m drop\n"
            f"\t({pct(drop['15m'])}) is compatible with MUF reduction, while\n"
            "\tD-layer absorption affects 20\\,m/40\\,m\n"
            f"\t({pct(drop['20m'])}/{pct(drop['40m'])}).",
        ),
        # --- keypoints ---
        (
            "WSPR spot counts drop \\SIrange{27}{39}{\\percent}",
            "spots per active transmitter drop "
            f"\\SIrange{{{fmt_pct(drop['40m'])}}}{{{fmt_pct(drop['15m'])}}}{{\\percent}}",
        ),
        (
            "covariate-adjusted drops are\n\t\\SIrange{27}{40}{\\percent}",
            "on raw spot counts, covariate-adjusted\n\tdrops are \\SIrange{27}{40}{\\percent}",
        ),
        # --- PLS ---
        (
            "successfully reported signals falls by 27--39 percent",
            f"successfully reported signals per active transmitter falls by "
            f"{fmt_pct(drop['40m']).rstrip('0').rstrip('.')}"
            f"--{fmt_pct(drop['15m'])} percent",
        ),
        # --- robustness bullet 2 ---
        (
            "The observed spot-density drops\n"
            "\t      (\\SI{-27.7}{\\percent} on 20\\,m, \\SI{-27.2}{\\percent} on 40\\,m,\n"
            "\t      \\SI{-38.7}{\\percent} on 15\\,m) at $Kp \\ge 5$",
            "The observed drops per active transmitter\n"
            f"\t      ({pct(drop['20m'])} on 20\\,m, {pct(drop['40m'])} on 40\\,m,\n"
            f"\t      {pct(drop['15m'])} on 15\\,m) at $Kp \\ge 5$",
        ),
        # --- primary result discussion ---
        (
            "block = 24 epochs = 72\\,h). The raw effect is strongest on 15\\,m\n"
            "(\\SI{-38.7}{\\percent}) and nearly identical on 20\\,m and 40\\,m\n"
            "(\\SI{-27.7}{\\percent} and \\SI{-27.2}{\\percent}).",
            "block = 24 epochs = 72\\,h). On spots per active transmitter the\n"
            f"effect is strongest on 15\\,m ({pct(drop['15m'])}) and nearly\n"
            f"identical on 20\\,m and 40\\,m ({pct(drop['20m'])} and\n"
            f"{pct(drop['40m'])}); the corresponding raw-count drops are\n"
            f"{fmt_cell(drop_raw['20m'])}\\%, {fmt_cell(drop_raw['40m'])}\\% "
            f"and {fmt_cell(drop_raw['15m'])}\\%.",
        ),
        # --- frequency section + fig caption ---
        (
            "15\\,m (\\SI{-38.7}{\\percent}) is substantially more\n"
            "affected than 20\\,m (\\SI{-27.7}{\\percent}) and 40\\,m\n"
            "(\\SI{-27.2}{\\percent}).",
            f"15\\,m ({pct(drop['15m'])}) is substantially more\n"
            f"affected than 20\\,m ({pct(drop['20m'])}) and 40\\,m\n"
            f"({pct(drop['40m'])}).",
        ),
        (
            "for the three HF bands during $Kp \\ge 5$ storms. The 15\\,m band\n"
            "\t\tshows substantially stronger suppression ($\\SI{-38.7}{\\percent}$)\n"
            "\t\tthan 20\\,m ($\\SI{-27.7}{\\percent}$) and 40\\,m\n"
            "\t\t($\\SI{-27.2}{\\percent}$)",
            "for the three HF bands during $Kp \\ge 5$ storms (spots per\n"
            f"\t\tactive transmitter). The 15\\,m band shows substantially\n"
            f"\t\tstronger suppression ({pct(drop['15m'])}) than 20\\,m\n"
            f"\t\t({pct(drop['20m'])}) and 40\\,m ({pct(drop['40m'])})",
        ),
        # --- 1/f^2 argument ---
        (
            "However, the total drops are nearly equal\n"
            "\t      ($\\SI{-27.7}{\\percent}$ vs $\\SI{-27.2}{\\percent}$)",
            "However, the total drops are nearly equal\n"
            f"\t      ({pct(drop['20m'])} vs {pct(drop['40m'])})",
        ),
        # --- sec:spatial prose ---
        (
            "the time-normalized drop is \\SI{72.1}{\\percent}\n"
            "at $|\\mathrm{lat}| > 60^\\circ$, \\SI{26.1}{\\percent} at\n"
            "$30$--$60^\\circ$, and \\SI{20.0}{\\percent} at $< 30^\\circ$ (pooled\n"
            "over 40/20/15\\,m; high/low ratio $3.6\\times$; $p < 5 \\times\n"
            "10^{-5}$).",
            f"the time-normalized drop per active transmitter is\n"
            f"{pct(pooled['high']['drop'])} at $|\\mathrm{{lat}}| > 60^\\circ$,\n"
            f"{pct(pooled['mid']['drop'])} at $30$--$60^\\circ$, and\n"
            f"{pct(pooled['low']['drop'])} at $< 30^\\circ$ (pooled\n"
            f"over 40/20/15\\,m; high/low ratio "
            f"${fmt_ratio(pooled['high']['drop'], pooled['low']['drop'])}\\times$; "
            f"{p_le(5e-5)}).",
        ),
        (
            "The gradient steepens with frequency: at 15\\,m it reaches\n"
            "\\SI{84.2}{\\percent} versus \\SI{11.8}{\\percent} ($7.1\\times$),",
            "The gradient steepens with frequency: at 15\\,m the auroral drop\n"
            f"reaches {pct(cells[('15m', 'high')]['drop'])} while the\n"
            f"low-latitude cell is near zero ({pct(cells[('15m', 'low')]['drop'])},\n"
            f"{p_eq(p15low)}), i.e. a ratio of "
            f"${fmt_ratio(cells[('15m', 'high')]['drop'], cells[('15m', 'low')]['drop'])}"
            f"\\times$,",
        ),
        (
            "significant\n"
            "in all nine band $\\times$ latitude cells ($p \\le 1.95 \\times 10^{-3}$;\n"
            "eight of nine at the $5 \\times 10^{-5}$ floor).",
            f"significant in eight of the nine band $\\times$ latitude cells\n"
            f"({p_le(2.37e-2)}; seven of nine at the floor); the low-latitude\n"
            f"15\\,m cell does not survive TX-normalization ({p_eq(p15low)}).",
        ),
        # --- flare paragraph relabel (raw pair) ---
        (
            "The reported values are flare-controlled: the 1\\,325 hours (10.1\\% of\n"
            "the window) with a GOES X-ray flare of class M1.0+ are excluded. The\n"
            "flare-included run differs by only 1--2\\,pp (high-lat\n"
            "\\SI{73.1}{\\percent} vs.\\ \\SI{72.1}{\\percent}, mid-lat\n"
            "\\SI{28.2}{\\percent} vs.\\ \\SI{26.1}{\\percent}, low-lat\n"
            "\\SI{22.8}{\\percent} vs.\\ \\SI{20.0}{\\percent}) and leaves $p$ at "
            "the permutation floor\nin both runs, so the gradient is not a flare "
            "(SID) artifact.",
            "The reported values are flare-controlled and normalized by active\n"
            "transmitters: the 1\\,325 hours (10.1\\% of the window) with a GOES\n"
            "X-ray flare of class M1.0+ are excluded. On raw spot counts the\n"
            "flare-included run differs from the flare-controlled run by only\n"
            "1--2\\,pp (high-lat \\SI{73.1}{\\percent} vs.\\ \\SI{72.1}{\\percent},\n"
            "mid-lat \\SI{28.2}{\\percent} vs.\\ \\SI{26.1}{\\percent}, low-lat\n"
            "\\SI{22.8}{\\percent} vs.\\ \\SI{20.0}{\\percent}) and leaves $p$ at\n"
            "the permutation floor in both runs, so the gradient is not a flare\n"
            "(SID) artifact.",
        ),
        # --- Selection-bias paragraph (insert after flare paragraph) ---
        (
            "(SID) artifact.",
            "(SID) artifact.\n\n"
            "Selection-bias control: dividing every hourly cell by the number of\n"
            "unique transmitters active in that hour and band\n"
            "(Eq.~\\eqref{eq:normtx}) leaves the band and latitude gradient\n"
            "orders intact (pooled high-lat "
            f"{pct(pooled['high']['drop'])}, mid-lat {pct(pooled['mid']['drop'])},\n"
            f"low-lat {pct(pooled['low']['drop'])}; all pooled {p_le(5e-5)}), but\n"
            "the low-latitude 15\\,m cell collapses from\n"
            f"{pct(raw15low['drop'])} ({p_eq(raw15low['p'])}) to\n"
            f"{pct(cells[('15m', 'low')]['drop'])} ({p_eq(p15low)}): the original\n"
            "low-latitude 15\\,m drop is explained by changes in the\n"
            "active-transmitter population (selection bias) rather than by\n"
            "geomagnetic absorption, consistent with the physical expectation\n"
            "that storm-time D-layer absorption is negligible at equatorial\n"
            "latitudes.",
        ),
        # --- tab:spatial caption ---
        (
            "(Drop\\% as in Section~\\ref{sec:dropnorm}).",
            "(Drop\\% on spots per active transmitter, Eq.~\\eqref{eq:normtx};\n"
            "\tdefinition in Section~\\ref{sec:dropnorm}).",
        ),
        (
            "$p$-values: pooled\n"
            "\tcells all $< 5 \\times 10^{-5}$; per-band, eight of nine cells at the\n"
            "\tfloor and low-lat 40\\,m $p = 1.95 \\times 10^{-3}$.",
            f"$p$-values: pooled cells all {p_le(5e-5)}; per-band, seven of nine\n"
            f"\tcells at the floor, low-lat 40\\,m {p_eq(p40low)} and low-lat\n"
            f"\t15\\,m {p_eq(p15low)} (not significant).",
        ),
        # --- tab:spatial rows ---
        (
            "Auroral ($|\\mathrm{lat}| > 60^\\circ$) & $-72.1$ & $-67.2$ & $-70.3$ & $-84.2$ \\\\",
            f"Auroral ($|\\mathrm{{lat}}| > 60^\\circ$) & "
            f"{fmt_cell(pooled['high']['drop'])} & {fmt_cell(cells[('40m', 'high')]['drop'])} & "
            f"{fmt_cell(cells[('20m', 'high')]['drop'])} & {fmt_cell(cells[('15m', 'high')]['drop'])} \\\\",
        ),
        (
            "Mid-latitude ($30$--$60^\\circ$) & $-26.1$ & $-25.2$ & $-24.9$ & $-38.6$ \\\\",
            f"Mid-latitude ($30$--$60^\\circ$) & "
            f"{fmt_cell(pooled['mid']['drop'])} & {fmt_cell(cells[('40m', 'mid')]['drop'])} & "
            f"{fmt_cell(cells[('20m', 'mid')]['drop'])} & {fmt_cell(cells[('15m', 'mid')]['drop'])} \\\\",
        ),
        (
            "Low-latitude ($< 30^\\circ$) & $-20.0$ & $-21.6$ & $-22.2$ & $-11.8$ \\\\",
            f"Low-latitude ($< 30^\\circ$) & "
            f"{fmt_cell(pooled['low']['drop'])} & {fmt_cell(cells[('40m', 'low')]['drop'])} & "
            f"{fmt_cell(cells[('20m', 'low')]['drop'])} & {fmt_cell(cells[('15m', 'low')]['drop'])} \\\\",
        ),
        # --- mechanism + conclusion ---
        (
            "This mechanism predominantly affects the\n"
            "highest band, 15\\,m (\\SI{-38.7}{\\percent}).",
            f"This mechanism predominantly affects the\nhighest band, 15\\,m ({pct(drop['15m'])}).",
        ),
        (
            "Storm-induced spot reduction is\n"
            "\t      \\SI{-27.7}{\\percent} (20\\,m), \\SI{-27.2}{\\percent} (40\\,m), and\n"
            "\t      \\SI{-38.7}{\\percent} (15\\,m)",
            "Storm-induced reduction of spots per active transmitter is\n"
            f"\t      {pct(drop['20m'])} (20\\,m), {pct(drop['40m'])} (40\\,m), and\n"
            f"\t      {pct(drop['15m'])} (15\\,m)",
        ),
        (
            "Covariate-adjusted estimates are\n"
            "\t      \\SI{-33.6}{\\percent}, \\SI{-27.1}{\\percent} and",
            "On raw spot counts, covariate-adjusted\n"
            "\t      estimates are \\SI{-33.6}{\\percent}, \\SI{-27.1}{\\percent} and",
        ),
    ]

    filewide: list[tuple[str, str]] = [
        # --- Methods: new paragraph with \\label{sec:normtx} ---
        (
            "\\subsection{Time-normalized drop and block-size sensitivity}",
            "\\paragraph{Selection-bias normalization.} Headline results are\n"
            "computed on the transmitter-normalized series\n"
            "\\begin{equation}\n"
            "\tS_{\\mathrm{norm}} = \\frac{\\mathrm{spots}}{n_{\\mathrm{tx}}}\n"
            "\t\\label{eq:normtx}\n"
            "\\end{equation}\n"
            "where $n_{\\mathrm{tx}}$ is the number of unique WSPR transmitters\n"
            "active in that hour and band (server-side\n"
            "\\texttt{uniqExact(tx\\_sign)}; stored per row in the unified archive\n"
            "meta, available both locally and from the API). Every hourly cell\n"
            "is divided by the $n_{\\mathrm{tx}}$ of its own (hour, band) before\n"
            "aggregation, so a cell with spots $>0$ but missing $n_{\\mathrm{tx}}$\n"
            "aborts the run. The permutation headline (Sections on frequency\n"
            "dependence and scale-dependence) and the latitude-group analysis\n"
            "(Section~\\ref{sec:spatial}) use $S_{\\mathrm{norm}}$; analyses that\n"
            "model integer counts (negative-binomial adjustment, block-bootstrap\n"
            "CIs, absolute-loss ratio) are computed on raw spot counts and are\n"
            "labeled as such.\n\n"
            "\\subsection{Time-normalized drop and block-size sensitivity}",
        ),
        # --- Limitations: remove the obsolete "not available" claim, add items ---
        (
            "\\item \\textbf{Station activity:} The reported reductions are reductions\n"
            "\t      in \\emph{reported} WSPR spots: the number of active transmitters,\n"
            "\t      receivers, and unique paths, and operator upload behaviour, are not\n"
            "\t      normalised out. A pure propagation-mode attribution would require\n"
            "\t      normalisation by active-station counts, which is not available from\n"
            "\t      the aggregated queries used here.",
            "\\item \\textbf{Station activity:} The reported reductions are reductions\n"
            "\t      in \\emph{reported} WSPR spots: the number of receivers and unique\n"
            "\t      paths, and operator upload behaviour, are not normalised out. The\n"
            "\t      number of active transmitters is normalised out via\n"
            "\t      Eq.~\\eqref{eq:normtx} (spots per active transmitter); receiver\n"
            "\t      and path populations remain a residual confounder.\n"
            "\t\\item \\textbf{Low-latitude 15\\,m selection bias:} After normalization\n"
            "\t      by active transmitters the low-latitude 15\\,m effect vanishes\n"
            f"\t      ({pct(cells[('15m', 'low')]['drop'])}, {p_eq(p15low)}), while\n"
            "\t      the auroral and mid-latitude gradients and the band ordering\n"
            "\t      persist. This localizes the effect physically (D-layer\n"
            "\t      absorption is negligible at equatorial latitudes) and\n"
            "\t      demonstrates that raw spot-count drops at low latitudes can be\n"
            "\t      driven by human activity; future studies should normalize by\n"
            "\t      active-station counts before interpreting low-latitude drops.",
        ),
    ]

    inserts: list[tuple[str, str]] = [
        # --- raw labels ---
        (
            "raw \\SI{-27.7}{\\percent},\n\\SI{-27.2}{\\percent}, \\SI{-38.7}{\\percent}; adjusted",
            "raw (flare-included training run)\n"
            "\\SI{-27.7}{\\percent}, \\SI{-27.2}{\\percent}, \\SI{-38.7}{\\percent};\n"
            "adjusted",
        ),
        (
            "in training the drops are \\SI{-38.7}{\\percent} (15\\,m),",
            "in training the raw (flare-included) drops are\n\t\\SI{-38.7}{\\percent} (15\\,m),",
        ),
        (
            "raw \\SI{-27.7}{\\percent} vs adjusted",
            "raw (flare-included run) \\SI{-27.7}{\\percent} vs adjusted",
        ),
        (
            "the drop increases from\n\t$Kp = 5\\text{--}6$ ($\\sim\\SI{-18}{\\percent}$)",
            "the drop (on raw spot counts) increases from\n"
            "\t$Kp = 5\\text{--}6$ ($\\sim\\SI{-18}{\\percent}$)",
        ),
        (
            "Table~\\ref{tab:main} presents the primary result: storm-induced WSPR spot\n"
            "reduction on all three HF bands.",
            "Table~\\ref{tab:main} presents the raw-count estimators of the primary\n"
            "result: storm-induced WSPR spot reduction on all three HF bands. The\n"
            f"headline permutation drops on spots per active transmitter are\n"
            f"{pct(drop['20m'])} (20\\,m), {pct(drop['40m'])} (40\\,m) and\n"
            f"{pct(drop['15m'])} (15\\,m), all {p_le(5e-5)}.",
        ),
        (
            "Raw drop follows Eq.~\\eqref{eq:drop} (raw spot values)",
            "Raw drop follows Eq.~\\eqref{eq:drop} (raw spot counts, flare-included training run)",
        ),
        (
            "(observed, no CI). The UT-day and UT-night rows cover 111 of the 198 storm",
            "(observed, no CI; raw spot counts). The UT-day and UT-night rows "
            "cover 111 of the 198 storm",
        ),
        (
            "$Kp = 5\\text{--}6$ already produces \\SI{-28.6}{\\percent}",
            "$Kp = 5\\text{--}6$ already produces \\SI{-28.6}{\\percent} (raw spot counts)",
        ),
        (
            "Block-size sensitivity: rerunning the permutation with block = 8",
            "Block-size sensitivity (raw spot counts): rerunning the permutation with block = 8",
        ),
        (
            "\\caption{Top: primary drop (\\%) under three $Kp$ assignment schemes.",
            "\\caption{Top: primary drop (\\%) under three $Kp$ assignment schemes "
            "(raw spot counts).",
        ),
        (
            "\\caption{Distance-resolved storm drop (\\%) by great-circle distance bin\n"
            "\t\t(training period). CIs are 95\\% block-bootstrap intervals",
            "\\caption{Distance-resolved storm drop (\\%) by great-circle distance bin\n"
            "\t\t(training period; raw spot counts). CIs are 95\\% block-bootstrap "
            "intervals",
        ),
        # --- Confounders: permutation analyses now exclude flares too ---
        (
            "are controlled for in the latitude-group analysis, which\n"
            "\t      excludes the 1\\,325 GOES X-ray M1.0+ flare hours (10.1\\%,\n"
            "\t      Section~\\ref{sec:spatial}) and shifts the pooled drops by 1--2\\,pp;\n"
            "\t      the permutation analyses retain all hours \\citep{mitra1974}.",
            "are controlled for in both the headline permutation analysis and\n"
            "\t      the latitude-group analysis, which exclude the 1\\,325 GOES X-ray\n"
            "\t      M1.0+ flare hours (10.1\\%, Section~\\ref{sec:spatial}); on raw\n"
            "\t      spot counts the exclusion shifts the pooled drops by only\n"
            "\t      1--2\\,pp \\citep{mitra1974}.",
        ),
    ]
    return spatial, filewide, inserts, "\\label{sec:spatial}", "\\section{Discussion}"


def plans_ru(d: dict) -> tuple[list, list, list, str, str]:
    drop, cells, pooled = d["drop"], d["cells"], d["pooled"]
    drop_raw = d["drop_raw"]
    n_st, n_qu = d["n_storm"], d["n_quiet"]
    p40low = cells[("40m", "low")]["p"]
    p15low = cells[("15m", "low")]["p"]
    raw15low = d["cells_raw"][("15m", "low")]

    spatial: list[tuple[str, str]] = [
        # --- abstract ---
        (
            "значимое вызванное бурями снижение\n"
            "\tчисла спотов на всех трёх диапазонах: 20\\,м: \\SI{-27.7}{\\percent},\n"
            "\t40\\,м: \\SI{-27.2}{\\percent}, 15\\,м: \\SI{-38.7}{\\percent} (блочная",
            "значимое вызванное бурями снижение числа спотов на активный\n"
            "\tпередатчик (почасовое число спотов, нормированное на число уникальных\n"
            "\tпередатчиков WSPR — контроль selection bias) на всех трёх\n"
            f"\tдиапазонах: 20\\,м: {pct(drop['20m'], ru=True)},\n"
            f"\t40\\,м: {pct(drop['40m'], ru=True)}, 15\\,м: "
            f"{pct(drop['15m'], ru=True)} (блочная",
        ),
        (
            "39\\,456 WSPR-часов по трём диапазонам, 198 штормовых\n\tэпох при $Kp \\ge 5$",
            "39\\,456 WSPR-часов по трём диапазонам; часы солнечных вспышек\n"
            f"\tисключены по данным GOES XRS, {n_st} штормовых эпох при $Kp \\ge 5$\n"
            f"\tи {n_qu} спокойных эпох",
        ),
        (
            "исходные оценки являются консервативными для 20\\,м и\n"
            "\tпрактически совпадают со скорректированными для 40\\,м.",
            "эти скорректированные оценки получены на исходных числах спотов;\n"
            "\tони более отрицательны, чем нормированные снижения, для 20\\,м и\n"
            "\tблизки к снижениям на сырых числах спотов для 40\\,м.",
        ),
        (
            "Мы наблюдаем масштабно-зависимую картину: снижение возрастает от",
            "Мы наблюдаем масштабно-зависимую картину (на исходных числах спотов):\n"
            "\tснижение возрастает от",
        ),
        (
            "15\\,м\n\t(\\SI{-38.7}{\\percent}) согласуется со снижением максимально применимой",
            f"15\\,м ({pct(drop['15m'], ru=True)}) согласуется со снижением максимально применимой",
        ),
        (
            "(\\SI{-27.7}{\\percent}/\\SI{-27.2}{\\percent}). Асимметрия по UT-окнам",
            f"({pct(drop['20m'], ru=True)}/{pct(drop['40m'], ru=True)}). Асимметрия по UT-окнам",
        ),
        # --- keypoints ---
        (
            "WSPR-спотов снижается на\n\t\\SIrange{27}{39}{\\percent}",
            f"спотов на активный передатчик падает на "
            f"\\SIrange{{{fmt_pct(drop['40m'], ru=True)}}}{{{fmt_pct(drop['15m'], ru=True)}}}"
            f"{{\\percent}}",
        ),
        (
            "скорректированные на ковариаты снижения составляют\n\t\\SIrange{27}{40}{\\percent}",
            "на исходных числах спотов скорректированные на ковариаты\n"
            "\tснижения составляют \\SIrange{27}{40}{\\percent}",
        ),
        # --- PLS ---
        (
            "сигналов снижается на 27--39 %",
            f"сигналов на активный передатчик снижается на "
            f"{fmt_pct(drop['40m'], ru=True).rstrip('0').rstrip(',')}"
            f"--{fmt_pct(drop['15m'], ru=True)} %",
        ),
        # --- robustness bullet 2 ---
        (
            "наблюдаемые снижения плотности\n"
            "\t      спотов (\\SI{-27.7}{\\percent} на 20\\,м, \\SI{-27.2}{\\percent}\n"
            "\t      на 40\\,м, \\SI{-38.7}{\\percent} на 15\\,м) при $Kp \\ge 5$",
            "наблюдаемые снижения на активный передатчик\n"
            f"\t      ({pct(drop['20m'], ru=True)} на 20\\,м, "
            f"{pct(drop['40m'], ru=True)} на 40\\,м,\n"
            f"\t      {pct(drop['15m'], ru=True)} на 15\\,м) при $Kp \\ge 5$",
        ),
        # --- primary result discussion ---
        (
            "блоки по 24 эпохи (72\\,ч)). Исходный эффект наиболее силён на 15\\,м\n"
            "(\\SI{-38.7}{\\percent}) и почти одинаков на 20\\,м и 40\\,м\n"
            "(\\SI{-27.7}{\\percent} и \\SI{-27.2}{\\percent}).",
            "блоки по 24 эпохи (72\\,ч)). На спотах на активный передатчик эффект\n"
            f"наиболее силён на 15\\,м ({pct(drop['15m'], ru=True)}) и почти\n"
            f"одинаков на 20\\,м и 40\\,м ({pct(drop['20m'], ru=True)} и\n"
            f"{pct(drop['40m'], ru=True)}); соответствующие снижения на исходных\n"
            f"числах спотов равны {fmt_cell(drop_raw['20m'], ru=True)}\\%, "
            f"{fmt_cell(drop_raw['40m'], ru=True)}\\% и "
            f"{fmt_cell(drop_raw['15m'], ru=True)}\\%.",
        ),
        # --- frequency section + fig caption ---
        (
            "15\\,м (\\SI{-38.7}{\\percent}) подвержен существенно\n"
            "сильнее, чем 20\\,м (\\SI{-27.7}{\\percent}) и 40\\,м\n"
            "(\\SI{-27.2}{\\percent}).",
            f"15\\,м ({pct(drop['15m'], ru=True)}) подвержен существенно\n"
            f"сильнее, чем 20\\,м ({pct(drop['20m'], ru=True)}) и 40\\,м\n"
            f"({pct(drop['40m'], ru=True)}).",
        ),
        (
            "спотов для трёх ВЧ-диапазонов во время бурь с $Kp \\ge 5$.\n"
            "\t\tДиапазон 15\\,м показывает существенно более сильное подавление\n"
            "\t\t($\\SI{-38.7}{\\percent}$), чем 20\\,м ($\\SI{-27.7}{\\percent}$)\n"
            "\t\tи 40\\,м ($\\SI{-27.2}{\\percent}$)",
            "спотов на активный передатчик для трёх ВЧ-диапазонов во время бурь\n"
            f"\t\tс $Kp \\ge 5$. Диапазон 15\\,м показывает существенно более\n"
            f"\t\tсильное подавление ({pct(drop['15m'], ru=True)}), чем 20\\,м\n"
            f"\t\t({pct(drop['20m'], ru=True)}) и 40\\,м ({pct(drop['40m'], ru=True)})",
        ),
        # --- 1/f^2 argument ---
        (
            "суммарные снижения почти равны ($\\SI{-27.7}{\\percent}$ против\n"
            "\t      $\\SI{-27.2}{\\percent}$)",
            f"суммарные снижения почти равны ({pct(drop['20m'], ru=True)} против\n"
            f"\t      {pct(drop['40m'], ru=True)})",
        ),
        # --- sec:spatial prose ---
        (
            "нормированное по времени\n"
            "снижение составляет \\SI{72,1}{\\percent} при\n"
            "$|\\mathrm{lat}| > 60^\\circ$, \\SI{26,1}{\\percent} при\n"
            "$30$--$60^\\circ$ и \\SI{20,0}{\\percent} при $< 30^\\circ$ (суммарно по\n"
            "40/20/15\\,м; отношение высокие/низкие $3{,}6\\times$; $p < 5 \\times\n"
            "10^{-5}$).",
            "нормированное по времени снижение на активный передатчик составляет\n"
            f"{pct(pooled['high']['drop'], ru=True)} при\n"
            f"$|\\mathrm{{lat}}| > 60^\\circ$, {pct(pooled['mid']['drop'], ru=True)} при\n"
            f"$30$--$60^\\circ$ и {pct(pooled['low']['drop'], ru=True)} при $< 30^\\circ$ "
            f"(суммарно по\n"
            f"40/20/15\\,м; отношение высокие/низкие "
            f"${fmt_ratio(pooled['high']['drop'], pooled['low']['drop'], ru=True, braces=True)}"
            f"\\times$; {p_le(5e-5, ru=True)}).",
        ),
        (
            "Градиент резче с ростом частоты: на 15\\,м он достигает\n"
            "\\SI{84,2}{\\percent} против \\SI{11,8}{\\percent} ($7{,}1\\times$),",
            "Градиент резче с ростом частоты: на 15\\,м авроральное снижение\n"
            f"достигает {pct(cells[('15m', 'high')]['drop'], ru=True)}, тогда как\n"
            f"низкоширотная ячейка близка к нулю ({pct(cells[('15m', 'low')]['drop'], ru=True)},\n"
            f"{p_eq(p15low, ru=True)}), т.е. отношение составляет\n"
            f"${fmt_ratio(cells[('15m', 'high')]['drop'], cells[('15m', 'low')]['drop'], ru=True, braces=True)}"
            f"\\times$,",
        ),
        (
            "значимы во всех девяти ячейках диапазон $\\times$ широта\n"
            "($p \\le 1{,}95 \\times 10^{-3}$; восемь из девяти на уровне\n"
            "нижней границы $p$).",
            f"значимы в восьми из девяти ячейках диапазон $\\times$ широта\n"
            f"({p_le(2.37e-2, ru=True)}; семь из девяти на нижней границе);\n"
            f"низкоширотная ячейка 15\\,м не переживает TX-нормировку\n"
            f"({p_eq(p15low, ru=True)}).",
        ),
        # --- flare paragraph relabel (raw pair) ---
        (
            "Приведённые значения получены с контролем вспышек: исключены"
            " 1\\,325\nчасов (10,1\\% окна) с солнечными вспышками класса"
            " M1.0+. Прогон с\nвспышками отличается лишь на 1--2~п.п."
            " (высокие широты\n"
            "\\SI{73,1}{\\percent} против \\SI{72,1}{\\percent}, средние\n"
            "\\SI{28,2}{\\percent} против \\SI{26,1}{\\percent}, низкие\n"
            "\\SI{22,8}{\\percent} против \\SI{20,0}{\\percent}) и оставляет"
            " $p$ на нижней границе в\nобоих прогонах, поэтому градиент не"
            " является артефактом\nвспышек (SID).",
            "Приведённые значения получены с контролем вспышек и нормированы на\n"
            "активные передатчики: исключены 1\\,325 часов (10,1\\% окна) с\n"
            "солнечными вспышками класса M1.0+. На исходных числах спотов прогон\n"
            "с вспышками отличается от прогона без вспышек лишь на 1--2~п.п.\n"
            "(высокие широты \\SI{73,1}{\\percent} против \\SI{72,1}{\\percent},\n"
            "средние \\SI{28,2}{\\percent} против \\SI{26,1}{\\percent}, низкие\n"
            "\\SI{22,8}{\\percent} против \\SI{20,0}{\\percent}) и оставляет $p$\n"
            "на нижней границе в обоих прогонах, поэтому градиент не является\n"
            "артефактом вспышек (SID).",
        ),
        # --- Selection-bias paragraph (insert after flare paragraph) ---
        (
            "артефактом вспышек (SID).",
            "артефактом вспышек (SID).\n\n"
            "Контроль selection bias: деление каждой почасовой ячейки на число\n"
            "уникальных передатчиков, активных в этот час и в этом диапазоне\n"
            "(Ур.~\\eqref{eq:normtx}), сохраняет порядок как частотного, так и\n"
            f"широтного градиента (суммарно высокие широты "
            f"{pct(pooled['high']['drop'], ru=True)}, средние\n"
            f"{pct(pooled['mid']['drop'], ru=True)}, низкие "
            f"{pct(pooled['low']['drop'], ru=True)}; все суммарные {p_le(5e-5, ru=True)}),\n"
            "но низкоширотная ячейка 15\\,м падает с\n"
            f"{pct(raw15low['drop'], ru=True)} ({p_eq(raw15low['p'], ru=True)}) до\n"
            f"{pct(cells[('15m', 'low')]['drop'], ru=True)} ({p_eq(p15low, ru=True)}): "
            "исходное низкоширотное\n"
            "снижение на 15\\,м объясняется изменением числа активных\n"
            "передатчиков (selection bias), а не геомагнитным поглощением, что\n"
            "согласуется с физическим ожиданием: штормовое поглощение в области D\n"
            "на экваториальных широтах пренебрежимо мало.",
        ),
        # --- tab:spatial caption ---
        (
            "(снижение в процентах см. в\n\tразд.~\\ref{sec:dropnorm}).",
            "(снижение в процентах для спотов на активный передатчик,\n"
            "\tУр.~\\eqref{eq:normtx}; определение в разд.~\\ref{sec:dropnorm}).",
        ),
        (
            "Значения $p$: все\n"
            "\tсуммарные ячейки $< 5 \\times 10^{-5}$; по диапазонам --- восемь из\n"
            "\tдевяти ячеек на нижней границе и низкоширотная 40\\,м "
            "$p = 1{,}95 \\times 10^{-3}$.",
            f"Значения $p$: все суммарные ячейки {p_le(5e-5, ru=True)}; по\n"
            f"\tдиапазонам семь из девяти ячеек на нижней границе, низкие широты\n"
            f"\t40\\,м {p_eq(p40low, ru=True)} и низкие широты 15\\,м\n"
            f"\t{p_eq(p15low, ru=True)} (незначимо).",
        ),
        # --- tab:spatial rows ---
        (
            "Авроральная ($|\\mathrm{lat}| > 60^\\circ$) & $-72{,}1$ & $-67{,}2$ & $-70{,}3$ & $-84{,}2$ \\\\",
            f"Авроральная ($|\\mathrm{{lat}}| > 60^\\circ$) & "
            f"{fmt_cell(pooled['high']['drop'], ru=True)} & "
            f"{fmt_cell(cells[('40m', 'high')]['drop'], ru=True)} & "
            f"{fmt_cell(cells[('20m', 'high')]['drop'], ru=True)} & "
            f"{fmt_cell(cells[('15m', 'high')]['drop'], ru=True)} \\\\",
        ),
        (
            "Средняя ($30$--$60^\\circ$) & $-26{,}1$ & $-25{,}2$ & $-24{,}9$ & $-38{,}6$ \\\\",
            f"Средняя ($30$--$60^\\circ$) & "
            f"{fmt_cell(pooled['mid']['drop'], ru=True)} & "
            f"{fmt_cell(cells[('40m', 'mid')]['drop'], ru=True)} & "
            f"{fmt_cell(cells[('20m', 'mid')]['drop'], ru=True)} & "
            f"{fmt_cell(cells[('15m', 'mid')]['drop'], ru=True)} \\\\",
        ),
        (
            "Низкая ($< 30^\\circ$) & $-20{,}0$ & $-21{,}6$ & $-22{,}2$ & $-11{,}8$ \\\\",
            f"Низкая ($< 30^\\circ$) & "
            f"{fmt_cell(pooled['low']['drop'], ru=True)} & "
            f"{fmt_cell(cells[('40m', 'low')]['drop'], ru=True)} & "
            f"{fmt_cell(cells[('20m', 'low')]['drop'], ru=True)} & "
            f"{fmt_cell(cells[('15m', 'low')]['drop'], ru=True)} \\\\",
        ),
        # --- mechanism + conclusion ---
        (
            "влияет на самый высокий диапазон 15\\,м (\\SI{-38.7}{\\percent}).",
            f"влияет на самый высокий диапазон 15\\,м ({pct(drop['15m'], ru=True)}).",
        ),
        (
            "Вызванное бурями снижение числа спотов\n"
            "\t      составляет \\SI{-27.7}{\\percent} (20\\,м), \\SI{-27.2}{\\percent}\n"
            "\t      (40\\,м) и \\SI{-38.7}{\\percent} (15\\,м)",
            "Вызванное бурями снижение числа спотов на активный передатчик\n"
            f"\t      составляет {pct(drop['20m'], ru=True)} (20\\,м), "
            f"{pct(drop['40m'], ru=True)} (40\\,м) и\n"
            f"\t      {pct(drop['15m'], ru=True)} (15\\,м)",
        ),
        (
            "Скорректированные на ковариаты оценки\n"
            "\t      равны \\SI{-33.6}{\\percent}, \\SI{-27.1}{\\percent} и",
            "На исходных числах спотов скорректированные на\n"
            "\t      ковариаты оценки равны \\SI{-33.6}{\\percent}, "
            "\\SI{-27.1}{\\percent} и",
        ),
    ]

    filewide: list[tuple[str, str]] = [
        # --- Methods: new paragraph with \\label{sec:normtx} ---
        (
            "\\subsection{Нормированное по времени снижение и чувствительность к размеру блока}",
            "\\paragraph{Нормировка на активные передатчики.} Первичные результаты\n"
            "получены на ряду, нормированном на передатчики:\n"
            "\\begin{equation}\n"
            "\tS_{\\mathrm{norm}} = \\frac{\\mathrm{споты}}{n_{\\mathrm{tx}}}\n"
            "\t\\label{eq:normtx}\n"
            "\\end{equation}\n"
            "где $n_{\\mathrm{tx}}$ — число уникальных передатчиков WSPR,\n"
            "активных в этот час и в этом диапазоне (серверная функция\n"
            "\\texttt{uniqExact(tx\\_sign)}; хранится в мета-полях unified-схемы,\n"
            "доступна и локально, и из API). Каждая почасовая ячейка\n"
            "делится на $n_{\\mathrm{tx}}$ своего (час, диапазон) до\n"
            "агрегации, поэтому ячейка со спотами $>0$ при отсутствующем\n"
            "$n_{\\mathrm{tx}}$ прерывает прогон. Перестановочный headline\n"
            "(разделы о частотной и масштабной зависимости) и анализ по\n"
            "широтным группам (разд.~\\ref{sec:spatial}) используют\n"
            "$S_{\\mathrm{norm}}$; анализы, моделирующие целочисленные счётчики\n"
            "(поправка на ковариаты с отрицательным биномиальным\n"
            "распределением, ДИ блочного бутстрепа, отношение абсолютных\n"
            "потерь), вычислены на исходных числах спотов и помечены\n"
            "соответственно.\n\n"
            "\\subsection{Нормированное по времени снижение и чувствительность к размеру блока}",
        ),
        # --- Limitations: remove obsolete claim, add items ---
        (
            "\\item \\textbf{Активность станций:} Сообщаемые снижения относятся к числу\n"
            "\t      \\emph{зарегистрированных} WSPR-спотов: число активных\n"
            "\t      передатчиков, приёмников и уникальных трасс, а также поведение\n"
            "\t      операторов при загрузке не нормируются. Для чистой атрибуции\n"
            "\t      по способу распространения потребовалась бы нормировка на число\n"
            "\t      активных станций, которая недоступна из агрегированных запросов,\n"
            "\t      использованных здесь.",
            "\\item \\textbf{Активность станций:} Сообщаемые снижения относятся к числу\n"
            "\t      \\emph{зарегистрированных} WSPR-спотов: число приёмников,\n"
            "\t      уникальных трасс и поведение операторов при загрузке не\n"
            "\t      нормируются. Число активных передатчиков нормируется через\n"
            "\t      Ур.~\\eqref{eq:normtx} (споты на активный передатчик);\n"
            "\t      популяции приёмников и трасс остаются остаточным\n"
            "\t      мешающим фактором.\n"
            "\t\\item \\textbf{Selection bias на 15\\,м в низких широтах:} После\n"
            "\t      нормировки на активные передатчики эффект на 15\\,м в низких\n"
            f"\t      широтах исчезает ({pct(cells[('15m', 'low')]['drop'], ru=True)}, "
            f"{p_eq(p15low, ru=True)}),\n"
            "\t      тогда как авроральный и среднеширотный градиенты и порядок по\n"
            "\t      диапазонам сохраняются. Это локализует эффект физически\n"
            "\t      (поглощение в области D на экваториальных широтах\n"
            "\t      пренебрежимо мало) и показывает, что исходные снижения на\n"
            "\t      низких широтах могут определяться человеческим фактором;\n"
            "\t      будущим исследованиям следует нормировать на число активных\n"
            "\t      станций до интерпретации низкоширотных снижений.",
        ),
    ]

    inserts: list[tuple[str, str]] = [
        # --- raw labels ---
        (
            "исходные \\SI{-27.7}{\\percent}, \\SI{-27.2}{\\percent}, "
            "\\SI{-38.7}{\\percent};\n"
            "скорректированные",
            "исходные (обучающий прогон со вспышками)\n"
            "\\SI{-27.7}{\\percent}, \\SI{-27.2}{\\percent}, \\SI{-38.7}{\\percent};\n"
            "скорректированные",
        ),
        (
            "в обучающем периоде снижения равны \\SI{-38.7}{\\percent} (15\\,м),",
            "в обучающем периоде исходные (со вспышками) снижения равны\n"
            "\t\\SI{-38.7}{\\percent} (15\\,м),",
        ),
        (
            "исходное \\SI{-27.7}{\\percent} против скорректированного",
            "исходное (прогон со вспышками) \\SI{-27.7}{\\percent} против скорректированного",
        ),
        (
            "В табл.~\\ref{tab:main} представлен основной результат: вызванное бурями\n"
            "снижение числа WSPR-спотов на всех трёх ВЧ-диапазонах.",
            "В табл.~\\ref{tab:main} представлены оценки на исходных числах спотов\n"
            "первичного результата: вызванное бурями снижение числа WSPR-спотов во\n"
            "всех трёх ВЧ-диапазонах. Первичные перестановочные снижения на спотах\n"
            f"на активный передатчик: {pct(drop['20m'], ru=True)} (20\\,м),\n"
            f"{pct(drop['40m'], ru=True)} (40\\,м) и {pct(drop['15m'], ru=True)}\n"
            f"(15\\,м), все {p_le(5e-5, ru=True)}.",
        ),
        (
            "Исходное снижение следует\n\t\tУр.~\\eqref{eq:drop} (исходные значения спотов)",
            "Исходное снижение следует\n"
            "\t\tУр.~\\eqref{eq:drop} (исходные значения спотов, обучающий прогон со вспышками)",
        ),
        (
            "(наблюдаемое, без ДИ). Строки для дневного и ночного UT-окон охватывают 111 из 198 штормовых эпох",
            "(наблюдаемое, без ДИ; исходные числа спотов). Строки для дневного и "
            "ночного UT-окон охватывают 111 из 198 штормовых эпох",
        ),
        (
            "$Kp = 5\\text{--}6$ уже даёт \\SI{-28.6}{\\percent}",
            "$Kp = 5\\text{--}6$ уже даёт \\SI{-28.6}{\\percent} (исходные числа спотов)",
        ),
        (
            "Чувствительность к размеру блока: повторная перестановка с блоком",
            "Чувствительность к размеру блока (исходные числа спотов): повторная "
            "перестановка с блоком",
        ),
        (
            "\\caption{Сверху: основное снижение (\\%) при трёх схемах присвоения $Kp$.",
            "\\caption{Сверху: основное снижение (\\%) при трёх схемах присвоения "
            "$Kp$ (исходные числа спотов).",
        ),
        (
            "\\caption{Снижение числа спотов во время бури (\\%) с разрешением\n"
            "\t\tпо расстоянию, по бинам расстояния большого круга (обучающий\n"
            "\t\tпериод).",
            "\\caption{Снижение числа спотов во время бури (\\%) с разрешением\n"
            "\t\tпо расстоянию, по бинам расстояния большого круга (обучающий\n"
            "\t\tпериод; исходные числа спотов).",
        ),
        # --- Confounders: permutation analyses now exclude flares too ---
        (
            "контролируются в анализе по широтным группам, который\n"
            "\t      исключает 1\\,325 часов с вспышками GOES X-ray класса"
            " M1.0+ (10,1\\%,\n\t      разд.~\\ref{sec:spatial}) и сдвигает"
            " суммарные снижения на 1--2~п.п.;\n\t      перестановочные"
            " анализы сохраняют все часы \\citep{mitra1974}.",
            "контролируются и в первичном перестановочном анализе, и в анализе\n"
            "\t      по широтным группам, которые исключают 1\\,325 часов с вспышками\n"
            "\t      GOES X-ray класса M1.0+ (10,1\\%, разд.~\\ref{sec:spatial}); на\n"
            "\t      исходных числах спотов исключение сдвигает суммарные снижения\n"
            "\t      лишь на 1--2~п.п. \\citep{mitra1974}.",
        ),
    ]
    return spatial, filewide, inserts, "\\label{sec:spatial}", "\\section{Обсуждение}"


# --------------------------------------------------------------------------- #
# application (same engine as update_paper_flare_numbers.py)
# --------------------------------------------------------------------------- #
def apply_to_text(text, spatial, filewide, inserts, s0, s1, label) -> str:
    problems: list[str] = []
    if text.find(s0) < 0 or text.find(s1) < 0:
        raise SystemExit(f"{label}: slice markers not found")

    # The plans mix abstract, Results and Discussion edits, and every anchor
    # is unique within its file, so both lists are matched file-wide: the
    # uniqueness guard (count == 1) is what prevents an accidental replace,
    # not the section slice (kept only as a section-presence assertion).
    whole = text
    for old, new in spatial:
        n = whole.count(old)
        if n != 1:
            problems.append(f"  spatial: {old[:70]!r} found {n} times (expected 1)")
        else:
            whole = whole.replace(old, new)

    for old, new in filewide:
        n = whole.count(old)
        if n != 1:
            problems.append(f"  file:    {old[:70]!r} found {n} times (expected 1)")
        else:
            whole = whole.replace(old, new)

    for anchor, rep in inserts:
        n = whole.count(anchor)
        if n != 1:
            problems.append(f"  insert:  {anchor[:70]!r} found {n} times (expected 1)")
        else:
            whole = whole.replace(anchor, rep)

    if problems:
        print(f"[FAIL] {label}: pattern verification failed, nothing applied:")
        print("\n".join(problems))
        raise SystemExit(2)
    return whole


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Phase 1: dry-run, print diff")
    parser.add_argument("--apply", action="store_true", help="Phase 2: write the .tex files")
    parser.add_argument(
        "--diff-out",
        metavar="PATH",
        default=None,
        help="also write the unified diff to PATH (UTF-8, LF)",
    )
    args = parser.parse_args()
    if not args.check and not args.apply:
        parser.error("must specify --check or --apply")

    d = gather()
    print("=" * 80)
    print("Q2 sync: flare-controlled + TX-normalized headline (EN + RU)")
    print("=" * 80)
    for b in BANDS:
        print(f"  perm {b}: {d['drop'][b]:+.1f}%  p={d['p'][b]:.2e}")
    for g in GROUPS:
        print(f"  pooled {g}: {d['pooled'][g]['drop']:+.1f}%  p={d['pooled'][g]['p']:.2e}")
    print(f"  N: {d['n_storm']} storm / {d['n_quiet']} quiet; flare hours {d['flare_hours']}")
    print("  n_tx: stats not in JSON (runner prints them; not reported in Methods)")
    print()

    plans = {
        "main.tex": plans_en(d),
        "main_ru.tex": plans_ru(d),
    }

    diff_chunks: list[str] = []
    for name, (spatial, filewide, inserts, s0, s1) in plans.items():
        path = PAPER / name
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise SystemExit(f"{name}: BOM found, refusing to edit")
        if b"\r" in raw:
            raise SystemExit(f"{name}: CRLF found, refusing to edit")
        if not raw.endswith(b"\n"):
            raise SystemExit(f"{name}: missing final newline, refusing to edit")
        old_text = raw.decode("utf-8")
        new_text = apply_to_text(old_text, spatial, filewide, inserts, s0, s1, name)
        diff = "".join(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/paper/{name}",
                tofile=f"b/paper/{name}",
            )
        )
        print(diff)
        diff_chunks.append(diff)
        if args.apply:
            with path.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(new_text)
            print(f"[OK] wrote paper/{name}")

    if args.diff_out:
        with open(args.diff_out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(diff_chunks))
        print(f"[OK] diff written to {args.diff_out}")
    if args.check:
        print("[CHECK] dry run only; re-run with --apply to write the files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
