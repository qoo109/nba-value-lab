# Wave 3 Injury Feature Backfill — Predeclaration

## Roadmap

This task remains inside Steps 1–3 of the canonical 2026-07-17 roadmap. It does not begin Injury Holdout, Timestamped Odds, Market Backtest, or betting decisions.

## Frozen upstream

```text
Wave 3 acquisition run: 29629052936
ready overlap reports: 44
ready overlap dates: 15
fixed exclusion: 2024-01-11 17:30 ET
```

Failed or non-ready timestamps may not be replaced.

## Frozen pipeline

```text
ready-overlap filter
→ exact Gold schedule match
→ deterministic identity
→ prior-only Expected Minutes / Impact
→ long injury features
→ team-submission reconciliation
→ latest feature-ready snapshot at or before T-60
```

Permanent rules:

- no fuzzy identity;
- same-day and future player rows excluded;
- both teams complete and feature-ready;
- minimum 60 minutes before tip;
- latest eligible publication wins;
- no fallback;
- multiple publications are not independent games;
- missing, NYS, or unknown team states do not create healthy zero burden.

## Preserved gates

```text
ready overlap reports >= 18
ready overlap dates >= 8
player and team schedule match rate = 100%
identity match rate >= 95%
high-confidence identity rate >= 90%
ambiguous identity rows = 0
Expected Minutes coverage >= 85%
Impact coverage >= 85%
strict-prior violations = 0
reconciliation errors = 0
duplicate selected games = 0
retained player-level files = 0
```

No threshold may be lowered after feature results are observed.

## Three-wave combination

Verified upstream feature runs:

```text
Wave 1: 29629052948
Wave 2: 29629052937
```

Inputs are the independently selected Wave 1, Wave 2, and Wave 3 panels.

```text
deduplication key: historical_game_id
duplicate rule: latest eligible observed_at, then wave name
```

Identity, team, commence-time, policy, or fallback conflicts block readiness.

The workflow must report actual Wave 3 yield and combined independent games. The prospective 280–300 range is not a promotion gate.

## Decision boundary

A pass means only that Wave 3 and the combined panel are structurally research-ready.

It may not enable:

```text
Injury Holdout
model training
probability adjustment
betting edge claims
```

After feature completion, official participation labels must be applied to the expanded panel and sample counts frozen before any Accuracy Audit v3 policy is declared.

Formal stake remains `0`.
