# NBA Value Lab — Project Status

狀態核對日期：2026-07-24  
研究定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。

## Latest G1.2.0 Milestone

```text
G1.2.0 live decision output: IMPLEMENTED / FIXTURE VALIDATED / REAL GOVERNED INPUT VALIDATION REQUIRED
G1.2.0 validation formal state: G1_2_0_LIVE_OUTPUT_IMPLEMENTATION_VALID
G1.2.0 validation run: 30025555150
G1.2.0 validation artifact: 8571205516
G1.2.0 validation artifact digest: sha256:0d5d4d65f8b50e9bc81057b1aaa96620d2f3b40c5a75df66357cbe58432b8ccb
G1.2.0 season resolver: season=2026-27 + competition_type=regular_season
pre-trigger primary: G1.1.1
pre-trigger parallel: G1.2.0 scheduled shadow
post-trigger primary: G1.2.0 EV-primary
post-trigger parallel: G1.1.1 control shadow
prediction record schema: 1.4.0
current real-input status: BLOCKED / REAL GOVERNED INPUT NOT AVAILABLE
formal Stake: 0
next unique mainline: VALIDATE_G1_2_0_END_TO_END_WITH_REAL_GOVERNED_2026_27_T60_INPUT
```

## Latest Research Milestone — PR #179 through PR #185

```text
frozen 2025-26 forward scoring: VALID / 1,230 GAMES / NO REFIT
private model-market time-banded sensitivity: VALID / 1,110 MATCHES
market comparison result: NO_EVIDENCE_FROZEN_MODEL_BEATS_PRIVATE_MARKET_ARCHIVE
model-market gap review: VALID / PRESERVE FROZEN BASELINE
prior-only rotation feature design: VALID
prior-only rotation source: VALID / 1,230 OF 1,230 GAMES
private player-game source rows: 43,265
public player rows: 0
real rotation feature build: NOT YET EXECUTED
current unique research mainline: BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_V1_WITHOUT_MODEL_RETRAINING
formal Stake: 0
```

PR #179 scored the frozen `walk-forward-v2` model on all 1,230 governed 2025-26 games without training, refitting, calibration, or market features. PR #180 joined 1,110 valid two-sided pre-tip Moneyline games and found the proportional no-vig market had lower Log Loss and Brier Score in every predeclared time-error band. PR #181 preserved the frozen baseline and market-backtest lock. PR #183 validated the prior-only rotation feature design, and PR #185 qualified the deidentified official 2025-26 player minutes/starter source. The next step may build private prior-only rotation features and aggregate QA only; it does not authorize residual promotion, model retraining, strict T-60 qualification, market backtesting, betting-edge claims, or Stake above `0`.

## Current Control Block

