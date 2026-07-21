#!/usr/bin/env python3
"""Repaired one-time executor for Legacy Market Archive retry request 002."""
from __future__ import annotations

import run_user_supplied_legacy_market_archive_real_file_audit_once_v1 as base
import run_user_supplied_legacy_market_archive_real_file_audit_once_v1_1 as hotfix
import validate_legacy_market_real_file_audit_retry_002_approval_v1 as retry_gate

base.gate = retry_gate
base.REQUEST_ID = retry_gate.REQUEST_ID
base.YEARS = retry_gate.EXPECTED_YEARS
base.reference_build = hotfix.reference_build_with_root
base.SELF_TEST_PASS = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_RETRY_002_EXECUTOR_SELF_TEST_PASS"
base.EXECUTION_BLOCKED = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_RETRY_002_BLOCKED_BEFORE_SCIENTIFIC_RESULT"


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
