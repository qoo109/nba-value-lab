# Prior-Only Player Rotation Source 2025-26 — Result v1

Updated: 2026-07-24  
Research state: **Official Source Qualified / Feature Build Not Yet Executed**  
Formal Stake: **0**

## Purpose

Build the deidentified, official player-game source required by the predeclared Prior-Only Player Rotation State Feature Layer v1.

This milestone does not build the rotation features, review model outcomes, retrain the frozen model or execute a market backtest.

## Source and governed scope

- Game identity, date, teams and official game duration: governed 2025-26 Silver.
- Player identity, minutes, played state and official starter flag: NBA Official LiveData final boxscore.
- Requested official games: `1,230`.
- Successful official games: `1,230`.
- Failed official games: `0`.
- Authentication or access-control bypass: none.

The importer retained source URL, retrieval time and raw response SHA-256 in the private source layer. Player names, free-text descriptions and raw JSON were not retained.

## Coverage

| Metric | Result |
|---|---:|
| Official games | 1,230 / 1,230 |
| Team-game rows | 2,460 |
| Deidentified player-game rows | 43,265 |
| Unique official player IDs | 603 |
| Teams represented | 30 |
| Months covered | 7 |

## Quality gates

| Gate | Result |
|---|---:|
| Duplicate game/player rows | 0 |
| Missing team rows | 0 |
| Unexpected team rows | 0 |
| Team mismatches | 0 |
| Invalid minute rows | 0 |
| Starter without played state | 0 |
| Team-games without exactly five official starters | 0 |
| Minute reconciliation errors | 0 |
| Maximum absolute team-minute difference | 0.003333 minutes |
| Public player rows | 0 |
| Public game-level feature rows | 0 |

## One bounded official-source reconciliation

The first live execution identified one official LiveData minute value that caused a team total of `231:20` instead of `240:00`.

The independent NBA.com official game box score displayed `36:48` for the same deidentified subject, while the LiveData field represented `28:08.2`. The exact difference was `8:39.8` and accounted for the entire team-minute discrepancy.

The correction was predeclared in:

```text
data/research/prior-only-player-rotation-source-exceptions-2025-26-v1.json
```

Guardrails:

- exact official game;
- exact team;
- exact SHA-256 deidentified subject key;
- exact original LiveData value;
- minutes field only;
- no identity, played or starter mutation;
- official NBA.com evidence only;
- no wildcard or fuzzy matching;
- no outcome, model or market result used to create the exception.

After reconciliation:

```text
exceptions declared: 1
exceptions applied: 1
unmatched exceptions: 0
value mismatches: 0
minute reconciliation errors: 0
```

This is a source reconciliation, not an imputation or lowered QA gate.

## Point-in-time boundary

The official final boxscore source does not provide a governed game-end timestamp in this source contract. Therefore the later feature builder must enforce the approved conservative fallback:

```text
source_game_date_et < target_game_date_et
```

The following remain prohibited:

- same-day source rows;
- target-game source rows;
- future source rows;
- target-game minutes, starters, participation or outcome as a feature.

This is stricter than using a date-only `<=` rule and may leave early-season features null.

## Private output

The private Artifact contains:

```text
prior-only-player-rotation-source-2025-26-v1.csv
prior-only-player-rotation-source-index-2025-26-v1.csv
prior-only-player-rotation-source-2025-26-report-v1.json
```

The player source CSV contains only:

- official game and team identifiers;
- deterministic player ID;
- minutes, played and official starter flags;
- source SHA-256 and retrieval timestamp;
- source-time semantics;
- optional source-reconciliation exception ID.

It remains outside the public repository.

## Qualification

```text
official source qualified for prior-only rotation v1: true
ready for prior-only rotation feature build: true
real feature build executed: false
residual audit executed: false
model training authorized: false
strict T-60 qualified: false
formal Market Backtest allowed: false
betting-edge claim allowed: false
Formal Stake: 0
```

Source qualification does not prove that the future rotation features improve model probability quality or add information beyond the market.

## Execution evidence

```text
source build head: 1cc53c6b898cf7c80fdf28649366f04ca9f636c3
workflow run: 30099845472
job: 89502852068
Artifact: 8599159260
Artifact digest: sha256:5f83f1c21e4a73696fd4d5dca8faa7f98908373f0795c45c6637a149bd345ee9
Artifact inspected: true
```

## Next unique mainline

```text
BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_V1
WITHOUT_MODEL_RETRAINING
```

The next milestone must build the already frozen player and team rotation features, run source-time and missingness QA, and remain training-free until a separate residual diagnostic and promotion decision are completed.