```text
current work mode: OFFSEASON_DATA_CONSTRUCTION
active offseason G: G1.1.1
scheduled next G: G1.2.0 / first 2026-27 regular-season game with complete T-60 data gate
real governed 2026-27 T-60 input: NOT AVAILABLE
legacy source role: ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
candidate cross-source scientific gates: PASS
candidate formal result: REFERENCE COVERAGE COMPLETE / MARKET EVALUATION NOT AUTHORIZED
Gold/Silver reconciliation result: SOURCE GAP RESOLVED VIA OFFICIAL CDN PBP RECOVERY
reference coverage: 5,826 / 5,826
2023-24 Silver games: 1,230
2023-24 games without team features before recovery: 2
2023-24 games without team features after recovery: 0
root-cause implementation: VALIDATED
root-cause request: EXECUTION ATTEMPTED / BLOCKED BY RUNNER FIELD-PATH BUG
real root-cause execution count: 1 / 1
root-cause incident run: 29888939524
root-cause incident artifact: 8517546804
root-cause incident error: KeyError team_inference_failures
root-cause retry request 002: EXECUTED / CONSUMED / SOURCE GAP CONFIRMED
root-cause retry 002 execution count: 1 / 1
root-cause retry 002 run: 29890527281
root-cause retry 002 artifact: 8518081820
root-cause retry 002 outcome: HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED
source archive reconciliation request: EXECUTED / CONSUMED
source archive reconciliation execution count: 1 / 1
source archive reconciliation run: 29901869841
source archive reconciliation artifact: 8522225397
source archive reconciliation artifact digest: sha256:2b42dca052d331bf94e31568b24492092beb00fef352405601fd812a8603b334
source archive reconciliation formal state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_AGGREGATE_VALIDATION_PASS
source archive reconciliation decision: SOURCE_ARCHIVE_GAP_STABLE
source archive reconciliation repeat execution: disabled
source gap exception manifest: VALIDATED / AGGREGATE ONLY
source gap exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
source gap exception historical count: 2
source gap exception remaining count: 0
source gap exception recovery: PASS / OFFICIAL CDN PBP
source gap exception patch allowed: false
source gap exception integration policy: VALIDATED / DESIGN ONLY
source gap exception integration implementation design: VALIDATED
source gap exception integration implementation: VALIDATED / SYNTHETIC ONLY
implementation contract: PURE_AGGREGATE_REPORT_TRANSFORMER
production integration module created: true
synthetic mutation tests: 17 / PASS
real-reference validation request design: VALIDATED
real-reference validation request: EXECUTED / PASS / CONSUMED
real-reference validation request id: HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001
real-reference validation request execution count: 1 / 1
real-reference validation approval granted: true
real-reference validation execution enabled: false
real-reference validation executed: true
real-reference validation repeat execution: disabled
real-reference validation formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_PASS_CONSUMED
real-reference validation result record: data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.json
real-reference validation result payload SHA-256: sha256:048149cd058c74c1ab441a99f3a4eec0972668500e469ff81ce663b3e5264340
real-reference validation recording PR: 131
real-reference validation recording merge: ce39a8f39032c5aebe07c2c6734ebc58b02e2108
real-reference validation result QA run: 29972975866
real-reference validation result QA artifact: 8550389215
real-reference validation result QA artifact digest: sha256:5ce4c745b0262b30d9d1f390338b2bbce3bb9a60ef4428e3268d634f274de081
official CDN recovery run: 29976204693
official CDN recovery Artifact: 8551587005
official CDN recovery Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
official CDN recovery recording PR: 133
official CDN recovery recording merge: 98bcb2538070eb57bba2ce79920262262c0924ef
eligible Historical Gold corpus for future policy design: 5,826
documented exceptions excluded from Gold eligibility: 0
raw Historical Silver games: 5,826
raw Historical Gold matchups: 5,826
raw missing Gold for Silver: 0
documented source gap exceptions remaining: 0
unexplained missing after recovery: 0
Gold dataset complete for governed five-season scope: true
complete corpus freeze policy: VALIDATED / DESIGN ONLY
complete corpus freeze policy id: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001
complete corpus freeze policy formal state: HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED
complete corpus freeze policy recording PR: 135
complete corpus freeze policy recording merge: b6edf9b8acaf51b1287d6976c6e42cac056dc726
complete corpus freeze policy validation run: 29978555275
complete corpus freeze policy validation artifact: 8552326235
complete corpus freeze policy validation digest: sha256:96fdcee4b39f6ca03b9597677aa01db2e47b15d6d8f780f2e4525be978dd3722
freeze manifest implementation design: VALIDATED / DESIGN ONLY
freeze manifest implementation design id: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-IMPLEMENTATION-DESIGN-2026-07-23-001
freeze manifest implementation design recording PR: 137
freeze manifest implementation design recording merge: 1730859888bd21cf7727ef6c5cbf348fb7aeddeb
freeze manifest implementation design validation run: 29982518227
freeze manifest implementation design validation artifact: 8553727483
freeze manifest implementation design validation digest: sha256:b752398847700bfc4a09831bbab069451606ecce2615cdcb511b5ddab06d3dc7
freeze manifest implementation module created: true
freeze manifest synthetic validation: PASS / 20 OF 20
freeze manifest synthetic implementation recording PR: 139
freeze manifest synthetic implementation recording merge: b561c941b5fc27a0bda3fa790244ff92c35b5c0b
freeze manifest synthetic validation run: 29984329419
freeze manifest synthetic validation job: 89132779309
freeze manifest synthetic validation artifact: 8554394051
freeze manifest synthetic validation digest: sha256:1ecf4862ff87c3eb23ccb8d6b1c9860a229b54b8c76c469930dd2723da213f6f
real Artifact execution request design: VALIDATED / DESIGN ONLY
real Artifact execution request design recording PR: 141
real Artifact execution request design recording merge: 5c6431110b7085dec1663cf6303df5393fd4dd97
real Artifact execution request design validation run: 29986783982
real Artifact execution request design validation job: 89140319716
real Artifact execution request design validation artifact: 8555320565
real Artifact execution request design validation digest: sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9
real Artifact execution request design validated: true
real Artifact execution request created: true
real Artifact execution request validation: PASS / AWAITING EXPLICIT USER APPROVAL
real Artifact execution request validation PR: 144
real Artifact execution request validation merge: 0ac67d836a6380c56565d9d8ac12465f260db65d
real Artifact execution request validation run: 29992891138
real Artifact execution request validation job: 89159516469
real Artifact execution request validation artifact: 8557702959
real Artifact execution request validation digest: sha256:bbea63ba827b29f10b14f76290eb67d47e9d3cb219f2b97219470616a1d24508
real Artifact execution request synthetic tests: 20 / 20 PASS
real Artifact execution request mutation tests: 35 / PASS
real Artifact freeze workflow created: true / RETIRED AFTER CONSUMPTION
real Artifact execution approved: true
real Artifact execution count: 1 / 1
real Artifact execution run: 30000293169
real Artifact execution job: 89183633328
real Artifact execution artifact: 8560678596
real Artifact execution artifact digest: sha256:a6bfa2afbd2aef32f7e3f87078caaf620d94c744cf1eec74760d20ae4d0d5531
real Artifact execution formal outcome: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_PASS_CONSUMED
real Artifact request consumed: true
real Artifact repeat execution: disabled
semantic freeze manifest created: true
semantic freeze manifest SHA-256: sha256:dcd9522e7ee55669d5b4fd413e424aa01ac9182a1330d51c6f9bf6b13ad8059d
semantic corpus SHA-256: sha256:c0c48fe17d843714209c822422b9675eadbff8b6be048782a599b2085bc20cbd
corpus freeze executed: true / SEMANTIC MANIFEST ONLY
adopted Gold Artifact expiry: 2026-08-06T03:14:00Z
timestamped bookmaker odds: POLICY ONLY / REAL OBSERVED_AT DATA NOT ACQUIRED
bloombet public review: COMPLETED / BLOCKED
bloombet free tier public claim: USD 0 / 500 requests per month / no credit card / NBA + NFL / live + historical / 15+ providers
bloombet public response schema: NOT VERIFIED
bloombet provider timestamp semantics: NOT VERIFIED
bloombet historical coverage: NOT VERIFIED
bloombet terms, retention and redistribution rights: NOT VERIFIED
bloombet zero-cost schema probe request design: VALIDATED / AWAITING EXPLICIT USER APPROVAL
bloombet account creation authorized: false
bloombet private API key connection authorized: false
bloombet probe execution count: 0 / 1
bloombet schema probe: DEFERRED BY USER / NO EXECUTION
hoopsapi public review: COMPLETED / FORWARD-ONLY CANDIDATE
hoopsapi free tier public claim: 10 requests per day / no card / current multi-provider markets
hoopsapi historical snapshots on free tier: false
hoopsapi provider observed_at in public example: false
hoopsapi raw odds redistribution: PROHIBITED BY PUBLIC TERMS
hoopsapi provider requests executed: 0
forward odds collector design: VALIDATED / SOURCE-AGNOSTIC / PRIVATE
forward collector quote schema: schemas/private-forward-odds-quote-v1.schema.json
forward collector fetched_at substitution: PROHIBITED
forward collector public quote rows: PROHIBITED
forward collector network client: false
forward collector provider requests executed: 0
forward odds collector offline core: VALIDATED / SYNTHETIC ONLY
forward collector offline SQLite writes: TEMPORARY PRIVATE ONLY
forward collector offline synthetic tests: 12 / PASS
forward collector offline network client: false
forward collector offline provider requests executed: 0
forward collector offline real quotes retained: 0
first provider adapter qualification gate: VALIDATED / HOOPSAPI / RUNTIME BLOCKED
hoopsapi synthetic adapter shell: AUTHORIZED
hoopsapi provider runtime qualified: false
hoopsapi point-in-time qualified: false
hoopsapi account, terms, key and requests: NOT AUTHORIZED
first provider adapter requests executed: 0
injury panel activation: 41 independent games / 31 T-60 selected / below 100-game gate
team submission completeness ledger: REQUIRED BEFORE FORMAL INJURY HOLDOUT
silver builder repair required: false
canonical repository: qoo109/nba-value-lab / SINGLE_ACTIVE_WORKSPACE
odds history hub: ARCHIVED_IN_MAIN / V0.19 / NO_EXTERNAL_DEPENDENCY
odds history hub snapshot: backups/nba-odds-history-hub-v0.19 @ 5d2659efb2fee1cf28816ebfc65ddac929d75d6a
formal stake: 0
```

