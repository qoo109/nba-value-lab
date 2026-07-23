# Historical Gold 5,826 Complete Corpus Freeze Policy v1

## Purpose

The five-season Historical Silver and Historical Gold reference is now complete for the governed scope:

```text
seasons: 2019-20 through 2023-24
Silver games: 5,826
Silver team-game features: 11,652
Gold matchup features: 5,826
Gold team-game features: 11,652
missing Gold for Silver: 0
remaining documented source exceptions: 0
Gold point-in-time violations: 0
```

This policy defines how that complete Gold corpus may later be frozen without treating an expiring compressed SQLite file as the only long-term scientific identity.

The policy itself does not download the database, calculate a corpus digest, freeze rows, authorize market evaluation, or change Stake from `0`.

## Why another freeze identity is required

The adopted Historical Gold binary is strongly bound by SHA-256:

```text
historical-gold-multiseason-recovered-v1.sqlite.gz
bytes: 5,268,851
sha256: a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085
```

That binary hash is valid execution evidence, but it is not sufficient as the only permanent scientific identity. Gold rows contain `feature_generated_at`, and Gold metadata also contains generation-time information. A scientifically equivalent rebuild can therefore produce a different compressed database hash even when all stable feature values are unchanged.

The long-term freeze identity must be an aggregate semantic manifest that excludes only explicitly volatile generation timestamps while preserving every stable schema column and all point-in-time feature values.

## Immutable evidence bindings

```text
policy base commit:
f19282040fb8e45326133c9b77afc1ff45c13bb4

recovery result SHA-256:
97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30

source archive SHA-256:
33d49fefc809f73d5d6cbad6d1d6690e0df6c89fe2b5a4d814ecc9ea4df6101b

adopted Artifact ID:
8551587005

adopted Artifact digest:
sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d

Artifact expiry:
2026-08-06T03:14:00Z

Silver SHA-256:
48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8

Gold SHA-256:
a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085
```

## Freeze unit

The freeze covers the complete corpus. No game or row may be excluded after inspecting outcomes, model errors, market coverage, injury coverage, or profitability.

```text
partial freeze: prohibited
row exclusions: prohibited
post-outcome sample selection: prohibited
exception exclusions: none
```

Any later scope change requires a new freeze-policy version.

## Semantic manifest design

The implementation must read these tables without modifying the database:

```text
gold_team_game_features
gold_matchup_features
gold_metadata
```

### Stable column rule

For both feature tables:

```text
include every schema column
except: feature_generated_at
```

No other feature, identifier, quality flag, version field, date, team code, or point-in-time value may be omitted from the digest calculation.

For `gold_metadata`, include all required scientific keys and exclude only the volatile `feature_generated_at` value.

Required metadata:

```text
pipeline_name
schema_version
feature_version
source_version
point_in_time_rule
same_day_games_policy
season_history_policy
season_labels
```

### Stable ordering

```text
gold_team_game_features:
season_label, game_date, game_id, team_abbr

gold_matchup_features:
game_date, game_id
```

Duplicate primary keys block the freeze.

### Canonical value encoding

```text
text: UTF-8, Unicode NFC
null: JSON null
integer: base-10 without leading zero
float: finite IEEE-754 round-trip representation, 17 significant digits
negative zero: normalized to zero
row: compact JSON array in schema-column order
row separator: newline
```

NaN and infinity block the freeze.

### Digest hierarchy

The implementation must produce:

```text
Gold team table semantic SHA-256
Gold matchup table semantic SHA-256
Gold metadata semantic SHA-256
Corpus semantic SHA-256
```

The corpus SHA-256 is calculated from a canonical aggregate manifest containing the table digests, stable row counts, schema/feature/source versions, season scope, duplicate checks, and point-in-time validation.

The public manifest may contain aggregate counts and hashes only. It must not emit game IDs, dates, team codes, raw rows, sampled rows, or row-level hashes.

## Real Artifact access policy

The preferred implementation path is:

```text
Download exact GitHub Artifact 8551587005 before expiry
Verify Artifact digest
Verify Gold filename, bytes and SHA-256
Open database read-only
Generate aggregate semantic manifest
Upload only the aggregate manifest and validation receipt
```

Real Artifact execution must be separately implemented and separately approved. It must be `workflow_dispatch` only, use a required confirmation value, run from `main`, and permit at most one execution attempt.

The policy stage performs no database or network access.

## Expiry rule

If Artifact `8551587005` expires before the freeze-manifest execution:

```text
Do not silently rebuild.
Do not accept an unbound replacement database.
Do not infer equivalence from row counts alone.
```

A new governed rebuild must first record the complete source archive manifest and produce a newly bound Artifact. This is necessary because the current recovery result binds the official CDN recovery archive and output files, but it does not publish every five-season upstream archive hash required for an independently reproducible byte-for-byte rebuild.

## Invalidation rules

A new freeze version is required when any of these changes:

- Gold binary SHA-256;
- Gold schema version;
- Gold feature version;
- source version;
- season scope;
- table row count;
- semantic table digest;
- semantic metadata digest.

The freeze is blocked when:

- point-in-time violations exceed zero;
- duplicate keys exceed zero;
- required metadata is missing;
- any unexplained Silver-to-Gold gap exists;
- any nonfinite numeric value exists.

## Remaining data dependencies

### Historical Silver and Gold

No additional game/PBP/team-feature data is required before the freeze-manifest design. This five-season reference is complete at `5,826 / 5,826`.

### Timestamped bookmaker odds

The project still lacks real, legal, auditable bookmaker-level historical NBA prices with reliable `observed_at`. This is a downstream market-data gap, not a Gold-corpus gap.

It is required before:

```text
market backtest
CLV
EV
ROI
Drawdown
```

It does not block the corpus freeze policy.

### Historical injury snapshots

The official injury pilot currently has:

```text
independent games available: 41
primary T-60 selected games: 31
minimum activation gate: 100 independent games
```

It also still requires a point-in-time team submission-completeness ledger before a formal injury holdout. These gaps block injury-aware activation, but do not block freezing the baseline Gold corpus.

## Boundaries

This policy does not authorize:

- a real Artifact download;
- a corpus freeze execution;
- database mutation;
- Silver or Gold rebuild;
- historical odds acquisition or purchase;
- market backtesting;
- CLV, EV, ROI or Drawdown;
- injury candidate activation;
- model training or retraining;
- probability adjustment;
- betting-edge claims;
- formal Stake above `0`.

## Formal outcome

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED
```

## Next controlled lane

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_DESIGN
```
