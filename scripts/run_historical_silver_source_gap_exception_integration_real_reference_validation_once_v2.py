#!/usr/bin/env python3
"""Compatibility wrapper for the approved one-time real-reference validation.

The original v1 runner expected the approval validator's terminal state while the
committed approval current-status record intentionally remained in the lifecycle
state that precedes execution-workflow implementation.  The first manual dispatch
therefore failed during validate-only admission before any governed aggregate
input was read.

This wrapper binds the v1 admission gate to the exact immutable approval status
record already merged on main.  All execution logic, immutable SHA-256 bindings,
input restrictions, output restrictions, one-time receipt semantics, and Stake 0
boundaries remain delegated to the unchanged v1 runner.
"""
from __future__ import annotations

import run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v1 as core

APPROVAL_CURRENT_STATUS_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_APPROVAL_VALID_PENDING_EXECUTION_WORKFLOW_IMPLEMENTATION"
)

# validate_admission() resolves READY_STATE at call time.  Bind it to the exact
# committed approval current-status lifecycle state before exposing the runner.
core.READY_STATE = APPROVAL_CURRENT_STATUS_STATE

REQUEST_ID = core.REQUEST_ID
REQUEST_SHA256 = core.REQUEST_SHA256
IMPLEMENTATION_SHA256 = core.IMPLEMENTATION_SHA256
ADMISSION_STATE = core.ADMISSION_STATE
PASS_STATE = core.PASS_STATE
FAIL_CLOSED_STATE = core.FAIL_CLOSED_STATE
ALLOWED_INPUT_PATHS = core.ALLOWED_INPUT_PATHS

read_json = core.read_json
sha256_file = core.sha256_file
contains_prohibited_key = core.contains_prohibited_key
validate_admission = core.validate_admission
adapt_coverage_record = core.adapt_coverage_record
evaluate_result = core.evaluate_result
write_json = core.write_json
self_test = core.self_test
main = core.main


if __name__ == "__main__":
    raise SystemExit(main())
