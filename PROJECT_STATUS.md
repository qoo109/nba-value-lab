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
source archive reconciliation request: EXECUTED / CONSUMED
source archive reconciliation execution count: 1 / 1
source archive reconciliation run: 29901869841
source archive reconciliation artifact: 8522225397
source archive reconciliation artifact digest: sha256:2b42dca052d331bf94e31568b24492092beb00fef352405601fd812a8603b334
source archive reconciliation formal state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_AGGREGATE_VALIDATION_PASS
source archive reconciliation decision: SOURCE_ARCHIVE_GAP_STABLE
source archive reconciliation repeat execution: disabled
source gap exception manifest: VALIDATED / AGGREGATE ONLY
source gap exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
source gap exception count: 2
source gap exception patch allowed: false
silver builder repair required: false
canonical repository: qoo109/nba-value-lab / SINGLE_ACTIVE_WORKSPACE
odds history hub: ARCHIVED_IN_MAIN / V0.19 / NO_EXTERNAL_DEPENDENCY
odds history hub snapshot: backups/nba-odds-history-hub-v0.19 @ 5d2659efb2fee1cf28816ebfc65ddac929d75d6a
formal stake: 0
```

## Next Unique Mainline

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_READY_FOR_DESIGN
```

The privacy-safe source-gap exception manifest is now validated. The next controlled lane may design how existing QA and coverage validators recognize the documented aggregate exception. It does not authorize row patches, Silver／Gold changes, cross-source audit reruns, market backtests, or model activation.

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

The approved root-cause request `001` recorded one execution attempt and must not be reused. The run stopped before a formal scientific classification because the executor read `team_inference_failures` from the wrong report path.

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

Retry `002` rebuilt only the `2023-24` Historical Silver reference in temporary storage and classified the two zero-feature games using aggregate counts. It is consumed and must not execute again.

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

The design defined three follow-up lanes: aggregate source archive reconciliation, secondary team-feature QA reference design, and documented source-gap exception handling.

### Source archive reconciliation request and approval

```text
request id: HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
request: data/research/historical-silver-2023-24-source-archive-reconciliation-request-v1.json
approval: data/research/historical-silver-2023-24-source-archive-reconciliation-approval-v1.json
pre-execution current status: data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v1.json
workflow_dispatch only: true
approval granted: true
maximum execution count: 1
```

The approval packet and pre-execution status remain immutable evidence of the authorized scope. They are not the current post-execution state.

### Source archive reconciliation execution result

```text
request id: HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
workflow run: 29901869841
job: execute-once / success
artifact id: 8522225397
artifact name: historical-silver-source-archive-reconciliation-execution-v1
artifact digest: sha256:2b42dca052d331bf94e31568b24492092beb00fef352405601fd812a8603b334
formal state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_AGGREGATE_VALIDATION_PASS
decision: SOURCE_ARCHIVE_GAP_STABLE
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
```

Aggregate coverage:

```text
nbastats_2023 games: 1,230
pbpstats_2023 games: 1,228
overlap games: 1,228
nbastats only: 2
pbpstats only: 0
missing reason: nbastats_game_present_pbpstats_game_absent = 2
```

Possession grouping QA:

```text
possession_base: 242,363 groups / 2 inconsistent / unusable
possession_with_score_context: 242,364 groups / 1 inconsistent / unusable
possession_with_score_and_start_type: 242,365 groups / 0 inconsistent / usable
```

The stable upstream archive gap is confirmed. No Silver builder repair is required. Historical Silver replacement, Gold rebuild, market backtest and model retraining remain blocked.

Formal records:

- `data/research/historical-silver-2023-24-source-archive-reconciliation-result-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v2.json`
- `docs/historical-silver-2023-24-source-archive-reconciliation-result-v1.md`

### Source gap exception manifest

```text
formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_VALIDATED
manifest: data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json
current status: data/research/historical-silver-2023-24-source-gap-exception-current-status-v1.json
documentation: docs/historical-silver-2023-24-source-gap-exception-manifest-v1.md
validator: scripts/validate_historical_silver_source_gap_exception_manifest_v1.py
workflow: .github/workflows/validate-historical-silver-source-gap-exception-manifest-v1.yml
exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
exception count: 2
unclassified count: 0
handling mode: DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH
```

The public manifest contains aggregate evidence only. It keeps the existing Silver game identities while explicitly denying synthetic, copied, imputed, or manual team-feature rows. The two exception games remain ineligible for Gold inclusion, model use, and market-backtest reference unless genuinely new valid source rows are separately governed and validated.

This manifest does not authorize a Silver exception patch or any data execution. The next possible work is an integration-policy design for existing QA and coverage validators.

## Consumed One-time Scopes

The following requests are permanently consumed and must not be rerun:

```text
HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001
HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002
HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
```

The source archive reconciliation was allowed only to temporarily download and read the Shufinskiy `2023-24` NBA Stats and PBP Stats archives, calculate aggregate manifest／coverage／grouping counts, delete temporary material, and upload one aggregate-only JSON report.

It was not allowed to download Candidate CSV, read Chris Munch or Eoin, create or read Gold, alter Silver, or emit raw rows, game IDs, dates, team codes, source paths, source hashes, row hashes, databases, or source archives.

## Still Blocked

- Silver builder changes or manual row insertion;
- source-gap exception row patch or downstream integration outside a separately validated integration policy;
- Gold rebuild;
- cross-source audit rerun;
- source archive reconciliation repeat execution;
- Chris Munch raw CSV read or import;
- Eoin repeat or full-bundle execution;
- Historical Silver or Gold replacement;
- Opening or Closing semantics;
- point-in-time market evaluation;
- CLV, EV, ROI, or Drawdown;
- model retraining;
- betting-edge claims;
- formal Stake above `0`;
- automatic import from the archived Odds History Hub snapshot.

## Important Files

- `data/research/historical-gold-silver-coverage-real-reference-result-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-implementation-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-current-status-v5.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-request-002-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-002-approval-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-002-result-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-design-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-request-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-approval-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-result-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v2.json`
- `data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-current-status-v1.json`
- `docs/historical-silver-2023-24-source-archive-reconciliation-design-v1.md`
- `docs/historical-silver-2023-24-source-archive-reconciliation-request-v1.md`
- `docs/historical-silver-2023-24-source-archive-reconciliation-approval-v1.md`
- `docs/historical-silver-2023-24-source-archive-reconciliation-result-v1.md`
- `docs/historical-silver-2023-24-source-gap-exception-manifest-v1.md`
- `scripts/validate_historical_silver_source_archive_reconciliation_result_v1.py`
- `scripts/validate_historical_silver_source_gap_exception_manifest_v1.py`
- `.github/workflows/validate-historical-silver-source-archive-reconciliation-result-v1.yml`
- `.github/workflows/validate-historical-silver-source-gap-exception-manifest-v1.yml`

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
