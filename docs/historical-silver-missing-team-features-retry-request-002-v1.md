# Historical Silver missing-team-features retry request 002

Request ID:

```text
HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002
```

Current state:

```text
AWAITING_EXPLICIT_USER_APPROVAL
```

## Reason

Request `001` produced run `29888939524`, which stopped before a scientific root-cause classification because the executor read:

```text
report["quality"]["team_inference_failures"]
```

The correct field path is:

```text
report["sources"]["pbpstats_2023"]["team_inference_failures"]
```

The blocked run uploaded one aggregate-only artifact, `8517546804`, and did not upload raw rows, game IDs, dates, team codes, source archives, or a Silver database.

## Repair

Repair commit:

```text
db5a7ea4ad38f5d3db763d6ea4457e5428292fb5
```

The repair changes only the executor report-path read and makes blocked execution errors visible in workflow logs.

Unchanged:

- `2023-24` Historical Silver temporary rebuild scope;
- expected Silver games: `1,230`;
- expected zero-team-feature games: `2`;
- aggregate-only output;
- no Candidate CSV;
- no Gold creation or modification;
- no Silver/Gold replacement;
- no fuzzy matching, manual row insertion, or score-assisted identity repair;
- no Opening/Closing labels, PIT market backtest, CLV, EV, ROI, Drawdown, model retraining, betting edge claim, or non-zero Stake.

## Approval Text

Use this exact approval sentence only if you want to authorize retry `002`:

```text
我核准 request HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002 執行一次修復後的 workflow_dispatch aggregate-only 2023-24 Historical Silver missing-team-features root-cause audit。此重試只修正 request 001 的 runner 欄位路徑錯誤；診斷範圍、2023-24 Historical Silver 暫存重建、分類兩場零 team features 的彙總輸出與所有 aggregate-only 邊界不得改變。不得下載或讀取 candidate CSV，不得建立或修改 Gold，不得上傳原始資料、Silver database、來源 archive、game IDs、日期、隊伍代碼、逐場資料或 row-key hashes，不得修改 Silver builder、人工補列、模糊配對或以比分修補 identity，不得解鎖 Opening／Closing、PIT market backtest、CLV、EV、ROI、Drawdown、模型重訓、betting edge 或非 0 Stake。
```

## Boundary

Request `002` is not approved by being created. It becomes executable only after explicit user approval is recorded in a separate approval file and validated by CI.
