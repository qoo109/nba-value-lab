# NBA Value Lab — Project Status

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、合併 PR、Actions 與 Artifact QA 是正式 Source of Truth；舊 handoff 與聊天紀錄只保留歷史脈絡。

## Current Control Block

### Latest Main SHA

```text
cc833fe2e7cf3f2bdd943f7692a1118866bd8b9b
```

最新已合併：

```text
PR #59 — Add Offline Timestamped Odds Qualification Adapter v1
```

### Open PR

| PR | 狀態 | 用途 |
|---|---|---|
| #60 — Frozen Timestamped Odds Pilot Manifest v1 | Draft / live QA passed | Historical Gold＋NBA Official season schedule；30 場 exact tip-off、180 no-price slots、exact 1,800-credit plan。 |

PR #61 已因與 #60 重複而關閉；嚴格驗證已整合回 #60，不存在第二套 manifest 主線。

### Next unique mainline

```text
驗證 latest-head regression 並合併 PR #60
→ 重新確認 The Odds API pricing / Terms / quota
→ 公開 exact maximum exposure = 1,800 credits
→ 停止並取得使用者明確付費核准
→ 私密連接 THE_ODDS_API_KEY
→ 只有之後才可執行 frozen 30-game source qualification pilot
```

### Known blockers

- PR #60 尚未合併。
- Historical Odds API 需要付費方案；尚未取得使用者對最高 1,800 credits 的明確核准。
- `THE_ODDS_API_KEY` 尚未提供或連接。
- 付費執行前仍須重新確認 provider pricing、Terms、quota 與資料使用邊界。
- 真實 bookmaker-level `observed_at` quotes 尚未取得。
- Point-in-time Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 尚未解鎖。
- Historical model 仍明顯輸給 Closing Market。

### Do Not Do

- 不自動建立帳號、訂閱、購買 credits 或產生費用。
- 未獲明確核准前，不呼叫 Historical paid endpoint。
- API key 不得寫入 commit、log、Artifact、錯誤訊息或下載檔。
- 不繞過 401、403、429、登入、付款或 access control。
- 不替換 frozen 失敗比賽或手挑日期補 coverage。
- 不把 T-6h、T-24h 或 provider first-seen 冒充 true Opening。
- 不用 future snapshot 補較早缺失 snapshot。
- 不混用不同 bookmaker 或不同 provider snapshot 的兩側價格。
- Qualification pilot 不計算 edge、EV、ROI、CLV、Drawdown、bet count 或 profit ranking。
- Primary bookmaker 只按 coverage 與固定 key 排序，不按模型結果或價格選擇。
- Public repo／Artifact 不保留 raw odds JSON、quote-level rows、價格或可下載 odds archive。
- 已拒絕的 injury candidate 不得回到市場模型；使用 frozen baseline-only path。
- 不重做 odds schema、bookmaker schema、no-vig boundary 或 source registry。
- Closing-only benchmark 不得當 executable market backtest。
- 未完成 PIT odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- CI 綠燈只代表執行成功，必須讀 Artifact QA。
- 正式 Stake 維持 0。

## Canonical Roadmap

```text
1. Historical Gold and baseline model
2. Official injury data and feature-ready matchups
3. Expected Minutes Accuracy Audit
4. Injury Feature Walk-forward Holdout
5. Real Timestamped Odds Acquisition
6. Point-in-time Odds Join and Market Backtest
7. CLV / EV / ROI / Drawdown
8. Betting Decision Layer
```

目前節點：

```text
Step 5 — Exact no-price Timestamped Odds pilot manifest completed in PR #60
→ pending merge and explicit paid-access approval
```

## Core Status

