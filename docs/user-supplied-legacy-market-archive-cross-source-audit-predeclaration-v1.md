# User-supplied Legacy Market Archive Cross-source Audit Predeclaration v1

## Purpose

This policy freezes the next research step for the owner-confirmed
`nba_2008-2026.csv` file before any real-file cross-source audit is implemented.

It compares the legacy archive with the verified five-season Historical
Silver/Gold reference only through deterministic game identity and final-score
validation. This PR does not run the real audit, read either real database, or
change the source role.

## Repository state checked first

Before this predeclaration was created, the following current sources of truth
were reviewed:

- `PROJECT_STATUS.md`;
- `README.md`;
- `docs/source-intake-sop-v1.md`;
- `docs/historical-gold-layer.md`;
- `docs/historical-expansion-walk-forward-v2.md`;
- `data/research/user-supplied-nba-betting-csv-audit-v1.json`;
- `data/research/user-supplied-nba-betting-csv-provenance-confirmation-v1.json`;
- `data/research/user-supplied-nba-betting-csv-provenance-current-status-v1.json`;
- `data/historical-odds-source-registry.json`.

The Eoin, Wyatt, Closing benchmark, Historical Gold, model and UI work already
completed in the repository is not repeated.

## Candidate source identity

```text
source id: kaggle_cviaxmiwnptr_nba_betting_data_user_supplied
dataset: cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024
file: nba_2008-2026.csv
bytes: 2,493,308
sha256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
rows: 24,440
columns: 27
provenance: user_confirmed
current role: ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
```

The source remains a legacy market archive. It does not contain bookmaker
identity or an exact observation timestamp.

## Reference scope

The verified reference covers the five regular seasons already used by the
Historical Gold and walk-forward pipeline:

```text
2019-20
2020-21
2021-22
2022-23
2023-24
```

Candidate season labels map as follows:

```text
2020 -> 2019-20
2021 -> 2020-21
2022 -> 2021-22
2023 -> 2022-23
2024 -> 2023-24
```

Only rows with `regular = true` and `playoffs = false` enter the audit.
Playoffs, play-in/other rows and all non-overlap seasons are excluded before
matching.

Moneyline, spread and total availability are not identity requirements. The
2023-24 candidate season may therefore participate even though its moneyline
fields are missing.

## Deterministic join contract

The only allowed join key is:

```text
game_date + home_team_abbr + away_team_abbr
```

Candidate columns:

```text
date + normalized home + normalized away
```

Reference identity columns:

```text
gold_matchup_features.game_date
gold_matchup_features.home_team_abbr
gold_matchup_features.away_team_abbr
```

Final scores are validation fields only:

```text
candidate score_home / score_away
reference games.home_score / games.away_score
```

Scores must never repair a failed identity join. Fuzzy matching, manual key
overrides and many-to-many joins are prohibited.

The exact 30-code candidate-to-reference team mapping is frozen in the policy
JSON. Unknown codes are a blocking error.

## Frozen scientific gates

A later real-file implementation must pass all of the following:

```text
reference games >= 5,700
eligible candidate games >= 5,700
reference match rate >= 98.5%
candidate match rate >= 98.5%
matched score-pair rate >= 99.0%
each-season reference match rate >= 97.0%
candidate duplicate key groups = 0
reference duplicate key groups = 0
ambiguous join keys = 0
unresolved team codes = 0
invalid dates = 0
missing in-scope scores = 0
raw rows emitted = 0
raw files emitted = false
```

The thresholds are predeclared before the real comparison is run. They must not
be reduced after observing the result without a new versioned policy and a new
review.

## Allowed aggregate outputs

A later audit may publish only compact aggregate evidence:

- file identity and hash confirmation;
- eligible game counts by season;
- matched and unmatched counts in both directions;
- match rates and score-pair agreement;
- duplicate, ambiguous-key, team-code and date-error counts;
- aggregate unmatched reason counts;
- formal outcome and guardrail status.

No raw candidate rows, raw reference rows, full databases or row-level unmatched
exports may be committed or uploaded as public artifacts.

## Candidate later outcomes

```text
ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_VALIDATED
RETAIN_ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED
```

The maximum possible role is still a role-limited legacy archive suitable for
cross-source QA and a separately reviewed forecast benchmark. It is not a
point-in-time odds source.

## Permanently blocked by this policy

This predeclaration does not authorize:

- calling any line Opening or Closing;
- bookmaker or `observed_at` inference;
- point-in-time joins or T-60/T-5 entry backtests;
- CLV, entry-price ROI, Drawdown or betting-edge claims;
- Historical Silver or Gold replacement;
- model retraining;
- raw CSV/database publication;
- fuzzy matching;
- non-zero Stake.

## Validation boundary

The policy validator reads only the committed predeclaration JSON. It makes no
network calls, does not read the real candidate CSV or reference databases, and
emits one small aggregate report.

Expected validation state:

```text
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_PREDECLARATION_READY
```

A passing state authorizes design of a separate audit implementation only. It
does not mean that the cross-source audit has passed and does not change the
current source role.
