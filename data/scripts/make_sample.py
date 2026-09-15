"""Создаёт маленький сэмпл унифицированной таблицы для тестов."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "processed" / "unified.parquet"
dst = ROOT / "samples" / "unified_sample.csv"
dst.parent.mkdir(parents=True, exist_ok=True)

if not src.exists():
    raise SystemExit("Сначала запустите unify_schema.py")

df = pd.read_parquet(src).head(500)
df.to_csv(dst, index=False)
print(f"[OK] {len(df)} строк -> {dst}")