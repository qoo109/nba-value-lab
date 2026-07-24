# NBA Value Lab Handoff — Kaggle Basketball-odds-history Local Inspector v1

更新日期：2026-07-24  
Formal Stake：0

## Repository state before milestone

```text
main: 711ebafe8996b507ef07c9aa5244e176f402cff3
latest merged PR: 170
open PRs before branch creation: none
```

## Preserved user decisions

```text
HoopsAPI runtime path: DEFERRED_BY_USER_NO_EXECUTION
BloomBet schema probe: DEFERRED_BY_USER_NO_EXECUTION
The Odds API runtime path: DEFERRED_BY_USER_NO_EXECUTION
paid historical odds path: NOT APPROVED
provider requests executed: 0
manual archive path: continue
```

## Milestone

```text
PR #171 — Add Kaggle basketball odds local archive inspector v1
KAGGLE_BASKETBALL_ODDS_HISTORY_LOCAL_INSPECTOR_VALID
```

Created:

- offline ZIP/directory inspector;
- NBA filename and CSV-header detection;
- aggregate row/file/column/hash reporting;
- possible timestamp/bookmaker/event/team/price column classification;
- notebook metadata inspection;
- contract tests using temporary synthetic archives;
- aggregate-only GitHub Actions QA;
- current status v13.

## Public dataset evidence

```text
dataset: Basketball-odds-history
Kaggle slug: zachht/wnba-odds-history
public license label: CC0: Public Domain
collection start claim: 2025-08-24
scrape attempt interval claim: 7 minutes
scope claim: global, NBA, college and WNBA
public file count observed: 550
```

These are dataset-page claims only. They do not verify upstream source rights, actual timestamp semantics, bookmaker identity or point-in-time suitability.

## Dedicated validation and Artifact QA

```text
workflow run: 30065900883
job: 89396695317 / success
artifact: 8586216269
artifact digest: sha256:b202cdf365caa1eebed5b1dfd543e695e5203c888a4570b1929a5c4e729fc9b6
artifact formal state: KAGGLE_BASKETBALL_ODDS_HISTORY_LOCAL_INSPECTOR_VALID
contract tests: 37 / 37 PASS
artifact inspected: true
```

Aggregate-only QA confirms:

```text
offline only: true
manual download required: true
source archive outside repo required: true
aggregate output outside repo until reviewed: true
ZIP and directory supported: true
synthetic contract only: true
real archive inspected: false
quote rows emitted: 0
prices emitted: 0
provider requests executed: 0
timestamp semantics verified: false
upstream provenance verified: false
point-in-time qualified: false
historical backfill qualified: false
formal history write authorized: false
market metrics executed: false
Formal Stake: 0
```

## No execution claims

```text
real archive downloaded by assistant: false
real archive inspected: false
network requests by project code: 0
provider requests: 0
real quote rows retained: 0
quote rows emitted: 0
prices emitted: 0
timestamp semantics verified: false
upstream provenance verified: false
point-in-time qualified: false
historical backfill qualified: false
formal history write authorized: false
Market Backtest: false
Formal Stake: 0
```

## Do not do

- Do not commit the downloaded Kaggle ZIP or extracted CSV files.
- Do not put the private inspection JSON in the public repo before review.
- Do not treat a CC0 Kaggle label as proof of upstream extraction rights.
- Do not treat column names containing `time` or `date` as proof of observation time.
- Do not publish CSV rows, prices or bookmaker quote histories.
- Do not authorize historical backfill, G1.2.0 or market metrics based only on schema presence.

## Next unique mainline

```text
AWAIT_MANUAL_KAGGLE_BASKETBALL_ODDS_HISTORY_ARCHIVE_FOR_LOCAL_INSPECTION
```

After the user manually downloads the current Kaggle archive to a private local folder, run the inspector and review aggregate-only output. A schema candidate then requires separate timestamp-semantics, bookmaker-identity, upstream-provenance and rights review.
