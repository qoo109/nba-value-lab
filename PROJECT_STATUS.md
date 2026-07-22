# NBA Value Lab — Project Status

狀態核對日期：2026-07-22
研究定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

```text
current work mode: OFFSEASON_DATA_CONSTRUCTION
legacy source role: ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
candidate cross-source scientific gates: PASS
candidate formal result: BLOCKED BY REFERENCE COVERAGE
Gold/Silver reconciliation result: SOURCE_DATA_GAP_CONFIRMED
2023-24 Silver games: 1,230
2023-24 games without team features: 2
root-cause implementation: VALIDATED
root-cause request: EXECUTION ATTEMPTED / BLOCKED BY RUNNER FIELD-PATH BUG
real root-cause execution count: 1 / 1
root-cause incident run: 29888939524
root-cause incident artifact: 8517546804
root-cause incident error: KeyError team_inference_failures
root-cause retry request 002: EXECUTED / CONSUMED / SOURCE GAP CONFIRMED
root-cause retry 002 execution count: 1 / 1
root-cause retry 002 run: 29890527281
root-cause retry 002 artifact: 8518081820
root-cause retry 002 outcome: HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED
source archive reconciliation design: READY
source archive reconciliation design policy: data/research/historical-silver-2023-24-source-archive-reconciliation-design-v1.json
source archive reconciliation design state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_DESIGN_READY
source archive reconciliation request: CREATED / EXPLICIT USER APPROVAL GRANTED
source archive reconciliation request policy: data/research/historical-silver-2023-24-source-archive-reconciliation-request-v1.json
source archive reconciliation approval: GRANTED / READY FOR MANUAL DISPATCH
source archive reconciliation approval policy: data/research/historical-silver-2023-24-source-archive-reconciliation-approval-v1.json
source archive reconciliation current state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH
canonical repository: qoo109/nba-value-lab / SINGLE_ACTIVE_WORKSPACE
odds history hub: ARCHIVED_IN_MAIN / V0.19 / NO_EXTERNAL_DEPENDENCY
odds history hub snapshot: backups/nba-odds-history-hub-v0.19 @ 5d2659efb2fee1cf28816ebfc65ddac929d75d6a
formal stake: 0
```

## Next Unique Mainline

```text
HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_READY_FOR_MANUAL_DISPATCH
```

Execution Request ID:

```text
HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
```

The request has explicit user approval and is ready for one manual `workflow_dispatch`. It has not executed yet.

## Completed Evidence

### Legacy candidate real-file audit

```text
workflow run: 29810347326
candidate eligible games: 5,829
matched games: 5,824
all frozen scientific gates passed: true
formal result: USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED
blocking boundary: reference_missing_gold_for_silver
```

### Gold/Silver coverage reconciliation

```text
workflow run: 29819457942
Silver games: 5,826
Gold matchups: 5,824
missing Gold coverage: 2
missing season: 2023-24
missing reason: missing_both_team_features = 2
Gold builder omission: 0
Gold transfer mismatch: 0
formal result: HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED
```

### Silver root-cause analyzer

```text
implementation merge: be61b82d74ba17f500787d2685275e572f209b1d
validation run: 29821350899
validation artifact: 8491472454
real rows read: false
real execution: false
```

### One-time request validation

```text
request merge: 7d52582bca2a8ef596e862c7655872a14e0a00ac
validation run: 29821759681
validation artifact: 8491635865
state: REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
```

### Explicit approval and blocked execution attempt

```text
approval granted: true
approved by: qoo109
execution enabled: true
execution count: 1
maximum execution count: 1
workflow_dispatch only: true
execution run: 29888939524
execution artifact: 8517546804
formal state: HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_BLOCKED_BEFORE_RESULT
error: KeyError 'team_inference_failures'
```

The approved request `001` recorded one execution attempt and must not be reused. The run stopped before a formal scientific root-cause classification because the executor read `team_inference_failures` from the wrong report path.

Incident note: `docs/historical-silver-missing-team-features-run-29888939524-incident-v1.md`

