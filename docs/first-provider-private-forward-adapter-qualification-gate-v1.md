# First Provider Private Forward Adapter Qualification Gate v1

更新日期：2026-07-24  
正式狀態：`FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_VALIDATED`  
Formal Stake：`0`

## 目的

本 Gate 決定第一個供應商專用 Adapter 在什麼條件下可以從「純離線 Synthetic Shell」前進到「私人 Runtime Preflight」，以及什麼情況下仍必須 fail closed。

目前候選供應商為：

```text
hoopsapi_free_forward_collection
```

選擇原因不是因為它已經可用，而是因為 BloomBet Schema Probe 已由使用者暫緩，而 HoopsAPI 是目前已完成公開審查、結構上可支援 forward-only 收集、但尚未獲准 Runtime 執行的候選來源。

## Gate 結論

```text
Gate design：VALIDATED
Synthetic Adapter Shell：ALLOWED
Provider Runtime：NOT QUALIFIED
Provider Point-in-time：NOT QUALIFIED
Historical Backfill：NOT QUALIFIED
Frozen Gold PIT Join：NOT QUALIFIED
Provider Requests Executed：0
Formal Stake：0
```

## 1. Structural Schema Gate

Synthetic Shell 必須至少能表示：

- stable source event ID；
- home team 與 away team；
- 含時區的 scheduled tipoff；
- Provider／Bookmaker identity；
- 同一 Bookmaker 的雙邊 Moneyline；
- decimal price，或可稽核的 deterministic conversion input。

HoopsAPI 公開範例已提供部分結構證據，因此允許建立 **Synthetic Adapter Shell**。這不等於 Runtime Schema 已驗證，也不代表可以呼叫 API。

## 2. Timestamp Authority Gate

Point-in-time 資格必須由供應商原始時間語意支撐：

- Provider snapshot timestamp，或 Bookmaker last-update timestamp；
- 明確證明該欄位對應回傳的 Quote；
- 時區與精度；
- Collector fetch time 不得早於供應商原始時間。

目前公開證據未提供 Quote-level Provider timestamp。因此 Synthetic Shell 的正式輸出必須是：

```text
quote_time_authority = unverified
quote_observed_at_utc = null
point_in_time_eligible = false
```

`collector_fetched_at_utc` **NEVER substitutes** `quote_observed_at_utc`。

## 3. Rights and Retention Gate

公開條款只支持 own-purpose 使用語意，同時禁止 Raw Odds 的轉售、再散布與再授權。因此：

- 使用者必須自行接受供應商條款；
- Private normalized retention 仍待 Runtime Policy 啟用；
- Raw payload retention 預設關閉；
- Repository 與 Artifact 不得包含逐筆 Quote 或價格；
- 不得建立可下載的公開 Odds Archive。

## 4. Access and Secret Gate

目前全部維持關閉：

```text
Account creation authorized：false
Provider terms acceptance authorized：false
API key connection authorized：false
Provider request execution authorized：false
```

API Key 不得進入 Repository、Artifact、Log 或聊天內容。任何 Private Secret 設定都需要後續獨立的使用者操作與明確批准。

## 5. Quota and Request Gate

公開免費方案標示每日 10 次請求，但這不是執行授權。若未來另行批准 Schema Preflight：

```text
Maximum initial requests：3
Rate-limit bypass：PROHIBITED
Scheduler：DISABLED
```

目前實際 Provider Request 仍為 `0`。

## 6. Event Mapping and Market Gate

- Exact mapping required；
- Fuzzy matching prohibited；
- Nearest-time matching prohibited；
- Season／competition inference prohibited；
- NBA `h2h` only；
- Same-book two-sided required；
- Single-sided quote prohibited；
- Opening inference prohibited；
- Closing-only 不得替代 T-60 或 T-5。

## 7. Private Storage and Public QA Gate

允許的實作邊界：

- Caller-supplied private SQLite；
- Cross-run deterministic deduplication；
- Aggregate-only QA；
- Synthetic fixture only。

禁止：

- Repository Quote rows；
- Artifact Quote rows；
- Raw payload；
- 市場價格明細；
- EV、CLV、ROI、Drawdown、Bet Count 或 Stake Recommendation。

## 8. 下一步

```text
IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1
```

下一步只建立離線 HoopsAPI-shaped Adapter Shell，使用由公開欄位形狀整理的 Synthetic Fixture。它必須輸出 `unverified` 時間權限、`null` observed_at 與 `point_in_time_eligible=false`。

下一步不得加入 HTTP Client、Secret Reader、Account Flow、真實 Provider Payload 或 Market Metrics。
