# Injury Team Submission Status v1

## Purpose

The official NBA injury PDF is a player-status report, but a game-level injury model also needs to know whether each team actually submitted its report.

A missing player row is ambiguous unless the team-level state is retained. It may mean:

- the team submitted one or more player statuses;
- the team explicitly submitted no injuries;
- the team was `NOT YET SUBMITTED`;
- the parser saw the team context but could not resolve its submission state;
- the source or player parser missed the team entirely.

This layer makes those states explicit before a zero injury burden can be assigned.

## Team states

```text
SUBMITTED_WITH_PLAYER_ROWS
SUBMITTED_NO_INJURIES
NOT_YET_SUBMITTED
UNKNOWN_NO_PLAYER_ROWS
```

Only `SUBMITTED_NO_INJURIES` may create a zero-burden healthy team.

The following may never be converted to zero burden:

```text
NOT_YET_SUBMITTED
UNKNOWN_NO_PLAYER_ROWS
MISSING_TEAM_LEDGER
synthetic missing side
conflicting submission state
```

## Parser

`scripts/build_multi_report_team_submission_panel.py` downloads each registered official PDF into temporary storage and extracts game/team context without retaining player names or injury reasons.

It records:

- official game key;
- team and opponent;
- home/away side;
- scheduled tip-off;
- publication time used as `observed_at`;
- source URL and SHA-256;
- player status row count;
- `NOT YET SUBMITTED` marker;
- explicit no-injuries marker;
- final submission state.

If only one side of a matchup appears in the parsed PDF context, the missing side is retained as:

```text
UNKNOWN_NO_PLAYER_ROWS
synthetic_missing_side = 1
```

It is not treated as healthy, and the full report is not discarded merely because one side is unresolved.

Raw PDFs are deleted when the temporary directory closes.

## Reconciliation

`scripts/reconcile_injury_team_submission_status.py` joins the team ledger to the existing long injury feature panel.

Rules:

- `SUBMITTED_WITH_PLAYER_ROWS` confirms that the team submitted a report;
- when its player panel is available, the existing prior-only values remain in use;
- when its player panel is missing, the team remains snapshot-available but feature-unavailable;
- `SUBMITTED_NO_INJURIES` requires zero player rows and creates explicit zero burden;
- `NOT_YET_SUBMITTED` remains incomplete;
- unknown, synthetic, or missing ledger states remain incomplete;
- state conflicts block selection readiness;
- repeated publication times remain longitudinal snapshots, not independent games.

The reconciled panel is then passed through the already frozen T-60 selection policy.

## Why this is separate from player identity

Player identity answers which listed person is referenced. Team submission completeness answers whether the absence of listed players is meaningful.

A high player-ID match rate cannot prove that a team with no player rows was healthy. The two layers must remain separate.

## Verified official live pilot

Workflow run:

```text
29592821690
```

Official team submission ingestion:

| Item | Result |
|---|---:|
| Requested reports | 7 |
| Successful reports | 7 |
| Failed reports | 0 |
| Unique report dates | 5 |
| Unique publication times | 7 |
| Team submission rows | 204 |
| Independent games covered | 72 |
| Submitted with player rows | 115 |
| Not Yet Submitted | 87 |
| Unknown synthetic sides | 2 |
| Submission conflicts | 0 |

All 204 team rows and all 72 games matched Historical Gold with no fuzzy team matching, unmatched games, or duplicate Gold schedule keys.

Reconciliation results:

| Item | Result |
|---|---:|
| Original player-derived team rows | 126 |
| Reconciled team rows | 204 |
| Reconciled matchup snapshots | 102 |
| Independent games represented | 72 |
| Complete matchup snapshots | 52 |
| Feature-ready matchup snapshots | 46 |
| Original rows missing a team ledger | 0 |
| Matchup side errors | 0 |
| Non-pregame rows | 0 |
| Reconciliation errors | 0 |
| Explicit submitted-no-injuries teams | 0 |

The pilot contained no explicit `SUBMITTED_NO_INJURIES` team, so the layer did not manufacture any new zero-burden teams.

## Frozen selection result

Before reconciliation, the player-only long panel contained:

```text
41 independent games
63 matchup snapshots
31 selected T-60 games
```

After adding the team submission ledger:

```text
72 independent games represented
102 matchup snapshots
31 selected T-60 games
```

The selected sample correctly remained **31 independent games**. The additional team-only and unsubmitted snapshots improved completeness accounting but did not pass the feature-ready gate.

Rejection after reconciliation:

```text
39 incomplete snapshots
2 feature-unavailable snapshots
```

This is a positive safety result: broader source coverage did not inflate the trainable sample.

## Workflow

```text
Validate injury team submission status v1
```

The live pilot:

1. builds the existing multi-report player panel;
2. independently builds the team submission panel;
3. matches both panels to Historical Gold;
4. rebuilds prior-only player values and the original long injury panel;
5. records the baseline frozen-policy selection;
6. reconciles team submission states;
7. reruns the same frozen selection policy;
8. verifies that only explicit submitted-no-injuries teams can receive zero burden;
9. deletes temporary player-level rows;
10. uploads aggregate and team/game-level QA only.

## Activation boundary

This layer improves completeness accounting, but it does not lower the independent-game threshold.

```text
minimum injury holdout gate: 100 independent selected games
initial reliability target: 300 independent games
ideal target: 500 independent games across months or seasons
```

Current result:

```text
31 / 100 independent selected games
```

Expected Minutes Accuracy Audit and Injury Feature Walk-forward Holdout remain blocked. Model training, probability adjustment, and betting-edge claims remain disabled.
