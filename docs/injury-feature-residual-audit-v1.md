# Injury Feature Residual Audit v1

## Purpose

Test whether point-in-time team injury burden moves in the expected direction relative to existing out-of-fold Walk-forward v2 prediction errors.

This audit is diagnostic only. It does not fit a new model, alter probabilities, or establish betting value.

## Join

The audit joins:

- `walk-forward-predictions.csv` from Model Walk-forward v2;
- `matchup-injury-burden.csv` from Team Injury Burden v1.

The join key is historical game ID. Game date and home/away team abbreviations must also match exactly.

## Residual definitions

```text
home win probability residual
= actual home win − predicted home win probability

home margin residual
= actual home margin − predicted home margin
```

A positive injury-burden difference means the home team has more unavailable value than the away team. The expected correlation with both residuals is therefore negative.

## Features audited

- weighted unavailable minutes, home minus away;
- signed weighted absence impact, home minus away;
- positive-only weighted absence impact, home minus away;
- absolute weighted absence impact, home minus away.

Spearman rank correlation is reported because the pilot is tiny and no linear relationship is assumed.

## Activation block

The first fixture contains:

- 11 joined games;
- 9 complete injury snapshots;
- 7 feature-ready games.

This is enough for a directional diagnostic, not enough for training or probability adjustment. The activation threshold is fixed at 100 independent point-in-time games.

```text
ready_for_injury_feature_model_training: false
ready_for_probability_adjustment: false
ready_for_betting_edge_claim: false
```

P-values are included for transparency but are not treated as evidence in this seven-game pilot.

## Promotion requirements

1. at least 100 independent games with both teams covered;
2. multiple report dates and publication times;
3. no overlapping target-game information;
4. season-based holdout testing;
5. incremental Log Loss and Brier improvement over Logistic+Elo;
6. calibration stability;
7. market residual evaluation after odds data is joined.