## Next Unique Mainline

```text
BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_V1_WITHOUT_MODEL_RETRAINING
```

Current status:

```text
READY — QUALIFIED PRIVATE SOURCE AVAILABLE / FEATURE BUILD NOT YET EXECUTED
```

Required point-in-time fallback:

```text
source_game_date_et < target_game_date_et
```

The feature build must exclude same-day, target-game, and future player rows. It may emit private feature rows and aggregate QA only. Activation requires at least 1,000 feature-ready games, at least 80% coverage, all 30 teams, at least five months, zero source-time violations, zero identity ambiguity, and the predeclared missingness and residual-direction audits. Passing those gates still does not authorize model retraining.

Longer-term blocked milestone:

```text
VALIDATE_G1_2_0_END_TO_END_WITH_REAL_GOVERNED_2026_27_T60_INPUT
```

That milestone remains blocked by the absence of legally governed provider-origin `observed_at` bookmaker odds. HoopsAPI and The Odds API work completed to date is public-review or synthetic-only and does not qualify strict T-60, Historical Backfill, Frozen Gold PIT joins, or formal Market Backtesting.

## Completed Evidence

### First provider private forward adapter qualification gate

```text
formal state: FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_VALIDATED
candidate provider: hoopsapi_free_forward_collection
gate design: VALIDATED
synthetic adapter shell: AUTHORIZED
runtime schema qualification: false
provider runtime qualified: false
provider point-in-time qualified: false
collector_fetched_at may substitute provider observed_at: false
required pre-qualification time authority: unverified
required pre-qualification observed_at: null
required pre-qualification point-in-time eligible: false
user must personally accept provider terms: true
account creation authorized: false
provider terms acceptance authorized: false
API key connection authorized: false
provider request execution authorized: false
initial preflight request cap if separately approved: 3
provider requests executed: 0
real quotes retained: 0
public raw quote rows: PROHIBITED
historical backfill qualified: false
frozen Gold PIT join qualified: false
market metrics executed: false
formal Stake: 0
next unique sub-mainline: IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1
```

The gate permits only a HoopsAPI-shaped synthetic adapter shell. It does not authorize account creation, provider terms acceptance, secret connection, network requests, real quote ingestion or point-in-time qualification. Missing provider timestamp semantics must remain `unverified` with null observed_at and point-in-time eligibility false.

### Source-agnostic private forward odds collector offline core

```text
formal state: SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_VALIDATED
implementation: OFFLINE / SYNTHETIC ONLY
canonical module: scripts/private_forward_odds_collector_v1.py
timestamp authority validation: ENABLED
collector_fetched_at may substitute provider observed_at: false
deterministic row hash: ENABLED
duplicate handling: PASS
quarantine: PASS
temporary private SQLite write: PASS
synthetic contract tests: 12 / PASS
HTTP client included: false
secret reader included: false
scheduler included: false
provider requests executed: 0
real provider payloads processed: 0
real quotes retained: 0
public quote rows emitted: 0
market metrics executed: false
formal Stake: 0
next unique sub-mainline: IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1
```

The offline core validates timestamp authority, exact mapping eligibility, deterministic deduplication, quarantine and private SQLite writes using synthetic inputs only. It exposes only aggregate QA and cannot connect to a provider or unlock market evaluation.

### Source-agnostic private forward odds collector design

```text
formal state: SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_DESIGN_VALIDATED
direction: FORWARD ONLY
provider binding: NONE
canonical private quote schema: schemas/private-forward-odds-quote-v1.schema.json
collector_fetched_at may substitute provider observed_at: false
exact event mapping required for PIT eligibility: true
fuzzy or nearest-time mapping allowed: false
Closing-only substitution for T-60 or T-5: false
private normalized quote storage: REQUIRED
public quote-level rows: PROHIBITED
HTTP client included: false
secret reader included: false
provider requests executed: 0
real quotes retained: 0
market metrics executed: false
formal Stake: 0
next unique sub-mainline: IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1
```

The design preserves three distinct timestamp concepts: provider snapshot time, bookmaker last-update time and collector fetch time. Collector fetch time proves only receipt and can never be promoted to canonical `observed_at`. Rows with unverified provider-origin time remain private forward observations and are not point-in-time eligible.

### HoopsAPI Free public forward-collection review

```text
formal state: HOOPSAPI_FREE_PUBLIC_REVIEW_FORWARD_ONLY_CANDIDATE
free tier publicly claimed: 10 requests per day / no card
current markets publicly claimed: moneyline / handicap / over-under
public sample game_id and start_time: present
same-provider two-sided moneyline shape: present
quote-level observed_at in public example: false
full history and snapshots on free tier: false
paid Data plan required for history: EUR 249 per month / not authorized
raw odds resale or redistribution: prohibited by public Terms
qualified for historical backfill: false
qualified for frozen-Gold point-in-time join: false
structurally promising for private forward collection: true
forward collection authorized: false
account created: false
API key connected: false
provider requests executed: 0
market metrics executed: false
formal Stake: 0
```

