# NBA Value Lab — Formal Handoff

更新日期：2026-07-18（Asia/Taipei）  
目前定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

## Current Control Block

### Latest Main SHA

```text
332d199122ad61815503d1165c81a696c28dbfee
```

### Latest merged PR

```text
PR #60 — Build Frozen Timestamped Odds Pilot Manifest v1
```

### Open research PRs

```text
none
```

### Next unique mainline

```text
revalidate The Odds API paid-plan / Historical API terms
→ disclose exact qualification exposure: 180 requests / 1,800 credits
→ obtain explicit user authorization for paid qualification
→ privately connect THE_ODDS_API_KEY
→ execute only the frozen 30-game source-qualification pilot
→ delete raw / quote-level temporary files
→ read aggregate source and bookmaker QA
```

### Known blockers

- Historical API access is paid-plan only.
- User has not authorized any subscription, purchase or use of up to 1,800 credits.
- `THE_ODDS_API_KEY` is not connected.
- No real bookmaker-level historical quote has been downloaded.
- Point-in-time Odds Join, Market Backtest, CLV, EV, ROI and Drawdown remain blocked.
- Historical model remains worse than the Closing Market benchmark.

### Do Not Do

- Do not create an account, subscribe, buy credits or incur charges without explicit user approval.
- Do not expose the API key in repository files, logs, Artifacts or error messages.
- Do not bypass 401, 403, 429, payment or access controls.
- Do not replace frozen games or dates after source coverage is observed.
- Do not infer Opening; v1 contains only T-6h, T-3h, T-1h, T-30m, T-5m and Closing.
- Do not fill a missing quote from a future snapshot, another bookmaker or another game.
- Do not calculate edge, EV, ROI, CLV, Drawdown, bet count or bookmaker profit during qualification.
- Do not select a bookmaker by outcomes, prices or model performance.
- Do not publish raw provider JSON, quote-level rows, prices or a downloadable odds archive.
- Do not reintroduce the rejected injury candidate; the market path remains frozen baseline-only.
- Formal Stake remains 0.

## Source of Truth order

1. Latest `main`, `PROJECT_STATUS.md`, merged PRs, Actions and Artifact QA.
2. This handoff.
3. Older handoffs and project reports.
4. V/G specifications as design governance only.
5. Chat history as decision context only.

## Completed evidence

### Historical model

```text
Historical Gold matchup rows: 5,824
Walk-forward OOF games: 3,688
Logistic + Elo Log Loss: 0.631306
Elo Log Loss: 0.634301
Logistic + Elo Brier: 0.220567
Elo Brier: 0.221949
```

Closing benchmark:

```text
matched games: 1,894
model Log Loss: 0.6421
Closing Market Log Loss: 0.6167
model Brier: 0.2250
Closing Market Brier: 0.2139
```

Formal conclusion: model probability quality slightly improves Elo, but the model clearly loses to Closing Market and has no demonstrated betting edge.

### Expected Minutes Accuracy Audit v3

```text
PR #53 predeclaration
PR #54 execution
formal state: ACCURACY_PASS
```

```text
overall MAE: 5.120902
RMSE: 6.693908
median AE: 4.093886
absolute bias: 0.668968
starter MAE: 4.663676
bench MAE: 5.792521
10+ history MAE: 5.092724
```

This validates the frozen prior-only Expected Minutes proxy gates only.

### Injury Feature Holdout v1

```text
PR #55 predeclaration
PR #56 execution
formal state: VALID_NEGATIVE_RESULT
market model path: frozen baseline-only
```

```text
combined forward Log Loss gain: -0.002274
combined Brier gain: -0.000010
combined bootstrap P(Log Loss gain > 0): 0.4023
```

The exact two-feature injury candidate was rejected and must not be tuned repeatedly until positive.

## Timestamped Odds milestone

### PR #57 — Acquisition policy

Frozen:

```text
source candidate: The Odds API Historical v4
sport: basketball_nba
region: us
market: h2h only
format: decimal
pilot games: 30
seasons: 2021-22 / 2022-23 / 2023-24
snapshots per game: 6
maximum slots: 180
maximum credits: 1,800
Opening: not included and not inferred
market model path: frozen baseline-only
```

### PR #59 — Offline adapter

```text
workflow run: 29638171563
artifact id: 8427770023
digest: sha256:420202ffb077869695e598d9052b722211318d2e9dad579df3b41e8706eb0c52
policy checks: 112 / 112
formal access state: ACCESS_NOT_PROVIDED
```

Validated without an HTTP client:

- exact home / away / scheduled-tipoff identity;
- provider snapshot at or before requested time;
- bookmaker `last_update <= provider_snapshot < tipoff`;
- same-book two-sided h2h outcomes;
- quota-header and response-hash provenance;
- coverage-only bookmaker ranking;
- no future fallback, fuzzy identity or inferred Opening.

### PR #60 — Exact no-price pilot manifest

Latest-head evidence:

```text
PR merge SHA: 332d199122ad61815503d1165c81a696c28dbfee
workflow run: 29639270948
artifact: timestamped-odds-pilot-manifest-v1
artifact id: 8428103801
digest: sha256:31aa2acafe9834a09720486c96413d8da863f35623de78ef8ef1da8b6432a2a4
formal state: PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED
```

Artifact QA:

```text
Historical Gold matches: 30 / 30
Gold duplicate / missing / identity errors: 0
NBA Official season schedule sources: 3 / 3
Official schedule games: 30 / 30
Schedule failures: 0
Games per season: 10 / 10 / 10
Game/snapshot slots: 180
Slots per season: 60 / 60 / 60
Unique requested_at timestamps: 180
Dedup savings: 0
Exact planned requests: 180
Exact planned quota: 1,800 credits
Opening labels: 0
Raw official JSON retained: 0
Player / score / bookmaker / price fields retained: 0
Odds API key read: false
Paid odds-provider requests: 0
Real quotes downloaded: 0
Subscription or purchase created: false
Market metrics calculated: false
Structural blockers: 0
```

The first per-game NBA LiveData schedule attempt remains recorded as a 30/30 HTTP 403 transport failure. It was not bypassed. The successful canonical schedule route uses three low-frequency NBA Official season schedule files while preserving the same frozen games and snapshot contract.

Complete latest-head regression suite: all existing Wave 1/2/3, Participation, Expanded Census, Expected Minutes Audits v1-v3, Injury Holdout and Timestamped Odds workflows completed successfully.

## Current provider access revalidation

Checked on 2026-07-18 against official provider pages:

```text
Historical odds access: paid plans only
Historical request cost: 10 credits per region per market
Frozen request count: 180
Frozen maximum credit exposure: 1,800
Current entry paid plan displayed: 20,000 credits for US$30 per month
Subscription or purchase made: false
```

Official references:

- `https://the-odds-api.com/historical-odds-data/`
- `https://the-odds-api.com/liveapi/guides/v4/`
- `https://the-odds-api.com/#pricing`
- `https://the-odds-api.com/terms-and-conditions.html`

Pricing and Terms must be checked once more immediately before any purchase or paid execution. Provider data must not be repackaged or redistributed as a standalone data product; raw and normalized quote rows remain restricted and temporary for qualification.

## Formal permissions after PR #60

```text
manifest_structurally_ready: true
access_state: ACCESS_NOT_PROVIDED
ready_for_paid_qualification_execution: false
explicit user approval required: true
private THE_ODDS_API_KEY required: true
ready_for_production_backfill: false
ready_for_point_in_time_odds_join: false
ready_for_market_backtest: false
ready_for_clv_ev_roi_drawdown: false
ready_for_betting_edge_claim: false
formal_stake: 0
```

## Exact approval question for the next turn

The next operation can incur a provider subscription cost and consume up to **1,800 credits**. The project must stop until the user explicitly approves that maximum exposure and independently provides a private API key through a secret connection. Approval of the 30-game qualification pilot does not approve the later 3,688-game production backfill.
