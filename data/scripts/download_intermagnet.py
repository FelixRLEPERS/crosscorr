"""
Загрузка магнитометрических данных INTERMAGNET (формат IAGA-2002).
Требуется аккаунт и API-ключ, либо ручное скачивание с https://intermagnet.org.

Скрипт — заготовка: подставьте путь к уже скачанному .min файлу
и/или реализуйте авторизацию.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "intermagnet"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def parse_iaga2002(path: Path) -> pd.DataFrame:
    """Парсит файл IAGA-2002 в DataFrame."""
    rows = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            date, time = parts[0], parts[1]
            ts = pd.Timestamp(f"{date} {time}", tz="UTC")
            try:
                x = float(parts[3])
                y = float(parts[4]) if len(parts) > 4 else float("nan")
                z = float(parts[5]) if len(parts) > 5 else float("nan")
            except ValueError:
                continue
            rows.append({"timestamp": ts, "X": x, "Y": y, "Z": z})
    return pd.DataFrame(rows)

def download_and_save_intermagnet(station: str, year: int, month: int) -> Path:
    """Скачать данные INTERMAGNET для станции и месяца.

    Примечание: INTERMAGNET требует ручной загрузки через веб-интерфейс.
    Эта функция — заглушка: создаёт пустой файл, чтобы не падать.
    Для реальной загрузки см. https://intermagnet.org
    """
    out_dir = Path("data/raw/intermagnet")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{station}_{year}_{month:02d}.min"
    # TODO: реальная загрузка через API
    out_path.touch()
    print(f"[STUB] {out_path}")
    return out_path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Путь к .min файлу IAGA-2002")
    parser.add_argument("--station", default="UNKNOWN")
    args = parser.parse_args()

    src = Path(args.file)
    if not src.exists():
        raise SystemExit(f"Файл не найден: {src}")

    df = parse_iaga2002(src)
    out = RAW_DIR / f"{args.station}_{src.stem}.csv"
    df.to_csv(out, index=False)
    print(f"[OK] {len(df)} строк -> {out}")


if __name__ == "__main__":
    main()