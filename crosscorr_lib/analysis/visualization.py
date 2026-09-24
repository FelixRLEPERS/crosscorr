"""
Визуализация результатов CrossCorr.

Три фигуры для статьи:
1. Карта детекторов (lat/lon scatter + границы России).
2. Scatter distance vs correlation + OLS regression.
3. Heatmap матрицы корреляций.

Все фигуры сохраняются в results/figures/ как PNG (300 dpi) + SVG (вектор).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIG_DIR = ROOT / "results" / "figures"

# Стиль для публикации
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# Упрощённые границы России (внешний контур).
# Точки — приблизительные, для визуального ориентира.
RUSSIA_OUTLINE = [
    (28.0, 60.0), (30.0, 65.0), (30.0, 70.0), (45.0, 68.0),
    (60.0, 70.0), (80.0, 73.0), (100.0, 76.0), (120.0, 74.0),
    (140.0, 72.0), (160.0, 70.0), (170.0, 68.0), (180.0, 66.0),
    (180.0, 62.0), (160.0, 60.0), (140.0, 50.0), (130.0, 44.0),
    (120.0, 42.0), (100.0, 50.0), (80.0, 50.0), (60.0, 52.0),
    (40.0, 48.0), (30.0, 52.0), (28.0, 60.0),
]


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def plot_detectors_map(
    detectors: pd.DataFrame,
    corr_pairs: pd.DataFrame,
    output_dir: Path = DEFAULT_FIG_DIR,
) -> Path:
    """
    Карта России с детекторами.

    Размер точки = число значимых пар, в которых участвует детектор.
    Цвет = доля значимых пар от общего числа.

    Args:
        detectors: DataFrame с колонками detector_id, lat, lon.
        corr_pairs: DataFrame с колонками detector_1, detector_2, significant.
        output_dir: папка для сохранения.

    Returns:
        Путь к сохранённому PNG.
    """
    _ensure_dir(output_dir)

    # Подсчёт значимых пар на детектор
    if "significant" in corr_pairs.columns:
        sig_pairs = corr_pairs[corr_pairs["significant"]]
        counts = pd.concat([
            sig_pairs["detector_1"].value_counts(),
            sig_pairs["detector_2"].value_counts(),
        ]).groupby(level=0).sum()
    else:
        counts = pd.Series(0, index=detectors["detector_id"])

    detectors = detectors.copy()
    detectors["n_significant"] = detectors["detector_id"].map(counts).fillna(0)

    fig, ax = plt.subplots(figsize=(10, 5))

    # Границы России (упрощённые)
    rx, ry = zip(*RUSSIA_OUTLINE, strict=False)
    ax.plot(rx, ry, color="0.7", linewidth=1.0, zorder=1)

    # Детекторы
    sizes = 50 + 40 * detectors["n_significant"]
    sc = ax.scatter(
        detectors["lon"], detectors["lat"],
        s=sizes, c=detectors["n_significant"],
        cmap="viridis", edgecolor="black", linewidth=0.8,
        alpha=0.85, zorder=3,
    )

    # Подписи
    for _, row in detectors.iterrows():
        ax.annotate(
            row["detector_id"].replace("D_", ""),
            (row["lon"], row["lat"]),
            xytext=(5, 5), textcoords="offset points",
            fontsize=8, color="0.2",
        )

    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title("CrossCorr detectors across Russia")
    ax.set_xlim(20, 185)
    ax.set_ylim(40, 80)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal", adjustable="box")

    cbar = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("Number of significant pairs")

    out_png = output_dir / "detectors_map.png"
    out_svg = output_dir / "detectors_map.svg"
    fig.savefig(out_png)
    fig.savefig(out_svg)
    plt.close(fig)
    print(f"[OK] {out_png}")
    return out_png


def plot_distance_correlation(
    distance_df: pd.DataFrame,
    model: dict,
    output_dir: Path = DEFAULT_FIG_DIR,
) -> Path:
    """
    Scatter plot: correlation vs distance, с линией OLS-регрессии.

    Args:
        distance_df: DataFrame с колонками distance_km, correlation.
        model: dict с ключами slope, intercept, r_squared.
        output_dir: папка для сохранения.

    Returns:
        Путь к сохранённому PNG.
    """
    _ensure_dir(output_dir)

    fig, ax = plt.subplots(figsize=(7, 5))

    x = distance_df["distance_km"].values
    y = distance_df["correlation"].values

    ax.scatter(x, y, s=50, c="steelblue", edgecolor="black",
               linewidth=0.8, alpha=0.8, zorder=3)

    # Линия регрессии
    if not np.isnan(model.get("slope", np.nan)):
        x_line = np.linspace(x.min(), x.max(), 100)
        y_line = model["slope"] * x_line + model["intercept"]
        ax.plot(x_line, y_line, color="crimson", linewidth=1.5, zorder=2)

        # Аннотация с коэффициентами
        text = (
            f"$r = {model['slope']:.4f}\\cdot d + {model['intercept']:.3f}$\n"
            f"$R^2 = {model['r_squared']:.3f}$\n"
            f"$n = {model['n']}$"
        )
        ax.text(
            0.02, 0.98, text,
            transform=ax.transAxes,
            verticalalignment="top",
            fontsize=10,
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
        )

    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Spearman correlation")
    ax.set_title("Correlation vs distance between detectors")
    ax.grid(True, alpha=0.3, linestyle="--")

    out_png = output_dir / "distance_correlation.png"
    out_svg = output_dir / "distance_correlation.svg"
    fig.savefig(out_png)
    fig.savefig(out_svg)
    plt.close(fig)
    print(f"[OK] {out_png}")
    return out_png


def plot_correlation_heatmap(
    corr_pairs: pd.DataFrame,
    detectors: pd.DataFrame,
    output_dir: Path = DEFAULT_FIG_DIR,
) -> Path:
    """
    Heatmap матрицы корреляций между детекторами.

    Args:
        corr_pairs: DataFrame с колонками detector_1, detector_2, correlation, significant.
        detectors: DataFrame с detector_id (для порядка осей).
        output_dir: папка для сохранения.

    Returns:
        Путь к сохранённому PNG.
    """
    _ensure_dir(output_dir)

    ids = sorted(detectors["detector_id"].unique().tolist())
    n = len(ids)
    idx = {d: i for i, d in enumerate(ids)}

    mat = np.full((n, n), np.nan)
    np.fill_diagonal(mat, 1.0)

    for _, row in corr_pairs.iterrows():
        i = idx.get(row["detector_1"])
        j = idx.get(row["detector_2"])
        if i is None or j is None:
            continue
        mat[i, j] = row["correlation"]
        mat[j, i] = row["correlation"]

    fig, ax = plt.subplots(figsize=(7, 6))

    im = ax.imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    short_ids = [s.replace("D_", "") for s in ids]
    ax.set_xticklabels(short_ids, rotation=45, ha="right")
    ax.set_yticklabels(short_ids)

    # Аннотации со значениями
    for i in range(n):
        for j in range(n):
            if not np.isnan(mat[i, j]):
                color = "white" if abs(mat[i, j]) > 0.6 else "black"
                ax.text(j, i, f"{mat[i, j]:.2f}",
                        ha="center", va="center",
                        fontsize=7, color=color)

    ax.set_title("Correlation matrix between detectors")
    fig.colorbar(im, ax=ax, shrink=0.85, label="Spearman correlation")

    out_png = output_dir / "correlation_heatmap.png"
    out_svg = output_dir / "correlation_heatmap.svg"
    fig.savefig(out_png)
    fig.savefig(out_svg)
    plt.close(fig)
    print(f"[OK] {out_png}")
    return out_png


def main() -> None:
    """CLI: сгенерировать все три фигуры."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corr-pairs", type=Path,
        default=ROOT / "results" / "cross_correlation_pairs.csv",
    )
    parser.add_argument(
        "--detectors", type=Path,
        default=ROOT / "data" / "detectors.csv",
    )
    parser.add_argument(
        "--distance", type=Path,
        default=ROOT / "results" / "distance_analysis.csv",
    )
    parser.add_argument(
        "--out", type=Path,
        default=DEFAULT_FIG_DIR,
    )
    args = parser.parse_args()

    if not args.corr_pairs.exists():
        raise SystemExit(f"[ERR] Не найден {args.corr_pairs}. Запустите cross_correlation.py сначала.")
    if not args.detectors.exists():
        raise SystemExit(f"[ERR] Не найден {args.detectors}. Запустите make_synthetic_unified.py.")

    corr_pairs = pd.read_csv(args.corr_pairs)
    detectors = pd.read_csv(args.detectors)

    # 1. Карта
    plot_detectors_map(detectors, corr_pairs, args.out)

    # 2. Heatmap
    plot_correlation_heatmap(corr_pairs, detectors, args.out)

    # 3. Distance scatter (если есть)
    if args.distance.exists():
        from crosscorr_lib.analysis.distance_analysis import fit_distance_model

        distance_df = pd.read_csv(args.distance)
        # Оставляем только валидные пары
        distance_df = distance_df.dropna(subset=["distance_km", "correlation"])
        model = fit_distance_model(distance_df)
        plot_distance_correlation(distance_df, model, args.out)
    else:
        print(f"[WARN] {args.distance} не найден. Distance scatter пропущен.")
        print("      Запустите: python -m crosscorr_lib.analysis.distance_analysis")

    print("\n[DONE] Все фигуры в", args.out)


if __name__ == "__main__":
    main()
