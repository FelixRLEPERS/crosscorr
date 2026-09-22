import numpy as np
import pandas as pd
from code.analysis.surrogate import fdr_bh

# Имитация результатов FDR
p = np.array([
    [0.0,   0.001, 0.5],
    [0.001, 0.0,   0.5],
    [0.5,   0.5,   0.0],
])
sig = fdr_bh(p, alpha=0.05)
cols = ['A', 'B', 'C']

# Тот же код, что теперь должен быть в surrogate.main()
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
print(df)

assert "Detector1" in df.columns, "Нет колонки Detector1"
assert "Detector2" in df.columns, "Нет колонки Detector2"
assert "p_value" in df.columns, "Нет колонки p_value"
assert len(pairs) == 1, "Ожидалась одна значимая пара (A, B)"
print("OK")