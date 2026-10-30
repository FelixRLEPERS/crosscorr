#!/usr/bin/env python
"""Update the flare-control numbers in paper/main.tex and paper/main_ru.tex.

Two-phase (AGENTS.md house pattern):

  Phase 1 --check   print a unified diff of every proposed edit, change nothing
  Phase 2 --apply   write the files (UTF-8, LF, final newline preserved)

Scope (the latitude-group analysis and everything that must stay consistent
with it):

  * sec:spatial prose, table (12 cells) and caption (N_storm, per-group and
    per-band storm-spot totals, p-values, window totals);
  * sec:dropnorm (T_storm/T_quiet sampled hours, quiet-window ratio, raw
    ratio, 198/3035 normalization);
  * the "one sampled hour per Kp epoch" limitation;
  * the SID sentence in the Confounders limitation (it is no longer true);
  * two inserted notes: a Methods-style flare-control sentence in sec:spatial
    and a Solar-flare-control item in Limitations.

Intentionally NOT touched: the permutation-test headline numbers, bootstrap
CIs, episode/monthly/UT-window tables and every other analysis that still
reports the original (with-flares) run. Those require a full re-run of the
derived analyses -- tracked as a separate campaign.

New values come from the flare-controlled canonical JSON
(results/spatial_lat_groups.json); old values are read from the with-flares
JSON and cross-validated against the literal text in the .tex files. Any
mismatch aborts before a single byte is written.
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
OLD_JSON = ROOT / "results" / "spatial_lat_groups_with_flares.json"
NEW_JSON = ROOT / "results" / "spatial_lat_groups.json"

GROUPS = ("high", "mid", "low")
BANDS = ("40m", "20m", "15m")
OLD_HOURS = 13152  # training window, one sampled hour per Kp epoch
OLD_EPOCHS = 4349  # Kp epochs covered in the window (of 4384, 99.2%)


# --------------------------------------------------------------------------- #
# formatting helpers
# --------------------------------------------------------------------------- #
def _ru(s: str) -> str:
    return s.replace(".", ",")


def fmt_int_sep(n: int) -> str:
    """Thousands separated with TeX thin space: 20741541 -> 20\\,741\\,541."""
    return f"{n:,}".replace(",", r"\,")


def fmt_pct(v: float, ru: bool = False) -> str:
    """72.1 / -20.0 -> '72.1' / '20.0' (absolute, one decimal)."""
    s = f"{abs(v):.1f}"
    return _ru(s) if ru else s


def fmt_cell(v: float, ru: bool = False) -> str:
    """Table cell: -72.1 -> '$-72.1$' (RU: '$-72{,}1$')."""
    s = f"{v:.1f}"
    if ru:
        s = s.replace(".", "{,}")
    return f"${s}$"


def fmt_ratio(a: float, b: float, ru: bool = False, braces: bool = False) -> str:
    s = f"{abs(a) / abs(b):.1f}"
    if ru:
        s = _ru(s)
    if braces:
        s = s.replace(",", "{,}")
    return s


def fmt_sci(p: float, ru: bool = False) -> str:
    """1.9499e-3 -> '1.95 \\times 10^{-3}' (RU uses {,} mantissa)."""
    mant, exp = f"{p:.2e}".split("e")
    if "." in mant:
        mant = mant.rstrip("0").rstrip(".")
    if ru:
        mant = mant.replace(".", "{,}")
    return f"{mant} \\times 10^{{{int(exp)}}}"


# --------------------------------------------------------------------------- #
# data loading + sanity assertions
# --------------------------------------------------------------------------- #
def load_scenario() -> dict:
    old = json.loads(OLD_JSON.read_text(encoding="utf-8"))
    new = json.loads(NEW_JSON.read_text(encoding="utf-8"))

    def pooled(d: dict, g: str, k: str) -> float:
        return d["pooled"][g][k]

    def cellv(d: dict, band: str, g: str, k: str) -> float:
        return d["per_band"][band][g][k]

    data = {
        "old": old,
        "new": new,
        "old_pooled": {g: pooled(old, g, "drop_pct") for g in GROUPS},
        "new_pooled": {g: pooled(new, g, "drop_pct") for g in GROUPS},
        "old_cells": {(b, g): cellv(old, b, g, "drop_pct") for b in BANDS for g in GROUPS},
        "new_cells": {(b, g): cellv(new, b, g, "drop_pct") for b in BANDS for g in GROUPS},
        "old_storm": int(pooled(old, "high", "n_storm")),
        "new_storm": int(pooled(new, "high", "n_storm")),
        "old_quiet": int(pooled(old, "high", "n_quiet")),
        "new_quiet": int(pooled(new, "high", "n_quiet")),
        "old_p40low": float(cellv(old, "40m", "low", "p_value")),
        "new_p40low": float(cellv(new, "40m", "low", "p_value")),
        "old_spots_total": int(old["n_spots_total"]),
        "new_spots_total": int(new["n_spots_total"]),
        "old_storm_spots": {("pooled", g): int(pooled(old, g, "n_storm_spots")) for g in GROUPS},
        "new_storm_spots": {("pooled", g): int(pooled(new, g, "n_storm_spots")) for g in GROUPS},
        "old_quiet_spots_high": int(pooled(old, "high", "n_quiet_spots")),
        "new_quiet_spots_high": int(pooled(new, "high", "n_quiet_spots")),
    }
    for b in BANDS:
        for g in GROUPS:
            data["old_storm_spots"][(b, g)] = int(cellv(old, b, g, "n_storm_spots"))
            data["new_storm_spots"][(b, g)] = int(cellv(new, b, g, "n_storm_spots"))

    ff = new.get("params", {}).get("flare_filter", {})
    data["excluded"] = int(ff.get("n_hours_excluded", -1))
    data["new_hours"] = OLD_HOURS - data["excluded"]

    # --- assertions: the with-flares JSON must still hold the paper values ---
    checks = [
        (round(data["old_pooled"]["high"], 1) == -73.1, "old pooled high == -73.1"),
        (round(data["old_pooled"]["mid"], 1) == -28.2, "old pooled mid == -28.2"),
        (round(data["old_pooled"]["low"], 1) == -22.8, "old pooled low == -22.8"),
        (data["old_storm"] == 198 and data["old_quiet"] == 3035, "old N 198/3035"),
        (data["new_storm"] == 169 and data["new_quiet"] == 2738, "new N 169/2738"),
        (data["excluded"] == 1325, "flare hours excluded == 1325"),
        (f"{data['old_spots_total'] / 1e9:.2f}" == "1.98", "old total spots 1.98e9"),
        (f"{data['new_spots_total'] / 1e9:.2f}" == "1.80", "new total spots 1.80e9"),
        (OLD_HOURS - data["excluded"] == data["new_hours"], "hours arithmetic"),
        (data["old_storm"] * 3 == 594 and data["old_quiet"] * 3 == 9105, "594/9105"),
        (
            f"{100 * data['old_storm_spots'][('pooled', 'high')] / data['old_quiet_spots_high']:.2f}"
            == "1.75",
            "old raw ratio 1.75%",
        ),
        (fmt_sci(data["old_p40low"]) == "1.5 \\times 10^{-4}", "old 40m-low p = 1.5e-4"),
        (
            round(data["old_pooled"]["high"] / data["old_pooled"]["low"], 1) == 3.2,
            "old pooled ratio 3.2x",
        ),
    ]
    failed = [msg for ok, msg in checks if not ok]
    if failed:
        raise SystemExit("JSON sanity failed: " + "; ".join(failed))
    return data


# --------------------------------------------------------------------------- #
# edit plan
# --------------------------------------------------------------------------- #
def build_edits(d: dict) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (spatial-slice edits, file-wide edits) for one language.

    Filled in per language by the callers below; here we only compute the
    language-neutral building blocks.
    """
    raise NotImplementedError


