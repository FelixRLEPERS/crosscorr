"""
tau_regression.py — Paper II LSTID velocity regression.

Physical model:
    tau(d, f) = tau_0(f) + d / V_TID(f)

Units:
    d       [km]
    tau     [min]
    b(f)    [min/km]     slope of tau vs d
    V_TID   [m/s]        = 16.667 / b(f)   (since 1 km/min = 16.667 m/s)

Two regimes:
    Wave  (LSTID): b(f) significantly > 0, CI excludes 0
    Chem  (O/N2) : b(f) indistinguishable from 0, CI includes 0

STATUS: skeleton. Do NOT run on real data until Paper I is
journal-published.
"""

from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

WSPR_BANDS: dict[int, float] = {
    7: 7.040,
    10: 10.140,
    14: 14.097,
    18: 18.106,
    21: 21.096,
    28: 28.126,
}

KM_PER_MIN_TO_M_PER_S = 1000.0 / 60.0  # = 16.6667


@dataclass
class BandResult:
    band: int
    freq_mhz: float
    n_points: int
    slope_b: float
    slope_ci_lo: float
    slope_ci_hi: float
    intercept_a: float
    intercept_ci_lo: float
    intercept_ci_hi: float
    v_tid_ms: float
    v_tid_ci_lo: float
    v_tid_ci_hi: float
    wave_regime: bool
    r_squared: float


