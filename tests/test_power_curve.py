"""
Тесты power_curve.py (docs/roadmap.md, шаг 1).

Модуль был покрыт на 35%: не исполнялись measure_point/power_curve/
power_curve_by_n, сериализация, график и CLI. Здесь проверяются механика
кривой мощности и инфраструктура вывода, а не статистическая мощность,
поэтому все прогоны берутся минимальными (n <= 300, n_surrogates <= 15),
чтобы тесты оставались быстрыми.
"""

import json
import runpy
import sys
from pathlib import Path

import numpy as np
import pytest

import crosscorr_lib.analysis.benchmark_utils as benchmark_utils
import crosscorr_lib.analysis.power_curve as power_curve_module
from crosscorr_lib.analysis.power_curve import (
    PowerPoint,
    main,
    make_couplings,
    measure_point,
    parse_args,
    plot_curves,
    power_curve,
    power_curve_by_n,
    print_table,
    save_csv,
    save_json,
)

# Маленькие параметры для быстрых прогонов benchmark().
FAST = {"n": 250, "true_lag": 2, "max_lag": 4, "n_surrogates": 10}


def _point(coupling: float = 0.5, n: int = 300) -> PowerPoint:
    """PowerPoint-заглушка для тестов сериализации/вывода/графика."""
    return PowerPoint(
        coupling=coupling,
        n_seeds=4,
        n=n,
        true_lag=6,
        ar=0.85,
        max_lag=24,
        null_model="time_shift",
        n_surrogates=200,
        power=0.5,
        lag_median=6.0,
        lag_iqr=1.0,
        rho_median=0.3,
        p_median=0.04,
        p_10=0.01,
        p_90=0.09,
        n_hits=2,
        elapsed_s=0.01,
    )


# ------------------------------------------------------------------ #
#                      measure_point                                  #
# ------------------------------------------------------------------ #


def test_measure_point_returns_consistent_summary():
    """Сводка по точке согласована сама с собой."""
    pt = measure_point(coupling=0.8, n_seeds=2, base_seed=7, verbose=False, **FAST)

    assert isinstance(pt, PowerPoint)
    assert pt.coupling == pytest.approx(0.8)
    assert pt.n_seeds == 2
    assert pt.n == FAST["n"]
    assert pt.true_lag == FAST["true_lag"]
    assert pt.max_lag == FAST["max_lag"]
    assert pt.n_surrogates == FAST["n_surrogates"]
    assert pt.null_model == "time_shift"

    assert 0.0 <= pt.power <= 1.0
    # power = среднее по булевым hits, n_hits = их сумма
    assert pt.n_hits == int(round(pt.power * pt.n_seeds))
    assert 0.0 <= pt.p_10 <= pt.p_median <= pt.p_90 <= 1.0
    assert pt.lag_iqr >= 0.0
    assert pt.elapsed_s >= 0.0


def test_measure_point_is_reproducible():
    """Один и тот же base_seed -> идентичная статистика."""
    a = measure_point(coupling=0.5, n_seeds=2, base_seed=3, verbose=False, **FAST)
    b = measure_point(coupling=0.5, n_seeds=2, base_seed=3, verbose=False, **FAST)

    assert a.power == b.power
    assert a.n_hits == b.n_hits
    assert a.p_median == b.p_median
    assert a.lag_median == b.lag_median
    assert a.rho_median == b.rho_median


def test_measure_point_verbose_prints_progress(capsys):
    """verbose=True печатает строку прогресса, verbose=False — молчит."""
    measure_point(coupling=0.4, n_seeds=1, verbose=True, **FAST)
    out = capsys.readouterr().out
    assert "power=" in out
    assert "lag_med=" in out

    measure_point(coupling=0.4, n_seeds=1, verbose=False, **FAST)
    assert capsys.readouterr().out == ""


# ------------------------------------------------------------------ #
#      регрессии исправленных багов (отчет сессии 2026-10-27)        #
# ------------------------------------------------------------------ #


def test_benchmark_passes_null_model_to_surrogate(monkeypatch):
    """FIX: null_model_name пробрасывается в max_lag_surrogate_pvalue."""
    captured: dict = {}

    def fake_max_lag(x, y, **kwargs):
        captured.update(kwargs)
        return 0.5, 0.01, 6

    monkeypatch.setattr(benchmark_utils, "max_lag_surrogate_pvalue", fake_max_lag)

    r = benchmark_utils.benchmark(n=64, true_lag=2, null_model_name="time_shift", seed=1)

    assert captured["surrogate_method"] == "time_shift"
    assert r["surrogate_method"] == "time_shift"


