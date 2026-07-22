# Historical Silver 2023-24 source archive reconciliation design v1

This design follows the consumed retry request:

```text
HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002
```

The retry classified both missing `2023-24` Silver team-feature games as:

```text
nbastats_game_present_pbpstats_game_absent = 2
```

This means the Silver builder did not omit valid possession-derived team features. The current evidence points to a source archive gap: game rows exist in the NBA Stats side of the archive, while PBP Stats possession rows are absent.

## Design objective

Define the next controlled follow-up without changing Silver, rebuilding Gold, reading candidate CSV files, or producing row-level evidence.

The next follow-up may design a one-time aggregate-only source archive reconciliation request. That request must be separately approved before any real source archive is downloaded or read.

## Allowed follow-up lanes

### 1. Source archive reconciliation

The primary lane is to compare existing Shufinskiy `nbastats` and `pbpstats` archive coverage at aggregate level for the same season.

Allowed only after a separate request and approval:

- temporary source archive download;
- aggregate counts by source component;
- aggregate classification of stable source gaps;
- one aggregate JSON artifact.

Still prohibited:

- raw rows or source archive artifacts;
- game IDs, dates, team codes, row-level records, or row-key hashes;
- Silver builder changes;
- Gold builder execution;
- manual row insertion or fuzzy matching.

### 2. Secondary team-feature QA reference

Chris Munch team-level statistics may be considered as a role-limited secondary QA candidate:

```text
ROLE_LIMITED_SECONDARY_TEAM_FEATURE_QA_CANDIDATE
```

The candidate files are:

```text
cumulative_scraped/games_advanced.csv
cumulative_scraped/games_four-factors.csv
cumulative_scraped/games_traditional.csv
data_dictionary.csv
```

Before any execution, this lane needs a separate manifest and fetch/verify script with dataset handle, dataset version, file list, sizes, SHA-256 values, row counts, columns, allowed outputs, and prohibited outputs.

Chris Munch data must not be used to patch Silver or rebuild Gold in this design.

### 3. Documented exception

If reconciliation confirms the two games are stable upstream gaps, the project may keep them as explicit source-gap exceptions. Such an exception must remain aggregate-only in public evidence and must not expose game IDs, dates, teams, or row hashes without a separate policy.

## Current boundary

This design is documentation and policy only:

```text
network calls made: false
candidate CSV downloaded or read: false
Chris Munch raw rows read: false
Shufinskiy raw rows read: false
Gold database created or read: false
raw rows emitted: 0
raw files emitted: false
formal stake: 0
```

## Next state

```text
HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_REQUEST_DRAFT_READY_FOR_IMPLEMENTATION
```

That next state may create an approval-gated request draft. It still must not perform data execution until the user explicitly approves the exact request.
