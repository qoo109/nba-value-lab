# Injury Team Submission Status v1

## Purpose

The official NBA injury PDF is a player-status report, but a game-level injury model also needs to know whether each team actually submitted its report.

A missing player row is ambiguous unless the team-level state is retained. It may mean:

- the team submitted one or more player statuses;
- the team explicitly submitted no injuries;
- the team was `NOT YET SUBMITTED`;
- the parser saw the team context but could not resolve its submission state;
- the source or parser missed the team entirely.

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

Raw PDFs are deleted when the temporary directory closes.

## Reconciliation

`scripts/reconcile_injury_team_submission_status.py` joins the team ledger to the existing long injury feature panel.

Rules:

- `SUBMITTED_WITH_PLAYER_ROWS` must agree with existing player rows;
- `SUBMITTED_NO_INJURIES` requires zero player rows and creates explicit zero burden;
- `NOT_YET_SUBMITTED` remains incomplete;
- unknown or missing ledger states remain incomplete;
- state conflicts block selection readiness;
- repeated publication times remain longitudinal snapshots, not independent games.

The reconciled panel is then passed through the already frozen T-60 selection policy.

## Why this is separate from player identity

Player identity answers which listed person is referenced. Team submission completeness answers whether the absence of listed players is meaningful.

A high player-ID match rate cannot prove that a team with no player rows was healthy. The two layers must remain separate.

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
8. verifies that only explicit submitted-no-injuries teams receive zero burden;
9. deletes temporary player-level rows;
10. uploads aggregate and team/game-level QA only.

## Activation boundary

This layer may improve completeness accounting, but it does not lower the independent-game threshold.

```text
minimum injury holdout gate: 100 independent selected games
initial reliability target: 300 independent games
ideal target: 500 independent games across months or seasons
```

Model training, probability adjustment and betting-edge claims remain disabled regardless of parser success.