| Module | Status | Formal conclusion |
|---|---|---|
| Historical Gold | Completed | 5,824 matchup rows；strict PIT violations 0。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 OOF；Log Loss / Brier 小幅且跨 Fold 優於 Elo。 |
| Calibration Gate | Completed | Platt / Isotonic 未穩定改善，保留 Raw。 |
| Closing Market Benchmark | Model lost | 模型明顯輸給 Closing Market。 |
| Market Residual v1 | Negative Result | 100% Closing Market、0% model residual。 |
| Rest / Travel v1 | Negative Result | Untouched holdout 未通過。 |
| Expected Minutes Audit v3 | **ACCURACY_PASS** | 所有預先宣告的結構、樣本與數值 gates 通過。 |
| Injury Feature Holdout v1 | **VALID_NEGATIVE_RESULT** | 結構通過；固定兩特徵 candidate 未達跨 Fold promotion gates。 |
| Injury candidate | Rejected | 後續只使用 frozen baseline-only path。 |
| Timestamped Odds Acquisition Policy v1 | Completed | PR #57 已鎖定 source、no-spend、quota、snapshots 與 storage contract。 |
| Timestamped Odds Adapter v1 | Completed / offline | PR #59；112 policy checks passed；正式 access state `ACCESS_NOT_PROVIDED`。 |
| Exact Pilot Manifest v1 | **Live QA passed / PR #60 Draft** | 30 exact games、180 slots、180 unique timestamps、exact 1,800-credit plan。 |
| Paid qualification pilot | Blocked | 需要使用者費用核准與 private `THE_ODDS_API_KEY`。 |
| Production Backfill | Blocked | 需要 qualification pass、offline production manifest 與另一次 cost approval。 |
| Market Backtest | Blocked | 尚無 executable PIT odds join。 |
| Betting Decision Layer | Blocked | Stake = 0。 |

## Historical Model Evidence

```text
Walk-forward OOF games: 3,688
Logistic + Elo Log Loss: 0.631306
Elo Log Loss: 0.634301
Logistic + Elo Brier: 0.220567
Elo Brier: 0.221949
```

Closing Market benchmark：

| Metric | Model | Closing |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

## Expected Minutes Audit v3

```text
PR #53 — predeclaration
PR #54 — execution
Formal state: ACCURACY_PASS
```

```text
MAE: 5.120902 <= 6.5
RMSE: 6.693908 <= 9.0
Median AE: 4.093886 <= 5.5
Absolute bias: 0.668968 <= 2.0
Starter MAE: 4.663676 <= 6.5
Bench MAE: 5.792521 <= 7.5
10+ history MAE: 5.092724 <= 6.25
```

此結果不證明 injury feature 或投注價值。

## Injury Feature Holdout v1

```text
PR #55 — predeclaration
PR #56 — execution
Formal state: VALID_NEGATIVE_RESULT
Market path: frozen baseline-only
```

| Population | Baseline LL | Candidate LL | Gain |
|---|---:|---:|---:|
| Feb development — 65 | 0.657411 | 0.667960 | **-0.010549** |
| Mar-Apr final — 104 | 0.589324 | 0.586426 | **+0.002898** |
| Combined — 169 | 0.615511 | 0.617785 | **-0.002274** |

Final fold 改善只保留為診斷，不推翻 combined negative decision。

## Timestamped Odds Acquisition v1 Contract

Existing assets must be reused：

```text
data/templates/point-in-time-odds-template.csv
scripts/build_point_in_time_odds.py
docs/point-in-time-odds-layer-v1.md
data/historical-odds-source-registry.json
.github/workflows/validate-point-in-time-odds.yml
Closing-only benchmark
proportional no-vig boundary
```

Candidate source scope：

```text
The Odds API Historical v4
basketball_nba
region: us
market: h2h only
decimal odds
paid historical access
secret: THE_ODDS_API_KEY
```

Frozen targets：

```text
T-6h / T-3h / T-1h / T-30m / T-5m / Closing
```

Opening 不屬於 v1，也不得推定。

Frozen qualification pilot：