HoopsAPI cannot repair the historical timestamped-odds gap because free access exposes current markets rather than full historical snapshots. Its public shape is sufficient to justify a provider-neutral private forward-collector design, but collector-generated `fetched_at` must remain explicitly distinct from a provider-origin timestamp. No account, key or request execution is authorized.

### BloomBet Free API public schema, terms and timestamp-semantics review

```text
formal state: BLOOMBET_FREE_API_PUBLIC_REVIEW_BLOCKED
public homepage reviewed: true
public API documentation landing page reviewed: true
free tier publicly claimed: USD 0 / 500 requests per month / no credit card
NBA and historical access publicly claimed: true
bookmaker/provider identity publicly claimed: true / 15+ providers
response schema verified: false
provider observed_at semantics verified: false
historical coverage verified: false
terms and retention rights verified: false
qualified for historical backfill: false
qualified for point-in-time join: false
qualified for market backtest: false
account created: false
API key connected: false
API requests executed: 0
market metrics executed: false
formal Stake: 0
```

Public marketing pages establish a promising zero-cost tier, but the publicly accessible material does not establish the request/response schema, provider-level timestamp meaning, historical retention window, or quote retention and redistribution rights required by the frozen qualification policy. A separate maximum-three-request schema probe has therefore been designed but remains disabled until explicit user approval and private secret setup.

### G1.2.0 EV-primary live output implementation and fixture validation

```text
PR: 153 / merged
merge commit: bcb66ba5b207d6a86cf87b3aeed18f3f3c2c0115
formal state: G1_2_0_LIVE_OUTPUT_IMPLEMENTATION_VALID
validation run: 30025555150
validation artifact: 8571205516
validation artifact digest: sha256:0d5d4d65f8b50e9bc81057b1aaa96620d2f3b40c5a75df66357cbe58432b8ccb
real governed 2026-27 T-60 validation executed: false
formal Stake: 0
```

The implementation, contract, executable T-60/T-5 fixtures, frontend routing, model registry and repository-hygiene boundaries passed. This does not substitute for a real governed 2026-27 regular-season T-60 input.

### Historical Gold 5,826 real Artifact semantic freeze execution

```text
formal outcome: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_PASS_CONSUMED
request ID: HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001
approval granted: true
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
workflow rerun allowed: false
executor retired: true
real Artifact read: true
semantic manifest created: true
corpus frozen by semantic manifest: true
market backtest executed: false
model retraining executed: false
formal Stake: 0
```

Execution evidence:

```text
approval recording PR: 146
approval recording merge: 5eb4bd9c11740ed0f68b5b3806ede24335796c6f
workflow run: 30000293169
job: 89183633328 / execute-once / success
source Artifact: 8551587005
source Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
output Artifact: 8560678596
output Artifact digest: sha256:a6bfa2afbd2aef32f7e3f87078caaf620d94c744cf1eec74760d20ae4d0d5531
output Artifact expiry: 2026-08-06T10:42:27Z
manifest SHA-256: sha256:dcd9522e7ee55669d5b4fd413e424aa01ac9182a1330d51c6f9bf6b13ad8059d
execution receipt SHA-256: sha256:a0b6ceba02d5cd7d4987dc293f1c41e3dd78d53f583ea5ab1474c469e17bd134
corpus semantic SHA-256: sha256:c0c48fe17d843714209c822422b9675eadbff8b6be048782a599b2085bc20cbd
```

Canonical aggregate result:

```text
Gold matchups: 5,826
Gold team-game rows: 11,652
seasons: 2019-20 through 2023-24
point-in-time violations: 0
duplicate matchup keys: 0
duplicate team-game keys: 0
database integrity: PASS
database SHA-256 unchanged: true
database modified: false
raw rows emitted: 0
```

Formal records:

- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-result-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-current-status-v2.json`
- `docs/historical-gold-5826-freeze-manifest-real-artifact-execution-result-v1.md`


### Historical Gold 5,826 real Artifact execution request validation — historical pre-execution snapshot

> Historical evidence only. This snapshot was superseded by the completed, consumed execution recorded above.

```text
formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
request ID: HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001
request valid: true
synthetic tests: 20 / 20 PASS
mutation tests: 35 / PASS
maximum execution count: 1
execution count: 0
request consumed: false
approval granted: false
execution enabled: false
execution workflow created: false
real Artifact downloaded: false
real Artifact read: false
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

Validation evidence:

```text
validation PR: 144
validation merge: 0ac67d836a6380c56565d9d8ac12465f260db65d
validated head: b0225215301e71b0f411810e8c1719ea5ea8d531
workflow run: 29992891138
job: 89159516469 / validate-request / success
Artifact: 8557702959
Artifact digest: sha256:bbea63ba827b29f10b14f76290eb67d47e9d3cb219f2b97219470616a1d24508
Artifact expiry: 2026-08-06T08:53:06Z
```

The request validator confirmed the exact Artifact binding, upstream evidence, expiry, aggregate-only privacy boundary and fail-closed mutations. It computed the approval SHA-256 bindings without downloading or reading the real Gold Artifact. Separate explicit user approval remains required before any executor may be created.

Formal records:

- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-current-status-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-validation-result-v1.json`
- `docs/historical-gold-5826-freeze-manifest-real-artifact-execution-request-validation-result-v1.md`


### Historical Gold 5,826 real Artifact execution request design

```text
formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED
exact Artifact ID: 8551587005
exact Artifact expiry: 2026-08-06T03:14:00Z
maximum execution attempts: 1
manual workflow_dispatch on main only: true
separate explicit user approval required: true
request consumed after any execution attempt: true
rerun allowed: false
automatic dispatch allowed: false
GitHub Artifact transport only: true
Silver database read allowed: false
request draft created: false
approval created: false
execution workflow created: false
real Artifact downloaded: false
real Artifact read: false
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

Validation evidence:

```text
design PR: 141
design merge: 5c6431110b7085dec1663cf6303df5393fd4dd97
validated head: f84a217b0f4b2d144c58032f5edc793a2b92553b
workflow run: 29986783982
job: 89140319716 / validate-request-design / success
Artifact: 8555320565
Artifact digest: sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9
Artifact expiry: 2026-08-06T06:59:00Z
```

