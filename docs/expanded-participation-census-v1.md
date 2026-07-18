# Expanded Participation Census v1 — Predeclaration

## Roadmap boundary

This task remains inside Step 3 of the canonical research roadmap:

```text
Expanded official participation-label census
→ predeclare Expected Minutes Accuracy Audit v3
→ Injury Feature Walk-forward Holdout
→ Timestamped Odds
→ Market Backtest
```

It does not calculate new accuracy metrics and does not begin Injury Holdout, model training, probability adjustment, Timestamped Odds, Market Backtest, or betting decisions.

## Frozen upstream population

Base merge commit:

```text
5eb62f969bc3df4ea2b89946c0e75cdadc45e66d
```

Frozen selected panel:

```text
Wave 1 selected games: 91
Wave 2 selected games: 85
Wave 3 selected games: 117
combined independent games: 293
cross-wave duplicate games: 0
selection policy: latest feature-ready snapshot at or before T-60m
fallback: none
```

The census must use exactly the combined 293-game panel produced by PR #51. Games may not be added, removed, replaced, or reselected after census results are observed.

## Frozen official label source

```text
source: NBA Official LiveData Boxscore
label policy: data/player-participation-label-policy-v1.json
importer: scripts/import_official_nba_participation_labels.py
```

Target-game participation labels and actual minutes are evaluation-only. They may not enter pregame features.

Frozen label states:

```text
PLAYED
EXPLICIT_DNP
INACTIVE_OR_NOT_DRESSED
UNKNOWN
SOURCE_MISSING at the game/source layer
```

Missing game sources, missing player rows, UNKNOWN states, and unmatched identities are never converted to DNP, zero minutes, healthy, or inactive.

## Frozen census pipeline

```text
rebuild Wave 1／2／3 selected player snapshots
→ require exact 293-game selected population
→ deterministic player identity only
→ rebuild prior-only Expected Minutes metadata
→ import official final-game participation labels
→ exact join by historical_game_id + player_id
→ classify evaluable conditional-role rows
→ aggregate census counts
→ delete temporary player-level rows before Artifact upload
```

No fuzzy player identity, fuzzy schedule matching, nearest-name guessing, or outcome-based sample selection is allowed.

## Census outputs

The retained Artifact may contain aggregate reports and source indexes, but no player names, injury reasons, free-text not-playing descriptions, raw official JSON, raw PDFs, player-level identity maps, or player-level prediction／label rows.

The census must freeze at least:

```text
combined selected games
successful official source games
source-missing games
official player rows
selected player snapshot rows
identity-matched rows
participation-label joined rows
UNKNOWN rows and rate
evaluable games
conditional PLAYED rows
starter PLAYED rows
bench PLAYED rows
10+ prior-game PLAYED rows
complete team-game groups
duplicate and team-consistency errors
```

## Preserved structural gates

The census is structurally ready only if all of the following hold:

```text
combined selected games = 293
cross-wave duplicate games = 0
official game source coverage = 100%
source-missing games = 0
participation-label join rate >= 99%
UNKNOWN rate <= 5%
identity match rate >= 95%
ambiguous identity rows = 0
fuzzy identity used = false
strict-prior violations = 0
duplicate selected games = 0
duplicate joined player rows = 0
team／game consistency errors = 0
forbidden player-level files retained = 0
```

These gates may not be lowered after observing the expanded census.

## Preserved Audit v2 sample thresholds

This census does not decide accuracy and does not calculate MAE, RMSE, bias, subgroup errors, or baseline improvements. It only measures whether the frozen v2 sample thresholds would be available for a separately predeclared Audit v3:

```text
evaluable games >= 150
conditional PLAYED rows >= 500
bench PLAYED rows >= 200
10+ prior-game PLAYED rows >= 400
```

Starter and complete team-game counts must also be reported using the same definitions as Audit v2. No threshold may be changed or redefined inside this census.

## Formal census states

```text
STRUCTURAL_BLOCKED
CENSUS_READY_AUDIT_V3_NOT_ELIGIBLE
CENSUS_READY_AUDIT_V3_ELIGIBLE
```

Interpretation:

- `STRUCTURAL_BLOCKED`: source, join, population, point-in-time, duplicate, consistency, or privacy gate failed.
- `CENSUS_READY_AUDIT_V3_NOT_ELIGIBLE`: structural gates passed, but one or more preserved Audit v2 sample thresholds are still below minimum.
- `CENSUS_READY_AUDIT_V3_ELIGIBLE`: structural gates and all preserved sample thresholds passed; only then may a separate Accuracy Audit v3 policy be predeclared.

Even `CENSUS_READY_AUDIT_V3_ELIGIBLE` does not authorize accuracy calculation, Injury Holdout, model training, probability adjustment, betting claims, or nonzero stake.

## Permanent non-activation boundary

```text
ready_for_expected_minutes_accuracy_audit_v3_execution = false
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
formal stake = 0
```

The only next decision after this census is whether a separate Expected Minutes Accuracy Audit v3 predeclaration may be created.
