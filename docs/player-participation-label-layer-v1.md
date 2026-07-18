# Player Participation Label Layer v1

## Roadmap position

This layer is not a new project direction. It is a repair subtask inside the 2026-07-17 roadmap step:

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

Wave 1＋Wave 2 already produced 176 independent frozen T-60 games. Accuracy Audit v1 executed, but target-game participation-label coverage was incomplete. This layer fills that data gap before a separately predeclared Accuracy Audit v2.

## Source

Provider:

```text
NBA Official LiveData Boxscore
```

URL contract:

```text
https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{official_game_id}.json
```

The official final-game payload provides:

- `personId`;
- team tricode;
- `played`;
- `starter`;
- official status;
- `notPlayingReason` code;
- actual minutes.

Player names and free-text `notPlayingDescription` values are read only as part of the source payload and are never retained in repository outputs or uploaded Artifacts.

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

No missing or ambiguous state is silently converted to a successful zero-minute label.

## Source validation

Every selected game must pass:

- historical game ID → 10-digit official NBA game ID normalization;
- official response game ID equality;
- final game status `3`;
- Gold-selected game date agreement;
- home and away team tricode agreement;
- unique `(historical_game_id, player_id)` rows;
- valid numeric player IDs;
- source URL, retrieval timestamp, byte count, and SHA-256 provenance.

Raw official JSON is not retained.

## Frozen structural gates

The gates are committed before the 176-game live result:

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

The gates are not relaxed after observing the live result.

## Workflow

```text
Validate player participation label layer v1
```

The workflow:

1. downloads audited five-season Historical Gold;
2. downloads the verified combined 176-game frozen T-60 panel;
3. rebuilds the fixed Wave 1 and Wave 2 official injury sources;
4. validates the frozen source success／failure patterns;
5. rebuilds deterministic player identity using the existing research archive;
6. downloads NBA Official LiveData final-game boxscores for all 176 games;
7. produces temporary deidentified participation labels;
8. joins labels only to the exact frozen selected snapshots;
9. audits source, identity, label, unknown, duplicate, and team coverage;
10. deletes player-level labels, identities, snapshots, boxscores, and raw source material;
11. uploads only aggregate reports, subgroup summaries, and game-level provenance.

## Decision boundary

Passing this layer means only:

```text
ready_for_expected_minutes_accuracy_audit_v2_inputs = true
```

It does not mean:

```text
Expected Minutes Accuracy Audit v2 passed
Injury Feature Walk-forward Holdout unlocked
model training unlocked
probability adjustment unlocked
betting edge established
```

After this layer passes, the next task is to predeclare Accuracy Audit v2 and rerun the Expected Minutes evaluation using the new official participation labels. Only an Accuracy Audit pass can return the project to the next 2026-07-17 roadmap stage: Injury Feature Walk-forward Holdout.