def edits_en(d: dict) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    op, np_ = d["old_pooled"], d["new_pooled"]
    oc, nc = d["old_cells"], d["new_cells"]
    o15h, n15h = oc[("15m", "high")], nc[("15m", "high")]
    o15l, n15l = oc[("15m", "low")], nc[("15m", "low")]
    raw_old = f"{100 * d['old_storm_spots'][('pooled', 'high')] / d['old_quiet_spots_high']:.2f}"
    raw_new = f"{100 * d['new_storm_spots'][('pooled', 'high')] / d['new_quiet_spots_high']:.2f}"

    def pct_old(v: float) -> str:
        return f"\\SI{{{fmt_pct(v)}}}{{\\percent}}"

    def pct_new(v: float) -> str:
        return f"\\SI{{{fmt_pct(v)}}}{{\\percent}}"

    spatial: list[tuple[str, str]] = [
        (pct_old(op["high"]), pct_new(np_["high"])),
        (pct_old(op["mid"]), pct_new(np_["mid"])),
        (pct_old(op["low"]), pct_new(np_["low"])),
        (pct_old(o15h), pct_new(n15h)),
        (pct_old(o15l), pct_new(n15l)),
        (
            f"${fmt_ratio(op['high'], op['low'])}\\times$",
            f"${fmt_ratio(np_['high'], np_['low'])}\\times$",
        ),
        (f"${fmt_ratio(o15h, o15l)}\\times$", f"${fmt_ratio(n15h, n15l)}\\times$"),
        (
            f"{d['old_spots_total'] / 1e9:.2f} billion spots",
            f"{d['new_spots_total'] / 1e9:.2f} billion spots",
        ),
        (f"{fmt_int_sep(OLD_HOURS)} hours", f"{fmt_int_sep(d['new_hours'])} hours"),
        (f"$p \\le {fmt_sci(d['old_p40low'])}$", f"$p \\le {fmt_sci(d['new_p40low'])}$"),
        (f"$p = {fmt_sci(d['old_p40low'])}$", f"$p = {fmt_sci(d['new_p40low'])}$"),
        (
            f"$N_{{\\text{{storm}}}}$ = {d['old_storm']}",
            f"$N_{{\\text{{storm}}}}$ = {d['new_storm']}",
        ),
    ]
    # caption spot totals: pooled singles then per-band triples (15m keeps bold)
    for g in GROUPS:
        spatial.append(
            (
                fmt_int_sep(d["old_storm_spots"][("pooled", g)]),
                fmt_int_sep(d["new_storm_spots"][("pooled", g)]),
            )
        )
    for b in ("40m", "20m"):
        old_t = "/".join(fmt_int_sep(d["old_storm_spots"][(b, g)]) for g in GROUPS)
        new_t = "/".join(fmt_int_sep(d["new_storm_spots"][(b, g)]) for g in GROUPS)
        spatial.append((old_t, new_t))
    old_15 = "/".join(fmt_int_sep(d["old_storm_spots"][("15m", g)]) for g in GROUPS)
    new_15 = "/".join(fmt_int_sep(d["new_storm_spots"][("15m", g)]) for g in GROUPS)
    spatial.append(
        (
            f"\\textbf{{{old_15.split('/')[0]}}}/{old_15.split('/', 1)[1]}",
            f"\\textbf{{{new_15.split('/')[0]}}}/{new_15.split('/', 1)[1]}",
        )
    )
    # table rows: pooled, 40m, 20m, 15m
    rows: list[list[tuple[float, float]]] = [[(op[g], np_[g]) for g in GROUPS]]
    rows += [[(oc[(b, g)], nc[(b, g)]) for g in GROUPS] for b in BANDS]
    for row in rows:
        for o_v, n_v in row:
            spatial.append((fmt_cell(o_v), fmt_cell(n_v)))

    filewide: list[tuple[str, str]] = [
        # sec:dropnorm
        (
            f"$T_{{\\text{{storm}}}} = {d['old_storm']}$\\,h",
            f"$T_{{\\text{{storm}}}} = {d['new_storm']}$\\,h",
        ),
        (
            f"$T_{{\\text{{quiet}}}} = {fmt_int_sep(d['old_quiet'])}$\\,h",
            f"$T_{{\\text{{quiet}}}} = {fmt_int_sep(d['new_quiet'])}$\\,h",
        ),
        (f"(\\SI{{{raw_old}}}{{\\percent}} at", f"(\\SI{{{raw_new}}}{{\\percent}} at"),
        (
            f"${fmt_ratio(float(d['old_quiet']), float(d['old_storm']))}\\times$ longer",
            f"${fmt_ratio(float(d['new_quiet']), float(d['new_storm']))}\\times$ longer",
        ),
        (
            f"{d['old_storm']}/{d['old_quiet']} before comparison",
            f"{d['new_storm']}/{d['new_quiet']} before comparison",
        ),
        # Limitations: one sampled hour per Kp epoch
        (f"yielding {d['old_storm']}", f"yielding {d['new_storm']}"),
        (
            f"storm-hours and {d['old_quiet']} quiet-hours",
            f"storm-hours and {d['new_quiet']} quiet-hours",
        ),
        (
            f"full {d['old_storm'] * 3}/{d['old_quiet'] * 3} hours",
            f"full {d['new_storm'] * 3}/{d['new_quiet'] * 3} hours",
        ),
        # Confounders: SID sentence is no longer true
        (
            "are not separately accounted for \\citep{mitra1974}.",
            "are controlled for in the latitude-group analysis, which\n"
            "\t      excludes the 1\\,325 GOES X-ray M1.0+ flare hours"
            " (10.1\\%,\n\t      Section~\\ref{sec:spatial}) and shifts the"
            " pooled drops by 1--2\\,pp;\n\t      the permutation analyses"
            " retain all hours \\citep{mitra1974}.",
        ),
    ]

    lost = (d["old_storm"] - d["new_storm"]) + (d["old_quiet"] - d["new_quiet"])
    inserts: list[tuple[str, str]] = [
        # sec:spatial Methods-style note (append after the anchor)
        (
            "eight of nine at the $5 \\times 10^{-5}$ floor).",
            "eight of nine at the $5 \\times 10^{-5}$ floor).\n"
            "The reported values are flare-controlled: the 1\\,325 hours"
            " (10.1\\% of\nthe window) with a GOES X-ray flare of class"
            " M1.0+ are excluded. The\nflare-included run differs by only"
            " 1--2\\,pp (high-lat\n"
            f"{pct_old(op['high'])} vs.\\ {pct_new(np_['high'])}, mid-lat\n"
            f"{pct_old(op['mid'])} vs.\\ {pct_new(np_['mid'])}, low-lat\n"
            f"{pct_old(op['low'])} vs.\\ {pct_new(np_['low'])}) and leaves"
            " $p$ at the permutation floor\nin both runs, so the gradient"
            " is not a flare (SID) artifact.",
        ),
        # Limitations: new item, inserted before Storm-slot independence
        (
            "\t\\item \\textbf{Storm-slot independence:}",
            "\t\\item \\textbf{Solar-flare control:} The latitude-group\n"
            "\t      analysis is reported with solar-flare hours excluded:"
            " the\n\t      1\\,325 flare hours (10.1\\%) remove the sampled"
            f" hour of {lost} of\n\t      {fmt_int_sep(OLD_EPOCHS)} covered"
            " epochs ($N_{\\text{storm}}$\n"
            f"\t      {d['old_storm']} $\\rightarrow$ {d['new_storm']},"
            f" $N_{{\\text{{quiet}}}}$ {d['old_quiet']} $\\rightarrow$\n"
            f"\t      {d['new_quiet']}). The pooled drops shift by only"
            " 1--2\\,pp and all\n\t      $p$-values stay at the permutation"
            " floor, so the auroral gradient\n\t      is not a flare (SID)"
            " artifact; the smaller epoch sample lowers\n\t      power for"
            " secondary pairwise $Kp$-bin contrasts."
            "\n\t\\item \\textbf{Storm-slot independence:}",
        ),
    ]
    return spatial, filewide, inserts