### Retry request 002

```text
request id: HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002
state: CONSUMED_SOURCE_GAP_CONFIRMED
approval granted: true
approved by: qoo109
execution enabled: false
execution count: 1
maximum execution count: 1
repair commit: db5a7ea4ad38f5d3db763d6ea4457e5428292fb5
execution run: 29890527281
execution artifact: 8518081820
formal outcome: HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED
source archive reconciliation required: true
silver builder repair required: false
silver game identity reconciliation required: false
```

Retry `002` rebuilt only the `2023-24` Historical Silver reference in temporary storage and classified the two zero-feature games using aggregate counts.

It was workflow_dispatch only and is now consumed. It must not be executed again.

Aggregate result:

```text
Silver games: 1,230
games without team features: 2
classified missing games: 2
unclassified missing games: 0
root cause: nbastats_game_present_pbpstats_game_absent = 2
team feature histogram: 0 => 2 / 2 => 1,228
temporary material deleted with runner: true
formal stake: 0
```

### Source archive reconciliation design

```text
formal state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_DESIGN_READY
policy: data/research/historical-silver-2023-24-source-archive-reconciliation-design-v1.json
documentation: docs/historical-silver-2023-24-source-archive-reconciliation-design-v1.md
validator: scripts/validate_historical_silver_source_archive_reconciliation_design_v1.py
workflow: .github/workflows/validate-historical-silver-source-archive-reconciliation-design-v1.yml
triggering result: HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED
ready for source archive reconciliation request draft: true
ready for Chris Munch manifest predeclaration: true
ready for Chris Munch data execution: false
ready for Silver builder change: false
ready for Gold rebuild: false
ready for market backtest: false
formal stake: 0
```

This design allows three follow-up lanes: aggregate source archive reconciliation, secondary team-feature QA reference design, or documented source-gap exception handling. It does not authorize any real data execution.

### Source archive reconciliation request

```text
request id: HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
policy: data/research/historical-silver-2023-24-source-archive-reconciliation-request-v1.json
documentation: docs/historical-silver-2023-24-source-archive-reconciliation-request-v1.md
validator: scripts/validate_historical_silver_source_archive_reconciliation_request_v1.py
workflow: .github/workflows/validate-historical-silver-source-archive-reconciliation-request-v1.yml
approval granted: false
execution enabled: false
execution count: 0 / 1
network calls made: 0
source archives read: false
candidate CSV rows read: false
raw rows emitted: 0
raw files emitted: false
formal stake: 0
```

This request only prepares an approval packet for one future aggregate-only Shufinskiy source archive reconciliation. It does not authorize execution, source archive uploads, raw row output, Silver or Gold database creation, Chris Munch CSV reads, Eoin bundle reads, model retraining, market backtest, betting-edge claims, or non-zero Stake.

### Source archive reconciliation approval

```text
request id: HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH
approval: data/research/historical-silver-2023-24-source-archive-reconciliation-approval-v1.json
current status: data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v1.json
documentation: docs/historical-silver-2023-24-source-archive-reconciliation-approval-v1.md
validator: scripts/validate_historical_silver_source_archive_reconciliation_approval_v1.py
runner: scripts/run_historical_silver_source_archive_reconciliation_once_v1.py
validation workflow: .github/workflows/validate-historical-silver-source-archive-reconciliation-approval-v1.yml
execution workflow: .github/workflows/run-approved-historical-silver-source-archive-reconciliation-once-v1.yml
approval granted: true
execution enabled: true
execution count: 0 / 1
network calls made: 0
source archives read: false
candidate CSV rows read: false
raw rows emitted: 0
raw files emitted: false
formal stake: 0
```

The only approved future execution is one manual aggregate-only Shufinskiy source archive reconciliation. It may not upload source archives, raw rows, raw files, source file paths, source file hashes, game IDs, dates, team codes, Silver or Gold databases, or any candidate CSV data.

## Consumed Retry 002 One-time Scope

