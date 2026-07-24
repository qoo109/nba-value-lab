# NBA Value Lab Handoff — Kaggle Official Schedule Alignment Pilot

Updated: 2026-07-24  
Formal Stake: 0

## Repository state before milestone

```text
main: 061edd87523733c396690fe276537447015d4f7a
latest merged PR: 172
open PRs before branch creation: none
```

## User request

Try repairing the private Kaggle odds archive by looking up official game times and matching them step by step.

## Milestone

```text
KAGGLE_OFFICIAL_SCHEDULE_ALIGNMENT_20_GAME_PILOT_VALID
```

## Inputs

- user-provided private Kaggle archive;
- archive SHA-256: `sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419`;
- first 20 games from the official NBA 2025-26 regular-season schedule-by-day PDF, as of 2025-08-14 and marked subject to change;
- no raw archive, quote rows or prices committed.

## Results

```text
official games uniquely matched: 20 / 20
Kaggle team1 = official away: 20 / 20
Kaggle team2 = official home: 20 / 20
detailed group present: 20 / 20
main/detail moneyline exact match: 19 / 20
closest batch within T-60 ±5m: 4 / 20
closest batch within T-60 ±60m: 6 / 20
median absolute T-60 error: 64.35m
post-tip snapshot events: 0 / 20
```

## Interpretation

Official schedule alignment successfully repairs official matchup identity, away/home orientation and published tipoff for the pilot. It does not repair quote time because the Kaggle timestamp is a collector-created league-batch timestamp and detailed pages were scraped afterward.

The four near-T-60 values remain batch candidates only:

```text
Detroit at Chicago: T-58.617
New Orleans at Memphis: T-58.617
Washington at Milwaukee: T-58.617
LA Clippers at Utah: T-64.467
```

## Decision

```text
OFFICIAL_SCHEDULE_ALIGNMENT_REPAIRS_GAME_ID_HOME_AWAY_AND_PUBLISHED_TIPOFF_BUT_NOT_QUOTE_TIME
```

## Preserved locks

```text
provider-origin quote time verified: false
strict T-60 qualified: false
point-in-time qualified: false
historical backfill qualified: false
formal history write: false
G1.2.0 real input: false
Market Backtest: false
CLV / EV / ROI / Drawdown: false
Formal Stake: 0
```

## Do not do

- Do not overwrite the original Kaggle timestamp.
- Do not call a batch timestamp an exact quote observation time.
- Do not use the 2025-08-14 schedule PDF without change control for postponed or adjusted games.
- Do not publish raw odds or quote rows.
- Do not unlock market metrics from this pilot.

## Next unique mainline

```text
EXPAND_KAGGLE_OFFICIAL_SCHEDULE_ALIGNMENT_TO_FULL_2025_26_REGULAR_SEASON_DIAGNOSTIC_ONLY
```

The full diagnostic pass should version official schedule evidence, isolate postponements and neutral-site games, exclude preseason and All-Star containers, and keep all quote-time uncertainty flags.
