# Player Participation Label Layer v1

## Roadmap position

This layer does not replace or reorder the 2026-07-17 roadmap. It is a repair subtask inside:

```text
Expected Minutes Accuracy Audit
```

The fixed research order remains:

```text
Official injury snapshot backfill
→ 100+ independent feature-ready matchups
→ Expected Minutes Accuracy Audit
→ Injury Feature Walk-forward Holdout
→ Timestamped Odds Acquisition
→ Market Backtest
→ CLV／EV／ROI
→ Betting Decision Layer
```

Wave 1＋Wave 2 produced 176 independent frozen T-60 games. Expected Minutes Accuracy Audit v1 executed, but its target-game participation labels were incomplete. Player Participation Label Layer v1 fills that specific evaluation-data gap before a separately predeclared Accuracy Audit v2.

## Source

Provider:

```text
NBA Official LiveData Boxscore
```

URL contract:

```text
https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{official_game_id}.json
```

The final-game payload supplies:

- `personId`;
- team tricode;
- `played`;
- `starter`;
- official status;
- `notPlayingReason` code;
- actual minutes.

NBA.com rejected the original research user agent from GitHub Actions with HTTP 403. The verified runner therefore uses browser-compatible `User-Agent`, `Origin`, `Referer`, `Accept`, and fetch-context headers with bounded parallelism. The source, label, and promotion contracts were not changed to solve the HTTP access issue.

Player names and free-text `notPlayingDescription` values are never retained in repository outputs or uploaded Artifacts.

## Frozen label contract

```text
PLAYED
EXPLICIT_DNP
INACTIVE_OR_NOT_DRESSED
SOURCE_MISSING
UNKNOWN
```

### PLAYED

The official player row has `played=true` or positive parsed minutes.

### EXPLICIT_DNP

The official player row has zero minutes and an explicit `DNP`-prefixed `notPlayingReason`.

### INACTIVE_OR_NOT_DRESSED

The official player row has zero minutes and either:

- official status `INACTIVE`; or
- a reason prefixed by `INACTIVE`, `DND`, or `NWT`.

### SOURCE_MISSING

The official game source could not be retrieved or did not pass game ID, date, team, final-status, or payload validation.

### UNKNOWN

The official game source passed, but the selected player row was absent, conflicting, or did not have an explicitly classifiable status.

## Prohibited inference

```text
missing official player row ≠ DNP
missing official player row ≠ zero minutes
source fetch failure ≠ DNP
UNKNOWN ≠ zero minutes
```

No missing or ambiguous state is converted into a successful zero-minute label.

## Source validation

Every selected game must pass:

- historical game ID → 10-digit official NBA game ID normalization;
- official response game ID equality;
- final game status `3`;
- selected game-date agreement;
- exact home and away team tricode agreement;
- unique `(historical_game_id, player_id)` rows;
- valid numeric player IDs;
- source URL, retrieval timestamp, byte count, and SHA-256 provenance.

Raw official JSON is not retained.

## Frozen structural gates

The following gates were committed before the official 176-game live result:

```text
combined selected games: exactly 176
official game source coverage: 100%
identity match rate: at least 95%
participation-label join rate among matched IDs: at least 95%
UNKNOWN rate among matched IDs: at most 5%
source-missing games: 0
duplicate selected games: 0
duplicate official game-player rows: 0
duplicate audit rows: 0
team mismatches: 0
```

The gates were not relaxed after observing the result.

## Official result

Verified workflow run:

```text
29626746364
```

Latest successful Artifact:

```text
player-participation-label-layer-v1-browser
artifact id: 8424167164
digest: sha256:5eff2c563eb1cb769a318ad4509d15635002e8ffb5426fe56dee4df5647b01ea
```

### Official source coverage

```text
requested selected games: 176
successful official games: 176
failed official games: 0
official source coverage: 100%
official player rows: 6,198
unique official player IDs: 585
```

All-roster official classifications:

```text
PLAYED: 3,718
EXPLICIT_DNP: 30
INACTIVE_OR_NOT_DRESSED: 1,707
UNKNOWN: 743
```

The all-roster UNKNOWN count is not the frozen audit denominator. The promotion gate applies only to matched players listed in the exact selected injury snapshots.

### Frozen selected-snapshot join

```text
combined selected games: 176
selected player snapshot rows: 1,840
identity matched rows: 1,834
identity match rate: 99.6739%
official participation joins: 1,832 / 1,834
participation join rate: 99.8909%
source-missing games: 0
complete team-game groups: 345
```

Selected matched-player labels:

```text
PLAYED: 314
EXPLICIT_DNP: 28
INACTIVE_OR_NOT_DRESSED: 1,450
UNKNOWN: 42
UNKNOWN rate: 2.2901%
```

All frozen structural gates passed:

- exact 176-game population;
- 100% official game-source coverage;
- identity match rate above 95%;
- participation-label join rate above 95%;
- UNKNOWN rate below 5%;
- zero source-missing games;
- zero selected-game, official game-player, and audit-row duplicates;
- zero team mismatches;
- zero invalid minutes／played label combinations;
- no selected game without participation rows.

## Privacy boundary

The live workflow temporarily rebuilds:

- Wave 1 and Wave 2 official injury player rows;
- deterministic identity maps;
- identity-reference player boxscores;
- official player participation rows;
- deidentified selected-snapshot participation audit rows.

Before Artifact upload it deletes:

- player names and injury reasons;
- injury player rows;
- identity maps;
- identity-reference boxscores;
- official player-level participation rows;
- selected player-level audit rows;
- raw PDFs and raw official JSON.

The retained Artifact contains aggregate reports, subgroup counts, and game-level source provenance only.

## Decision

```text
ready_for_expected_minutes_accuracy_audit_v2_inputs = true
ready_for_expected_minutes_accuracy_audit_v2 = false
ready_for_injury_feature_walk_forward_holdout_design = false
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

Passing this layer means only that the target-game participation input gap found by Accuracy Audit v1 has been repaired for the frozen 176-game population.

It does not mean that Expected Minutes Accuracy Audit v2 has passed. It does not unlock Injury Feature Walk-forward Holdout.

## Next task

The next task remains inside step 3 of the 2026-07-17 roadmap:

```text
Predeclare Expected Minutes Accuracy Audit v2
→ rebuild the same frozen 176-game evaluation population
→ use the official participation labels as target-game evaluation labels only
→ rerun structural and accuracy gates
```

Only an Accuracy Audit v2 pass may advance the project to the next canonical roadmap step:

```text
Injury Feature Walk-forward Holdout
```
