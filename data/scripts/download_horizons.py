"""
Загрузка эфемерид планет через JPL Horizons (astroquery).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from astroquery.jplhorizons import Horizons

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "horizons"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Коды планет в Horizons
PLANETS = {
    "mercury": "199",
    "venus": "299",
    "earth": "399",
    "mars": "499",
    "jupiter": "599",
    "saturn": "699",
}


def fetch_ephemeris(planet: str, start: str, stop: str, step: str = "1h") -> "object":
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

    out = RAW_DIR / f"horizons_{args.planet}_{args.start}_{args.stop}.csv"
    df.to_csv(out, index=False)
    print(f"[OK] {len(df)} строк -> {out}")


if __name__ == "__main__":
    main()