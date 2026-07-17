# Point-in-time Player Value & Expected Minutes v1

## Goal

Create prior-only player availability features that can be joined to official injury snapshots without using the target game's result or box score.

## Official source

The source pilot uses NBA Official LiveData boxscores:

```text
https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json
```

The audited historical Gold schedule supplies the request allowlist. Only official 10-digit game IDs already present in `gold_matchup_features` are requested.

Each official boxscore provides stable player and team IDs, play and starter status, minutes, base box-score statistics, and plus/minus. The importer verifies that the returned game ID and home/away team tricodes exactly match Gold before accepting any player rows.

The bulk `stats.nba.com/stats/playergamelogs` endpoint was tested first but proved unreliable from GitHub-hosted runners for full-season retrieval. It is not used as the production source for this pilot.

## Source validation

For one regular season, the importer validates:

- all requested game IDs come from Gold;
- returned game ID and home/away teams match Gold exactly;
- at least 99.5% game coverage;
- unique `(game_id, player_id)` keys;
- valid player IDs and minute durations;
- at least ten played players per completed game;
- expected season, game, row, and player coverage;
- response SHA-256 provenance and retry counts.

Requests use bounded concurrency and retries. A failed or mismatched game remains an explicit QA failure rather than being replaced with a guessed source.

Player-level source rows are temporary and are deleted before Artifact upload. The retained Artifact contains only source provenance, response hashes, aggregate counts, and QA.

## Point-in-time rule

Official boxscore rows are finalized after games. They may influence only later target games.

For a target game on date `D`, every player feature must use rows where:

```text
source_game_date < D
```

Same-game, same-date, and future rows are excluded. Feature builders must record the latest included source game and the target observation timestamp.

## Planned expected-minutes baseline

Expected minutes will be derived from prior usage only, using stabilized recent windows:

- prior 5-game minutes;
- prior 10-game minutes;
- season-to-date minutes;
- days since last appearance;
- prior starts where available;
- offseason carryover only when current-season evidence is missing.

The output will be capped to the valid NBA range and will retain its sample size and source cutoff.

## Planned player-value baseline

The first transparent value estimate will use prior box-score contribution and minutes, not target-game statistics. It is a research proxy rather than an official NBA metric.

The raw per-game contribution components will include:

- points and shooting efficiency;
- offensive and defensive rebounds;
- assists, steals, and blocks;
- turnovers and personal fouls;
- minutes and plus/minus as separately reported context.

The estimate will be standardized against league rows available before the target date and shrunk toward zero for small samples.

## Activation boundary

A successful source response does not enable model training. Promotion requires:

1. multi-season source reliability;
2. exact Gold game and player-ID coverage;
3. strict prior-date feature tests;
4. expected-minutes backtesting;
5. injury snapshot joins across multiple report times;
6. season holdout evaluation against the existing model.
