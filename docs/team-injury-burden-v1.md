# Team Injury Burden v1

## Purpose

Aggregate point-in-time player availability, expected minutes, and player-impact estimates into team- and matchup-level research features.

The output is designed for a later season holdout experiment. It is not yet part of the production model.

## Inputs

The builder consumes only ID-based outputs from Point-in-time Player Value & Expected Minutes v1:

- player value rows;
- injury snapshot to player-ID mapping;
- injury snapshot to historical game-ID mapping.

It does not consume player names or injury reasons.

## Status-specific features

The following unweighted buckets are retained so that future experiments can change assumptions without re-parsing source reports:

- definite OUT / INACTIVE / SUSPENDED minutes;
- DOUBTFUL minutes;
- QUESTIONABLE minutes;
- PROBABLE minutes;
- status-specific player counts.

## Research status weights

A transparent research index also applies:

```text
AVAILABLE    0.00
PROBABLE     0.10
QUESTIONABLE 0.50
DOUBTFUL     0.75
OUT          1.00
INACTIVE     1.00
SUSPENDED    1.00
```

These are assumptions, not learned probabilities. Status-specific raw buckets remain available and the weights must be re-evaluated in holdout testing.

## Team features

For every expected home and away team, the builder records:

- whether a team snapshot is present;
- whether value coverage is sufficient for research;
- listed injury rows and matched value rows;
- missing identity, expected-minutes, and impact counts;
- expected-minutes and impact coverage;
- status counts;
- definite and probability-weighted unavailable minutes;
- signed, positive-only, and absolute weighted absence impact;
- observation and target dates.

A team with no snapshot rows is represented with `team_snapshot_available=0` and null burden metrics. Missing is never interpreted as zero injuries.

## Matchup features

The matchup output retains home and away values plus home-minus-away differences.

For burden features:

```text
positive home-minus-away = greater injury burden for the home team
```

A positive difference is therefore expected to be a home disadvantage. Incomplete matchups retain missing feature values rather than zero.

## Point-in-time validation

The team builder rechecks that every latest source game is strictly earlier than the target game date.

It inherits the upstream controls that exclude:

- target-game boxscores;
- same-day rows;
- future rows;
- fuzzy player identities;
- unknown values imputed as zero.

## Builder gate and registered pilot gate

The generic builder retains a conservative default requirement of 70% feature-ready matchup coverage.

The registered single-report pilot was defined separately because its pre-registered target was **at least seven feature-ready matchups**. The pilot gate preserves the original builder decision in the QA report, then requires:

- at least eight total matchups;
- at least 80% complete matchup snapshot coverage;
- at least seven feature-ready matchups;
- at least 60% feature-ready matchup coverage;
- no duplicate snapshot, player-value, or game mappings;
- no unknown statuses or numeric errors;
- no strict prior-date violations;
- no zero-filling of missing teams or unknown player values.

Both the absolute and relative requirements must pass. This prevents seven matches from being sufficient in a much larger future batch.

## Verified single-report result

The 2023-12-18 08:30 ET report produced:

- games: 11;
- team rows: 22;
- teams with snapshot rows: 20;
- teams with feature-ready values: 17;
- complete snapshot matchups: 9 / 11, or 81.8182%;
- feature-ready matchups: 7 / 11, or 63.6364%;
- identity snapshot rows: 118;
- player value rows: 117;
- strict prior-date violations: 0;
- unknown statuses: 0;
- numeric errors: 0;
- team snapshot missing rows: 2;
- team feature unavailable rows: 5.

Status counts in retained player-value rows were:

```text
AVAILABLE     6
PROBABLE      5
QUESTIONABLE 24
DOUBTFUL      3
OUT          79
```

The original generic builder gate remained false at 63.6364%. The registered pilot gate passed because the result met the declared minimum of seven ready matchups, 60% ready coverage, and 80% complete snapshot coverage.

## Activation boundary

The resulting decision enables a **team injury feature experiment**, not model training.

```text
ready_for_team_injury_feature_experiment: true
ready_for_model_training: false
ready_for_betting_edge_claim: false
```

The report retains the original builder decision and the separate pilot-gate decision for auditability.

## Next phase

Promotion requires:

1. multiple report dates and intraday publication times;
2. status-change sequencing;
3. cross-season injury coverage;
4. team feature joins to Walk-forward folds;
5. season holdout comparison against Logistic+Elo;
6. calibration and market-residual checks after feature addition.