The validated contract binds the exact adopted Artifact, exact three-file set and hashes, builder Git blob, separate approval evidence, one-time consumption, expiry fail-closed behavior, GitHub-Artifact-only transport, Silver no-read, Gold read-only execution and two-file aggregate output under 1 MiB. No request, approval or execution workflow was created.

Formal records:

- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-result-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-current-status-v1.json`
- `docs/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-result-v1.md`



### Historical Gold 5,826 freeze-manifest synthetic implementation validation

```text
formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALID
implementation module created: true
synthetic SQLite tests: 20 / 20 PASS
Gold matchups / team rows: 5,826 / 11,652
remaining source exceptions: 0
point-in-time violations: 0
real Artifact downloaded: false
real Artifact read: false
real execution workflow created: false
real execution approved: false
real execution count: 0
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

Validation evidence:

```text
recording PR: 139
recording merge: b561c941b5fc27a0bda3fa790244ff92c35b5c0b
validated head: 04fdbe44f642af85bc287a02a2f978f12bf62cb0
workflow run: 29984329419
job: 89132779309 / validate-synthetic-implementation / success
Artifact: 8554394051
Artifact digest: sha256:1ecf4862ff87c3eb23ccb8d6b1c9860a229b54b8c76c469930dd2723da213f6f
Artifact expiry: 2026-08-06T06:12:27Z
```

The builder uses SQLite `mode=ro&immutable=1`, `query_only=ON`, integrity checking, exact schema and relationship gates, policy-only volatile exclusions, type-tagged canonical JSON Lines, incremental SHA-256, pre/post database hash equality and aggregate-only output under 1 MiB. The validation Artifact contains one aggregate report and no real Gold rows or identifiers.

Formal records:

- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-synthetic-implementation-result-v1.json`
- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-implementation-current-status-v1.json`
- `docs/historical-gold-5826-freeze-manifest-synthetic-validation-result-v1.md`
- `scripts/build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py`
- `scripts/test_build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py`



### Historical Gold 5,826 freeze-manifest implementation design

