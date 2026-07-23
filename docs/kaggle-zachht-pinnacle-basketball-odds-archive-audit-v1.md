# Kaggle ZachHT Pinnacle Basketball Odds Archive Audit v1

Updated: 2026-07-23  
Project: NBA Value Lab  
Formal Stake: 0

## Formal result

```text
KAGGLE_ZACHHT_PINNACLE_BASKETBALL_ODDS_ARCHIVE_RESEARCH_BLOCKED
```

The user supplied the public `Basketball-odds-history` ZIP for local qualification. The raw archive was inspected locally and was not committed to the repository or uploaded as a public Actions Artifact.

The files contain useful timestamped Pinnacle snapshots, but this source is not eligible for the formal point-in-time odds pipeline because the notebook uses prohibited automated scraping and evasion techniques, the archive does not store scheduled tipoff, and it does not overlap the frozen 2019-20 through 2023-24 Gold/OOF market-backtest population.

## Exact archive identity

```text
ZIP bytes: 7,477,620
ZIP SHA-256: sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419
Uncompressed bytes: 111,637,971
Files: 597
CSV files: 595
Notebook files: 1
Debug HTML files: 1
```

Only aggregate findings and file hashes are recorded. No quote-level rows or prices are preserved in the repository.

## What the notebook actually does

The included notebook identifies the dataset slug as `zachht/wnba-odds-history` and navigates to:

```text
https://www.pinnacle.com/en/basketball/matchups/
```

It:

- uses Selenium;
- includes an `undetected_chromedriver` implementation;
- masks `navigator.webdriver` in another implementation;
- reads the Pinnacle matchups page and individual event pages;
- creates `timestamp` with `datetime.utcnow()`;
- appends newly scraped rows to the prior CSV files;
- does not deduplicate unchanged snapshots before writing a new dataset version.

Therefore, the CSV `timestamp` is a UTC scrape-batch timestamp. For the detailed odds file it is not an exact per-quote observation time: the timestamp is created before the scraper visits the event pages sequentially and is later assigned to all detailed rows in that batch.

## NBA regular main-lines file

```text
File: archive/nba_main_lines.csv
Bytes: 1,634,926
SHA-256: sha256:5ae91c0a6a3813c181a2e38e21b0d18cdb2f36631cf0236e9af9c5183b354185
Rows: 8,153
Unique Pinnacle event URLs: 1,199
Unique scrape timestamps: 1,979
Observed range: 2025-09-10 23:14:26 UTC through 2026-05-24 23:44:55 UTC
```

Schema:

```text
team1, team2, game_link,
team1_moneyline, team2_moneyline,
team1_spread, team1_spread_odds,
team2_spread, team2_spread_odds,
over_total, over_total_odds,
under_total, under_total_odds,
timestamp
```

Aggregate QA:

| Check | Result |
|---|---:|
| Complete two-sided moneyline snapshots | 8,109 / 8,153 (99.4603%) |
| Missing-moneyline snapshots | 44 |
| Events with at least one complete moneyline snapshot | 1,199 / 1,199 |
| Full duplicate rows | 0 |
| Repeated identical snapshots when timestamp is ignored | 3,181 (39.0163%) |
| Consecutive event transitions | 6,954 |
| Transitions with a line or price change | 3,789 (54.4866%) |
| Median interval between NBA scrape timestamps | 30.34 minutes |
| Intervals at or below 15 minutes | 22.60% |

The file supplies two-sided decimal moneylines from one recoverable source bookmaker, as well as spreads and totals. `game_link` contains a stable Pinnacle event URL and event number.

## NBA detailed-odds file

```text
File: archive/nba_detailed_odds.csv
Bytes: 15,108,702
SHA-256: sha256:bae1cafa869fd6a1e38b033fb7484d52297f9fed5a0f1f1302dcd707e38448b7
Rows: 149,752
Markets: 10
Moneyline rows: 16,214
Complete two-sided moneyline snapshots: 8,107
```

All 149,752 detailed rows join uniquely to a main-lines snapshot using exact `matchup + timestamp` inside this archive. There are no full duplicate rows and no duplicate `Market + Selection + matchup + timestamp` keys.

However, the detailed schema contains no event URL, explicit bookmaker field or scheduled tipoff field. Its assigned timestamp is the league-batch timestamp rather than an exact time recorded when each quote was read.

## Positive findings

- A real scrape-time timestamp exists and its UTC interpretation is recoverable from the notebook.
- The upstream bookmaker is recoverable as Pinnacle from the notebook and event URLs.
- Two-sided decimal h2h prices are present.
- Stable Pinnacle event identifiers are present in the main-lines URL.
- Spread, total and detailed market snapshots are present.
- The detailed rows can be deterministically linked back to main snapshots within this archive.

## Blocking findings

### 1. Upstream terms and collection method

The Kaggle card labels the dataset CC0, but the notebook shows that the actual quote source is Pinnacle. Current Pinnacle terms prohibit scraping and automated access unless separately authorized, and the website states that sports odds are proprietary and may not be copied or disseminated without express written consent.

The notebook additionally uses `undetected_chromedriver` and browser-automation masking. This directly conflicts with the project's permanent rule not to bypass or evade access controls or technical restrictions.

A downstream CC0 label does not establish that the upstream odds were collected or redistributed with sufficient rights.

### 2. Point-in-time mapping is incomplete

The archive does not store `scheduled_tipoff`. Consequently, it cannot independently establish:

- whether every snapshot is strictly pre-tip;
- T-6h, T-3h, T-1h, T-30m, T-5m or Closing identity;
- snapshot lag relative to game start;
- an explicit Opening quote.

Team roles are stored only as `team1` and `team2`; explicit home/away fields are absent.

### 3. No overlap with the frozen formal backtest population

The regular NBA file begins in September 2025. The frozen Historical Gold corpus covers 2019-20 through 2023-24 and the frozen walk-forward OOF predictions cover 2021-22 through 2023-24. Therefore this archive cannot supply the missing historical quotes for the current 3,688-game OOF market backtest.

At most, with separate legal permission and a new schedule/model design, it could have served as a later-season forward research source. That path is not authorized because the upstream rights gate already fails.

## Formal permissions

```text
qualified for historical backfill: false
qualified for point-in-time odds join: false
qualified for market backtest: false
qualified for forward collection: false
raw or quote-level repository storage: false
raw or quote-level public Artifact storage: false
market metrics: false
CLV / EV / ROI: false
betting-edge claim: false
formal Stake: 0
```

Allowed role:

```text
local aggregate-only schema research and provenance evidence only
```

## Next exact task

Continue the no-cost source search with BloomBet's public documentation and terms. Do not create an account or connect a key until historical schema, provider timestamp semantics, retention rights and the zero-cost boundary have been verified.
