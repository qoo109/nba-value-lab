# Point-in-time Player Value & Expected Minutes v1

## Goal

Create prior-only player availability features that can be joined to official injury snapshots without using the target game's result or box score.

This version establishes a research data chain for:

1. historical player boxscores;
2. Gold-controlled game identity and schedule QA;
3. injury-name to player-ID matching;
4. expected minutes from earlier appearances only;
5. a transparent, shrunk player-impact proxy;
6. explicit missingness when history is unavailable.

## Source selection

### Selected research source

The pipeline uses the MIT-licensed secondary archive:

```text
https://github.com/NocturneBear/NBA-Data-2010-2024
```

The archive provides regular-season player boxscore rows with:

- `gameId`, game date and team tricode;
- `personId` and player name;
- minutes and starting position;
- shooting, rebounding, assists, turnovers, steals, blocks and fouls;
- points and plus/minus.

The repository does not fully document its upstream collection process. It is therefore classified as a **secondary open archive**, not an approved primary source.

### Official routes tested but not activated

Two direct NBA routes were tested from GitHub-hosted runners:

- `stats.nba.com/stats/playergamelogs` was unreliable for full-season and segmented retrieval;
- NBA LiveData CDN boxscores returned HTTP 403 even with ordinary browser request headers.

The project does not attempt to bypass those restrictions. The direct-source importers and diagnostics were removed from the final branch.

## Gold-controlled validation

Historical Gold is authoritative for:

- historical `game_id`;
- official 10-digit game-ID normalization;
- game date;
- home and away teams;
- season label.

Archive rows not found in Gold are excluded rather than guessed. Date or team disagreement is a hard failure.

### Verified coverage

#### 2022–23

- archive roster rows: 31,542
- played player rows: 25,892
- unique players: 547
- Gold games: 1,230
- matched Gold games: 1,230
- game coverage: 100%
- date, team, player-ID and minute errors: 0

#### 2023–24

- archive roster rows: 32,385
- normalized Gold-matched rows: 32,328
- played player rows: 26,350
- unique players: 586
- Gold games: 1,228
- matched Gold games: 1,228
- game coverage: 100%
- date, team, player-ID and minute errors: 0
- two archive games not present in audited Gold were excluded

## Minute normalization

The archive normally uses `MM:SS`. It also contains rounded values such as:

```text
28:60
39:60
```

A dedicated diagnostic confirmed that these rows contain valid non-zero boxscores. They are normalized by carrying the rounded sixty seconds into the next minute:

```text
28:60 → 29:00
39:60 → 40:00
```

Values above sixty seconds remain invalid and are blocked.

## Injury player identity

For the official 2023-12-18 08:30 ET injury report:

- injury rows: 118
- rows matched to historical games: 118
- player IDs matched: 117
- high-confidence exact matches: 117
- player match rate: 99.1525%
- ambiguous identities: 0
- fuzzy or nearest-name matching: not used
- one unmatched OUT player remains blocked

The ID map excludes player names and injury reasons.

## Point-in-time rule

For a target game on date `D`, every player feature uses only rows where:

```text
source_game_date < D
```

Same-day and future rows are excluded before any aggregate is calculated.

The verified pilot excluded:

- 26 same-day source rows;
- 2,693 future source rows;
- strict prior-date violations: 0.

## Expected-minutes baseline

Expected minutes use prior appearances only:

- last 5 played games;
- last 10 played games;
- current season-to-date;
- prior-season carryover for small or absent current-season samples.

For at least five current-season games:

```text
0.50 × prior-5 minutes
+ 0.30 × prior-10 minutes
+ 0.20 × season-to-date minutes
```

Small current-season samples blend 60% current-season mean with 40% prior-season last-10 mean. Estimates are capped to 0–48 minutes.

## Player-impact research proxy

The transparent per-game box contribution is:

```text
PTS + 0.4×FGM − 0.7×FGA − 0.4×(FTA−FTM)
+ 0.7×OREB + 0.3×DREB
+ STL + 0.7×AST + 0.7×BLK
− 0.4×PF − TOV
```

The value is converted to per-36, standardized against league rows available before the target date, supplemented with 0.25 times the prior plus/minus per-36 z-score, and shrunk by:

```text
n / (n + 8)
```

The final research proxy is capped to `[-3, 3]`. It is not an official NBA metric.

## Missingness policy

Unknown does not equal zero.

For the verified injury report:

- player-ID map rows: 118
- feature rows: 117
- expected-minutes rows: 106
- player-impact rows: 106
- expected-minutes coverage: 89.8305%
- impact coverage: 89.8305%
- players with no earlier played history: 11
- missing player IDs: 1

Unknown expected minutes and impact remain null with explicit missingness indicators. Ten of the eleven no-history players were OUT and one was QUESTIONABLE.

## Outputs

The retained ID-only feature output contains:

- snapshot record ID;
- historical game ID;
- season, team and player ID;
- availability status;
- target date and observation timestamp;
- expected minutes, method and missingness;
- prior sample sizes;
- player-impact estimate and missingness;
- latest included source game and feature version.

It does not contain player names or injury reasons.

## Activation boundary

The current decision is:

```text
ready_for_injury_snapshot_feature_join: true
ready_for_model_training: false
ready_for_betting_edge_claim: false
```

Research join readiness means the values may enter the next team-aggregation experiment with explicit missingness. Promotion still requires:

1. multiple injury reports and publication times;
2. cross-season feature coverage;
3. team-level injury burden aggregation;
4. expected-minutes accuracy evaluation;
5. season holdout comparison against Walk-forward v2;
6. no degradation of calibration or market residual metrics.
