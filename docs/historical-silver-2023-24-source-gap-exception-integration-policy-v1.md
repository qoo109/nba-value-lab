# Historical Silver 2023-24 Source Gap Exception Integration Policy v1

更新日期：2026-07-22  
Repository：`qoo109/nba-value-lab`  
正式 Stake：`0`

## 目的

本 policy 定義既有 QA／coverage reporting 未來如何辨識已驗證的兩場 source-gap exceptions，同時保留原始缺口數字，不把 Gold 偽裝成完整，也不修改 Silver 或 Gold。

已驗證前提：

```text
exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
exception count: 2
unclassified count: 0
source archive decision: SOURCE_ARCHIVE_GAP_STABLE
```

## Reporting contract

原始數字永久保留：

```text
Historical Silver games: 5,826
Historical Gold matchups: 5,824
raw missing Gold for Silver: 2
```

文件化後可增加以下 aggregate-only 欄位：

```text
documented_source_gap_exception_count: 2
unexplained_missing_count_after_documentation: 0
covered_or_documented_count: 5,826
```

但必須同時保留：

```text
gold_matchup_count_after_documentation: 5,824
gold_coverage_rewritten_as_complete: false
gold_dataset_complete: false
```

`covered_or_documented_count` 只代表每個 Silver game 都有 Gold row 或正式文件化的上游缺口，不代表所有比賽都有可用 Gold features。

## Recognition gate

只有所有條件同時成立，QA／coverage report 才能標記：

```text
HISTORICAL_GOLD_SILVER_COVERAGE_DOCUMENTED_SOURCE_EXCEPTION_RECOGNIZED
```

必要條件包括：

- 2023-24 raw missing count 仍為 2；
- raw reason 仍是兩場 `missing_both_team_features`；
- reconciliation 仍是 `SOURCE_ARCHIVE_GAP_STABLE`；
- exception manifest count 仍為 2；
- unclassified count 為 0；
- exception code 未變；
- Silver builder repair required 為 false；
- manifest 不包含 row-level identifiers；
- Stake 為 0。

任一條件不一致時必須 fail closed：

```text
FAIL_CLOSED_UNEXPLAINED_COVERAGE_GAP
```

不得部分認列，也不得自動調整 count。

## 不改變的正式結論

```text
raw outcome:
HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED

builder repair required: false
Gold dataset complete: false
cross-source audit rerun ready: false
market backtest ready: false
model retraining ready: false
formal Stake: 0
```

本 policy 只改善 QA 的語意：把「已解釋的上游缺口」與「仍未解釋的資料錯誤」分開報告。

## Privacy boundary

不得新增或輸出：

- game ID；
- 日期；
- 主客隊或隊伍代碼；
- source path／hash；
- row-level records；
- row-key hashes；
- raw rows／files。

## 本次實作邊界

本 PR 只建立 policy、current status、validator 與文件：

```text
current analyzer changed: false
current builder changed: false
database read/write: false
network calls: false
source archives read: false
real data execution: false
```

未來若要讓 analyzer 或 downstream QA 工具讀取本 policy，必須另開 branch／PR，先做 synthetic fixture 與 mutation tests。第一次 real-reference validation 以及任何 cross-source audit rerun 都需要另外核准。

## 下一步

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_READY_FOR_DESIGN
```

下一步仍是 implementation design，不是直接改 production analyzer，更不是重跑資料或市場研究。
