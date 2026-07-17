# Player Identity Layer v1

## Purpose

Match official NBA injury-report player names to the audited NBA Stats player IDs stored in historical Silver.

This layer exists because the injury report provides names while the play-by-play source provides stable numeric player IDs. The join must be deterministic before injury statuses can become model features.

## Silver `player_aliases`

The Silver builder now extracts all available `PLAYER1`, `PLAYER2`, and `PLAYER3` identity fields from NBA Stats event rows and aggregates them into:

- `player_id`
- most frequent raw player name
- accent- and punctuation-normalized name key
- suffixless name key
- team ID and abbreviation
- season label
- first and last observed game ID
- event appearance count
- source and quality flags

The table contains one row per player, normalized name, team, and season. Raw source archives remain outside the repository.

## Name normalization

Normalization is deterministic and does not use approximate edit distance:

- Unicode accents are folded: `Jokić` → `jokic`;
- official `Last, First` order is reversed;
- apostrophes, periods, and hyphens are normalized;
- suffixes are standardized: `Junior` → `jr`;
- a suffixless key is stored only as a controlled fallback.

Examples:

```text
Lively II, Dereck → dereck lively ii
Jokić, Nikola     → nikola jokic
O'Neale, Royce    → royce oneale
```

## Matching order

For each injury snapshot row, the matcher first finds the exact historical game using:

```text
game date + away team + home team
```

It then evaluates player candidates in this order:

1. team + season + exact normalized name;
2. season + unique exact normalized name;
3. full Silver database + unique exact normalized name;
4. team + season + unique suffixless name;
5. season + unique suffixless name;
6. full Silver database + unique suffixless name.

Any scope that returns more than one distinct player ID is marked ambiguous and blocked. The system does not pick the closest name.

## Outputs

The player-level mapping intentionally excludes names and injury reasons. It contains only:

- `snapshot_record_id`
- historical `game_id`
- season and team
- `player_id`
- match method and confidence
- candidate count

Aggregate QA reports include coverage and method counts.

## Activation gate

A pilot is ready for the player-ID join only when:

- all injury rows map to historical games;
- there are no home/away side errors;
- there are no ambiguous names;
- at least 95% of player rows match;
- at least 90% are high-confidence exact matches;
- the Silver alias table contains at least 300 unique-season identities.

Even a successful identity join does not enable model training. The next requirements are:

1. multiple official report timestamps and dates;
2. cross-season player-identity coverage;
3. status-change sequencing;
4. point-in-time player value and expected-minutes estimates;
5. holdout validation before any feature promotion.

## GitHub Actions

```text
Actions
→ Validate player identity layer v1
→ Run workflow
```

The live pilot rebuilds 2023–24 Silver, imports one official injury report, performs the identity join, deletes the normalized name-level snapshot, and uploads only aggregate QA plus the ID-only map.
