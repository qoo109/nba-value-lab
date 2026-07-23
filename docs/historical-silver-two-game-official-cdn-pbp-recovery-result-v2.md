# Historical Silver two-game official CDN PBP recovery — Result v2

## Outcome

```text
formal state:
HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS

target games: 2
recovered games: 2
remaining games without team features: 0
documented exceptions remaining: 0
formal Stake: 0
```

The two `2023-24` games previously classified as `SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT` were located in the alternate official CDN play-by-play archive, reconstructed, validated, and included in newly rebuilt five-season Silver and Gold artifacts.

## Source

```text
source key: cdnnba_2023
provider: shufinskiy/nba_data archive of official cdn.nba.com play-by-play
archive bytes: 18,598,380
archive SHA-256:
33d49fefc809f73d5d6cbad6d1d6690e0df6c89fe2b5a4d814ecc9ea4df6101b
CSV rows scanned: 674,937
target event rows found: 1,108
```

The raw archive was used only in temporary GitHub Actions storage and was not committed.

## Recovery QA

```text
team feature rows before: 2,456
team feature rows after: 2,460
team feature rows added: 4
possession rows before: 242,365
possession rows after: 242,777
possession rows added: 412
recovered game dates: 2
remaining zero-feature games: 0
remaining recovered games without dates: 0
duplicate team-game feature rows: 0
```

Aggregate per-game diagnostics:

```text
Game A: 563 event rows / 561 possession-tagged rows / 206 possession segments
        home possessions 103 / away possessions 103 / terminal score matched

Game B: 545 event rows / 543 possession-tagged rows / 206 possession segments
        home possessions 104 / away possessions 102 / terminal score matched
```

The public record does not expose the two game IDs, dates, or team codes.

## Rebuilt five-season output

```text
seasons:
2019-20, 2020-21, 2021-22, 2022-23, 2023-24

Historical Silver games: 5,826
Historical Silver team-game features: 11,652
Historical Gold matchup features: 5,826
Historical Gold team-game features: 11,652
Gold point-in-time violations: 0
Gold point-in-time validation: PASS
```

The previous `5,824 Gold + 2 documented exceptions` coverage reference is superseded by the recovered `5,826 Gold` reference for this governed five-season scope.

## GitHub Actions evidence

```text
workflow: Recover Historical Silver two-game official CDN PBP v2
run ID: 29976204693
job ID: 89108363564
job: recover-and-rebuild / success
head SHA: ad12518a55e6077295c4df1a099977a6e5cd024b

Artifact ID: 8551587005
Artifact name: historical-silver-gold-two-game-official-cdn-recovery-v2
Artifact bytes: 374,591,375
Artifact digest:
sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
Artifact expiry: 2026-08-06T03:14:00Z
```

Artifact file bindings:

```text
historical-silver-multiseason-recovered-v1.sqlite.gz
bytes: 369,318,173
sha256: 48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8

historical-gold-multiseason-recovered-v1.sqlite.gz
bytes: 5,268,851
sha256: a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085

two-game-official-cdn-pbp-recovery-result-v2.json
bytes: 3,751
sha256: 97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30
```

The binary Artifact is temporary, but the committed recovery runner, immutable source binding, result record and hashes make the databases deterministically rebuildable.

## Scientific interpretation

This is not a manual patch. The recovery used alternate official-source play-by-play events and required:

- existing NBA Stats identity agreement;
- recovery of both game dates;
- exact terminal-score agreement;
- exact event-score reconstruction agreement;
- two team-feature rows per game;
- plausible possession and shooting ranges;
- no duplicate team-game rows;
- a complete multi-season Gold rebuild with zero point-in-time violations.

## Remaining boundaries

The successful data repair does not authorize:

- market backtesting;
- Opening／Closing or other point-in-time odds semantics;
- CLV／EV／ROI／Drawdown calculations;
- model retraining;
- betting-edge claims;
- Stake above `0`.

## Next controlled lane

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN
```