def test_benchmark_normalizes_unknown_null_model(monkeypatch):
    """Неизвестная модель ("block" из CLI) трактуется как phase — и так записывается."""
    captured: dict = {}

    def fake_max_lag(x, y, **kwargs):
        captured.update(kwargs)
        return 0.5, 0.01, 6

    monkeypatch.setattr(benchmark_utils, "max_lag_surrogate_pvalue", fake_max_lag)

    r = benchmark_utils.benchmark(n=64, true_lag=2, null_model_name="block", seed=1)

    assert captured["surrogate_method"] == "phase"
    assert r["surrogate_method"] == "phase"


def test_measure_point_forwards_ar_and_records_effective_model(monkeypatch):
    """FIX: ar уходит в benchmark; null_model = фактически использованная модель."""
    captured: dict = {}

    def fake_benchmark(**kwargs):
        captured.update(kwargs)
        return {
            "hit": True,
            "detected_lag": 6,
            "rho_max": 0.5,
            "p_value": 0.01,
            "surrogate_method": "phase",
        }

    monkeypatch.setattr(power_curve_module, "benchmark", fake_benchmark)

    pt = measure_point(
        coupling=0.3,
        n_seeds=3,
        ar=0.42,
        null_model_name="block",
        verbose=False,
        **FAST,
    )

    assert captured["ar"] == 0.42
    assert captured["null_model_name"] == "block"
    assert pt.ar == 0.42
    assert pt.null_model == "phase"  # запрошен "block", фактически phase
    assert pt.power == 1.0
    assert pt.n_hits == 3


# ------------------------------------------------------------------ #
#                  power_curve / power_curve_by_n                     #
# ------------------------------------------------------------------ #


def test_power_curve_one_point_per_coupling():
    """Количество точек кривой = количеству coupling, порядок сохраняется."""
    couplings = np.array([0.2, 0.5])
    points = power_curve(couplings=couplings, n_seeds=1, verbose=False, **FAST)

    assert len(points) == 2
    assert [p.coupling for p in points] == [0.2, 0.5]
    assert all(isinstance(p, PowerPoint) for p in points)


def test_power_curve_accepts_random_couplings(rng):
    """Кривая строится и по случайному массиву coupling (фикстура rng)."""
    couplings = rng.uniform(0.1, 0.9, size=2)
    points = power_curve(couplings=couplings, n_seeds=1, verbose=False, **FAST)

    assert len(points) == 2
    np.testing.assert_allclose([p.coupling for p in points], couplings)


def test_power_curve_verbose_prints_header(capsys):
    """verbose=True печатает заголовок прогона."""
    power_curve(couplings=np.array([0.3]), n_seeds=1, verbose=True, **FAST)
    out = capsys.readouterr().out
    assert "=== Power curve" in out
    assert f"n={FAST['n']}" in out


def test_power_curve_by_n_covers_grid():
    """Прогон по сетке n дает len(n_values) * len(couplings) точек."""
    points = power_curve_by_n(
        n_values=[200, 250],
        couplings=np.array([0.4]),
        n_seeds=1,
        true_lag=2,
        max_lag=4,
        n_surrogates=8,
        verbose=False,
    )

    assert len(points) == 2
    assert sorted({p.n for p in points}) == [200, 250]
    assert all(p.coupling == pytest.approx(0.4) for p in points)


def test_power_curve_by_n_verbose_prints(capsys):
    """verbose=True печатает разделитель по n."""
    power_curve_by_n(
        n_values=[200],
        couplings=np.array([0.4]),
        n_seeds=1,
        true_lag=2,
        max_lag=4,
        n_surrogates=8,
        verbose=True,
    )
    assert "--- n = 200 ---" in capsys.readouterr().out


# ------------------------------------------------------------------ #
#                       сериализация и вывод                          #
# ------------------------------------------------------------------ #


def test_save_csv_and_json_roundtrip(tmp_path, capsys):
    points = [_point(coupling=0.1), _point(coupling=0.2, n=500)]
    csv_path = tmp_path / "nested" / "curve.csv"
    json_path = tmp_path / "nested" / "curve.json"

    save_csv(points, csv_path)
    save_json(points, json_path)

    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # header + 2 строки
    assert lines[0].startswith("coupling,n_seeds,n,true_lag")
    assert "0.1" in lines[1] and "0.2" in lines[2]

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert [d["coupling"] for d in data] == [0.1, 0.2]
    assert data[0]["null_model"] == "time_shift"
    assert data[1]["n"] == 500

    out = capsys.readouterr().out
    assert "CSV сохранён" in out
    assert "JSON сохранён" in out


def test_save_empty_list_writes_nothing(tmp_path):
    """Пустой список точек -> ранний выход без создания файлов."""
    csv_path = tmp_path / "empty.csv"
    json_path = tmp_path / "empty.json"

    save_csv([], csv_path)
    save_json([], json_path)

    assert not csv_path.exists()
    assert not json_path.exists()


