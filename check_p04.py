"""Проверка P0-4: MFDFA long-format с обработкой q=0."""

import numpy as np
import pandas as pd

from crosscorr_lib.analysis.mfdfa import mfdfa_spectrum

# Два ряда разной длины — раньше это ломало pd.DataFrame(results)
x1 = np.random.default_rng(1).normal(size=500)
x2 = np.random.default_rng(2).normal(size=1500)

lag1, q1, dq1 = mfdfa_spectrum(x1)
lag2, q2, dq2 = mfdfa_spectrum(x2)

print(f"x1: len(lag)={len(lag1)}, len(q)={len(q1)}, dq.shape={dq1.shape}")
print(f"x2: len(lag)={len(lag2)}, len(q)={len(q2)}, dq.shape={dq2.shape}")
print(f"Масштабы разные? {len(lag1) != len(lag2)}")

# ВАЖНО: dq.shape[1] может быть меньше len(q),
# если библиотека исключила q=0.
q_cols_1 = dq1.shape[1]
q_cols_2 = dq2.shape[1]
print(f"Фактических q-колонок: x1={q_cols_1}, x2={q_cols_2}")
print(f"len(q) == dq.shape[1]? x1: {len(q1) == q_cols_1}, x2: {len(q2) == q_cols_2}")

# Long-format: одна строка на (detector, lag, q_index)
rows = []
for i, l in enumerate(lag1):
    for j in range(q_cols_1):
        rows.append({
            "detector": "D1",
            "lag": int(l),
            "q_index": int(j),
            "dq": float(dq1[i, j]),
        })
for i, l in enumerate(lag2):
    for j in range(q_cols_2):
        rows.append({
            "detector": "D2",
            "lag": int(l),
            "q_index": int(j),
            "dq": float(dq2[i, j]),
        })

df = pd.DataFrame(rows)
print(f"Всего строк: {len(df)}")
print(f"Колонки: {list(df.columns)}")
print(f"Ожидали: {len(lag1) * q_cols_1 + len(lag2) * q_cols_2}")
print()
print(df.head(8))

# Assertions
assert set(df.columns) == {"detector", "lag", "q_index", "dq"}, \
    f"Колонки не совпадают: {set(df.columns)}"
assert len(df) == len(lag1) * q_cols_1 + len(lag2) * q_cols_2, \
    "Число строк не совпадает"
assert df["dq"].notna().all(), "Есть NaN в dq"

print()
print("OK")