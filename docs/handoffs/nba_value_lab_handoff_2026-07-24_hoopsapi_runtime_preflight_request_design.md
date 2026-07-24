# NBA Value Lab — HoopsAPI Runtime Preflight Request Design Handoff

更新日期：2026-07-24

## Latest completed milestone

```text
PR #165 — HoopsAPI Private Forward Adapter Synthetic Shell v1
merge commit: 31c3ef8a0175d323cdb61e506acd100b302df757
validation run: 30059383153
validation artifact: 8583951648
validation digest: sha256:53a633b973538f7acaf827be0be806a0c48dfbef6ef1174912cf5a3a9197da9d
```

Synthetic Shell 已完成離線、合成資料、fail-closed 驗證。它不包含 HTTP client、secret reader、account workflow 或 scheduler；provider requests executed 維持 0。

## Current milestone

```text
PR #166 — Design HoopsAPI Private Runtime Preflight Request v1
DESIGN_HOOPSAPI_PRIVATE_RUNTIME_PREFLIGHT_REQUEST_V1
```

Request：

```text
request id: HOOPSAPI-PRIVATE-RUNTIME-PREFLIGHT-2026-07-24-001
formal state: HOOPSAPI_PRIVATE_RUNTIME_PREFLIGHT_REQUEST_DESIGN_VALIDATED_AWAITING_USER_SETUP_AND_EXPLICIT_APPROVAL
design only: true
provider request cap: 3
execution count: 0 / 1
provider requests executed: 0
Formal Stake：0
```

## What the design establishes

- 一次性、最多三次、read-only 的 runtime schema preflight。
- Request 1：最小範圍 current NBA games response。
- Request 2：只有必要時取得 provider identity metadata。
- Request 3：只有必要時重複最小範圍 request，檢查 schema stability 與 timestamp behavior。
- 公開 Artifact 僅允許 aggregate QA。
- 不保存或公開 raw payload、raw quote rows、bookmaker prices、API Key 或 Authorization header。
- `collector_fetched_at_utc` NEVER substitutes `quote_observed_at_utc`。
- 沒有 provider-origin timestamp semantics 時，固定輸出 `unverified`、`null observed_at`、`point_in_time_eligible=false`。

## User action required before any runtime execution

以下全部完成前，不可建立或執行 network runner：

1. 使用者本人接受 HoopsAPI Terms。
2. 使用者本人建立帳號。
3. 使用者取得 API Key。
4. 使用者選定私人 secret store。
5. 使用者私下連接 API Key。
6. 使用者對 request `HOOPSAPI-PRIVATE-RUNTIME-PREFLIGHT-2026-07-24-001` 給出明確核准。

目前：

```text
provider terms accepted by user: false
account created by user: false
API key connected privately: false
explicit preflight approval granted: false
execution enabled: false
```

## Still blocked

```text
continuous collection: false
real quote ingestion: false
historical backfill: false
Frozen Gold PIT join: false
Market Backtest: false
CLV / EV / ROI / Drawdown: false
model retraining: false
betting edge claims: false
Formal Stake：0
```

## Next unique mainline

```text
AWAIT_HOOPSAPI_USER_SETUP_AND_EXPLICIT_PREFLIGHT_APPROVAL
```

下一次繼續時，先檢查 GitHub `main`、Open PR、Actions 與 Artifact QA。若 PR #166 尚未合併，先完成 validator 與 aggregate-only Artifact QA；不得直接跳到帳號建立、Key 連接或 network execution。
