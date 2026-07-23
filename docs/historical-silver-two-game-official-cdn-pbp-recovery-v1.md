# Historical Silver two-game official CDN PBP recovery v1

## Purpose

Resolve the two `2023-24` Historical Silver games currently classified as:

```text
SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
```

The existing NBA Stats event rows and game identities are retained. The recovery uses a genuinely new alternate play-by-play source: Shufinskiy's archived `cdnnba_2023` dataset, whose underlying provider is official `cdn.nba.com` LiveData play-by-play.

## Authorized operation

The repository owner explicitly requested an end-to-end attempt to locate, verify, recover, and rebuild the affected Silver and Gold data.

The workflow performs the complete operation in temporary GitHub Actions storage:

1. rebuilds the five governed Silver seasons (`2019-20` through `2023-24`);
2. identifies the two `2023-24` games with zero `team_game_features` rows;
3. downloads the alternate `cdnnba_2023` archive;
4. requires both target game IDs to exist in that official-source archive;
5. reconstructs possessions and two team feature rows per game;
6. requires terminal scores to match the existing NBA Stats official scores exactly;
7. patches only the temporary `2023-24` Silver database;
8. combines all five Silver seasons;
9. rebuilds the strict point-in-time multi-season Gold database;
10. uploads the repaired Silver, repaired Gold, and an aggregate validation receipt as a GitHub Actions Artifact.

## Fail-closed gates

The recovery stops without adopting any result unless all conditions pass:

```text
target games: exactly 2
alternate-source games found: exactly 2
team feature rows added: exactly 4
remaining zero-feature games: 0
duplicate team-game features: 0
Silver games: 5,826
Silver team-game features: 11,652
Gold matchup features: 5,826
Gold team features: 11,652
Gold point-in-time violations: 0
```

Each target game must also satisfy:

- two-team identity agreement with the existing NBA Stats game record;
- official CDN terminal score equals the NBA Stats final score;
- reconstructed score equals the official final score for both teams;
- valid possession ownership for both teams;
- plausible possession and shooting ranges;
- finite pace, rating and four-factor metrics.

## Metric compatibility

Recovered features use the existing Silver definitions:

```text
pace = 48 * (team possessions + opponent possessions) / (2 * game minutes)
off_rtg = 100 * official points / team possessions
def_rtg = 100 * official opponent points / opponent possessions
efg_pct = (FGM + 0.5 * 3PM) / FGA
tov_pct_estimated = TOV / (FGA + 0.44 * FTA + TOV)
orb_pct_fg_miss_estimate = ORB / missed field goals
free_throw_rate = FTA / FGA
```

Official NBA Stats final scores remain the rating numerator. Event-derived score reconstruction remains a QA requirement.

## Storage and provenance

Raw source archives are temporary and are not committed. The output Artifact contains:

```text
historical-silver-multiseason-recovered-v1.sqlite.gz
historical-gold-multiseason-recovered-v1.sqlite.gz
two-game-official-cdn-pbp-recovery-result-v1.json
```

The aggregate receipt records the source URL, download SHA-256, source size, recovered counts, final database counts and scientific boundaries. It does not expose the two game IDs publicly.

## Boundaries

This recovery does not:

- fabricate, zero-impute, copy, or manually type team features;
- overwrite a database committed to the Repository;
- execute market backtesting;
- calculate CLV, EV, ROI or Drawdown;
- retrain a model;
- make a betting-edge claim;
- raise formal Stake above `0`.

A successful Artifact still requires a separate adoption record before it becomes the canonical project reference.
