# Legacy Market Archive real-file audit retry request 002

Request ID:

```text
LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-002
```

Current state:

```text
AWAITING_EXPLICIT_USER_APPROVAL
```

## Reason

Request 001 produced run `29804975869`, which stopped before the scientific cross-source comparison because the temporary reference root did not exist before the first season configuration was written.

PR #111 fixed that deterministic path at merge commit:

```text
613ce3a6232780c486d899b02dd7a99e799b0a27
```

## Retry scope

The retry uses:

```text
scripts/run_user_supplied_legacy_market_archive_real_file_audit_once_v1_1.py
```

The only change is creating the temporary reference root before delegating to the reviewed v1 executor.

Unchanged:

- exact candidate file identity;
- five reference seasons;
- deterministic date/home/away matching;
- no fuzzy matching or manual identity overrides;
- score validation only;
- frozen scientific gates;
- one aggregate report only;
- formal Stake 0.

## Execution boundary

Request 002 may be executed only once, manually, from `main`, after explicit user approval.

It does not permit reusing request 001 or rerunning workflow run `29804975869`.

The run may use temporary storage for candidate and reference reconstruction, but must not upload raw candidate data, source archives, Historical Silver/Gold databases, raw rows, unmatched keys, game IDs, or row-level mismatch lists.

Opening/Closing classification, point-in-time market testing, CLV, EV, ROI, Drawdown, model retraining, betting-edge claims, and non-zero Stake remain disabled.
