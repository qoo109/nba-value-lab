# Historical Silver 2023-24 source-gap exception integration implementation design v1

## Purpose

This design converts the validated QA／coverage reporting policy into a frozen implementation contract. It does **not** implement production integration yet.

The future implementation will be a pure aggregate report transformer:

```text
raw Historical Gold／Silver coverage report
+ validated aggregate exception manifest
+ validated integration policy
↓
raw report preserved without mutation
+ additive documented_exception_reporting section
```

The transformer must not access databases, networks, source archives, Silver builders, Gold builders, or row-level identifiers.

## Triggering state

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_VALIDATED
```

Frozen evidence:

```text
raw Historical Silver games: 5,826
raw Historical Gold matchups: 5,824
raw missing Gold for Silver: 2
documented upstream source-gap exceptions: 2
exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
Gold dataset complete: false
formal Stake: 0
```

## Proposed module

```text
scripts/integrate_historical_silver_source_gap_exception_v1.py
```

Proposed pure function:

```python
integrate_documented_source_gap(
    raw_report: dict,
    exception_manifest: dict,
    integration_policy: dict,
) -> dict
```

The function may validate and transform in-memory dictionaries only. The initial implementation must not modify `scripts/analyze_historical_gold_silver_coverage_v1.py`.

## Structural validation

The transformer must reject structurally incomplete inputs before creating output. Required raw-report evidence includes:

- report schema and formal outcome;
- season scope;
- raw Silver, Gold and missing counts;
- missing counts by season and reason;
- unclassified missing count;
- builder-repair decision;
- privacy-boundary flags;
- formal Stake.

Structural failure means no output report is produced.

## Recognition gate

Recognition is all-or-nothing. Partial recognition is prohibited.

All conditions must remain true:

```text
report schema is frozen v1
2023-24 is in scope
raw formal outcome remains SOURCE_DATA_GAP_CONFIRMED
raw total missing count = 2
2023-24 missing count = 2
2023-24 missing_both_team_features = 2
all other missing reasons = 0
unclassified missing = 0
builder repair required = false
exception code = SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
exception count = 2
manifest unclassified count = 0
no prohibited identifiers emitted
formal Stake = 0
```

When every condition passes:

```text
documented_source_gap_exception_count = 2
unexplained_missing_count_after_documentation = 0
documented_exception_state = HISTORICAL_GOLD_SILVER_COVERAGE_DOCUMENTED_SOURCE_EXCEPTION_RECOGNIZED
```

On any semantic mismatch:

```text
documented_source_gap_exception_count = 0
unexplained_missing_count_after_documentation = raw missing Gold for Silver
documented_exception_state = FAIL_CLOSED_UNEXPLAINED_COVERAGE_GAP
```

The transformer must never guess a partial exception count.

## Output contract

Future schema:

```text
historical-gold-silver-coverage-with-documented-exceptions-v1
```

The output must preserve the complete raw report without mutation and add one aggregate-only section:

```text
documented_exception_reporting
```

Required additive fields:

```text
exception_policy_version
exception_policy_state
documented_source_gap_exception_code
documented_source_gap_exception_count
unexplained_missing_count_after_documentation
covered_or_documented_count
gold_dataset_complete
recognition_gate_passed
recognition_failure_reasons
```

Derived fields:

```text
covered_or_documented_count
  = raw covered_games + documented_source_gap_exception_count

unexplained_missing_count_after_documentation
  = raw missing_gold_for_silver - documented_source_gap_exception_count

gold_matchup_count_after_documentation
  = raw gold_matchup_rows
```

The raw Gold count stays `5,824`. The report must not rewrite Gold coverage as complete.

## Privacy boundary

The future transformer may not output or accept exception evidence containing:

```text
game_id
game_date
home_team_abbr
away_team_abbr
team_code
source_file_path
source_file_hash
row_level_record
row_key_hash
```

The output must remain below 1 MiB.

## Synthetic test matrix

The initial implementation PR must cover at least:

1. valid frozen aggregate fixture recognizes exactly two exceptions;
2. raw missing count `3` recognizes zero and reports three unexplained;
3. wrong missing reason recognizes zero;
4. builder repair required recognizes zero;
5. unclassified gaps recognize zero;
6. exception-count mutation recognizes zero;
7. exception-code mutation recognizes zero;
8. Stake above zero fails closed;
9. privacy-boundary mutation fails closed;
10. structurally incomplete input raises before output;
11. all input dictionaries remain unchanged;
12. output remains aggregate-only and below 1 MiB.

## Implementation sequence

```text
1. Create pure transformer module on a separate branch.
2. Add synthetic fixtures and mutation tests only.
3. Add validation workflow.
4. Verify the current analyzer is unchanged.
5. Verify no database, network or source-archive path exists.
6. Merge synthetic implementation after CI passes.
7. Request separate approval before any real-reference validation.
```

## Current boundaries

This design performs no data execution:

```text
production module created: false
coverage analyzer changed: false
database read or write: false
network calls: false
source archives read: false
real rows read: false
raw rows emitted: 0
Silver or Gold changed: false
cross-source audit rerun: false
market backtest: false
model retraining: false
betting-edge claim: false
formal Stake: 0
```

## Next state

After validation:

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_READY_FOR_IMPLEMENTATION
```

That next lane authorizes only a synthetic, pure-transformer implementation. It does not authorize real-reference execution, analyzer replacement, Silver／Gold modification, cross-source audit reruns, market backtests, or model activation.
