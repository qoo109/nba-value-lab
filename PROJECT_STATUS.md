# NBA Value Lab — Project Status

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 main、合併 PR、Actions 與 Artifact QA 是正式 Source of Truth；舊 handoff 與聊天紀錄只保留歷史脈絡。

## Current Control Block

### Latest Main SHA

```text
926fd8355602935f51a5fe38f82ba2fa37c825fb
```

最新已合併：

```text
PR #57 — Predeclare Real Timestamped Odds Acquisition v1
```

### Open PR

| PR | 狀態 | 用途 |
|---|---|---|
| #59 — Offline Timestamped Odds Qualification Adapter v1 | Draft | Parser、no-price manifest、synthetic tests 與 `ACCESS_NOT_PROVIDED`；不讀 key、不呼叫 paid endpoint。 |

### Next unique mainline

```text
驗證並合併 PR #59
→ 從 Historical Gold 產生 frozen 30-game exact schedule manifest
→ 固定 180 requested timestamps 與 <= 1,800 credits
→ 停在 paid pilot 前
→ 只有使用者明確核准費用並提供 THE_ODDS_API_KEY 後才執行
```

### Known blockers

- PR #59 尚未合併。
- Frozen 30-game sample 的 exact scheduled tipoff manifest 尚未完成。
- Historical API 需要付費方案；尚未取得使用者費用核准。
- `THE_ODDS_API_KEY` 尚未提供或連接。
- 正式執行前仍須重新確認價格、Terms、quota 與資料使用邊界。
- 真實 bookmaker-level `observed_at` quotes 尚未取得。
- Point-in-time Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 尚未解鎖。
- Historical model 仍明顯輸給 Closing Market。

### Do Not Do

- 不自動建立帳號、訂閱、購買 credits 或產生費用。
- 未獲明確核准前，不呼叫 Historical paid endpoint。
- API key 不得寫入 commit、log、Artifact、錯誤訊息或下載檔。
- 不繞過 401、403、429、登入、付款或 access control。
- 不把 T-6h、T-24h 或 provider first-seen 冒充 true Opening。
- 不用 future snapshot 補較早缺失 snapshot。
- 不混用不同 bookmaker 或不同 provider snapshot 的兩側價格。
- Qualification pilot 不計算 edge、EV、ROI、CLV、Drawdown、bet count 或 profit ranking。
- Primary bookmaker 只按 coverage 與固定 key 排序，不按模型結果或價格選擇。
- Public repo／Artifact 不保留 raw JSON、quote-level rows、價格或可下載 odds archive。
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
Step 5 — Offline Timestamped Odds adapter and exact manifest preparation
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
| Timestamped Odds Acquisition Policy v1 | Completed | PR #57 已鎖定來源、no-spend、quota、snapshot 與 storage contract。 |
| Timestamped Odds Adapter v1 | Offline validation in progress | PR #59 Draft；正式 access state 為 `ACCESS_NOT_PROVIDED`。 |
| Paid qualification pilot | Blocked | 需要 exact manifest、費用核准與 `THE_ODDS_API_KEY`。 |
| Production Backfill | Blocked | 需要 pilot pass、offline production manifest 與另一次 cost approval。 |
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
6 requests per game
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
```

Offline capabilities：

- build a no-price request manifest from exact schedule rows;
- parse supplied Historical v4 payloads;
- exact home/away mapping only;
- reject future snapshots and ambiguous events;
- separate provider snapshot, bookmaker last_update and fetched_at;
- keep two sides from one bookmaker / one h2h market;
- calculate overround and aggregate coverage;
- emit `ACCESS_NOT_PROVIDED` without reading a secret or calling the provider.

Current formal state：

```text
ACCESS_NOT_PROVIDED
provider requests: 0
quotes downloaded: 0
API key read: false
paid endpoint called: false
subscription or purchase created: false
market metrics calculated: false
ready_for_production_manifest: false
ready_for_market_backtest: false
formal_stake: 0
```

## Next Exact Task

```text
Validate and merge PR #59
→ derive exact frozen 30-game scheduled tipoffs from Historical Gold
→ build the 180-row no-price request manifest
→ verify quota <= 1,800 credits
→ stop before paid execution
```

## Important Recent PRs

```text
#52 Expanded Participation Census
#53 / #54 Expected Minutes Audit v3
#55 / #56 Injury Holdout v1
#57 Timestamped Odds Acquisition Policy v1
#59 Timestamped Odds Adapter v1 — Draft
```
