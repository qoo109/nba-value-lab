# Source-Agnostic Private Forward Odds Collector — Offline Core v1

更新日期：2026-07-24  
狀態：**Validated / Synthetic only / Network disabled**  
Formal state：`SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_VALIDATED`  
Formal Stake：`0`

## 完成內容

本階段將已合併的 provider-neutral collector 設計實作為純離線核心：

- synthetic payload adapter；
- NBA `h2h` 雙邊 decimal quote 正規化；
- provider snapshot、bookmaker last-update、collector fetch 三種時間概念分離；
- exact mapping 與 point-in-time eligibility fail-closed；
- deterministic SHA-256 row hash；
- SQLite append-only private store；
- duplicate 計數與 quarantine；
- aggregate-only QA。

正式時間規則：

```text
collector_fetched_at_utc NEVER substitutes quote_observed_at_utc
```

沒有文件化 provider-origin timestamp 的 row 可以私人保存為 forward observation，但必須保持：

```text
quote_time_authority = unverified
quote_observed_at_utc = null
point_in_time_eligible = false
```

## 私人 SQLite 邊界

Offline core 只接受呼叫端提供的私人 SQLite path。CI 使用 temporary directory 建庫、驗證後自動刪除。Repository 與公開 Artifact 不保存 SQLite、逐筆價格、隊伍、事件或 raw payload。

## Synthetic validation

固定測試包括：

1. provider snapshot authority 合格；
2. bookmaker last-update authority 合格；
3. unverified timestamp fail closed；
4. collector fetch substitution 不可能；
5. exact mapping gate；
6. temporary private SQLite write；
7. deterministic hash；
8. duplicate 不重複計 coverage；
9. post-tipoff quote quarantine；
10. invalid decimal price quarantine；
11. raw payload retention disabled；
12. aggregate QA 不洩露 quote-level 欄位。

## 未授權事項

```text
HTTP client: false
Secret reader: false
Scheduler: false
Provider requests: 0
Real provider payloads: 0
Real quotes retained: 0
Historical backfill: false
Market Backtest: false
CLV / EV / ROI: false
Betting claim: false
Formal Stake: 0
```

## 下一條唯一主線

```text
DESIGN_FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_V1
```

該步只設計第一個 provider adapter 的 admission、timestamp semantics、rights、quota、private retention 與 execution approval gate；不得建立帳號、接受條款、連接金鑰或執行 provider request。