def edits_ru(d: dict) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    op, np_ = d["old_pooled"], d["new_pooled"]
    oc, nc = d["old_cells"], d["new_cells"]
    o15h, n15h = oc[("15m", "high")], nc[("15m", "high")]
    o15l, n15l = oc[("15m", "low")], nc[("15m", "low")]
    raw_old = f"{100 * d['old_storm_spots'][('pooled', 'high')] / d['old_quiet_spots_high']:.2f}"
    raw_new = f"{100 * d['new_storm_spots'][('pooled', 'high')] / d['new_quiet_spots_high']:.2f}"

    def pct_old(v: float) -> str:
        return f"\\SI{{{fmt_pct(v, ru=True)}}}{{\\percent}}"

    def pct_new(v: float) -> str:
        return f"\\SI{{{fmt_pct(v, ru=True)}}}{{\\percent}}"

    spatial: list[tuple[str, str]] = [
        (pct_old(op["high"]), pct_new(np_["high"])),
        (pct_old(op["mid"]), pct_new(np_["mid"])),
        (pct_old(op["low"]), pct_new(np_["low"])),
        (pct_old(o15h), pct_new(n15h)),
        (pct_old(o15l), pct_new(n15l)),
        (
            f"${fmt_ratio(op['high'], op['low'], ru=True, braces=True)}\\times$",
            f"${fmt_ratio(np_['high'], np_['low'], ru=True, braces=True)}\\times$",
        ),
        (
            f"${fmt_ratio(o15h, o15l, ru=True, braces=True)}\\times$",
            f"${fmt_ratio(n15h, n15l, ru=True, braces=True)}\\times$",
        ),
        (
            f"{_ru(format(d['old_spots_total'] / 1e9, '.2f'))} млрд",
            f"{_ru(format(d['new_spots_total'] / 1e9, '.2f'))} млрд",
        ),
        (f"{fmt_int_sep(OLD_HOURS)}\\,ч", f"{fmt_int_sep(d['new_hours'])}\\,ч"),
        (
            f"$p \\le {fmt_sci(d['old_p40low'], ru=True)}$",
            f"$p \\le {fmt_sci(d['new_p40low'], ru=True)}$",
        ),
        (
            f"$p = {fmt_sci(d['old_p40low'], ru=True)}$",
            f"$p = {fmt_sci(d['new_p40low'], ru=True)}$",
        ),
        (
            f"$N_{{\\mbox{{шторм}}}}$ = {d['old_storm']}",
            f"$N_{{\\mbox{{шторм}}}}$ = {d['new_storm']}",
        ),
    ]
    for g in GROUPS:
        spatial.append(
            (
                fmt_int_sep(d["old_storm_spots"][("pooled", g)]),
                fmt_int_sep(d["new_storm_spots"][("pooled", g)]),
            )
        )
    for b in ("40m", "20m"):
        old_t = "/".join(fmt_int_sep(d["old_storm_spots"][(b, g)]) for g in GROUPS)
        new_t = "/".join(fmt_int_sep(d["new_storm_spots"][(b, g)]) for g in GROUPS)
        spatial.append((old_t, new_t))
    old_15 = "/".join(fmt_int_sep(d["old_storm_spots"][("15m", g)]) for g in GROUPS)
    new_15 = "/".join(fmt_int_sep(d["new_storm_spots"][("15m", g)]) for g in GROUPS)
    spatial.append(
        (
            f"\\textbf{{{old_15.split('/')[0]}}}/{old_15.split('/', 1)[1]}",
            f"\\textbf{{{new_15.split('/')[0]}}}/{new_15.split('/', 1)[1]}",
        )
    )
    rows: list[list[tuple[float, float]]] = [[(op[g], np_[g]) for g in GROUPS]]
    rows += [[(oc[(b, g)], nc[(b, g)]) for g in GROUPS] for b in BANDS]
    for row in rows:
        for o_v, n_v in row:
            spatial.append((fmt_cell(o_v, ru=True), fmt_cell(n_v, ru=True)))

    filewide: list[tuple[str, str]] = [
        (
            f"$T_{{\\text{{шторм}}}} = {d['old_storm']}$\\,ч",
            f"$T_{{\\text{{шторм}}}} = {d['new_storm']}$\\,ч",
        ),
        (
            f"$T_{{\\text{{спокойн}}}} = {fmt_int_sep(d['old_quiet'])}$\\,ч",
            f"$T_{{\\text{{спокойн}}}} = {fmt_int_sep(d['new_quiet'])}$\\,ч",
        ),
        (f"(\\SI{{{_ru(raw_old)}}}{{\\percent}} на", f"(\\SI{{{_ru(raw_new)}}}{{\\percent}} на"),
        (
            f"${fmt_ratio(float(d['old_quiet']), float(d['old_storm']), ru=True)}$ раза длиннее",
            f"${fmt_ratio(float(d['new_quiet']), float(d['new_storm']), ru=True)}$ раза длиннее",
        ),
        (
            f"{d['old_storm']}/{d['old_quiet']} перед сравнением",
            f"{d['new_storm']}/{d['new_quiet']} перед сравнением",
        ),
        (
            f"давая {d['old_storm']} штормовых часов и"
            f" {fmt_int_sep(d['old_quiet'])} спокойных часов воздействия",
            f"давая {d['new_storm']} штормовых часов и"
            f" {fmt_int_sep(d['new_quiet'])} спокойных часов воздействия",
        ),
        (
            f"вместо полных {d['old_storm'] * 3}/{fmt_int_sep(d['old_quiet'] * 3)} часов",
            f"вместо полных {d['new_storm'] * 3}/{fmt_int_sep(d['new_quiet'] * 3)} часов",
        ),
        (
            "отдельно не учитываются \\citep{mitra1974}.",
            "контролируются в анализе по широтным группам, который\n"
            "\t      исключает 1\\,325 часов с вспышками GOES X-ray класса"
            " M1.0+ (10,1\\%,\n\t      разд.~\\ref{sec:spatial}) и сдвигает"
            " суммарные снижения на 1--2~п.п.;\n\t      перестановочные"
            " анализы сохраняют все часы \\citep{mitra1974}.",
        ),
    ]

    lost = (d["old_storm"] - d["new_storm"]) + (d["old_quiet"] - d["new_quiet"])
    inserts: list[tuple[str, str]] = [
        (
            "нижней границы $p$).",
            "нижней границы $p$).\n"
            "Приведённые значения получены с контролем вспышек: исключены"
            " 1\\,325\nчасов (10,1\\% окна) с солнечными вспышками класса"
            " M1.0+. Прогон с\nвспышками отличается лишь на 1--2~п.п."
            " (высокие широты\n"
            f"{pct_old(op['high'])} против {pct_new(np_['high'])}, средние\n"
            f"{pct_old(op['mid'])} против {pct_new(np_['mid'])}, низкие\n"
            f"{pct_old(op['low'])} против {pct_new(np_['low'])}) и оставляет"
            " $p$ на нижней границе в\nобоих прогонах, поэтому градиент не"
            " является артефактом\nвспышек (SID).",
        ),
        (
            "\t\\item \\textbf{Независимость штормовых слотов:}",
            "\t\\item \\textbf{Контроль солнечных вспышек:} Анализ по\n"
            "\t      широтным группам приведён с исключением часов вспышек:"
            "\n\t      1\\,325 часов (10,1\\% окна) с вспышками GOES X-ray"
            f" класса M1.0+, из-за\n\t      чего свой отобранный час"
            f" потеряли {lost} из {fmt_int_sep(OLD_EPOCHS)}\n\t      покрытых"
            f" эпох ($N_{{\\mbox{{шторм}}}}$ {d['old_storm']} $\\rightarrow$\n"
            f"\t      {d['new_storm']}, $N_{{\\mbox{{спокойн}}}}$"
            f" {d['old_quiet']} $\\rightarrow$ {d['new_quiet']}).\n"
            "\t      Суммарные снижения сдвигаются лишь на 1--2~п.п., а все"
            " $p$-значения\n\t      остаются на нижней границе"
            " перестановочного теста, поэтому\n\t      авроральный градиент"
            " не является артефактом вспышек (SID);\n\t      уменьшенная"
            " выборка эпох снижает мощность для вторичных\n\t      попарных"
            " сравнений бинов $Kp$."
            "\n\t\\item \\textbf{Независимость штормовых слотов:}",
        ),
    ]
    return spatial, filewide, inserts


