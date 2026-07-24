# HoopsAPI Private Runtime Preflight Request v1

更新日期：2026-07-24

## Purpose

建立一份**設計完成但尚未授權執行**的 HoopsAPI 私人 runtime schema preflight 申請封包。

```text
request id: HOOPSAPI-PRIVATE-RUNTIME-PREFLIGHT-2026-07-24-001
design only: true
provider terms accepted by user: false
account created by user: false
API key connected privately: false
explicit preflight approval granted: false
execution enabled: false
execution count: 0 / 1
provider request cap: 3
provider requests executed: 0
formal Stake: 0
```

Formal Stake：0

本文件不會建立帳號、不會代表使用者接受 HoopsAPI Terms、不會連接 API Key，也不會執行任何網路請求。

## Upstream evidence

已完成並合併的前置工作：

- PR #163：First Provider Private Forward Adapter Qualification Gate v1。
- PR #165：HoopsAPI Private Forward Adapter Synthetic Shell v1。
- Synthetic Shell validation run：`30059383153`。
- Artifact：`8583951648`。
- Artifact digest：`sha256:53a633b973538f7acaf827be0be806a0c48dfbef6ef1174912cf5a3a9197da9d`。

Synthetic Shell 已證明離線轉接邊界可以 fail-closed 運作，但沒有證明真實 response schema、provider timestamp semantics 或 runtime rights。

## Preconditions that require the user

執行 preflight 前，以下條件必須全部由使用者完成或明確核准：

1. 使用者本人閱讀並接受 HoopsAPI Terms。
2. 使用者本人建立 HoopsAPI 帳號。
3. 使用者取得 API Key。
4. 使用者選定私人 secret 儲存位置。
5. API Key 只能存於使用者控制的私人 secret store，建議名稱為 `HOOPSAPI_API_KEY`。
6. 使用者明確核准 request `HOOPSAPI-PRIVATE-RUNTIME-PREFLIGHT-2026-07-24-001`。

任何一項未完成，`execution_enabled` 必須保持 `false`。

## Maximum-three-request plan

預檢上限固定為三次 read-only requests：

```text
Request 1
  取得最小範圍的 authenticated current NBA games response，
  只驗證 runtime envelope 與欄位形狀。

Request 2（只有必要時）
  取得 provider identity metadata，
  只用於解讀 Request 1 的 provider key。

Request 3（只有必要時）
  重複一次最小範圍 games request，
  只檢查 schema stability 與 timestamp behavior。
```

禁止 pagination、historical endpoint、scheduler、continuous collection、rate-limit bypass，以及 authentication failure 後自動重試。

## Runtime qualification checks

必須檢查：

- stable source event id；
- home／away team；
- scheduled tipoff 與 timezone；
- provider identity；
- same-provider two-sided `h2h` Moneyline；
- decimal prices 或可確定轉換的輸入；
- provider snapshot timestamp 或 bookmaker last-update timestamp 是否存在；
- timestamp 欄位是否真的代表 quote observation time。

`collector_fetched_at_utc` NEVER substitutes `quote_observed_at_utc`。

若 runtime schema 可解析但 provider-origin timestamp semantics 仍未建立：

```text
provider runtime schema qualified: true
provider point-in-time qualified: false
quote_time_authority: unverified
quote_observed_at_utc: null
point_in_time_eligible: false
```

## Aggregate-only QA

公開 Artifact 只允許：

- request count；
- HTTP status class counts；
- content type；
- payload byte count；
- payload SHA-256；
- 欄位存在與否；
- event／provider／two-sided h2h aggregate counts；
- timestamp-field presence；
- runtime schema qualification flag；
- point-in-time qualification flag；
- formal state。

禁止輸出：

- API Key 或 Authorization header；
- raw payload；
- raw quote rows；
- bookmaker prices；
- team-level quote rows；
- 可下載 odds archive。

## Passing state of this design

```text
HOOPSAPI_PRIVATE_RUNTIME_PREFLIGHT_REQUEST_DESIGN_VALIDATED_AWAITING_USER_SETUP_AND_EXPLICIT_APPROVAL
```

這只代表申請封包與安全邊界完整，不代表 provider runtime、point-in-time 或 market evaluation 已通過。

## Approval text template

```text
I approve request HOOPSAPI-PRIVATE-RUNTIME-PREFLIGHT-2026-07-24-001 for one
maximum-three-request aggregate-only HoopsAPI schema preflight after I have
personally accepted the provider terms, created the account and connected the
API key through a private user-controlled secret store. This does not authorize
continuous collection, raw quote publication, historical backfill, Frozen Gold
join, Market Backtest, CLV, EV, ROI, Drawdown, model retraining, betting claims
or Stake above 0.
```

## Permanent boundaries

即使未來完成 preflight，仍不自動解鎖：

```text
continuous collection: false
historical backfill: false
Frozen Gold PIT join: false
Market Backtest: false
CLV / EV / ROI / Drawdown: false
model retraining: false
betting edge claim: false
formal Stake: 0
```

## Next unique mainline

```text
AWAIT_HOOPSAPI_USER_SETUP_AND_EXPLICIT_PREFLIGHT_APPROVAL
```
