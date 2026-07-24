# Next Design — Prior-only Player Rotation State Feature Layer v1

Status: **Predeclaration target only / Not implemented**  
Formal Stake: **0**

The next model candidate must add genuinely new pre-game information. It must not reweight the rejected two-feature injury candidate, use market prices as model features, or tune against the private market comparison.

Proposed prior-only feature families:

```text
prior 5 / 10 game player minutes concentration
rotation continuity
starter continuity inferred from prior games only
projected available top-8 minutes before tipoff
return-from-absence state using prior participation only
roster-change / trade integration state
role volatility and missingness flags
```

Required source-time rule:

```text
source_game_time < target_game_analysis_cutoff < target_game_tipoff
```

Target-game boxscore, minutes, participation and outcome remain evaluation-only.

Before implementation, the next PR must freeze:

- exact source Artifacts and licenses;
- player identity and roster rules;
- feature formulas;
- missingness treatment;
- chronological train/test folds;
- baseline and candidate model form;
- promotion and negative-result gates;
- privacy-safe Artifact outputs.

This document does not authorize training, execution, market backtesting, or betting claims.