The already consumed retry `002` manual workflow was allowed to:

1. download the existing `shufinskiy/nba_data` 2023-24 Silver inputs into temporary storage;
2. rebuild the existing 2023-24 Historical Silver without changing builder code;
3. read temporary `games`, `possessions`, and `team_game_features` rows;
4. classify the two zero-feature games;
5. delete temporary archives and database with the runner;
6. upload one aggregate JSON report of at most 1 MiB.

It was not allowed to download Candidate CSV, create or read Gold, or emit raw rows, game IDs, dates, team codes, row hashes, databases, or source archives.

## Still Blocked

- Silver builder changes;
- Gold rebuild;
- cross-source audit rerun;
- source archive reconciliation repeat execution;
- source archive reconciliation execution outside the approved one-time manual dispatch;
- Chris Munch raw CSV read or import;
- Historical Silver or Gold replacement;
- Opening or Closing semantics;
- point-in-time market evaluation;
- CLV, EV, ROI, or Drawdown;
- model retraining;
- betting-edge claims;
- formal Stake above `0`.
- automatic import from the archived Odds History Hub snapshot.
- rerunning request `HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001`.
- rerunning request `HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002`.

## Important Files

- `data/research/historical-gold-silver-coverage-real-reference-result-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-implementation-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-real-execution-request-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-approval-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-current-status-v2.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-current-status-v3.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-current-status-v4.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-current-status-v5.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-request-002-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-002-approval-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-002-result-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-design-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-request-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-approval-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v1.json`
- `docs/historical-silver-2023-24-source-archive-reconciliation-design-v1.md`
- `docs/historical-silver-2023-24-source-archive-reconciliation-request-v1.md`
- `docs/historical-silver-2023-24-source-archive-reconciliation-approval-v1.md`
- `docs/historical-silver-missing-team-features-retry-request-002-v1.md`
- `docs/historical-silver-missing-team-features-run-29888939524-incident-v1.md`
- `scripts/analyze_historical_silver_missing_team_features_root_cause_v1.py`
- `scripts/validate_historical_silver_missing_team_features_root_cause_approval_v1.py`
- `scripts/validate_historical_silver_missing_team_features_retry_request_002_v1.py`
- `scripts/validate_historical_silver_missing_team_features_retry_002_approval_v1.py`
- `scripts/validate_historical_silver_source_archive_reconciliation_design_v1.py`
- `scripts/validate_historical_silver_source_archive_reconciliation_request_v1.py`
- `scripts/validate_historical_silver_source_archive_reconciliation_approval_v1.py`
- `scripts/run_historical_silver_source_archive_reconciliation_once_v1.py`
- `scripts/run_historical_silver_missing_team_features_root_cause_once_v1.py`
- `scripts/run_historical_silver_missing_team_features_root_cause_retry_002_v1.py`
- `.github/workflows/run-approved-historical-silver-missing-team-features-root-cause-once-v1.yml`
- `.github/workflows/validate-historical-silver-missing-team-features-retry-request-002-v1.yml`
- `.github/workflows/validate-historical-silver-missing-team-features-retry-002-approval-v1.yml`
- `.github/workflows/run-approved-historical-silver-missing-team-features-root-cause-retry-002-v1.yml`
- `.github/workflows/validate-historical-silver-source-archive-reconciliation-design-v1.yml`
- `.github/workflows/validate-historical-silver-source-archive-reconciliation-request-v1.yml`
- `.github/workflows/validate-historical-silver-source-archive-reconciliation-approval-v1.yml`
- `.github/workflows/run-approved-historical-silver-source-archive-reconciliation-once-v1.yml`

## Eoin and Other Research Lines

```text
Eoin role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
Eoin integration: alert-only
Eoin repeat execution: disabled
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
request consumed: true
repeat execution allowed: false
Wyatt: STRUCTURAL_BLOCKED
Chris Munch: ROLE_LIMITED_SECONDARY_TEAM_FEATURE_QA_CANDIDATE / manifest required before execution
live odds capture: offseason sleep mode
```
