#!/usr/bin/env python3
"""Run the exact no-price pilot manifest with the approved NBA browser profile.

This runner reuses ``nba_browser_headers_v1`` from the already validated official
participation layer. It fetches NBA Official LiveData schedule metadata only and
never reads an odds API key or calls a paid odds endpoint.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_timestamped_odds_pilot_manifest_v1 import run
from run_official_nba_participation_import import browser_fetch_json

REQUEST_PROFILE = "nba_browser_headers_v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    report = run(
        args.policy,
        args.gold,
        args.output_dir,
        fetcher=browser_fetch_json,
    )
    report["source"]["request_profile"] = REQUEST_PROFILE
    report["source"]["browser_profile_reused_from"] = (
        "scripts/run_official_nba_participation_import.py"
    )
    report["quality"]["access_control_bypass_used"] = False
    report["quality"]["bounded_official_retries"] = True
    (args.output_dir / "timestamped-odds-pilot-manifest-v1.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "formal_state": report["formal_state"],
        "coverage": report["coverage"],
        "source": report["source"],
    }, indent=2))


if __name__ == "__main__":
    main()
