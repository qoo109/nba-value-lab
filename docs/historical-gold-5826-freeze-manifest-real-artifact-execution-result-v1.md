# Historical Gold 5,826 Real Artifact Semantic Freeze Execution Result v1

## Formal outcome

```text
formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_PASS_CONSUMED
request ID: HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
workflow rerun allowed: false
formal Stake: 0
```

The repository owner's exact approval was executed once through the manual `workflow_dispatch` executor on `main`. The request is consumed and the executor must remain retired.

## Execution evidence

```text
workflow run: 30000293169
job: 89183633328 / execute-once / success
executed head: 5eb4bd9c11740ed0f68b5b3806ede24335796c6f
source Artifact: 8551587005
source Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
output Artifact: 8560678596
output Artifact digest: sha256:a6bfa2afbd2aef32f7e3f87078caaf620d94c744cf1eec74760d20ae4d0d5531
output Artifact expiry: 2026-08-06T10:42:27Z
```

Every governed step passed: approval and immutable binding revalidation, exact Artifact transport, read-only semantic freeze execution, aggregate-only output enforcement, and final Artifact upload.

## Canonical semantic freeze

```text
manifest formal state: HISTORICAL_GOLD_SEMANTIC_CORPUS_MANIFEST_VALID
manifest SHA-256: sha256:dcd9522e7ee55669d5b4fd413e424aa01ac9182a1330d51c6f9bf6b13ad8059d
corpus semantic SHA-256: sha256:c0c48fe17d843714209c822422b9675eadbff8b6be048782a599b2085bc20cbd
decompressed SQLite SHA-256: sha256:c5e25f12ace407a2a0314d2968dd9af77bcb78a2ab3e75fadb30cd8af232a558
Gold matchups: 5826
Gold team-game rows: 11652
seasons: 2019-20, 2020-21, 2021-22, 2022-23, 2023-24
point-in-time violations: 0
duplicate matchup keys: 0
duplicate team-game keys: 0
database modified: false
raw rows emitted: 0
```

The manifest passed exact schema, exact row count, season set, integrity, relationship, duplicate, finite-value and read-only checks. The source database SHA-256 was unchanged before and after processing.

## Privacy and scientific boundary

The recorded files are aggregate-only. They contain no game IDs, dates, team codes, individual feature values, row-level hashes or raw rows.

This execution did **not** perform a market backtest, train or retrain a model, activate injury features, make a betting-edge claim, or authorize Stake above `0`.

## Formal records

- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-result-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-current-status-v2.json`

## Next unique mainline

```text
TIMESTAMPED_BOOKMAKER_ODDS_REAL_OBSERVED_AT_DATA_ACQUISITION_REQUIRED
```

Historical Gold is now semantically frozen for the governed five-season scope. Market evaluation remains blocked because real timestamped bookmaker odds with `observed_at`, opening/closing identity and bookmaker provenance have not been acquired and separately authorized.
