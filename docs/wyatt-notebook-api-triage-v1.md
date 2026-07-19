# Wyatt Notebook and API Triage v1

## Inputs Reviewed

Local files:

```text
database-updater-daily.ipynb
historic-nba-drafting-game-and-player-analysis.ipynb
dataset-metadata.json
```

Observed on 2026-07-19.

## Formal Conclusion

The notebooks are useful as reference material, but they do not qualify the
downloaded Wyatt dataset.

The actual local files remain blocked:

```text
nba.sqlite: 16 tables, latest game date 2023-06-12
nba.duckdb: 12 KB empty shell
2023-24 pilot games: 0
formal stake: 0
```

## Notebook Findings

### database-updater-daily.ipynb

This notebook is a thin Kaggle execution wrapper.

It does only three important things:

```text
clone wyattowalsh/nba-db
install requirements.txt
load Kaggle secrets and call nba_db.update.daily()
```

The real ETL logic is not inside the notebook. Any reuse requires inspecting the
current upstream repository and pinning exact code revisions before running
anything locally.

Potentially useful:

```text
daily update entrypoint shape
Kaggle credential pattern
upstream project discovery
```

Not sufficient for:

```text
source qualification
Silver / Gold replacement
2023-24 cross-source audit
market backtest
```

### historic-nba-drafting-game-and-player-analysis.ipynb

This notebook explicitly uses the old Kaggle SQLite surface:

```text
../input/basketball/basketball.sqlite
16 tables
```

It is an exploratory analysis notebook for the legacy schema, not the advertised
235-table star schema.

Potentially useful:

```text
basic SQLite connection examples
legacy Game table exploratory queries
home / away pivot pattern
simple data visualization examples
```

Not useful for:

```text
current-season coverage
player game boxscore qualification
fact_* / dim_* / agg_* star-schema queries
point-in-time model validation
```

## API Triage

### Kaggle API

Allowed role:

```text
download user-authorized public datasets
record content length, SHA-256, inventory, and retrieved_at
run aggregate-only local census
```

Required boundary:

```text
do not commit kaggle.json
do not commit raw archives
do not commit extracted raw data
do not treat metadata as schema evidence
```

### nba_api / NBA Stats

Allowed role:

```text
research-only schedule, game, team, player, boxscore, and PBP acquisition
small scoped pilots with adapter version and error capture
T+final backfill candidates
```

Required boundary:

```text
rate limit conservatively
record endpoint, parameters, observed_at, fetched_at, hash, and adapter version
stop on schema drift or repeated upstream errors
do not use fuzzy matching
```

### The Odds API Free Tier

Allowed role:

```text
current / upcoming NBA moneyline research snapshots
manual comparison against user-observed prices
API plumbing smoke tests
```

Blocked role:

```text
historical odds backfill
executable market backtest
CLV / EV / ROI / drawdown claims
betting decision layer
```

The free tier is not enough for historical point-in-time odds. Historical odds
must remain blocked unless the user approves a paid source or supplies a lawful
timestamped odds file with provenance.

## Next Practical Work

1. Keep Wyatt as `STRUCTURAL_BLOCKED` for the current downloaded files.
2. Run Eoin CSV census once the user supplies the downloaded CSV bundle.
3. If API work is approved, start with a tiny `nba_api` smoke test for schedule
   and boxscore endpoints only.
4. Keep odds API work to live/current smoke tests unless historical PIT access is
   explicitly approved and lawful.
