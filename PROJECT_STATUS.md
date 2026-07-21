# NBA Value Lab — Project Status

狀態核對日期：2026-07-21  
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
root-cause request: VALID / AWAITING EXPLICIT USER APPROVAL
real root-cause execution count: 0
formal stake: 0
```

## Next Unique Mainline

```text
HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_AWAITING_EXPLICIT_USER_APPROVAL
```

Request ID:

```text
HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001
```

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
approval granted: false
execution enabled: false
```

## Approved Future Scope Only After Explicit Approval

A later approved run may rebuild only the `2023-24` Historical Silver reference in temporary storage and classify the two zero-feature games using aggregate counts.

It must not emit raw rows, game IDs, dates, team codes, row hashes, databases, or source archives. It must not modify the Silver or Gold builders during execution.

## Still Blocked

- Silver builder changes;
- Gold rebuild;
- cross-source audit rerun;
- Historical Silver or Gold replacement;
- Opening or Closing semantics;
- point-in-time market evaluation;
- CLV, EV, ROI, or Drawdown;
- model retraining;
- formal Stake above `0`.

## Important Files

- `data/research/historical-gold-silver-coverage-real-reference-result-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-implementation-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-real-execution-request-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-current-status-v2.json`
- `scripts/analyze_historical_silver_missing_team_features_root_cause_v1.py`
- `scripts/validate_historical_silver_missing_team_features_root_cause_request_v1.py`

## Eoin and Other Research Lines

```text
Eoin role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
Eoin integration: alert-only
Eoin repeat execution: disabled
Wyatt: STRUCTURAL_BLOCKED
live odds capture: offseason sleep mode
```
