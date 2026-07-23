# Historical Gold 5,826 freeze manifest synthetic implementation v1

## Purpose

Implement the read-only semantic freeze-manifest builder defined by the validated implementation design, then validate it exclusively against miniature synthetic SQLite databases.

This stage does not download or read Artifact `8551587005`, does not create the canonical production manifest, and does not freeze the real Historical Gold corpus.

## Builder

```text
scripts/build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py
```

Required CLI:

```text
--gold-sqlite <decompressed SQLite path>
--policy <validated freeze policy JSON>
--output <aggregate manifest JSON>
```

The module uses only the Python standard library.

## Read-only controls

The builder:

- opens SQLite through `file:{path}?mode=ro&immutable=1`;
- enables and verifies `PRAGMA query_only=ON`;
- requires `PRAGMA integrity_check` to return `ok`;
- hashes the SQLite file before and after processing and requires equality;
- never performs DDL, DML, `VACUUM`, `ATTACH`, package installation, network access, or row export;
- fails closed on schema, unique-key, count, season, metadata, relational, type, privacy, or size mismatches.

Verification of the compressed GitHub Artifact archive remains outside this module and requires a later separately approved workflow. The builder records that compressed-artifact validation is still required.

## Exact schema contract

The implementation binds the existing `gold_metadata`, `gold_team_game_features`, and `gold_matchup_features` schemas from `scripts/historical_gold_schema.py`.

It validates:

```text
exact table set
exact column names, order, declared types, NOT NULL state and primary keys
exact unique-key sets
exact governed row counts
exact governed season set
exactly two aligned team rows for every matchup
no orphan team-game rows
no blank identifiers or dates
required metadata keys and season metadata
```

## Semantic encoding

The implementation-level design refines the policy's general canonical-encoding language into an explicit versioned representation:

```text
stream format: canonical JSON Lines
key ordering: sorted
UTF-8 text: Unicode NFC
NULL: {"type":"null"}
INTEGER: {"type":"int","value":"<base-10>"}
REAL: {"type":"real","value":"<finite float.hex()>"}
TEXT: {"type":"text","value":"<NFC text>"}
BLOB: prohibited
negative zero: normalized to positive zero before float.hex()
```

Rows are ordered by the validated policy and streamed directly into SHA-256. No row values or row-level hashes are retained in the output.

The only excluded feature column is:

```text
feature_generated_at
```

The only excluded metadata key is:

```text
feature_generated_at
```

## Aggregate manifest

The builder produces aggregate fields only:

```text
policy and implementation identifiers
source Artifact and binary bindings
actual decompressed SQLite SHA-256
Gold metadata identity
season labels
schema SHA-256 digests
table semantic SHA-256 digests
metadata semantic SHA-256 digest
corpus semantic SHA-256 digest
row and column counts
point-in-time and duplicate validation
privacy and scientific boundaries
formal Stake
```

Forbidden output includes game IDs, game dates, team codes, feature IDs, raw/sample rows, row-level hashes, individual feature values, player information and market prices.

Maximum output size remains `1,048,576` bytes.

## Synthetic validation suite

```text
scripts/test_build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py
```

The suite executes 20 required tests:

1. repeated digest stability;
2. insertion-order independence;
3. volatile feature timestamp invariance;
4. volatile metadata invariance;
5. stable feature sensitivity;
6. stable metadata sensitivity;
7. missing-table blocking;
8. unexpected-column blocking;
9. missing-stable-column blocking;
10. wrong-row-count blocking;
11. duplicate team-game blocking;
12. orphan/incomplete matchup blocking;
13. wrong-season blocking;
14. blank-date blocking;
15. non-finite REAL blocking;
16. BLOB blocking;
17. SQLite write-attempt blocking;
18. database SHA-change blocking;
19. forbidden-output-key blocking;
20. output-size-limit blocking.

## Current boundaries

```text
real Artifact downloaded: false
real Gold database read: false
real execution workflow created: false
canonical semantic manifest created: false
real corpus frozen: false
market backtest executed: false
model training or retraining executed: false
formal Stake: 0
```

## Next controlled lane after successful validation

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DESIGN
```

That next lane may design the one-time real Artifact request and approval lifecycle. It still may not download or execute the real Artifact without a later explicit user confirmation.
