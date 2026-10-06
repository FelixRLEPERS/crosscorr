"""
Загрузка эфемерид планет через JPL Horizons (astroquery).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from astroquery.jplhorizons import Horizons

if TYPE_CHECKING:
    from astropy.table import Table

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "horizons"

# Коды планет в Horizons
PLANETS = {
    "mercury": "199",
    "venus": "299",
    "earth": "399",
    "mars": "499",
    "jupiter": "599",
    "saturn": "699",
}


def fetch_ephemeris(
    planet: str, start: str, stop: str, step: str = "1h"
) -> Table:
    code = PLANETS[planet.lower()]
    obj = Horizons(id=code, location="@sun", epochs={"start": start, "stop": stop, "step": step})
    return obj.ephemerides()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--planet", required=True, choices=list(PLANETS))
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--stop", required=True, help="YYYY-MM-DD")
    parser.add_argument("--step", default="1h")
    args = parser.parse_args()

    table = fetch_ephemeris(args.planet, args.start, args.stop, args.step)
    df = table.to_pandas()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"horizons_{args.planet}_{args.start}_{args.stop}.csv"
    df.to_csv(out, index=False)
    # ВАЖНО: JPL Horizons пересчитывает положения планет при обновлении
    # DE-ядер, поэтому без сохранения исходного ответа позиция за прошлую
    # дату не воспроизводима (находка A28 / V2-36). Сохраняем рядом
    # метаданные запроса.
    meta = RAW_DIR / f"horizons_{args.planet}_{args.start}_{args.stop}.json"
    meta.write_text(
        json.dumps({
            "planet": args.planet,
            "horizons_id": PLANETS[args.planet.lower()],
            "start": args.start,
            "stop": args.stop,
            "step": args.step,
            "location": "@sun",
            "rows": int(len(df)),
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    (RAW_DIR / f"horizons_{args.planet}_{args.start}_{args.stop}.sha256").write_text(
        f"{digest}  {out.name}\n", encoding="utf-8"
    )
    print(f"[OK] {len(df)} строк -> {out} (sha256 записан)")


if __name__ == "__main__":
    main()