def bootstrap_regression(
    d: np.ndarray,
    tau: np.ndarray,
    n_bootstraps: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> BandResult:
    if len(d) != len(tau):
        raise ValueError("d and tau must have equal length")
    if len(d) < 10:
        raise ValueError(f"Too few points for regression: n={len(d)}")

    rng = np.random.default_rng(seed)
    n = len(d)

    slopes = np.empty(n_bootstraps)
    intercepts = np.empty(n_bootstraps)

    for i in range(n_bootstraps):
        idx = rng.integers(0, n, size=n)
        d_b, tau_b = d[idx], tau[idx]
        if np.ptp(d_b) == 0:
            slopes[i] = np.nan
            intercepts[i] = np.nan
            continue
        s, a, *_ = stats.linregress(d_b, tau_b)
        slopes[i] = s
        intercepts[i] = a

    alpha = (1.0 - ci) / 2.0
    slope_lo, slope_hi = np.nanpercentile(slopes, [alpha * 100, (1 - alpha) * 100])
    int_lo, int_hi = np.nanpercentile(intercepts, [alpha * 100, (1 - alpha) * 100])

    b, a, r, p, se = stats.linregress(d, tau)

    wave_regime = slope_lo > 0.0

    if wave_regime and b > 0:
        v_tid = KM_PER_MIN_TO_M_PER_S / b
        v_lo = KM_PER_MIN_TO_M_PER_S / slope_hi
        v_hi = KM_PER_MIN_TO_M_PER_S / slope_lo
    else:
        v_tid = np.nan
        v_lo = np.nan
        v_hi = np.nan

    return BandResult(
        band=-1, freq_mhz=np.nan, n_points=n,
        slope_b=b, slope_ci_lo=slope_lo, slope_ci_hi=slope_hi,
        intercept_a=a, intercept_ci_lo=int_lo, intercept_ci_hi=int_hi,
        v_tid_ms=v_tid, v_tid_ci_lo=v_lo, v_tid_ci_hi=v_hi,
        wave_regime=wave_regime, r_squared=r ** 2,
    )


def _synthesize_mock(band: int, n: int = 60, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    d = rng.uniform(500.0, 3000.0, size=n)
    v_tid_ms = 350.0
    b_true = KM_PER_MIN_TO_M_PER_S / v_tid_ms
    tau_0 = 15.0
    noise = rng.normal(0.0, 1.5, size=n)
    tau = tau_0 + b_true * d + noise
    return d, tau


def _synthesize_mock_chem(band: int, n: int = 60, seed: int = 1) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    d = rng.uniform(500.0, 3000.0, size=n)
    tau = 15.0 + rng.normal(0.0, 3.0, size=n)
    return d, tau


def analyze_all_bands(
    load_real: bool = False,
    data_dir: Path | None = None,
) -> pd.DataFrame:
    if data_dir is None:
        data_dir = Path(".")
    rows: list[BandResult] = []

    for band, freq in WSPR_BANDS.items():
        if load_real:
            raise NotImplementedError(
                "Real-data path not yet implemented. "
                "Requires tau(d,f) cube from Paper II pipeline."
            )
        else:
            if band == 7:
                d, tau = _synthesize_mock(band)
            elif band == 14:
                d, tau = _synthesize_mock_chem(band)
            else:
                d, tau = _synthesize_mock(band, seed=band)

        res = bootstrap_regression(d, tau, n_bootstraps=1000)
        res.band = band
        res.freq_mhz = freq
        rows.append(res)

    return pd.DataFrame([asdict(r) for r in rows])


def plot_tau_vs_d(
    per_band_points: dict[int, tuple[np.ndarray, np.ndarray]],
    per_band_results: dict[int, BandResult],
    out_path: Path,
) -> None:
    import matplotlib.pyplot as plt

    bands = sorted(per_band_points.keys())
    fig, axes = plt.subplots(1, len(bands), figsize=(4 * len(bands), 4), sharey=True)
    if len(bands) == 1:
        axes = [axes]

    for ax, band in zip(axes, bands, strict=False):
        d, tau = per_band_points[band]
        r = per_band_results[band]
        ax.scatter(d, tau, s=12, alpha=0.6, label="data")

        d_grid = np.linspace(d.min(), d.max(), 100)
        tau_fit = r.intercept_a + r.slope_b * d_grid
        ax.plot(d_grid, tau_fit, color="C1", label="fit")

        ax.fill_between(
            d_grid,
            r.intercept_ci_lo + r.slope_ci_lo * d_grid,
            r.intercept_ci_hi + r.slope_ci_hi * d_grid,
            color="C1", alpha=0.15, label="95% CI (approx)",
        )

        regime = "WAVE" if r.wave_regime else "CHEM"
        v_txt = f"{r.v_tid_ms:.0f} m/s" if not np.isnan(r.v_tid_ms) else "n/a"
        ax.set_title(f"{band} m / {r.freq_mhz:.2f} MHz - {regime}\nV_TID = {v_txt}")
        ax.set_xlabel("d [km]")
        ax.grid(alpha=0.3)

    axes[0].set_ylabel("tau [min]")
    axes[-1].legend(loc="best", fontsize=8)
    fig.suptitle("Paper II skeleton: tau(d) regression per WSPR band")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    print("[tau_regression] skeleton run on mock data")
    df = analyze_all_bands(load_real=False)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    print("\n--- Regression results per band ---")
    print(df[[
        "band", "freq_mhz", "n_points",
        "slope_b", "slope_ci_lo", "slope_ci_hi",
        "intercept_a", "v_tid_ms", "v_tid_ci_lo", "v_tid_ci_hi",
        "wave_regime", "r_squared",
    ]].to_string(index=False))

    row40 = df.loc[df["band"] == 7].iloc[0]
    row20 = df.loc[df["band"] == 14].iloc[0]
    print("\n--- Sanity check ---")
    print(f"40 m: wave_regime={row40.wave_regime}, V_TID={row40.v_tid_ms:.1f} m/s (expected ~ 350)")
    print(f"20 m: wave_regime={row20.wave_regime}, V_TID={row20.v_tid_ms} (expected NaN -> chemical regime)")

    out_csv = Path("results_tau_regression.csv")
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")

    mock_points = {
        7:  _synthesize_mock(7),
        14: _synthesize_mock_chem(14),
    }
    mock_results = {
        7:  bootstrap_regression(*mock_points[7]),
        14: bootstrap_regression(*mock_points[14]),
    }
    mock_results[7].band, mock_results[7].freq_mhz = 7, 7.040
    mock_results[14].band, mock_results[14].freq_mhz = 14, 14.097
    plot_tau_vs_d(mock_points, mock_results, Path("tau_vs_d_by_band.png"))
    print("Saved: tau_vs_d_by_band.png")


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main()
