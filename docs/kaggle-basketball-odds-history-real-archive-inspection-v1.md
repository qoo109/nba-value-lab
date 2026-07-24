# Kaggle Basketball-odds-history Real Archive Inspection v1

Updated: 2026-07-24  
Project state: Research Candidate / Pre-Market-Backtest  
Formal Stake: 0

## Scope

This milestone inspected the user-provided Kaggle archive locally. The ZIP and raw CSV rows remain outside the public repository. Only aggregate counts, hashes, field names and qualification conclusions are recorded.

Archive SHA-256:

```text
sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419
```

## NBA contents

| File | Rows | Key structural result |
|---|---:|---|
| `nba_main_lines.csv` | 8,153 | 1,199 recoverable Pinnacle event IDs and 1,979 scrape timestamps |
| `nba_detailed_odds.csv` | 149,752 | 8,107 matchup/timestamp groups and 10 market labels |
| `nba_preseason_main_lines.csv` | 629 | 50 source events and 246 timestamps |
| `nba_preseason_detailed_odds.csv` | 12,868 | 616 matchup/timestamp groups |

Positive findings:

- every detailed NBA snapshot group maps uniquely to a main-line snapshot through exact `matchup + timestamp`;
- Pinnacle numeric source event IDs are recoverable from all main-line `game_link` values;
- duplicate `event + timestamp` main-line keys are zero;
- duplicate detailed `matchup + timestamp + market + selection` keys are zero;
- detailed decimal odds are numerically valid;
- no quote rows or prices were copied to the repository.

## Blocking findings

### Timestamp is not provider-origin

The notebook creates `scrape_timestamp` with `datetime.utcnow()` and writes it as a timezone-naive string. One timestamp is assigned to an entire league batch. Detailed event pages are scraped sequentially after that timestamp is created.

Therefore:

```text
provider-origin timestamp: false
exact quote-level observed_at: unverified
strictly pre-tip: unverified
```

The timing drift is visible in the data. Of 8,076 comparable regular-container moneyline snapshots, only 6,413 (79.41%) match between the main page and detailed page. There are 449 groups with a maximum side difference above 0.05 decimal and 188 above 0.10.

### T-60 cannot be derived

The archive does not contain scheduled tip-off. It also does not declare home/away semantics. An external, deterministic schedule mapping would be required, but it would not repair the batch-level timestamp limitation.

### Coverage is not a stable seven-minute series

For regular-container events, the median observed within-event gap is 26.125 minutes and only 26.89% of gaps are 15 minutes or less. A public claim that scraping is attempted every seven minutes is not equivalent to achieved quote coverage.

### Competition contamination

`nba_main_lines.csv` contains 11 rows using non-standard All-Star mini-tournament teams (`USA Stars`, `USA Stripes`, `World`). The file cannot be treated as regular-season-only without a governed competition filter.

### Upstream rights are not established

The notebook identifies Pinnacle pages as the upstream source and uses Selenium; a later notebook cell imports `undetected_chromedriver`. The archive contains no evidence establishing automation, retention or redistribution rights. A Kaggle CC0 label does not by itself establish rights to the upstream extracted data.

## Decision

```text
KEEP_PRIVATE_RESEARCH_DIAGNOSTIC_ONLY_REJECT_FORMAL_POINT_IN_TIME_INGESTION
```

Allowed role:

- private schema and cadence research;
- source-event identity research;
- non-formal data-quality diagnostics.

Not allowed:

- formal T-60 input;
- Frozen Gold point-in-time join;
- historical market backfill;
- G1.2.0 real dry-run;
- Market Backtest, CLV, EV, ROI or Drawdown;
- betting-edge claims or Stake above 0.

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```
