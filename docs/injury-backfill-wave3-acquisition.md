# Injury Backfill Wave 3 — Acquisition Predeclaration

## Canonical roadmap position

Wave 3 remains inside Steps 1–3 of the canonical 2026-07-17 roadmap:

```text
Official injury snapshot backfill
→ independent feature-ready matchups
→ Expected Minutes Accuracy Audit
```

It does not begin the Injury Feature Walk-forward Holdout, Timestamped Odds acquisition, Market Backtest, CLV, EV, ROI, or a betting decision layer.

## Why Wave 3 exists

Expected Minutes Accuracy Audit v2 was formally:

```text
STRUCTURAL_BLOCKED
```

The official participation-label source, identity coverage, Expected Minutes coverage, point-in-time rules, privacy rules, and all preserved numerical accuracy gates passed. Four preserved sample gates did not:

```text
evaluable games: 135 / 150
conditional PLAYED rows: 313 / 500
bench rows: 127 / 200
10+ prior-game rows: 305 / 400
```

Wave 3 is a data-expansion task required by those pre-existing sample deficits. It is not a new modeling experiment and is not selected from injury severity, player identity, outcomes, or market prices.

## Frozen calendar

Registry:

```text
data/multi-report-injury-backfill-wave3-times.json
```

Calendar contract:

```text
season: 2023-24
phase: regular season only
weekday: Thursday
cadence: weekly
cadence_days: 7
start: 2024-01-04
end: 2024-04-11
dates: 15
official slots ET: 08:30, 13:30, 17:30
candidate reports: 45
```

The 15 dates are consecutive Thursdays. All 45 requested timestamps must be unique and disjoint from Waves 1 and 2.

## Why this window was selected

The window is chosen before Wave 3 source inspection and only from structural planning information already known after v2:

- the project needs roughly 100–125 additional independent selected games;
- Wave 1 plus Wave 2 produced 176 selected games from 24 calendar dates;
- a 15-date calendar sample projects roughly 110 additional selected games at the prior-wave observed rate;
- a later regular-season window gives more prospective players the opportunity to have 10+ strictly prior games.

The planning projection is not a promotion gate and may be wrong. No failed date may be replaced after observing source availability or selected-game yield.

## Acquisition gates

The acquisition wave must satisfy:

```text
successful player reports: at least 27 / 45
successful team reports: at least 27 / 45
overlapping successful reports: at least 27 / 45
unique overlapping dates: at least 10 / 15
maximum failure rate per pipeline: 40%
duplicate requested timestamps: 0
team-submission conflicts: 0
unexpected successful timestamps: 0
duplicate successful timestamps: 0
duplicate source URLs: 0
player-level files retained in Artifact: 0
```

These gates evaluate source and provenance quality. They do not guarantee a sufficient expanded selected-game population.

## Source and failure rules

Wave 3 uses the existing official NBA injury-report player and team-submission importers.

Every requested timestamp must end in one of the following observable states:

```text
SUCCESS
HTTP/source failure
NYS-only
parsed but single-report-ready=false
team pre-tip QA failure
structurally rejected
```

Permanent rules:

- unavailable reports remain failures;
- NYS-only reports remain NYS-only;
- parsed-but-not-ready reports remain excluded;
- failed times may not be replaced;
- no hand-picked successful dates;
- no player or injury-severity filtering;
- no outcome or market join during acquisition;
- multiple publication times are not independent games.

## Cadence-aware audit change

The reusable acquisition auditor previously assumed a fixed 14-day gap because Waves 1 and 2 were alternating-Monday samples.

Wave 3 requires the registry to declare:

```json
"cadence_days": 7
```

The auditor is updated so:

- missing `cadence_days` defaults to 14, preserving Waves 1 and 2;
- Wave 3 validates exactly 7-day gaps;
- a generic `ready_for_feature_backfill` decision is added;
- the legacy `ready_for_wave1_feature_backfill` alias remains for backward compatibility.

Wave 1 and Wave 2 regressions must remain unchanged.

## Privacy boundary

Before Artifact upload, remove:

- normalized player injury rows;
- parsed PDF files;
- player identity maps;
- point-in-time player values;
- player boxscore rows;
- any file containing player names or injury reasons.

The acquisition Artifact may retain only aggregate QA reports, source indexes, team-level submission states, and calendar/provenance summaries.

## Decision boundary

A successful Wave 3 acquisition may set:

```text
ready_for_feature_backfill = true
```

It may not set:

```text
ready_for_model_training
ready_for_probability_adjustment
ready_for_betting_edge_claim
```

A successful acquisition does not prove:

- Wave 3 features are ready;
- combined selected games reach 280–300;
- Expected Minutes passes;
- Injury Holdout may begin.

## Required next steps after acquisition

Only after the acquisition result is frozen:

```text
filter player and team panels to successful overlap
→ Gold schedule matching
→ deterministic player identity
→ prior-only Expected Minutes and Impact
→ team-submission reconciliation
→ frozen latest feature-ready at or before T-60
→ deduplicate against Wave 1 and Wave 2 by historical_game_id
→ measure expanded independent-game and player-label counts
```

If the expanded sample is structurally sufficient, a new Expected Minutes Accuracy Audit policy must be predeclared before observing expanded-sample accuracy results.

Formal stake remains:

```text
0
```
