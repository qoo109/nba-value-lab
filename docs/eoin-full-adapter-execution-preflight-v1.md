# Eoin Full Adapter Execution Preflight v1

更新日期：2026-07-19

## Purpose

建立完整 Eoin bundle execution 前的安全預檢層。

此步驟仍不執行完整 Eoin Kaggle bundle，不讀真實 raw Eoin rows，不輸出 derived tables，也不允許 Silver／Gold replacement、model retraining、market backtest 或非 0 stake。

正式 Stake 維持 `0`。

## Required Upstream Evidence

Preflight 必須同時看見：

```text
data/eoin-cross-source-audit-v1.json
data/eoin-adapter-predeclaration-v1.json
eoin-role-limited-secondary-adapter-v1-report.json
```

其中 self-test report 必須來自 `Validate Eoin role-limited adapter v1` 的成功執行或同等 CI 步驟重新產生的 aggregate-only report。

## What This Allows

```text
validate cross-source aggregate evidence
validate adapter predeclaration policy
validate role-limited adapter self-test report
validate raw-output ban
validate future full-execution boundaries
```

## What This Still Does Not Allow

```text
full Eoin bundle execution: false
raw Eoin rows read: false
raw rows emitted: 0
raw files emitted: false
Historical Silver replacement: false
Historical Gold replacement: false
player stat parity claim: false
model retraining: false
market metrics: false
CLV / EV / ROI / Drawdown: false
betting decision layer: false
formal stake: 0
```

## Local Command

Generate a fresh aggregate-only self-test report, then validate preflight:

```bash
rm -rf out/eoin-role-limited-adapter-v1
python3 scripts/run_eoin_role_limited_adapter_v1.py \
  --self-test \
  --output-dir out/eoin-role-limited-adapter-v1

python3 scripts/validate_eoin_full_adapter_preflight_v1.py \
  --adapter-self-test-report out/eoin-role-limited-adapter-v1/eoin-role-limited-secondary-adapter-v1-report.json \
  --output out/eoin-role-limited-adapter-v1/eoin-full-adapter-execution-preflight-v1-report.json
```

CI uses the Parquet fixture path and uploads only aggregate JSON reports.

## Passing State

```text
FULL_ADAPTER_EXECUTION_PREFLIGHT_READY_BUT_DISABLED
```

This means the next discussion may design a separate execution policy. It does not authorize direct full-bundle execution.
