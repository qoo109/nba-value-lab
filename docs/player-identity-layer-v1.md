# Player Identity Layer v1

## Purpose

Match official NBA injury-report player names to audited NBA Stats player IDs.

This layer exists because the injury report provides names while the play-by-play source provides stable numeric player IDs. The join must be deterministic before injury statuses can become model features.

## Silver `player_aliases`

The Silver builder extracts all available `PLAYER1`, `PLAYER2`, and `PLAYER3` identity fields from NBA Stats event rows and aggregates them into:

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

## Five-season player directory

A lightweight directory builder scans only NBA Stats event archives for 2019–20 through 2023–24. It does not rebuild possessions, Gold features, or model data.

The verified directory contains:

- 4,615 player alias rows
- 1,331 unique NBA player IDs
- five complete seasons
- zero duplicate alias IDs
- zero unusable normalized names

The multi-season directory is used only to resolve stable identity. It may use appearances from other dates or seasons because a player ID is not a predictive game feature. Injury status, expected minutes, and player value remain subject to strict point-in-time rules.

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
3. full five-season directory + unique exact normalized name;
4. team + season + unique suffixless name;
5. season + unique suffixless name;
6. full five-season directory + unique suffixless name.

Any scope that returns more than one distinct player ID is marked ambiguous and blocked. The system does not pick the closest name.

## Verified historical fixture

The official 2023-12-18 08:30 ET injury report produced:

- 118 normalized injury rows
- 118 rows matched to historical games
- 115 player IDs matched
- 97.4576% player match rate
- 97.4576% high-confidence exact match rate
- 109 team-and-season exact matches
- 6 globally unique exact matches recovered from prior seasons
- zero ambiguous identities
- zero fuzzy matches
- zero schedule or home/away errors

The three intentionally unmatched rows were players with no NBA event identity in the five-season source window:

- Miles Norris
- Jaylen Clark
- Jaylen Martin

They remain blocked rather than being guessed from G League or non-approved roster sources.

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
- the identity directory covers all configured seasons;
- duplicate alias IDs are zero.

Even a successful identity join does not enable model training. The next requirements are:

1. multiple official report timestamps and dates;
2. cross-season injury-report layout and identity coverage;
3. status-change sequencing;
4. point-in-time player value and expected-minutes estimates;
5. holdout validation before any feature promotion.

## GitHub Actions

```text
Actions
→ Validate player identity layer v1
→ Run workflow
```

The live pilot rebuilds the 2023–24 Silver schedule, builds the five-season player directory, imports one official injury report, performs the identity join, deletes the normalized name-level snapshot, and uploads only aggregate QA plus the ID-only map.
