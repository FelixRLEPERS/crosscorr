import numpy as np
import pandas as pd
from crosscorr_lib.analysis.surrogate import fdr_bh

p = np.array([
    [0.0,   0.001, 0.5],
    [0.001, 0.0,   0.5],
    [0.5,   0.5,   0.0],
])
sig = fdr_bh(p, alpha=0.05)
cols = ['A', 'B', 'C']

pairs = []
for i in range(len(cols)):
    for j in range(i + 1, len(cols)):
        if sig[i, j]:
            pairs.append({
                "Detector1": cols[i],
                "Detector2": cols[j],
                "p_value": float(p[i, j]),
            })

df = pd.DataFrame(pairs)
print("Колонки:", list(df.columns))
print("Пар:", len(pairs))
assert "Detector1" in df.columns
assert "Detector2" in df.columns
assert "p_value" in df.columns
assert len(pairs) == 1
print("OK")