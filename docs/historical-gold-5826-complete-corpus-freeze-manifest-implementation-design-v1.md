# Historical Gold 5,826 complete corpus freeze manifest implementation design v1

## Purpose

Define the implementation contract for a deterministic, read-only semantic identity of the complete five-season Historical Gold corpus.

Current governed reference:

```text
seasons: 2019-20 through 2023-24
Gold matchup rows: 5,826
Gold team-game rows: 11,652
remaining source exceptions: 0
point-in-time violations: 0
formal Stake: 0
```

This stage designs the future implementation. It does not download or read the real Artifact, create a semantic manifest, freeze the corpus, execute market backtesting, or retrain a model.

## Why the compressed database SHA is not enough

The adopted compressed Gold database SHA-256 remains immutable execution evidence, but generated timestamps and generated metadata can change during an otherwise scientifically equivalent rebuild. The long-term scientific identity therefore needs a semantic digest that includes every stable value and excludes only fields explicitly declared volatile by the validated freeze policy.

No implementation may invent an additional exclusion after inspecting the data.

## Future module

```text
scripts/build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py
```

Required command line:

```text
--gold-sqlite <decompressed SQLite path>
--policy <validated freeze policy JSON>
--output <aggregate manifest JSON>
```

The module must use only the Python standard library and must not contain networking code.

## Read-only database controls

The future module must:

1. validate the compressed input size and SHA-256 against the policy before decompression;
2. validate the decompressed database before semantic processing;
3. open SQLite through `file:{path}?mode=ro&immutable=1` with URI mode enabled;
4. enable and verify `PRAGMA query_only=ON`;
5. run `PRAGMA integrity_check`;
6. never execute DDL, DML, VACUUM, ATTACH, writable PRAGMA, or schema mutation;
7. compute the database SHA-256 before and after processing and require equality;
8. fail closed on any table, schema, count, season, identity, completeness, or point-in-time mismatch.

## Required tables

```text
gold_team_game_features
gold_matchup_features
gold_metadata
```

Expected counts:

```text
gold_team_game_features: 11,652
gold_matchup_features: 5,826
```

Every matchup must have exactly two corresponding team rows. Duplicate `(game_id, team_abbr)` and duplicate matchup `game_id` keys are prohibited.

## Canonical semantic encoding

The implementation must introspect table columns with `PRAGMA table_info` and derive stable columns from the validated policy:

```text
stable columns = all schema columns - explicit policy volatile columns
```

The only feature-column exclusion currently permitted by policy is `feature_generated_at`. Metadata exclusions must also come from the policy's explicit metadata exclusion list.

Rows are processed in policy-defined order:

```text
team table: season_label, game_date, game_id, team_abbr
matchup table: game_date, game_id
metadata: key
```

Values use explicit type tags:

```text
NULL    -> {"type":"null"}
INTEGER -> {"type":"int","value":"<base-10>"}
REAL    -> {"type":"real","value":"<finite float.hex()>"}
TEXT    -> {"type":"text","value":"<UTF-8 text>"}
BLOB    -> prohibited
```

Each row is encoded as sorted-key canonical JSON with compact separators, UTF-8, `allow_nan=false`, followed by one LF byte. Rows are streamed directly into SHA-256; they are not retained or exported.

## Required digests

The aggregate manifest must contain:

```text
team schema SHA-256
team table SHA-256
matchup schema SHA-256
matchup table SHA-256
stable metadata SHA-256
corpus SHA-256
```

The corpus digest must bind, in fixed order:

```text
manifest schema version
policy ID
team schema digest
team table digest
team row count
matchup schema digest
matchup table digest
matchup row count
metadata digest
metadata entry count
season set
point-in-time validation state
```

## Aggregate output only

The manifest may include counts, digests, schema/policy identifiers, Artifact bindings, season labels, validation booleans, scientific boundaries, and Stake.

It must not include:

```text
game IDs
game dates
team codes
feature IDs
raw or sample rows
row-level hashes
individual feature values
player information
market prices
```

Maximum output size is 1 MiB.

## Synthetic validation requirements

Before any real Artifact workflow is designed, the implementation must pass synthetic SQLite tests proving:

- identical stable data produces identical digests;
- insertion order does not affect digests;
- changing `feature_generated_at` does not affect the semantic digest;
- changing policy-excluded metadata does not affect the semantic digest;
- changing any stable feature or stable metadata changes the appropriate digest and corpus digest;
- missing tables, schema drift, wrong counts, duplicate keys, incomplete matchups, wrong seasons, blank dates, non-finite reals, BLOB values, attempted writes, database mutation, forbidden output keys, and oversized output all fail closed.

Synthetic tests may use miniature row counts. Real counts remain mandatory only for the separately approved real Artifact execution stage.

## Artifact boundary

Preferred future input remains exact Artifact `8551587005`, which expires at `2026-08-06T03:14:00Z`.

If that Artifact expires before real execution, the workflow must stop. It may not silently rebuild or substitute another file. A replacement requires a newly governed rebuild with a complete upstream source-hash manifest and a new explicit execution approval.

## Current boundaries

```text
implementation module created: false
real Artifact execution workflow created: false
real Gold database read: false
semantic freeze manifest created: false
corpus frozen: false
market backtest executed: false
model retraining executed: false
injury candidate activated: false
betting-edge claim: false
formal Stake: 0
```

## Next controlled lane

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_SYNTHETIC_VALIDATION
```