```text
formal state: HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_DESIGN_VALIDATED
design ID: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-IMPLEMENTATION-DESIGN-2026-07-23-001
Gold matchups / team rows: 5,826 / 11,652
remaining source exceptions: 0
point-in-time violations: 0
read-only SQLite required: true
policy-driven stable columns required: true
canonical type-tagged JSON Lines: true
incremental SHA-256: true
aggregate output maximum: 1 MiB
real Artifact read: false
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

Validation evidence:

```text
recording PR: 137
recording merge: 1730859888bd21cf7727ef6c5cbf348fb7aeddeb
workflow run: 29982518227
job: 89127261444 / validate-implementation-design / success
Artifact: 8553727483
Artifact digest: sha256:b752398847700bfc4a09831bbab069451606ecce2615cdcb511b5ddab06d3dc7
```

The design requires SQLite URI read-only mode with `immutable=1`, `query_only=ON`, pre/post database hash equality, policy-derived stable columns, type-tagged canonical encoding, table/schema/metadata/corpus digests, and an aggregate-only privacy boundary. The real Gold Artifact was not downloaded or read.

Formal records:

- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-implementation-design-v1.json`
- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-implementation-current-status-v1.json`
- `docs/historical-gold-5826-complete-corpus-freeze-manifest-implementation-design-v1.md`
- `scripts/validate_historical_gold_5826_freeze_manifest_implementation_design_v1.py`
- `.github/workflows/validate-historical-gold-5826-freeze-manifest-implementation-design-v1.yml`


### Legacy candidate real-file audit

```text
workflow run: 29810347326
candidate eligible games: 5,829
matched games: 5,824
all frozen scientific gates passed: true
formal result: USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED
blocking boundary: reference_missing_gold_for_silver
```

### Gold/Silver coverage reconciliation

```text
workflow run: 29819457942
Silver games: 5,826
Gold matchups: 5,824
missing Gold coverage: 2
missing season: 2023-24
missing reason: missing_both_team_features = 2
Gold builder omission: 0
Gold transfer mismatch: 0
formal result: HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED
```

### Silver root-cause analyzer

```text
implementation merge: be61b82d74ba17f500787d2685275e572f209b1d
validation run: 29821350899
validation artifact: 8491472454
real rows read: false
real execution: false
```

### One-time request validation

```text
request merge: 7d52582bca2a8ef596e862c7655872a14e0a00ac
validation run: 29821759681
validation artifact: 8491635865
state: REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
```

### Explicit approval and blocked execution attempt

```text
approval granted: true
approved by: qoo109
execution enabled: true
execution count: 1
maximum execution count: 1
workflow_dispatch only: true
execution run: 29888939524
execution artifact: 8517546804
formal state: HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_BLOCKED_BEFORE_RESULT
error: KeyError 'team_inference_failures'
```

The approved root-cause request `001` recorded one execution attempt and must not be reused. The run stopped before a formal scientific classification because the executor read `team_inference_failures` from the wrong report path.

Incident note: `docs/historical-silver-missing-team-features-run-29888939524-incident-v1.md`

### Retry request 002

```text
request id: HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002
state: CONSUMED_SOURCE_GAP_CONFIRMED
approval granted: true
approved by: qoo109
execution enabled: false
execution count: 1
maximum execution count: 1
repair commit: db5a7ea4ad38f5d3db763d6ea4457e5428292fb5
execution run: 29890527281
execution artifact: 8518081820
formal outcome: HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED
source archive reconciliation required: true
silver builder repair required: false
silver game identity reconciliation required: false
```

Retry `002` rebuilt only the `2023-24` Historical Silver reference in temporary storage and classified the two zero-feature games using aggregate counts. It is consumed and must not execute again.

Aggregate result:

```text
Silver games: 1,230
games without team features: 2
classified missing games: 2
unclassified missing games: 0
root cause: nbastats_game_present_pbpstats_game_absent = 2
team feature histogram: 0 => 2 / 2 => 1,228
temporary material deleted with runner: true
formal stake: 0
```

### Source archive reconciliation design

```text
formal state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_DESIGN_READY
policy: data/research/historical-silver-2023-24-source-archive-reconciliation-design-v1.json
documentation: docs/historical-silver-2023-24-source-archive-reconciliation-design-v1.md
validator: scripts/validate_historical_silver_source_archive_reconciliation_design_v1.py
workflow: .github/workflows/validate-historical-silver-source-archive-reconciliation-design-v1.yml
triggering result: HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED
ready for source archive reconciliation request draft: true
ready for Chris Munch manifest predeclaration: true
ready for Chris Munch data execution: false
ready for Silver builder change: false
ready for Gold rebuild: false
ready for market backtest: false
formal stake: 0
```

The design defined three follow-up lanes: aggregate source archive reconciliation, secondary team-feature QA reference design, and documented source-gap exception handling.

### Source archive reconciliation request and approval

```text
request id: HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
request: data/research/historical-silver-2023-24-source-archive-reconciliation-request-v1.json
approval: data/research/historical-silver-2023-24-source-archive-reconciliation-approval-v1.json
pre-execution current status: data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v1.json
workflow_dispatch only: true
approval granted: true
maximum execution count: 1
```

The approval packet and pre-execution status remain immutable evidence of the authorized scope. They are not the current post-execution state.

### Source archive reconciliation execution result

```text
request id: HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
workflow run: 29901869841
job: execute-once / success
artifact id: 8522225397
artifact name: historical-silver-source-archive-reconciliation-execution-v1
artifact digest: sha256:2b42dca052d331bf94e31568b24492092beb00fef352405601fd812a8603b334
formal state: HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_AGGREGATE_VALIDATION_PASS
decision: SOURCE_ARCHIVE_GAP_STABLE
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
```

Aggregate coverage:

```text
nbastats_2023 games: 1,230
pbpstats_2023 games: 1,228
overlap games: 1,228
nbastats only: 2
pbpstats only: 0
missing reason: nbastats_game_present_pbpstats_game_absent = 2
```

Possession grouping QA:

```text
possession_base: 242,363 groups / 2 inconsistent / unusable
possession_with_score_context: 242,364 groups / 1 inconsistent / unusable
possession_with_score_and_start_type: 242,365 groups / 0 inconsistent / usable
```

The stable upstream archive gap is confirmed. No Silver builder repair is required. Historical Silver replacement, Gold rebuild, market backtest and model retraining remain blocked.

Formal records:

- `data/research/historical-silver-2023-24-source-archive-reconciliation-result-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v2.json`
- `docs/historical-silver-2023-24-source-archive-reconciliation-result-v1.md`

### Source gap exception manifest

```text
formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_VALIDATED
manifest: data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json
current status: data/research/historical-silver-2023-24-source-gap-exception-current-status-v1.json
documentation: docs/historical-silver-2023-24-source-gap-exception-manifest-v1.md
validator: scripts/validate_historical_silver_source_gap_exception_manifest_v1.py
workflow: .github/workflows/validate-historical-silver-source-gap-exception-manifest-v1.yml
exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
exception count: 2
unclassified count: 0
handling mode: DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH
```

The public manifest contains aggregate evidence only. It keeps the existing Silver game identities while explicitly denying synthetic, copied, imputed, or manual team-feature rows. The two exception games remain ineligible for Gold inclusion, model use, and market-backtest reference unless genuinely new valid source rows are separately governed and validated.

### Source gap exception integration policy

```text
formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_VALIDATED
policy: data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json
current status: data/research/historical-silver-2023-24-source-gap-exception-integration-current-status-v1.json
documentation: docs/historical-silver-2023-24-source-gap-exception-integration-policy-v1.md
validator: scripts/validate_historical_silver_source_gap_exception_integration_policy_v1.py
workflow: .github/workflows/validate-historical-silver-source-gap-exception-integration-policy-v1.yml
policy role: QA_AND_COVERAGE_REPORTING_ONLY
raw Silver / Gold / gap: 5,826 / 5,824 / 2
documented exceptions: 2
unexplained missing after documentation: 0
Gold dataset complete: false
```

The policy allows future reports to add aggregate fields for documented exceptions while preserving the original 5,826 Silver, 5,824 Gold and two missing-game metrics. It does not rewrite Gold coverage as complete and does not change the analyzer or databases in this design PR.

### Source gap exception integration implementation design

```text
formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_DESIGN_VALIDATED
design: data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-design-v1.json
current status: data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-current-status-v1.json
documentation: docs/historical-silver-2023-24-source-gap-exception-integration-implementation-design-v1.md
validator: scripts/validate_historical_silver_source_gap_exception_integration_implementation_design_v1.py
workflow: .github/workflows/validate-historical-silver-source-gap-exception-integration-implementation-design-v1.yml
design role: PURE_AGGREGATE_REPORT_TRANSFORMER_CONTRACT
proposed module: scripts/integrate_historical_silver_source_gap_exception_v1.py
proposed output schema: historical-gold-silver-coverage-with-documented-exceptions-v1
recognition mode: ALL_OR_NOTHING_FAIL_CLOSED
production module created: false
ready for synthetic implementation: true
```

The design freezes a pure transformer that preserves the complete raw coverage report and adds only aggregate documented-exception fields. Structural failures produce no output; semantic mismatches recognize zero exceptions and retain the entire raw gap as unexplained. The current analyzer and all data assets remain unchanged.

### Source gap exception integration synthetic implementation

```text
formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_VALIDATED_SYNTHETIC_ONLY
implementation: scripts/integrate_historical_silver_source_gap_exception_v1.py
synthetic tests: scripts/test_integrate_historical_silver_source_gap_exception_v1.py
validator: scripts/validate_historical_silver_source_gap_exception_integration_implementation_v1.py
workflow: .github/workflows/validate-historical-silver-source-gap-exception-integration-implementation-v1.yml
status: data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-current-status-v2.json
documentation: docs/historical-silver-2023-24-source-gap-exception-integration-implementation-v1.md
execution model: PURE_IN_MEMORY_TRANSFORM
synthetic mutation tests: 17
real data read: false
coverage analyzer changed: false
formal stake: 0
```

The implementation returns a new aggregate report, preserves all inputs byte-for-byte, rejects prohibited identifier evidence before output, and fails closed on semantic mismatches. Its validation workflow runs synthetic fixtures only and uploads aggregate summaries only.

### Source gap exception real-reference validation request design

```text
formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_DESIGN_VALIDATED
design: data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-design-v1.json
status: data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-current-status-v1.json
documentation: docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-design-v1.md
validator: scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_request_design_v1.py
workflow: .github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-request-design-v1.yml
maximum execution count: 1
explicit approval required: true
execution enabled: false
formal stake: 0
```

The design permits a future request to validate only committed aggregate records. It forbids database rebuilds, source archives, raw CSV, raw rows, network access, automatic dispatch, and execution without a separately validated approval.

### Source gap exception real-reference validation request

```text
request id: HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001
formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
request: data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-v1.json
status: data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-current-status-v2.json
documentation: docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-v1.md
validator: scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_request_v1.py
workflow: .github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-request-v1.yml
execution count: 0 / 1
approval granted: false
execution enabled: false
real-reference inputs read: false
formal stake: 0
```

The request validator computes immutable request and implementation SHA-256 bindings but does not run the transformer or read any real-reference input. A separate explicit approval record is required before an execution workflow may be created.


### Source gap exception real-reference validation result

```text
request id: HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001
execution workflow run number: 2
execution workflow run id: unavailable / not guessed
execution head SHA: 596ade65cd26cb148f8a3b9a0ffa6092b16a6737
job: execute-once / success
observed duration: 20 seconds
observed execution Artifacts: 1
formal execution state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_PASS
recording PR: 131
recording merge: ce39a8f39032c5aebe07c2c6734ebc58b02e2108
result QA run: 29972975866
result QA artifact: 8550389215
result QA artifact digest: sha256:5ce4c745b0262b30d9d1f390338b2bbce3bb9a60ef4428e3268d634f274de081
result payload SHA-256: sha256:048149cd058c74c1ab441a99f3a4eec0972668500e469ff81ce663b3e5264340
validation checks: 88 / 88
mutation tests: 12 / 12
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
formal stake: 0
```

Aggregate interpretation:

```text
raw Historical Silver games: 5,826
raw Historical Gold matchups: 5,824
raw missing Gold for Silver: 2
documented source-gap exceptions: 2
unexplained missing after documentation: 0
covered or documented: 5,826
Gold dataset complete: false
recognition gate passed: true
exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
```

The result contains aggregate evidence only. It does not create the two missing Gold rows or rewrite Gold as complete. The execution result export did not include the GitHub workflow run ID, Artifact ID, or Artifact archive digest; those execution metadata values remain explicitly unavailable rather than inferred. The separately generated result-QA run and Artifact are recorded above.

Formal records:

- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-current-status-v3.json`
- `docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.md`


