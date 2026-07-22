# Historical Silver 2023-24 source archive reconciliation request v1

Request ID:

```text
HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
```

Current state:

```text
AWAITING_EXPLICIT_USER_APPROVAL
```

## Purpose

Retry request `002` confirmed that the two `2023-24` Silver games without team features are classified as:

```text
nbastats_game_present_pbpstats_game_absent = 2
```

This request asks for a separate one-time aggregate-only source archive reconciliation to confirm whether the Shufinskiy NBA Stats and PBP Stats source archives have a stable upstream coverage gap.

## Frozen scope

```text
season: 2023-24
source path: shufinskiy/nba_data
expected Silver games: 1,230
expected zero-feature games: 2
expected classified missing games: 2
candidate CSV: forbidden
Gold database/build: forbidden
```

## Allowed operations after explicit approval

A later approved workflow may run exactly once and may only:

1. download the Shufinskiy NBA Stats and PBP Stats source archives to temporary workflow storage;
2. scan archive manifest and coverage counts for the frozen `2023-24` scope;
3. count NBA Stats game coverage, PBP Stats game coverage, and aggregate overlap;
4. produce an aggregate missing-reason histogram and decision summary;
5. delete temporary archives and any temporary database or extracted material;
6. upload one aggregate JSON report not larger than 1 MiB.

## Forbidden output and actions

The workflow must not emit or upload:

- game IDs;
- dates;
- team codes;
- source file paths;
- source file hashes;
- raw rows;
- row-key hashes;
- the Silver database;
- the Gold database;
- source archives;
- Chris Munch, Eoin, or other candidate CSV data.

The execution also must not:

- modify the Silver builder;
- run or modify the Gold builder;
- insert or override rows manually;
- use fuzzy matching;
- repair identity using scores;
- replace Historical Silver or Gold;
- rerun the cross-source audit automatically;
- unlock market evaluation or model retraining;
- change formal Stake from `0`.

## Approval boundary

Request validation does not enable execution. After CI passes, the repository owner must explicitly approve the exact request ID and the full aggregate-only boundary before an execution workflow may be added or dispatched.

Suggested approval text:

```text
我核准 request HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001 執行一次 workflow_dispatch 的 aggregate-only 2023-24 Shufinskiy source archive reconciliation。

核准範圍只包含在暫存空間下載並讀取 Shufinskiy NBA Stats／PBP Stats source archives、計算 archive manifest counts、coverage overlap counts 與 missing reason aggregate histogram，並輸出一份不超過 1 MiB 的彙總 JSON。

不得下載或讀取 Chris Munch、Eoin 或任何 candidate CSV，不得建立、修改或上傳 Silver／Gold database，不得上傳來源 archive、raw rows、raw files、game IDs、日期、隊伍代碼、source file paths、source file hashes、逐列資料或 row-key hashes，不得修改 Silver builder、人工補列、模糊配對、以比分修補 identity、替換 Historical Silver／Gold、重跑 cross-source audit、開啟市場回測、模型重訓、betting edge 或非 0 Stake。
```
