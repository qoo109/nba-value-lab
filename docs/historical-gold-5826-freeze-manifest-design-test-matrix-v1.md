# Gold 5,826 Freeze Manifest Synthetic Test Matrix v1

The synthetic implementation must prove deterministic hashing and fail-closed behavior without reading the real Gold Artifact.

Required positive tests:

```text
repeat digest stability
insertion-order independence
volatile feature timestamp invariance
policy-excluded metadata invariance
```

Required negative tests:

```text
stable feature mutation
stable metadata mutation
missing/extra schema columns
missing table
wrong row count
wrong season set
duplicate team-game or matchup key
incomplete matchup
blank date/identifier
non-finite REAL
BLOB value
write attempt
database file mutation
forbidden output key
output over 1 MiB
```