def test_print_table_formats_rows(capsys):
    print_table([_point(coupling=0.1), _point(coupling=0.3)])

    out = capsys.readouterr().out
    assert "coupling" in out
    assert "lag_med" in out
    assert "p_10" in out
    assert "0.100" in out and "0.300" in out
    assert "2/4" in out  # n_hits/n_seeds


def test_plot_curves_writes_png(tmp_path):
    """График строится по точкам с разными n (группировка по n)."""
    points = [
        _point(coupling=0.1, n=300),
        _point(coupling=0.2, n=300),
        _point(coupling=0.1, n=600),
    ]
    path = tmp_path / "fig" / "curves.png"

    plot_curves(points, path)

    assert path.exists()
    assert path.stat().st_size > 0


# ------------------------------------------------------------------ #
#                       CLI-утилиты                                   #
# ------------------------------------------------------------------ #


def test_make_couplings_default_grid():
    c = make_couplings(None)
    assert len(c) == 15
    assert c[0] == pytest.approx(0.02)
    assert c[-1] == pytest.approx(0.30)


def test_make_couplings_single_value():
    c = make_couplings([0.1])
    assert len(c) == 10
    assert c[0] == pytest.approx(0.02)
    assert c[-1] == pytest.approx(0.1)


def test_make_couplings_min_max_count():
    c = make_couplings([0.1, 0.2, 5])
    assert len(c) == 5
    assert c[0] == pytest.approx(0.1)
    assert c[-1] == pytest.approx(0.2)


def test_make_couplings_explicit_list():
    c = make_couplings([0.05, 0.15])
    np.testing.assert_allclose(c, [0.05, 0.15])


def test_parse_args_defaults():
    args = parse_args([])
    assert args.seeds == 30
    assert args.n == 4000
    assert args.couplings is None
    assert args.null_model == "time_shift"
    assert args.plot is False
    assert args.by_n is False


def test_parse_args_rejects_unknown_null_model(capsys):
    with pytest.raises(SystemExit):
        parse_args(["--null", "bogus"])
    assert "invalid choice" in capsys.readouterr().err


# ------------------------------------------------------------------ #
#                              main()                                 #
# ------------------------------------------------------------------ #


def test_main_single_curve_writes_outputs(tmp_path, capsys):
    out_dir = tmp_path / "out"
    rc = main(
        [
            "--couplings",
            "0.4",
            "0.8",
            "--seeds",
            "1",
            "--n",
            str(FAST["n"]),
            "--true-lag",
            str(FAST["true_lag"]),
            "--max-lag",
            str(FAST["max_lag"]),
            "--n-surrogates",
            str(FAST["n_surrogates"]),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert rc == 0
    assert (out_dir / f"power_curve_n{FAST['n']}.csv").exists()
    assert (out_dir / f"power_curve_n{FAST['n']}.json").exists()

    out = capsys.readouterr().out
    assert "CrossCorr 2.0" in out
    assert "0.400" in out  # строки таблицы
    assert "CSV сохранён" in out


def test_main_by_n_with_plot(tmp_path, capsys):
    """Ветка --by-n + --plot: сетка n, CSV/JSON/PNG в out-dir."""
    out_dir = tmp_path / "out"
    rc = main(
        [
            "--by-n",
            "--n-list",
            "200",
            "250",
            "--couplings",
            "0.5",
            "--seeds",
            "1",
            "--true-lag",
            str(FAST["true_lag"]),
            "--max-lag",
            str(FAST["max_lag"]),
            "--n-surrogates",
            "8",
            "--out-dir",
            str(out_dir),
            "--plot",
        ]
    )

    assert rc == 0
    assert (out_dir / "power_curve_by_n.csv").exists()
    assert (out_dir / "power_curve_by_n.json").exists()
    png = out_dir / "power_curve_by_n.png"
    assert png.exists() and png.stat().st_size > 0

    out = capsys.readouterr().out
    assert "График сохранён" in out


def test_script_entry_point_runs(tmp_path, monkeypatch, capsys):
    """Запуск файла как скрипта (guard ``__main__``) доходит до main()."""
    module = Path(__file__).resolve().parents[1] / "crosscorr_lib" / "analysis" / "power_curve.py"
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "power_curve.py",
            "--couplings",
            "0.4",
            "0.6",
            "--seeds",
            "1",
            "--n",
            str(FAST["n"]),
            "--true-lag",
            str(FAST["true_lag"]),
            "--max-lag",
            str(FAST["max_lag"]),
            "--n-surrogates",
            "8",
            "--out-dir",
            str(out_dir),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(module), run_name="__main__")

    assert exc.value.code == 0
    assert (out_dir / f"power_curve_n{FAST['n']}.csv").exists()
    assert "CrossCorr 2.0" in capsys.readouterr().out


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
