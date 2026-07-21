# NBA Value Lab — Project Status

狀態核對日期：2026-07-21  
研究定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

```text
current work mode: OFFSEASON_DATA_CONSTRUCTION
live odds capture required now: false
legacy source role: ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
request 001: consumed by blocked pre-scientific execution
blocked workflow run: 29804975869
scientific result produced: false
reference-root repair merged: 613ce3a6232780c486d899b02dd7a99e799b0a27
retry request 002: AWAITING_EXPLICIT_USER_APPROVAL
retry execution enabled: false
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
formal stake: 0
```

## Next Unique Mainline

```text
LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_RETRY_REQUEST_002
AWAITING_EXPLICIT_USER_APPROVAL
```

## Blocked Run 29804975869

```text
request id: LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001
workflow run: 29804975869
job id: 88553587348
head SHA: caf3177194a1a503714c91214359afc125052669
artifact id: 8485141135
artifact digest: sha256:0fb59d1b3801eb5edba7bb4a124c7d64c5e7850df97b794e2a3309ecdc2a52c4
formal state: LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_EXECUTION_BLOCKED_BEFORE_SCIENTIFIC_RESULT
error: FileNotFoundError before writing reference/config-2019.json
approval checks: 90 / 90 passed
network download performed: true
exact candidate identity check completed: true
reference rebuild completed: false
cross-source comparison completed: false
scientific gates evaluated: false
raw rows emitted: 0
raw files uploaded: false
formal stake: 0
```

The Artifact contains one aggregate JSON report only. No candidate CSV, source archive, Historical Silver/Gold database, raw row, unmatched key, or game ID was uploaded.

Request `LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001` recorded one execution attempt and must not be reused or rerun.

## Repair

PR #111 merged the deterministic reference-root repair:

```text
merge commit: 613ce3a6232780c486d899b02dd7a99e799b0a27
hotfix entrypoint:
scripts/run_user_supplied_legacy_market_archive_real_file_audit_once_v1_1.py
```

The repair creates the temporary reference root before calling the reviewed v1 reference builder.

Unchanged:

- exact candidate bytes and SHA-256;
- 2019-20 through 2023-24 reference seasons;
- deterministic date/home/away join;
- no fuzzy matching or manual overrides;
- score validation only;
- frozen scientific gates;
- aggregate-only output;
- Stake 0.

## Retry Request 002

```text
request id: LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-002
state: AWAITING_EXPLICIT_USER_APPROVAL
one-time only: true
workflow_dispatch only: true
approval granted: false
execution enabled: false
execution count: 0
maximum execution count: 1
```

Request file:

```text
data/research/legacy-market-real-file-audit-retry-request-002-v1.json
```

The retry cannot be executed until a new explicit user approval is recorded and a separate one-time retry workflow is reviewed and merged.

## Legacy Market Archive

```text
source id: kaggle_cviaxmiwnptr_nba_betting_data_user_supplied
required file: nba_2008-2026.csv
bytes: 2,493,308
SHA-256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
rows: 24,440
columns: 27
provenance: user_confirmed
current role: ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
```

`nba_2008-2026_cleaned.csv` or any derived file cannot replace the frozen candidate.

## Frozen Comparison Contract

```text
reference seasons: 2019-20 through 2023-24
candidate labels: 2020 through 2024
candidate filter: regular == true and playoffs == false
join key: game_date + home_team_abbr + away_team_abbr
Gold to Silver join: game_id
fuzzy matching: false
manual key override: false
many-to-many join: false
score-assisted identity repair: false
```

## Frozen Quality Gates

```text
reference games >= 5,700
eligible candidate games >= 5,700
reference match rate >= 98.5%
candidate match rate >= 98.5%
matched score-pair rate >= 99.0%
each-season reference match rate >= 97.0%
duplicate / ambiguous / unresolved / invalid / missing-score counts = 0
raw rows emitted = 0
raw files emitted = false
```

No gate was evaluated in blocked run `29804975869`.

## Eoin Evidence Line

```text
formal execution result: ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
contract monitor: EOIN_SECONDARY_QA_CONTRACT_HEALTHY
integration mode: alert_only_evidence_contract_monitor
source data integration active: false
request consumed: true
repeat execution allowed: false
evidence review due: 2027-07-21
formal stake: 0
```

Eoin is deterministic QA evidence only. It is not a primary source and does not replace Historical Silver or Gold.

## Current Research Position

- Historical Gold: Completed, 5,824 matchup rows, strict PIT violations 0.
- Logistic + Elo Walk-forward v2: Completed, 3,688 OOF.
- Closing Market Benchmark: model materially trails Closing Market.
- Expected Minutes Audit v3: `ACCURACY_PASS`.
- Injury Feature Holdout v1: `VALID_NEGATIVE_RESULT`.
- Wyatt Real-file Audit: `STRUCTURAL_BLOCKED`.
- Eoin Secondary QA: `VALIDATED / HEALTHY / ALERT-ONLY`.
- Legacy Market Archive: `REPAIR MERGED / RETRY REQUEST 002 AWAITING APPROVAL`.

## Offseason Market State

```text
OFFSEASON_CAPTURE_SLEEP_MODE
```

No new live snapshot capture is required during the offseason. Point-in-time market joins remain blocked.

## Do Not Do

- Do not rerun workflow run `29804975869` or reuse request 001.
- Do not dispatch request 002 before a new explicit approval and reviewed one-time workflow.
- Do not substitute a cleaned or derived candidate file.
- Do not continue if candidate bytes or SHA-256 differ.
- Do not commit or upload raw CSV, SQLite, Parquet, source archives, or raw rows.
- Do not emit unmatched keys, game IDs, or row-level mismatch lists.
- Do not use fuzzy matching, manual identity overrides, or score-assisted identity repair.
- Do not label the Legacy Archive as point-in-time, Opening, or Closing.
- Do not unlock market backtests, CLV, EV, ROI, Drawdown, model retraining, or betting-edge claims.
- Do not repeat the consumed Eoin request.
- Keep formal Stake at 0.

## Important Files

- `data/historical-odds-source-registry.json`
- `data/research/user-supplied-nba-betting-csv-provenance-current-status-v1.json`
- `data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json`
- `data/research/user-supplied-legacy-market-archive-cross-source-audit-implementation-v1.json`
- `data/research/user-supplied-legacy-market-archive-real-file-audit-execution-request-v1.json`
- `data/research/user-supplied-legacy-market-archive-real-file-audit-approval-v1.json`
- `data/research/legacy-market-real-file-audit-retry-request-002-v1.json`
- `docs/legacy-market-real-file-audit-run-29804975869-incident-v1.md`
- `docs/legacy-market-real-file-audit-retry-request-002-v1.md`
- `scripts/run_user_supplied_legacy_market_archive_real_file_audit_once_v1.py`
- `scripts/run_user_supplied_legacy_market_archive_real_file_audit_once_v1_1.py`

## Explicit Next Step

```text
1. Validate and merge retry request 002.
2. Obtain new explicit user approval for request 002.
3. Create and validate one new manual retry workflow.
4. Dispatch exactly one new run from main.
5. Read the aggregate Artifact before recording any scientific outcome.
6. Keep Stake at 0.
```