### Two-game official CDN PBP recovery

```text
formal state: HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS
source: cdnnba_2023 / archived official cdn.nba.com play-by-play
source archive SHA-256: 33d49fefc809f73d5d6cbad6d1d6690e0df6c89fe2b5a4d814ecc9ea4df6101b
source archive rows scanned: 674,937
target games found: 2 / 2
target event rows found: 1,108
recovered game dates: 2
possession rows added: 412
team feature rows added: 4
remaining games without team features: 0
remaining documented exceptions: 0
Silver games / team rows: 5,826 / 11,652
Gold matchups / team rows: 5,826 / 11,652
Gold point-in-time violations: 0
formal Stake: 0
```

Adopted execution evidence:

```text
workflow run: 29976204693
job: 89108363564 / recover-and-rebuild / success
Artifact: 8551587005
Artifact bytes: 374,591,375
Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
Artifact expiry: 2026-08-06T03:14:00Z
Silver SHA-256: 48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8
Gold SHA-256: a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085
result SHA-256: 97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30
recording PR: 133
recording merge: 98bcb2538070eb57bba2ce79920262262c0924ef
```

Final PR-head reproducibility and committed-record validation:

```text
reproducibility run: 29976847034 / success
reproducibility Artifact: 8551840465
reproducibility digest: sha256:28827c57e4a96402db3ee6c873c1a423680ab2f604a6fe9dd426feec917e9469
result validation run: 29976847035 / success
result validation Artifact: 8551731929
result validation digest: sha256:94ee584488e7121331fbfb128fcb1d157ee4af6d69b1b8ec3f87177b3a473d72
```

This recovery used alternate official-source event rows rather than manual, synthetic, copied or zero-imputed values. The public aggregate record does not expose the two game IDs, dates or team codes. The earlier `5,824 Gold + 2 documented exceptions` state remains historical evidence but is superseded for current five-season coverage counts.

Formal records:

- `data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2.json`
- `data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-current-status-v1.json`
- `docs/historical-silver-two-game-official-cdn-pbp-recovery-v1.md`
- `docs/historical-silver-two-game-official-cdn-pbp-recovery-result-v2.md`


### Historical Gold 5,826 complete corpus freeze policy

```text
policy id: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001
formal state: HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED
Silver games / team rows: 5,826 / 11,652
Gold matchups / team rows: 5,826 / 11,652
remaining source exceptions: 0
Gold point-in-time violations: 0
policy role: DESIGN ONLY / NO FREEZE EXECUTION
corpus freeze executed: false
formal Stake: 0
```

Evidence and validation:

```text
recording PR: 135
recording merge: b6edf9b8acaf51b1287d6976c6e42cac056dc726
validation run: 29978555275
validation job: 89115413805 / validate-freeze-policy / success
validation Artifact: 8552326235
validation digest: sha256:96fdcee4b39f6ca03b9597677aa01db2e47b15d6d8f780f2e4525be978dd3722
```

Immutable execution-input bindings:

```text
adopted recovery Artifact: 8551587005
adopted Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
Artifact expiry: 2026-08-06T03:14:00Z
Gold binary SHA-256: a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085
Silver binary SHA-256: 48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8
recovery result SHA-256: 97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30
```

Scientific identity design:

```text
binary hash role: execution evidence, not sole permanent semantic identity
required stable tables: gold_team_game_features / gold_matchup_features / gold_metadata
excluded volatile column: feature_generated_at only
required digests: team table / matchup table / metadata / corpus SHA-256
partial freeze: prohibited
row exclusions: prohibited
public row values or identifiers: prohibited
```

