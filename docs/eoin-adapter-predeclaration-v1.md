# Eoin Adapter Predeclaration v1

更新日期：2026-07-19

## Purpose

Eoin A Moore 已通過 2023-24 deterministic cross-source audit，但只能作
role-limited secondary source。這份 predeclaration 在任何 adapter
execution 或 derived import 之前先固定邊界。

Formal stake remains `0`.

## Upstream Evidence

Required evidence:

```text
data/eoin-cross-source-audit-v1.json
formal outcome: ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
workflow run: 29672984966
artifact id: 8437932113
digest: sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a
```

Observed audit summary:

```text
reference games: 1,230
matched games: 1,230
game identity match: 100%
final score match: 99.9187%
team boxscore coverage: 100%
PBP game coverage: 100%
player boxscore candidate coverage: 100% coverage-only
```

## Allowed v1 Scope

The adapter may read these files only in temporary workflow storage:

```text
Games.csv
TeamStatistics.csv
PlayerStatistics.csv
PlayByPlay.parquet
```

Allowed output domains:

```text
game identity cross-check
final score cross-check
team boxscore score cross-check
player boxscore candidate coverage
play-by-play game coverage
aggregate source health
```

Allowed public outputs:

```text
aggregate JSON reports
schema metadata
row counts
coverage rates
hashes and file sizes
```

## Explicitly Blocked

```text
raw game rows
raw team rows
raw player rows
raw PBP rows
full CSV / Parquet files
full SQLite / DuckDB files
derived tables committed to public repo
Historical Silver replacement
Historical Gold replacement
model retraining
market backtest
CLV / EV / ROI / Drawdown
betting decision layer
nonzero stake
```

## Player Boxscore Boundary

Player boxscore is coverage-only in v1. The cross-source reference is
event-level, not an independent player boxscore stat reference. Player-stat
parity requires a separate source and a separate predeclared audit.

## Validation

Machine-readable policy:

```text
data/eoin-adapter-predeclaration-v1.json
```

Offline validator:

```bash
python3 scripts/validate_eoin_adapter_predeclaration_v1.py \
  --policy data/eoin-adapter-predeclaration-v1.json \
  --evidence data/eoin-cross-source-audit-v1.json \
  --self-test
```

GitHub workflow:

```text
Actions -> Validate Eoin adapter predeclaration v1
```

Passing state:

```text
ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION
```

That state authorizes implementation of the adapter only. It does not authorize
adapter execution against raw files, Silver/Gold replacement, model retraining,
market metrics, betting claims, or stake.
