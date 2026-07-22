#!/usr/bin/env python3
"""Approved repaired executor for Historical Silver root-cause retry request 002."""
from __future__ import annotations

import run_historical_silver_missing_team_features_root_cause_once_v1 as base
import validate_historical_silver_missing_team_features_retry_002_approval_v1 as retry_gate

base.gate = retry_gate
base.REQUEST_ID = retry_gate.REQUEST_ID
base.SELF_TEST_PASS = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_RETRY_002_EXECUTOR_SELF_TEST_PASS"
base.EXECUTION_BLOCKED = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_RETRY_002_BLOCKED_BEFORE_RESULT"


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
