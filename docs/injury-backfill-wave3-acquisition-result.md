# Injury Backfill Wave 3 — Official Acquisition Result

## Canonical roadmap position

This result remains inside Steps 1–3 of the canonical 2026-07-17 roadmap. It does not begin Injury Holdout, Timestamped Odds, Market Backtest, CLV, EV, ROI, or a betting decision layer.

## Predeclared calendar

```text
season: 2023-24 regular season
weekday: Thursday
cadence: weekly / 7 days
start: 2024-01-04
end: 2024-04-11
dates: 15
slots ET: 08:30, 13:30, 17:30
candidate reports: 45
```

Registry commit:

```text
061f5af060890666d9fc7ca9de865fe129ce3a51
```

The calendar was committed before implementation or source inspection.

## Verified run and Artifact

```text
workflow run: 29628847808
artifact: injury-backfill-wave3-acquisition
artifact id: 8424782891
digest: sha256:4c974008f9f5055a78e1b57649feca0dcc189a262050abec5439035360db61af
```

## Official coverage

```text
requested reports: 45
requested dates: 15
player successful reports: 45
team successful reports: 44
ready overlap reports: 44
ready overlap dates: 15
player failure rate: 0%
team failure rate: 2.2222%
```

Aggregate source rows:

```text
normalized player rows: 3,008
player unique games: 167
team submission rows: 1,306
team unique games: 223
```

Team submission states:

```text
NOT_YET_SUBMITTED: 725
SUBMITTED_WITH_PLAYER_ROWS: 572
UNKNOWN_NO_PLAYER_ROWS: 9
submission conflicts: 0
```

## Fixed exclusion

```text
2024-01-11 17:30 ET
```

The player PDF parsed, but the report was `single_report_ready=false`. The team-submission parser rejected the source because multiple listed contexts were not before scheduled tip-off.

The timestamp remains a recorded failure and was not replaced.

## Cadence-aware auditor

The reusable acquisition auditor now reads `sampling_policy.cadence_days`.

```text
missing cadence_days → backward-compatible 14-day default
Wave 3 cadence_days → 7
```

Wave 1 and Wave 2 acquisition regressions passed unchanged.

## Formal decision

```text
ready_for_feature_backfill = true
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

Wave 3 acquisition passed its source, provenance, calendar, overlap, conflict, and privacy gates.

It does not yet establish deterministic player identity coverage, prior-only Expected Minutes coverage, frozen T-60 selected games, cross-wave independent-game yield, expanded participation-label sample counts, or Expected Minutes Accuracy Audit readiness.

## Next exact task

```text
filter Wave 3 panels to 44 ready overlaps
→ Gold schedule matching
→ deterministic player identity
→ prior-only Expected Minutes and Impact
→ team-submission reconciliation
→ frozen latest feature-ready at or before T-60
→ deduplicate against Waves 1 and 2 by historical_game_id
→ measure expanded independent-game and participation-label counts
```

Formal stake remains `0`.
