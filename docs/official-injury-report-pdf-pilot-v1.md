# Official NBA Injury Report PDF Pilot v1

## Purpose

This pilot converts one archived official NBA Injury Report PDF into the provider-neutral `injury-lineup-snapshot-v1` contract.

It is intentionally not a bulk backfill. The first goal is to prove:

- the official URL and report timestamp are preserved;
- the seven-column report can be parsed without a third-party injury client or PDF parser;
- matchup, team, player, status and reason fields are normalized;
- the report publication time is before the scheduled game;
- raw PDFs and player-level rows are not uploaded by default.

## Official source

Season page:

- <https://official.nba.com/nba-injury-report-2025-26-season/>

The archived PDF URL uses the report date, hour and AM/PM:

```text
https://ak-static.cms.nba.com/referee/injury/
Injury-Report_YYYY-MM-DD_hhAM.pdf
```

For example, the report published at 08:30 ET is stored as:

```text
Injury-Report_2023-12-18_08AM.pdf
```

The minute is part of the publication timestamp but is not encoded in the PDF filename.

The official report page states that teams submit injury statuses and reasons before games and that reports are continually updated during the day. Each publication timestamp must therefore be treated as a separate point-in-time snapshot.

## Historical timestamp semantics

For an archived official report:

- `source_report_time` is the official publication timestamp;
- `observed_at` uses that publication timestamp as the earliest verifiable public availability time;
- actual download time is stored separately as `retrieved_at` in the aggregate import report.

This prevents a report downloaded today from being represented as a live retrieval performed before the historical game.

## Native parser

The importer uses PyMuPDF word coordinates and the known seven-column landscape layout:

1. Game Date
2. Game Time
3. Matchup
4. Team
5. Player Name
6. Current Status
7. Reason

`Current Status` provides the row anchor. Player text is read only from the same baseline, while the Reason column may span multiple lines between adjacent status anchors.

Date, time, matchup and team values are carried forward only when they match strict field formats. This prevents report headers, publication timestamps and page metadata from changing game context.

Continuation pages may place valid rows above 95 points, so the parser reads the 40–530 point body window while separately excluding the seven-column header.

Current layout identifier:

```text
official-landscape-seven-column-2023-v1
```

If the official format changes, the importer must fail its row-count and layout QA rather than silently guessing.

## Validated historical fixture

The live verification uses the official report published on 2023-12-18 at 08:30 ET.

Verified result:

- 8 PDF pages
- 118 player status rows
- 10 `NOT YET SUBMITTED` team rows
- 11 games with at least one player status
- 20 teams with player rows
- 0 parser conversion errors
- 0 contract validation errors
- 0 contract validation warnings

Status distribution:

- Available: 6
- Doubtful: 3
- Out: 80
- Probable: 5
- Questionable: 24

The report is ready for the manual official-PDF pilot only. It is not approved for automated multi-season backfill or model training.

## Game times

Official reports label scheduled times as ET and omit AM/PM. Scheduled NBA times from 1:00 through 11:59 are interpreted as p.m. ET, while 12:xx remains noon. The timezone-aware result is converted to UTC.

This assumption is recorded in the pilot and must be revalidated if the official format changes.

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

1. reports sampled across multiple seasons and PDF layout revisions;
2. game IDs matched against the historical Silver schedule;
3. player-name resolution and alias QA;
4. missing-report and duplicate-report handling;
5. parser regression fixtures that do not redistribute NBA PDF content;
6. source terms and collection-rate review.
