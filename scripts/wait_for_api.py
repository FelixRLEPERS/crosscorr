#!/usr/bin/env python
"""Poll the WSPR API until it responds, then optionally chain a command.

The WSPR live API (wspr.live / db1.wspr.live) is unreachable from some
regions without a VPN (see AGENTS.md, "Known system limitations"). This
script polls it in the background so the operator does not have to watch
the screen.

Usage:
    python scripts/wait_for_api.py
    python scripts/wait_for_api.py --interval 60 --timeout 7200
    python scripts/wait_for_api.py --run spatial

On HTTP 200 it prints "API is back!" and exits 0. With --run it then
executes the chained analysis command (Phase 2 --apply) in the same
process family, so the whole wait-and-run happens unattended.

All parameters are CLI flags; nothing is hardcoded (AGENTS.md rule).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.parse
import urllib.request

DEFAULT_URL = "http://db1.wspr.live/"
PROBE_QUERY = "SELECT 1"
RUN_COMMANDS = {
    # Full spatial Phase 2 with flare control (default flags -> --exclude-flares).
    "spatial": [
        sys.executable,
        "scripts/spatial_analysis.py",
        "--source",
        "api",
        "--skip-crosscheck",
        "--apply",
    ],
}


def probe(url: str, timeout: float) -> bool:
    """Return True when the API answers HTTP 200 for a trivial SELECT 1."""
    separator = "&" if "?" in url else "?"
    full = (
        url + separator + urllib.parse.urlencode({"query": PROBE_QUERY, "default_format": "JSON"})
    )
    try:
        with urllib.request.urlopen(full, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--interval", type=float, default=60.0, help="seconds between probes")
    parser.add_argument(
        "--timeout", type=float, default=0.0, help="give up after N seconds (0 = never)"
    )
    parser.add_argument(
        "--request-timeout", type=float, default=25.0, help="per-request timeout, seconds"
    )
    parser.add_argument(
        "--run",
        choices=sorted(RUN_COMMANDS),
        default=None,
        help="chain this analysis command after the API responds",
    )
    args = parser.parse_args()

    started = time.time()
    attempt = 0
    while True:
        attempt += 1
        if probe(args.url, args.request_timeout):
            print("API is back!", flush=True)
            break
        elapsed = time.time() - started
        if args.timeout and elapsed >= args.timeout:
            print(
                f"[FAIL] {args.url} unreachable after {elapsed:.0f}s "
                f"({attempt} attempts) — giving up",
                flush=True,
            )
            return 1
        print(
            f"[wait_for_api] attempt {attempt}: unreachable "
            f"(elapsed {elapsed:.0f}s), retry in {args.interval:.0f}s",
            flush=True,
        )
        time.sleep(args.interval)

    if args.run:
        cmd = RUN_COMMANDS[args.run]
        print(f"[wait_for_api] chaining: {' '.join(cmd)}", flush=True)
        return subprocess.call(cmd)

    return 0


if __name__ == "__main__":
    sys.exit(main())
