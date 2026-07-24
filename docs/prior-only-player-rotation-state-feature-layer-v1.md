# Prior-Only Player Rotation State Feature Layer v1

Updated: 2026-07-24  
Research state: **Design Predeclared / Not Executed**  
Formal Stake: **0**

## Why this is the next step

PR #181 formally preserved the frozen model and market-backtest lock. The frozen model's large probability disagreements with the private market were not reliable, and the previously tested two-feature injury offset remains a binding negative result. The next credible experiment must therefore add genuinely new pre-game information rather than retuning the same aggregate team features.

This design freezes a player-level rotation and role-state layer before any outcome review.

## Core rule

Every source row must satisfy:

```text
source_game_end_time_utc < target_analysis_cutoff_utc < target_tipoff_utc
```

The primary target cutoff is scheduled tipoff UTC. When a source lacks a reliable end timestamp, it is excluded. A date-only fallback must use a strictly earlier Eastern game date; same-day rows are not allowed.

Target-game boxscores, starters, minutes, participation, DNP states and outcomes are prohibited.

## Primary source boundary

- Game identity and schedule: governed Silver.
- Player identity: deterministic official person ID only.
- Player minutes and starters: official completed-game boxscore or a separately qualified equivalent archive.
- No fuzzy matching, nearest-name guessing or silent team inference.
- HTTP 403, authentication and technical access restrictions are recorded, not bypassed.
- Raw player rows and player names are not published.

## Season boundary

Primary features use current-season completed games only. They require at least three completed current-season games.

Early-season values remain null with explicit sample-size and missingness flags. Prior-season carryover is excluded from primary features. A future carryover diagnostic may be separately namespaced for same-team official player IDs, but cannot be silently mixed into v1.

## Player-level prior-state features

- minutes averages over prior 3, 5 and 10 completed team games;
- minutes trend: prior 3 minus prior 10;
- start rates over prior 5 and 10;
- appearance rate over prior 10;
- days since last positive-minute appearance;
- recent-return state: appeared in the latest prior game after missing at least three immediately preceding team games;
- team-relative minutes role rank over prior 5.

All windows are team-specific. Prior minutes from another team do not enter the primary current-team role state.

## Team rotation features

- distinct rotation players over prior 5;
- top-5 and top-8 player-minute concentration;
- normalized rotation entropy over prior 5 and 10;
- consecutive top-8 set continuity over prior 5;
- official starter-set continuity over prior 5;
- player-minute allocation volatility;
- aggregate role-change magnitude, prior 3 versus prior 10;
- count of prior-only recent returnees;
- count of new-team top-eight rotation players.

Share, entropy and Jaccard features must remain between 0 and 1.

## Starter policy

Official completed-game starter flags are primary. A minutes-based starter inference is not primary and, if researched later, must be called `starter_proxy_by_prior_minutes_v1`. It cannot be described as a confirmed lineup.

## Matchup output

Each target game produces two team rows and one matchup row. Matchup differences are defined as:

```text
home value - away value
```

Both team values remain available. A missing side keeps the difference null; missing values are never imputed to zero.

## QA gates

Expected governed target population:

```text
games: 1,230
team rows: 2,460
exactly two team rows per game: true
duplicate target game/team keys: 0
target-game source rows used: 0
same or future source rows used: 0
fuzzy identity rows: 0
non-finite features: 0
public player rows: 0
public game-level feature rows: 0
```

Official player-minute totals must reconcile to official game duration, including overtime.

## Diagnostic sequence

1. Source, coverage, identity, timestamp and distribution QA.
2. Training-free residual audit against the frozen model error and market residual.
3. Only after a separate promotion decision, predeclare a walk-forward candidate experiment.

Primary residual population is the existing private same-game market join with absolute T-60 batch error at most 5 minutes. The 15, 30 and 60-minute bands are sensitivity checks only.

No outcome-based feature selection or post-hoc threshold tuning is allowed.

## Activation gates

Before a later candidate experiment can even be designed:

- at least 1,000 feature-ready independent games;
- all 30 teams represented;
- at least five months covered;
- feature-ready rate at least 80%;
- zero source-time violations;
- zero identity ambiguities;
- explicit missingness subgroup audit;
- predeclared residual direction.

Passing these gates does not itself authorize model training.

## Binding exclusions

Do not:

- retune the existing aggregate Gold features on the same outcomes;
- use market prices as prediction features;
- retune `bounded_injury_logit_offset_v1`;
- reopen Rest/Travel v1 without materially different data;
- calculate EV, ROI, CLV or Drawdown;
- create betting selections;
- increase Formal Stake.

## Current qualification

```text
design predeclared: true
source qualified: false
real feature build executed: false
residual audit executed: false
model training authorized: false
strict T-60 qualified: false
formal Market Backtest allowed: false
betting-edge claim allowed: false
Formal Stake: 0
```

## Next unique mainline

```text
QUALIFY_AND_BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_SOURCE_V1
WITHOUT_MODEL_RETRAINING
```
