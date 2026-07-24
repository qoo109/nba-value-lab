# Kaggle Official Schedule Alignment Pilot v1

Updated: 2026-07-24  
Formal Stake: 0

## Goal

Test whether official NBA schedule data can repair game identity, home/away orientation and scheduled tipoff for the private Kaggle `Basketball-odds-history` archive without pretending that the Kaggle batch timestamp is an exact quote time.

## Inputs

- private Kaggle archive SHA-256: `sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419`;
- first 20 games in the NBA 2025-26 regular-season schedule-by-day PDF published as of 2025-08-14;
- official PDF explicitly marked subject to change;
- ET tipoff converted to UTC with `America/New_York`;
- Kaggle collector timestamp preserved and interpreted under the notebook's `datetime.utcnow` assumption.

The raw archive, quote rows and prices are not committed.

## Matching method

1. Interpret official `TEAM 1 at TEAM 2` as away at home.
2. Match an exact unordered official team pair against Kaggle `team1` and `team2`.
3. When a pair can repeat during the season, choose the source event whose latest pre-tip snapshot is closest to the official published tipoff.
4. Recover the Pinnacle numeric event identifier from `game_link`.
5. Select the available Kaggle batch timestamp nearest official T-60.
6. Preserve that value as a collector batch timestamp; do not rename it provider quote time.
7. Check whether the exact matchup/timestamp detailed group exists and whether its game moneyline matches the main-line snapshot, without publishing prices.

## Pilot results

```text
Official games: 20
Unique matches: 20 / 20
Kaggle team1 = official away: 20 / 20
Kaggle team2 = official home: 20 / 20
Events with post-tip snapshots: 0 / 20
Detailed group present at selected snapshot: 20 / 20
Main/detail game-moneyline exact match: 19 / 20
Largest selected main/detail decimal-odds difference: 0.02
```

T-60 proximity:

```text
within ±5 minutes: 4 / 20
within ±15 minutes: 4 / 20
within ±30 minutes: 4 / 20
within ±60 minutes: 6 / 20
median absolute T-60 error: 64.35 minutes
median last snapshot before tip: T-124.35
```

The four near-T-60 batch candidates are:

- Detroit at Chicago: T-58.617;
- New Orleans at Memphis: T-58.617;
- Washington at Milwaukee: T-58.617;
- LA Clippers at Utah: T-64.467.

These remain batch-time candidates, not exact T-60 quotes.

## What was repaired

- official published game date and tipoff;
- deterministic official away/home orientation for all 20 pilot games;
- unique mapping to 20 Pinnacle source event IDs;
- distance between collector batch time and official published tipoff.

## What was not repaired

- provider-origin quote time;
- exact detailed-page observation time;
- schedule changes after the 2025-08-14 PDF publication;
- proof that every selected snapshot is strictly T-60;
- upstream retention or automation rights;
- formal point-in-time eligibility.

A league-batch timestamp was created before detailed pages were scraped sequentially. Official tipoff data can calculate a conservative distance from the batch time, but it cannot turn that batch timestamp into the precise observation time for every detailed quote.

## Decision

```text
OFFICIAL_SCHEDULE_ALIGNMENT_REPAIRS_GAME_ID_HOME_AWAY_AND_PUBLISHED_TIPOFF_BUT_NOT_QUOTE_TIME
```

This validates the schedule-alignment direction for diagnostic research. It does not authorize historical ingestion, G1.2.0, Market Backtest, CLV, EV, ROI, Drawdown, betting-edge claims or Stake above 0.

## Next unique mainline

```text
EXPAND_KAGGLE_OFFICIAL_SCHEDULE_ALIGNMENT_TO_FULL_2025_26_REGULAR_SEASON_DIAGNOSTIC_ONLY
```

The full pass must use versioned official schedule evidence and separate changed/postponed games, neutral-site games, NBA Cup scheduling adjustments, All-Star containers, preseason and unmatched or ambiguous pairs.
