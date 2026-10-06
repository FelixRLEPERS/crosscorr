"""Группа E — покрытие load_unified (E7)."""

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.cross_correlation import load_unified


def test_load_unified_parses_timestamp_utc(tmp_path):
    """load_unified читает parquet и переводит timestamp_utc в UTC datetime."""
    path = tmp_path / "unified.parquet"
    df = pd.DataFrame({
        "timestamp_utc": [
            "2020-01-01T00:00:00Z",
            "2020-01-01T01:00:00Z",
        ],
        "detector_id": ["D_A", "D_B"],
        "residual": [1.0, 2.0],
    })
    df.to_parquet(path, index=False)

    out = load_unified(path)

    assert len(out) == 2
    assert pd.api.types.is_datetime64_any_dtype(out["timestamp_utc"])
    assert str(out["timestamp_utc"].dt.tz) == "UTC"
    assert list(out["detector_id"]) == ["D_A", "D_B"]
    np.testing.assert_allclose(out["residual"].values, [1.0, 2.0])
