# G1.2.0 Real Governed T-60 Intake Validator v1

更新日期：2026-07-24  
Formal Stake：0

## Milestone

```text
IMPLEMENT_G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_VALIDATOR_V1
```

PR #167 已固定第一份真實 2026-27 regular-season T-60 input 的 readiness gate。本里程碑把該 Gate 實作成一個 **provider-agnostic、offline、fail-closed** 的私人 intake validator。

它不選定新賠率來源、不執行 provider request、不寫入 formal history，也不執行 Market Backtest、CLV、EV、ROI 或 Drawdown。

## Private input package

實際使用時需要三個私人檔案：

```text
1. normalized T-60 input JSON
2. source evidence JSON
3. original raw provider response or export
```

Production CLI：

```bash
python scripts/g1_2_0_real_t60_intake_validator_v1.py \
  --input /private/path/t60-input.json \
  --evidence /private/path/source-evidence.json \
  --raw-source /private/path/raw-provider-export.json \
  --output /private/path/intake-aggregate-qa.json
```

CLI 沒有 `--contract-test` 選項，因此 repository 內的 contract fixture only 測試資料不能被當成真實輸入。

## Required identity

```text
data_mode: real_governed
season: 2026-27
competition_type: regular_season
evaluation_stage: T-60m
market_id: moneyline_ot_included
includes_overtime: true
lock window: 30..90 minutes before tip
```

Bookmaker 必須是真實 identity，不接受 `fixture_book`、`unknown`、`placeholder` 或 synthetic 名稱。

## Source evidence

Evidence manifest 必須綁定：

```text
source_id
HTTPS source_url
source_rights_state = private_research_allowed
rights_reviewed_by_user = true
provider_timestamp_semantics_verified = true
quote_time_authority = provider_snapshot | bookmaker_last_update
provider_observed_at_field
canonical_game_mapping_method = exact
normalized_input_sha256
raw_source_sha256
public_redistribution_allowed = false
```

`collector_fetched_at` 永遠不能代替 provider-origin `observed_at`。

Normalized input 與 raw source 的 SHA-256 必須和 evidence manifest 完全一致，避免輸入檔與來源證據脫鉤。

## Slate and candidate gates

每場比賽必須：

- 精確兩邊：home 與 away；
- 同一 bookmaker、同一 snapshot；
- target／opponent odds 互相一致；
- 共用完全相同的 `observed_at` 與 `scheduled_at`；
- `observed_at <= analysis_cutoff < tipoff`；
- `P_C <= P_N <= P_O`；
- 兩邊機率互補；
- source lineage、market rules、price timestamp 均完整；
- 禁止 fuzzy mapping、nearest-time mapping、Closing-only substitution 或 future fill。

整份 slate 至少要有一場通過完整 injury／starter／minutes-limit／information Gate，才可標記為 `g120_dry_run_ready=true`。

## Aggregate-only output

允許公開或留存在 QA 的內容僅限：

```text
formal state
game count
candidate count
fully gated game count
readiness booleans
formal history authorization = false
provider requests executed = 0
market metrics executed = false
Formal Stake = 0
```

禁止出現在 Artifact：

- team IDs；
- bookmaker prices；
- raw provider payload；
- API Key 或 Authorization header；
- quote-level rows。

## Contract validation

Repository 只包含 contract fixture only 測試資料，用來驗證：

- contract fixture 只能在測試模式通過；
- real CLI 一律拒絕 fixture；
- Closing-only、placeholder bookmaker、錯誤 season／competition 均拒絕；
- unreviewed rights、fuzzy mapping、collector fetch-time authority 均拒絕；
- normalized／raw SHA-256 不一致均拒絕；
- observed_at 不一致、晚於 cutoff、T-60 window 不合格均拒絕；
- 沒有完整 injury／information Gate 的 slate 拒絕。

Contract validation 不代表任何真實來源已合格，也不代表真實 G1.2.0 dry-run 已執行。

## Formal boundaries

```text
real input validated: false
real G1.2.0 dry-run executed: false
formal history write authorized: false
qualified timestamped odds source: none
provider requests executed: 0
Market Backtest: false
CLV / EV / ROI / Drawdown: false
betting edge claim: false
Formal Stake：0
```

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```

當兩項 prerequisite 都存在時，先在私人環境執行 intake validator，只檢查 aggregate-only QA；通過後才可另行申請一次真實 G1.2.0 dry-run。
