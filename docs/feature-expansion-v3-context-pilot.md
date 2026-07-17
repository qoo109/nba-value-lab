# Feature Expansion v3 — Schedule and Travel Context Pilot

## Purpose

This layer tests whether pregame schedule load and travel context add stable forecast value beyond the existing out-of-fold `walk-forward-v2` predictions.

It is deliberately separate from production Gold. Features are promoted only after an untouched-season holdout improves with paired bootstrap support.

## Point-in-time inputs

The builder uses only fields already available before each game:

- prior game dates
- home/away designation
- rest days
- back-to-back status
- games played in the previous 3 and 7 days
- previous game venue proxy
- current game venue proxy

No market odds, current-game outcomes, future games, injury statuses, or lineups are used.

## Context groups

### Schedule

- capped rest days for each side and the difference
- back-to-back flags
- games in the prior 3 and 7 days
- 3-in-4, 4-in-6, and 5-in-8 indicators

### Travel

- direct distance from the previous game venue
- cumulative travel distance over seven days
- timezone shift, including eastward and westward components
- altitude gain from the previous venue
- road-trip game number
- same-venue streak
- distance travelled on a back-to-back

## Venue approximation

`data/nba-venue-context-v1.json` contains arena or nearby city-center proxies. IANA timezones are evaluated on the game date so daylight-saving offsets are handled by the runtime.

Major systematic overrides:

- 2019-20 restart games from 2020-07-30 use an Orlando bubble proxy.
- 2020-21 Toronto home games use a Tampa proxy.

The archive does not identify every neutral-site game. The report therefore keeps `travel_is_venue_proxy=true` and `neutral_sites_fully_enumerated=false`.

## Temporal experiment

The existing OOF predictions provide three test seasons:

1. 2021-22: development fit
2. 2022-23: feature-group and regularization selection
3. 2023-24: untouched holdout

Probability correction candidates:

- baseline-logit recalibration only
- schedule context
- travel context
- schedule plus travel

Margin correction candidates use the same feature groups around the baseline predicted margin.

Promotion requires:

- a context group, not recalibration alone
- better holdout Log Loss and Brier Score for probability, or better MAE and RMSE for margin
- paired-bootstrap 95% interval supporting the improvement

## Outputs

The Artifact contains only aggregate research files:

- `feature-expansion-v3-run-status.json`
- `feature-expansion-v3-report.json`
- `feature-expansion-v3-candidate-summary.csv`
- `feature-expansion-v3-coefficients.csv`

No game-level prediction or context rows are uploaded.

## Non-goals

This pilot cannot establish betting profitability. It does not use entry-price odds, CLV, or precise injury/lineup snapshots.

The next phase is a point-in-time injury and lineup snapshot schema. That phase should begin only after reviewing this context holdout result.