Remaining downstream data gaps do not block this freeze policy:

```text
timestamped bookmaker odds: real legal auditable observed_at data still missing
injury panel: 41 independent games / 31 selected T-60 games / below 100-game gate
team submission-completeness ledger: still required before formal injury holdout
```

Formal records:

- `data/research/historical-gold-5826-complete-corpus-freeze-policy-v1.json`
- `data/research/historical-gold-5826-complete-corpus-freeze-policy-current-status-v1.json`
- `docs/historical-gold-5826-complete-corpus-freeze-policy-v1.md`
- `scripts/validate_historical_gold_5826_complete_corpus_freeze_policy_v1.py`
- `.github/workflows/validate-historical-gold-5826-complete-corpus-freeze-policy-v1.yml`

## Consumed One-time Scopes

The following requests are permanently consumed and must not be rerun:

```text
HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001
HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002
HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001
```

## Still Blocked

- reuse, rerun, or re-dispatch of consumed real-reference validation Request `001`;
- freeze-manifest implementation before a separately validated implementation design;
- real Artifact freeze execution before a separately approved one-time workflow;
- any unbound rebuild after Artifact `8551587005` expires;
- Silver builder changes or manual row insertion outside the adopted official-CDN recovery recipe;
- synthetic, copied, zero-imputed or manually entered source-gap rows;
- further Silver／Gold rebuild or canonical replacement outside the adopted recovery recipe;
- cross-source audit rerun;
- source archive reconciliation repeat execution;
- Chris Munch raw CSV read or import;
- Eoin repeat or full-bundle execution;
- Historical Silver or Gold replacement;
- Opening or Closing semantics;
- point-in-time market evaluation;
- CLV, EV, ROI, or Drawdown;
- model retraining;
- betting-edge claims;
- formal Stake above `0`;
- automatic import from the archived Odds History Hub snapshot.

## Important Files

- `data/research/historical-gold-silver-coverage-real-reference-result-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-implementation-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-current-status-v5.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-request-002-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-002-approval-v1.json`
- `data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-002-result-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-design-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-request-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-approval-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-result-v1.json`
- `data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v2.json`
- `data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-current-status-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-current-status-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-design-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-current-status-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-current-status-v2.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-design-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-current-status-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-current-status-v2.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-current-status-v3.json`
- `docs/historical-silver-2023-24-source-archive-reconciliation-design-v1.md`
- `docs/historical-silver-2023-24-source-archive-reconciliation-request-v1.md`
- `docs/historical-silver-2023-24-source-archive-reconciliation-approval-v1.md`
- `docs/historical-silver-2023-24-source-archive-reconciliation-result-v1.md`
- `docs/historical-silver-2023-24-source-gap-exception-manifest-v1.md`
- `docs/historical-silver-2023-24-source-gap-exception-integration-policy-v1.md`
- `docs/historical-silver-2023-24-source-gap-exception-integration-implementation-design-v1.md`
- `docs/historical-silver-2023-24-source-gap-exception-integration-implementation-v1.md`
- `docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-design-v1.md`
- `docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-v1.md`
- `docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.md`
- `scripts/integrate_historical_silver_source_gap_exception_v1.py`
- `scripts/test_integrate_historical_silver_source_gap_exception_v1.py`
- `scripts/validate_historical_silver_source_archive_reconciliation_result_v1.py`
- `scripts/validate_historical_silver_source_gap_exception_manifest_v1.py`
- `scripts/validate_historical_silver_source_gap_exception_integration_policy_v1.py`
- `scripts/validate_historical_silver_source_gap_exception_integration_implementation_design_v1.py`
- `scripts/validate_historical_silver_source_gap_exception_integration_implementation_v1.py`
- `scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_request_design_v1.py`
- `scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_request_v1.py`
- `scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_result_v1.py`
- `.github/workflows/validate-historical-silver-source-archive-reconciliation-result-v1.yml`
- `.github/workflows/validate-historical-silver-source-gap-exception-manifest-v1.yml`
- `.github/workflows/validate-historical-silver-source-gap-exception-integration-policy-v1.yml`
- `.github/workflows/validate-historical-silver-source-gap-exception-integration-implementation-design-v1.yml`
- `.github/workflows/validate-historical-silver-source-gap-exception-integration-implementation-v1.yml`
- `.github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-request-design-v1.yml`
- `.github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-request-v1.yml`
- `.github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-result-v1.yml`
- `data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2.json`
- `data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-current-status-v1.json`
- `docs/historical-silver-two-game-official-cdn-pbp-recovery-v1.md`
- `docs/historical-silver-two-game-official-cdn-pbp-recovery-result-v2.md`
- `scripts/recover_historical_silver_two_game_official_cdn_pbp_v1.py`
- `scripts/recover_historical_silver_two_game_official_cdn_pbp_v2.py`
- `scripts/validate_historical_silver_two_game_official_cdn_pbp_recovery_result_v2.py`
- `.github/workflows/recover-historical-silver-two-game-official-cdn-pbp-v1.yml`
- `.github/workflows/validate-historical-silver-two-game-official-cdn-pbp-recovery-result-v2.yml`
- `data/research/historical-gold-5826-complete-corpus-freeze-policy-v1.json`
- `data/research/historical-gold-5826-complete-corpus-freeze-policy-current-status-v1.json`
- `docs/historical-gold-5826-complete-corpus-freeze-policy-v1.md`
- `scripts/validate_historical_gold_5826_complete_corpus_freeze_policy_v1.py`
- `.github/workflows/validate-historical-gold-5826-complete-corpus-freeze-policy-v1.yml`

## Eoin and Other Research Lines

```text
Eoin role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
Eoin integration: alert-only
Eoin repeat execution: disabled
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
request consumed: true
repeat execution allowed: false
Wyatt: STRUCTURAL_BLOCKED
Chris Munch: ROLE_LIMITED_SECONDARY_TEAM_FEATURE_QA_CANDIDATE / manifest required before execution
live odds capture: offseason sleep mode
```
