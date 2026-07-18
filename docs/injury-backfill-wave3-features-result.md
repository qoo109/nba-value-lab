# Wave 3 Injury Feature Backfill — Official Result

## Roadmap boundary

This result remains inside Steps 1–3 of the canonical 2026-07-17 roadmap. It does not begin Injury Holdout, Timestamped Odds, Market Backtest, or betting decisions.

## Verified run

```text
workflow run: 29629748942
artifact: injury-backfill-wave3-features
artifact id: 8425081360
digest: sha256:5f600148ce07f2388173b2151ba31e5ec822a31e1774377e15fda40a0d393d6e
```

## Gold-domain correction

The first run exposed two team-only official contexts absent from Historical Gold and absent from the player map:

```text
2024-01-19 DAL@GSW
2024-04-12 LAL@MEM
```

They contributed 12 team-ledger rows but could not create player features. The Gold-domain filter removed only these rows and enforced:

```text
unmatched player-backed games: 0
excluded player-backed games: 0
fuzzy schedule matching: false
```

Filtered team domain:

```text
input team games: 223
Gold-matched team games: 221
excluded team-only games: 2
input team rows: 1,306
Gold-domain team rows: 1,294
excluded team-only rows: 12
```

## Wave 3 feature QA

```text
ready overlap reports: 44
ready overlap dates: 15
filtered player rows: 2,918
filtered team rows: 1,306
player schedule games: 160
Gold-domain team games: 221
identity matched: 2,905 / 2,918 = 99.5545%
Expected Minutes rows: 2,818 = 96.5730%
Impact rows: 2,818 = 96.5730%
strict-prior violations: 0
same-day rows excluded: 513
future rows excluded: 25,940
ambiguous identity rows: 0
fuzzy identity used: false
```

## Frozen T-60 selection

```text
available independent games: 221
selected independent games: 117
games without primary selection: 104
selection rate: 52.9412%
feature unavailable: 4
incomplete snapshot: 100
duplicate selected games: 0
```

No cutoff, fallback, or diagnostic policy was changed after observing the result.

## Three-wave combined panel

```text
Wave 1 selected: 91
Wave 2 selected: 85
Wave 3 selected: 117
raw selected rows: 293
cross-wave duplicate games: 0
combined independent games: 293
game identity conflicts: 0
selection policy conflicts: 0
duplicate output games: 0
```

Sample status:

```text
minimum Accuracy Audit game gate 100: met
initial reliability gate 300: not met
ideal gate 500: not met
```

## Formal decision

```text
Wave 3 selected panel: Research Ready
combined Wave 1/2/3 panel: Research Ready
ready_for_expected_minutes_accuracy_audit: true
ready_for_injury_feature_walk_forward_holdout: false
ready_for_model_training: false
ready_for_probability_adjustment: false
ready_for_betting_edge_claim: false
formal stake: 0
```

`ready_for_expected_minutes_accuracy_audit` means the independent-game minimum is met. It does not mean the expanded player-level sample gates are met and does not authorize an audit without a new predeclared policy.

## Next exact task

Apply NBA Official LiveData participation labels to the expanded 293-game panel and freeze:

```text
evaluable games
conditional PLAYED rows
starter rows
bench rows
10+ prior-game rows
UNKNOWN and source-missing rates
```

Only after those counts are known may an expanded Expected Minutes Accuracy Audit policy be predeclared. Injury Holdout and Odds remain blocked.
