# Historical Gold / Silver Coverage Reconciliation — Real-reference Execution Request v1

更新日期：2026-07-21（Asia/Taipei）

## Request

```text
HISTORICAL-GOLD-SILVER-COVERAGE-RECONCILIATION-2026-07-21-001
```

Current state:

```text
AWAITING_EXPLICIT_USER_APPROVAL
```

This request does not execute the reconciliation. It defines the one-time scope that may be approved later.

## Trigger

Real workflow run `29810347326` passed every frozen scientific gate, but the source role remained blocked because:

```text
Historical Silver games: 5,826
Historical Gold matchups: 5,824
Missing Gold for Silver: 2
```

The candidate CSV passed identity and scientific checks and is not required for this diagnostic.

## Approved scope after later explicit approval

One `workflow_dispatch` run may:

1. Download the frozen five-season public reference archives into temporary workflow storage.
2. Rebuild Historical Silver for 2019-20 through 2023-24.
3. Combine Silver and rebuild season-aware Historical Gold without modifying builder code.
4. Read the temporary Silver and Gold rows.
5. Run `scripts/analyze_historical_gold_silver_coverage_v1.py`.
6. Delete all archives and databases before artifact upload.
7. Upload one aggregate JSON report of at most 1 MiB.

## Candidate exclusion

The diagnostic does not need the user-supplied market archive. It must not download or read the candidate CSV.

## Aggregate classifications

The report may contain counts for:

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

It may also include counts by season, feature-count histograms, and whether builder repair or source-data reconciliation is required.

## Prohibited output

The workflow must not emit or upload:

- game IDs;
- dates;
- team codes;
- unmatched row-level records;
- row-key hashes;
- Silver or Gold databases;
- source archives;
- raw rows or derived row-level tables.

## Prohibited actions

The diagnostic run may not:

- change the Gold builder;
- insert or override Silver or Gold rows;
- replace Historical Silver or Gold;
- use fuzzy matching;
- use scores to repair identity;
- rerun the Legacy Market Archive cross-source audit;
- unlock Opening/Closing, PIT market backtest, CLV, EV, ROI, Drawdown, model retraining, betting-edge claims, or non-zero Stake.

## Approval boundary

Request validation only makes the packet ready for user approval. Execution remains disabled until the repository owner explicitly approves the exact request ID and scope.

## Suggested approval text

> 我核准 request HISTORICAL-GOLD-SILVER-COVERAGE-RECONCILIATION-2026-07-21-001 執行一次 workflow_dispatch 的 aggregate-only Historical Gold／Silver coverage reconciliation。核准範圍只包含在暫存空間重建 2019-20 至 2023-24 Historical Silver／Gold、讀取暫存 reference rows、診斷 Silver 5,826 場與 Gold 5,824 場之間缺少 2 場的原因並輸出按賽季與原因分類的彙總 JSON；不得下載或讀取 candidate CSV，不得上傳原始資料、資料庫、來源 archive、game IDs、日期、隊伍代碼、逐場資料或 row-key hashes，不得在診斷執行中修改 Gold builder、人工補列、模糊配對或以比分修補 identity，不得解鎖 Opening／Closing、PIT market backtest、CLV、EV、ROI、Drawdown、模型重訓、betting edge 或非 0 Stake。
