# Legacy Market Archive real-file audit incident — Run 29804975869

日期：2026-07-21

## Result

Run `29804975869` reached the approved execution path but stopped before the scientific cross-source comparison.

Formal state:

```text
LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_EXECUTION_BLOCKED_BEFORE_SCIENTIFIC_RESULT
```

## Root cause

The temporary reference directory was not created before the executor attempted to write:

```text
reference/config-2019.json
```

This caused a `FileNotFoundError` during the first Historical Silver season configuration step.

## Completed before the failure

- Approval validation: 90 / 90 checks passed.
- Workflow event and main-branch binding passed.
- Candidate dataset download started successfully.
- The exact candidate identity check completed before reference reconstruction.
- No scientific comparison or frozen gate evaluation was produced.

## Output boundary

Artifact `8485141135` contained one aggregate JSON report only.

No candidate CSV, Historical Silver/Gold database, source archive, raw row, unmatched key, or game ID was uploaded. Opening/Closing, market backtest, CLV, EV, ROI, Drawdown, model retraining, betting edge, and non-zero Stake remain disabled.

## Request consumption

Request `LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001` recorded one execution attempt and must not be reused. A new explicitly approved retry request is required.

## Repair

The repair adds a compatibility entrypoint that creates the temporary reference root before calling the already-reviewed v1 executor:

```text
scripts/run_user_supplied_legacy_market_archive_real_file_audit_once_v1_1.py
```

The candidate identity, five-season reference scope, deterministic join, frozen scientific gates, aggregate-only output, and Stake 0 boundaries are unchanged.
