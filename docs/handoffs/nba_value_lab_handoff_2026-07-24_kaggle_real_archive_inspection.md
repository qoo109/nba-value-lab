# NBA Value Lab Handoff — Kaggle Real Archive Inspection

Updated: 2026-07-24  
Formal Stake: 0

## Repository state before milestone

```text
main: 18507ce6bb6e2214156f20770e221d579bedadae
latest merged PR: 171
open PRs before branch creation: none
```

## Input

The user uploaded a private Kaggle `Basketball-odds-history` ZIP. The raw archive and CSV rows were inspected locally and were not committed.

```text
archive SHA-256:
sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419
```

## Aggregate findings

```text
nba_main_lines.csv: 8,153 rows / 1,199 source events
nba_detailed_odds.csv: 149,752 rows / 8,107 snapshot groups
nba_preseason_main_lines.csv: 629 rows / 50 source events
nba_preseason_detailed_odds.csv: 12,868 rows / 616 snapshot groups
```

Positive structure:

- numeric Pinnacle event ID recoverable from all main-line game links;
- detailed groups map 100% to a unique main snapshot by exact matchup and timestamp;
- duplicate main event/timestamp keys: 0;
- duplicate detailed quote keys: 0.

Blocking findings:

- timestamps are collector-generated, timezone-naive and shared across a league batch;
- detailed pages are scraped sequentially after the batch timestamp is created;
- only 79.41% of comparable regular moneylines match between main and detailed pages;
- scheduled tip-off is absent, so T-60 and strictly pre-tip status cannot be derived;
- home/away semantics are not declared;
- the NBA container includes All-Star mini-tournament rows;
- achieved event cadence is much weaker than a stable seven-minute series;
- notebook provenance shows Pinnacle Selenium scraping and later `undetected_chromedriver`, but upstream automation and retention rights are not established.

## Decision

```text
KEEP_PRIVATE_RESEARCH_DIAGNOSTIC_ONLY_REJECT_FORMAL_POINT_IN_TIME_INGESTION
```

## No unlocks

```text
qualified T-60 source: none
historical backfill: false
formal history write: false
G1.2.0 real input: false
Market Backtest: false
CLV / EV / ROI / Drawdown: false
Formal Stake: 0
```

## Do not do

- Do not commit or redistribute the original ZIP or quote rows.
- Do not treat Kaggle CC0 as proof of upstream Pinnacle extraction rights.
- Do not treat the batch scrape timestamp as provider-origin quote time.
- Do not infer scheduled tip-off, home/away, regular-season status or T-60 from this archive alone.
- Do not use these prices for model selection or betting claims.

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```