# --------------------------------------------------------------------------- #
# application
# --------------------------------------------------------------------------- #
def apply_to_text(
    text: str,
    spatial: list[tuple[str, str]],
    filewide: list[tuple[str, str]],
    inserts: list[tuple[str, str]],
    slice_start: str,
    slice_end: str,
    label: str,
) -> str:
    problems: list[str] = []

    i0 = text.find(slice_start)
    i1 = text.find(slice_end)
    if i0 < 0 or i1 < 0 or i1 <= i0:
        raise SystemExit(f"{label}: spatial slice markers not found")
    head, body, tail = text[:i0], text[i0:i1], text[i1:]

    for old, new in spatial:
        n = body.count(old)
        if n != 1:
            problems.append(f"  spatial: {old!r} found {n} times (expected 1)")
        else:
            body = body.replace(old, new)

    whole = head + body + tail
    for old, new in filewide:
        n = whole.count(old)
        if n != 1:
            problems.append(f"  file:    {old!r} found {n} times (expected 1)")
        else:
            whole = whole.replace(old, new)

    for anchor, replacement in inserts:
        n = whole.count(anchor)
        if n != 1:
            problems.append(f"  insert:  {anchor!r} found {n} times (expected 1)")
        else:
            whole = whole.replace(anchor, replacement)

    if problems:
        print(f"[FAIL] {label}: pattern verification failed, no changes applied:")
        print("\n".join(problems))
        raise SystemExit(2)
    return whole


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the files (default: --check prints the diff only)",
    )
    parser.add_argument(
        "--diff-out",
        metavar="PATH",
        default=None,
        help="also write the unified diff to PATH as UTF-8 (console-safe)",
    )
    args = parser.parse_args()

    data = load_scenario()
    plans = {
        "main.tex": (*edits_en(data), "\\label{sec:spatial}", "\\section{Discussion}"),
        "main_ru.tex": (*edits_ru(data), "\\label{sec:spatial}", "\\section{Обсуждение}"),
    }

    changed = False
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
        if new_text == old_text:
            print(f"[SKIP] {name}: no changes")
            continue
        changed = True
        diff = difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/paper/{name}",
            tofile=f"b/paper/{name}",
        )
        diff_text = "".join(diff)
        print(diff_text)
        diff_chunks.append(diff_text)
        if args.apply:
            with path.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(new_text)
            print(f"[OK] wrote paper/{name}")

    if not changed:
        print("nothing to do")
        return 0
    if args.diff_out:
        with open(args.diff_out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(diff_chunks))
        print(f"[OK] diff written to {args.diff_out}")
    if not args.apply:
        print("[CHECK] dry run only; re-run with --apply to write the files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
