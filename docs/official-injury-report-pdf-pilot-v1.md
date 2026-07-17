# Official NBA Injury Report PDF Pilot v1

## Purpose

This pilot converts one archived official NBA Injury Report PDF into the provider-neutral `injury-lineup-snapshot-v1` contract.

It is intentionally not a bulk backfill. The first goal is to prove:

- the official URL and report timestamp are preserved;
- the PDF table can be parsed into the expected seven columns;
- matchup, team, player, status and reason fields are normalized;
- the report publication time is before the scheduled game;
- raw PDFs and player-level rows are not uploaded by default.

## Official source

Season page:

- <https://official.nba.com/nba-injury-report-2025-26-season/>

PDFs follow the official filename convention:

```text
https://ak-static.cms.nba.com/referee/injury/
Injury-Report_YYYY-MM-DD_hh_mmAM.pdf
```

The report page states that teams submit injury statuses and reasons before games and that reports are continually updated during the day. Each PDF timestamp must therefore be treated as a separate point-in-time snapshot.

## Historical timestamp semantics

For an archived official report:

- `source_report_time` is the publication timestamp encoded by the official report link;
- `observed_at` uses that same publication timestamp as the earliest verifiable public availability time;
- actual download time is stored separately as `retrieved_at` in the aggregate import report.

This prevents a report downloaded today from being misrepresented as a live retrieval performed before the historical game.

## Parser

The pilot uses the MIT-licensed `nba-injury-report-pdf-to-df==0.1.7` package as a replaceable PDF table adapter. It expects:

- Game Date
- Game Time
- Matchup
- Team
- Player Name
- Current Status
- Reason

The repository's own code performs all provenance, matchup, team, time and contract validation after PDF extraction.

## Game times

Official reports label times as ET and omit AM/PM. The adapter treats scheduled NBA game times from 1:00 through 11:59 as p.m. ET, while 12:xx remains noon. The resulting timezone-aware timestamp is converted to UTC.

This assumption is recorded as part of the pilot and must be revalidated if the official format changes.

## Privacy and redistribution controls

Raw official PDFs are downloaded only into temporary GitHub Actions storage and deleted when the job ends.

By default the workflow also deletes the normalized player-level CSV before Artifact upload. Artifacts retain only:

- source URL and SHA-256;
- official report time and actual retrieval time;
- aggregate row, game, team and player counts;
- status counts;
- parsing and contract QA summaries.

## Usage

```bash
PYTHONPATH=scripts python scripts/import_official_nba_injury_report.py \
  --report-time 2023-12-18T08:30:00-05:00 \
  --output-dir out/official-injury-pilot
```

GitHub Actions:

```text
Actions
→ Import official NBA injury report PDF pilot
→ Run workflow
```

## Activation boundary

A successful single-report pilot does not authorize automated multi-season collection or model training.

Before bulk backfill, require:

1. reports sampled across multiple seasons and PDF format revisions;
2. game IDs matched against the historical Silver schedule;
3. player-name resolution and alias QA;
4. missing-report and duplicate-report handling;
5. parser regression fixtures that do not redistribute NBA PDF content;
6. source terms and collection-rate review.
