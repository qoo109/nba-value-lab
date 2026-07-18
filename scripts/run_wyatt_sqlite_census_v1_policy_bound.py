#!/usr/bin/env python3
"""Run the Wyatt SQLite census using the frozen input ceiling from policy.

This is a small policy adapter around `run_wyatt_sqlite_census_v1.py`. It does
not alter integrity, schema, coverage, privacy, or qualification gates.
"""

from __future__ import annotations

import json
from pathlib import Path

import run_wyatt_sqlite_census_v1 as runner

POLICY_PATH = Path("data/wyatt-sqlite-file-pilot-v1.json")
EXPECTED_MAXIMUM_SIZE_BYTES = 3_221_225_472


def apply_policy() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    contract = policy["input_contract"]
    maximum = int(contract["maximum_size_bytes"])
    if maximum != EXPECTED_MAXIMUM_SIZE_BYTES:
        raise RuntimeError("unexpected Wyatt SQLite maximum_size_bytes")
    if contract.get("maximum_size_basis") != "operational_safety_ceiling_only_not_a_research_promotion_gate":
        raise RuntimeError("missing operational ceiling boundary")
    runner.MAXIMUM_SIZE_BYTES = maximum


def main() -> int:
    apply_policy()
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
