# Historical Silver 2023-24 source archive reconciliation approval v1

Request ID:

```text
HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
```

Current state:

```text
HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH
```

## Approval

The repository owner explicitly approved one `workflow_dispatch` execution for aggregate-only 2023-24 Shufinskiy source archive reconciliation.

The approval allows exactly one future GitHub Actions run to temporarily download and read the Shufinskiy NBA Stats and PBP Stats source archives, compute aggregate archive manifest counts, coverage overlap counts, and the missing-reason aggregate histogram, then upload one aggregate JSON report not larger than 1 MiB.

## Still forbidden

The approved execution must not:

- download or read Chris Munch, Eoin, or any candidate CSV;
- create, modify, or upload Silver or Gold databases;
- upload source archives, raw rows, or raw files;
- emit game IDs, dates, team codes, source file paths, source file hashes, row-level records, or row-key hashes;
- modify the Silver builder;
- manually insert or override rows;
- use fuzzy matching;
- repair identity using scores;
- replace Historical Silver or Gold;
- rerun the cross-source audit;
- unlock market backtest, model retraining, betting-edge claims, or non-zero Stake.

## Manual dispatch

After this approval validates in CI, the one-time execution workflow is:

```text
Run approved Historical Silver source archive reconciliation once v1
```

Use branch:

```text
main
```

Use request ID:

```text
HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
```
