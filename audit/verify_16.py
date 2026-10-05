import numpy as np
import pandas as pd
from crosscorr_lib.pairs import cross_correlation_pairs_with_max_stat

rng = np.random.default_rng(0)
wide = pd.DataFrame(rng.normal(size=(100, 3)), columns=["a", "b", "c"])

for label, kwargs in [
    ("B=0", {"B": 0}),
    ("seed=-1", {"seed": -1}),
]:
    try:
        df = cross_correlation_pairs_with_max_stat(
            wide, n_jobs=1, **kwargs,
        )
        print(f"{label}: no exception, rows =", len(df))
    except Exception as e:
        print(f"{label}: EXCEPTION {type(e).__name__}: {e}")