```text
30 deterministic games
10 per season: 2021-22 / 2022-23 / 2023-24
6 game slots per game
maximum 180 slots
maximum 1,800 credits
market metrics forbidden
```

Decision states：

```text
ACCESS_NOT_PROVIDED
SOURCE_QUALIFICATION_BLOCKED
NO_QUALIFIED_BOOKMAKER
QUALIFIED_FOR_PRODUCTION_MANIFEST
```

即使 qualified，也只允許 offline production manifest 與 cost preflight。

## Timestamped Odds Adapter v1 — PR #59

```text
scripts/qualify_timestamped_odds_v1.py
scripts/run_timestamped_odds_qualification_v1.py
```

Latest validation：

```text
workflow run: 29638171563
artifact id: 8427770023
digest: sha256:420202ffb077869695e598d9052b722211318d2e9dad579df3b41e8706eb0c52
policy checks: 112 / 112
manifest slots tested: 180
maximum quota tested: 1,800
Opening labels: 0
formal access state: ACCESS_NOT_PROVIDED
```

Hardened offline checks：

- exact home / away / scheduled-tipoff identity;
- reject wrong tipoff, future provider snapshot and ambiguous event;
- bookmaker `last_update <= provider_snapshot < tipoff`;
- same-book two-sided h2h only;
- coverage-only stable-key tie-break;
- quota-header and response-hash provenance;
- no HTTP client and no paid source call.

## Frozen Pilot Manifest v1 — PR #60

### Failed per-game official path retained

```text
workflow run: 29638960721
Historical Gold matches: 30 / 30
NBA Official LiveData per-game requests: 30
HTTP 403: 30 / 30
paid odds-provider calls: 0
```

此失敗沒有被繞過，也沒有替換 sample。Schedule metadata 改由低頻 NBA Official season schedule files 取得。

### Successful official season schedule result

```text
workflow run: 29639184035
artifact: timestamped-odds-pilot-manifest-v1
artifact id: 8428065745
digest: sha256:d049e340163142d40e09ea19d339055707670cd571ca812c7e6846cf67d9e02c
formal state: PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED
```

Coverage／QA：

```text
Historical Gold matches: 30 / 30
Gold duplicates: 0
Gold missing / identity mismatch: 0
Official season source requests: 3
Official season source success: 3 / 3
Official source hashes: 3
Official schedule games: 30 / 30
Game schedule failures: 0
Games per season: 10 / 10 / 10
Game slots: 180
Slots per season: 60 / 60 / 60
Snapshot labels: 30 each × 6 labels
Unique request timestamps: 180
Dedup request savings: 0
Exact planned quota: 1,800 credits
Opening labels: 0
Raw official JSON retained: 0
Player / score / bookmaker / price fields retained: 0
Paid odds-provider calls: 0
Real quotes downloaded: 0
Market metrics calculated: false
```

Current permissions：

```text
manifest_structurally_ready: true
access_state: ACCESS_NOT_PROVIDED
ready_for_paid_qualification_execution: false
paid_execution_requires_explicit_user_approval: true
paid_execution_requires_private_secret: true
ready_for_production_backfill: false
ready_for_market_backtest: false
ready_for_clv_ev_roi: false
ready_for_betting_edge_claim: false
formal_stake: 0
```

## Next Exact Task

```text
Validate latest PR #60 head and full regression suite
→ merge exact no-price manifest
→ revalidate provider price / Terms / quota
→ present exact maximum exposure: 1,800 credits
→ obtain explicit user approval before any paid execution
```

## Important Recent PRs

```text
#52 Expanded Participation Census
#53 / #54 Expected Minutes Audit v3
#55 / #56 Injury Holdout v1
#57 Timestamped Odds Acquisition Policy v1
#59 Timestamped Odds Adapter v1 — merged
#60 Frozen Timestamped Odds Pilot Manifest v1 — Draft / live QA passed
#61 duplicate manifest PR — closed
```
