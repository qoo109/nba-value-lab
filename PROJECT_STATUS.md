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
request 002: consumed by completed real-file execution
real audit workflow run: 29810347326
all frozen scientific gates passed: true
formal audit outcome: USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED
blocking boundary: reference_missing_gold_for_silver
Silver rows in scope: 5,826
Gold matchup rows: 5,824
missing Gold for Silver: 2
coverage reconciliation implementation: READY / REAL EXECUTION DISABLED
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
formal stake: 0
```

## Next Unique Mainline

```text
HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_REAL_REFERENCE_EXECUTION_REQUEST
```

The candidate archive itself passed identity, deterministic matching, and every frozen scientific gate. The only blocker is a two-game reference coverage gap between rebuilt Historical Silver and Historical Gold.

## Completed Real-file Audit Retry 002

```text
request id: LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-002
workflow run: 29810347326
workflow attempt: 1
head SHA: 78ac0931cd28b2315b6e24954dc9ad1af9caf4f0
real-file audit executed: true
request consumed: true
repeat execution allowed: false
```

Aggregate result:

```text
candidate eligible rows: 5,829
matched games: 5,824
candidate-only games: 5
reference-only games: 0
candidate match rate: 99.914222%
reference match rate: 99.9656711%
score-pair matches: 5,820 / 5,824
score-pair match rate: 99.9313187%
ambiguous join keys: 0
duplicate candidate keys: 0
unresolved team codes: 0
invalid dates: 0
all scientific gates passed: true
```

Formal outcome:

```text
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED
```

Boundary failure:

```text
reference_missing_gold_for_silver
```

Reference rebuild:

```text
2019-20 Silver games: 1,056
2020-21 Silver games: 1,080
2021-22 Silver games: 1,230
2022-23 Silver games: 1,230
2023-24 Silver games: 1,230
combined Silver games: 5,826
Gold matchup rows: 5,824
Gold team-feature rows: 11,648
strict PIT violations: 0
```

Result record:

```text
data/research/legacy-market-real-file-audit-retry-002-result-v1.json
```

## Coverage Reconciliation Implementation

```text
formal state:
HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_IMPLEMENTATION_READY_REAL_EXECUTION_DISABLED
```

Analyzer:

```text
scripts/analyze_historical_gold_silver_coverage_v1.py
```

The analyzer classifies missing Gold coverage without changing any source row. It checks:

1. Silver home team feature presence.
2. Silver away team feature presence.
3. Exact two-sided Silver identity consistency.
4. Transfer into Gold team features.
5. Gold matchup-builder omission despite both Gold team rows existing.

Aggregate categories:

```text
missing_home_team_feature
missing_away_team_feature
missing_both_team_features
silver_feature_pair_identity_mismatch
gold_team_feature_transfer_mismatch
gold_matchup_builder_omission
silver_game_outside_gold_identity_contract
unclassified
```

Current validation is synthetic-only:

```text
network calls: false
real Silver/Gold rows read: false
real reconciliation executed: false
raw rows emitted: 0
raw files emitted: false
source role changed: false
formal stake: 0
```

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

The candidate does not need modification. `nba_2008-2026_cleaned.csv` or any derived file still cannot replace the frozen candidate.

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
- Historical Silver five-season rebuild: 5,826 games.
- Gold/Silver coverage gap: 2 games, cause not yet classified on real reference data.
- Logistic + Elo Walk-forward v2: Completed, 3,688 OOF.
- Closing Market Benchmark: model materially trails Closing Market.
- Expected Minutes Audit v3: `ACCURACY_PASS`.
- Injury Feature Holdout v1: `VALID_NEGATIVE_RESULT`.
- Wyatt Real-file Audit: `STRUCTURAL_BLOCKED`.
- Eoin Secondary QA: `VALIDATED / HEALTHY / ALERT-ONLY`.
- Legacy Market Archive: scientific gates passed, role upgrade blocked by reference coverage integrity.

## Offseason Market State

```text
OFFSEASON_CAPTURE_SLEEP_MODE
```

No new live snapshot capture is required during the offseason. Point-in-time market joins remain blocked.

## Do Not Do

- Do not rerun request 001 or request 002.
- Do not modify the candidate CSV; it passed exact identity and scientific gates.
- Do not classify the two missing Gold games without reading a reviewed reconciliation result.
- Do not add rows manually to Gold or Silver.
- Do not change the Gold builder during a diagnostic execution.
- Do not commit or upload raw CSV, SQLite, Parquet, source archives, or raw rows.
- Do not emit game IDs, dates, team codes, unmatched keys, row hashes, or row-level examples.
- Do not use fuzzy matching, manual identity overrides, or score-assisted identity repair.
- Do not label the Legacy Archive as point-in-time, Opening, or Closing.
- Do not unlock market backtests, CLV, EV, ROI, Drawdown, model retraining, or betting-edge claims.
- Do not repeat the consumed Eoin request.
- Keep formal Stake at 0.

## Important Files

- `data/historical-odds-source-registry.json`
- `data/research/user-supplied-nba-betting-csv-provenance-current-status-v1.json`
- `data/research/legacy-market-real-file-audit-retry-002-result-v1.json`
- `data/research/historical-gold-silver-coverage-reconciliation-implementation-v1.json`
- `docs/historical-gold-silver-coverage-reconciliation-implementation-v1.md`
- `scripts/analyze_historical_gold_silver_coverage_v1.py`
- `.github/workflows/validate-historical-gold-silver-coverage-reconciliation-v1.yml`

## Explicit Next Step

```text
1. Validate and merge the aggregate audit result record and reconciliation analyzer implementation.
2. Create a separate one-time real-reference reconciliation request.
3. Obtain explicit approval before rebuilding or reading real Silver/Gold rows again.
4. Execute one aggregate-only reconciliation run.
5. Use its classified cause to decide between Gold builder repair and source-data gap handling.
6. Do not rerun the cross-source audit until reconciliation is resolved.
7. Keep Stake at 0.
```
