#!/usr/bin/env python3
"""Synchronize PROJECT_STATUS after the successful official-CDN two-game recovery.

The synchronizer is deterministic and fail-closed. It replaces only exact current-state
blocks, appends the completed recovery evidence, and preserves all earlier audit history.
"""
from __future__ import annotations

from pathlib import Path

STATUS = Path("PROJECT_STATUS.md")
NEXT_STEP = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN"
RECOVERY_STATE = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    before = STATUS.read_text(encoding="utf-8")
    text = before

    text = replace_once(
        text,
        """candidate formal result: CROSS-SOURCE GATES PASS / MARKET EVALUATION NOT AUTHORIZED
Gold/Silver reconciliation result: SOURCE_DATA_GAP_CONFIRMED / DOCUMENTED EXCEPTIONS RECOGNIZED
""",
        """candidate formal result: REFERENCE COVERAGE COMPLETE / MARKET EVALUATION NOT AUTHORIZED
Gold/Silver reconciliation result: SOURCE GAP RESOLVED VIA OFFICIAL CDN PBP RECOVERY
reference coverage: 5,826 / 5,826
""",
        "current reference state",
    )

    text = replace_once(
        text,
        """source gap exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
source gap exception count: 2
source gap exception patch allowed: false
""",
        """source gap exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
source gap exception historical count: 2
source gap exception remaining count: 0
source gap exception recovery: PASS / OFFICIAL CDN PBP
source gap exception patch allowed: false
""",
        "exception recovery state",
    )

    text = replace_once(
        text,
        """eligible Historical Gold corpus for future policy design: 5,824
documented exceptions excluded from Gold eligibility: 2
raw Historical Silver games: 5,826
raw Historical Gold matchups: 5,824
raw missing Gold for Silver: 2
documented source gap exceptions: 2
unexplained missing after documentation: 0
Gold dataset complete: false
silver builder repair required: false
""",
        """official CDN recovery run: 29976204693
official CDN recovery Artifact: 8551587005
official CDN recovery Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
official CDN recovery recording PR: 133
official CDN recovery recording merge: 98bcb2538070eb57bba2ce79920262262c0924ef
eligible Historical Gold corpus for future policy design: 5,826
documented exceptions excluded from Gold eligibility: 0
raw Historical Silver games: 5,826
raw Historical Gold matchups: 5,826
raw missing Gold for Silver: 0
documented source gap exceptions remaining: 0
unexplained missing after recovery: 0
Gold dataset complete for governed five-season scope: true
silver builder repair required: false
""",
        "coverage control counts",
    )

    text = replace_once(
        text,
        """## Next Unique Mainline

```text
HISTORICAL_GOLD_5824_ELIGIBLE_CORPUS_FREEZE_AND_EXCEPTION_EXCLUSION_POLICY_READY_FOR_DESIGN
```

The aggregate-only real-reference validation passed and Request `001` is permanently consumed. The validated research interpretation is `5,824` Gold-eligible matchups plus `2` documented upstream source exceptions excluded from Gold eligibility. Gold remains formally incomplete. The next controlled lane is policy design only; it does not freeze data, rebuild Gold, rerun the cross-source audit, authorize market backtesting, or change Stake from `0`.
""",
        """## Next Unique Mainline

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN
```

The two documented `2023-24` source exceptions were recovered from archived official `cdn.nba.com` play-by-play, their missing dates and possession-derived team features were restored, and the five-season Silver and strict point-in-time Gold references were rebuilt to `5,826 / 5,826` with zero point-in-time violations. The next controlled lane is complete-corpus freeze policy design only; market backtesting, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        "next unique mainline",
    )

    anchor = "\n## Consumed One-time Scopes\n"
    evidence = """
### Two-game official CDN PBP recovery

```text
formal state: HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS
source: cdnnba_2023 / archived official cdn.nba.com play-by-play
source archive SHA-256: 33d49fefc809f73d5d6cbad6d1d6690e0df6c89fe2b5a4d814ecc9ea4df6101b
source archive rows scanned: 674,937
target games found: 2 / 2
target event rows found: 1,108
recovered game dates: 2
possession rows added: 412
team feature rows added: 4
remaining games without team features: 0
remaining documented exceptions: 0
Silver games / team rows: 5,826 / 11,652
Gold matchups / team rows: 5,826 / 11,652
Gold point-in-time violations: 0
formal Stake: 0
```

Adopted execution evidence:

```text
workflow run: 29976204693
job: 89108363564 / recover-and-rebuild / success
Artifact: 8551587005
Artifact bytes: 374,591,375
Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
Artifact expiry: 2026-08-06T03:14:00Z
Silver SHA-256: 48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8
Gold SHA-256: a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085
result SHA-256: 97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30
recording PR: 133
recording merge: 98bcb2538070eb57bba2ce79920262262c0924ef
```

Final PR-head reproducibility and committed-record validation:

```text
reproducibility run: 29976847034 / success
reproducibility Artifact: 8551840465
reproducibility digest: sha256:28827c57e4a96402db3ee6c873c1a423680ab2f604a6fe9dd426feec917e9469
result validation run: 29976847035 / success
result validation Artifact: 8551731929
result validation digest: sha256:94ee584488e7121331fbfb128fcb1d157ee4af6d69b1b8ec3f87177b3a473d72
```

This recovery used alternate official-source event rows rather than manual, synthetic, copied or zero-imputed values. The public aggregate record does not expose the two game IDs, dates or team codes. The earlier `5,824 Gold + 2 documented exceptions` state remains historical evidence but is superseded for current five-season coverage counts.

Formal records:

- `data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2.json`
- `data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-current-status-v1.json`
- `docs/historical-silver-two-game-official-cdn-pbp-recovery-v1.md`
- `docs/historical-silver-two-game-official-cdn-pbp-recovery-result-v2.md`

"""
    if text.count(anchor) != 1:
        raise RuntimeError("Consumed One-time Scopes anchor must exist exactly once")
    if "### Two-game official CDN PBP recovery" in text:
        raise RuntimeError("recovery evidence section already exists")
    text = text.replace(anchor, "\n" + evidence + "## Consumed One-time Scopes\n", 1)

    text = replace_once(
        text,
        """- treating the two documented exceptions as Gold-eligible rows without genuinely new governed source evidence;
- eligible-corpus freeze before a separately validated policy design and implementation;
- Silver builder changes or manual row insertion;
- source-gap exception row patch;
- Gold rebuild;
""",
        """- complete `5,826`-matchup corpus freeze before a separately validated freeze policy and implementation;
- Silver builder changes or manual row insertion outside the adopted official-CDN recovery recipe;
- synthetic, copied, zero-imputed or manually entered source-gap rows;
- further Silver／Gold rebuild or canonical replacement outside the adopted recovery recipe;
""",
        "still-blocked recovery items",
    )

    important_anchor = """- `.github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-result-v1.yml`
"""
    important_addition = important_anchor + """- `data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2.json`
- `data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-current-status-v1.json`
- `docs/historical-silver-two-game-official-cdn-pbp-recovery-v1.md`
- `docs/historical-silver-two-game-official-cdn-pbp-recovery-result-v2.md`
- `scripts/recover_historical_silver_two_game_official_cdn_pbp_v1.py`
- `scripts/recover_historical_silver_two_game_official_cdn_pbp_v2.py`
- `scripts/validate_historical_silver_two_game_official_cdn_pbp_recovery_result_v2.py`
- `.github/workflows/recover-historical-silver-two-game-official-cdn-pbp-v1.yml`
- `.github/workflows/validate-historical-silver-two-game-official-cdn-pbp-recovery-result-v2.yml`
"""
    text = replace_once(text, important_anchor, important_addition, "important recovery files")

    required = (
        RECOVERY_STATE,
        NEXT_STEP,
        "reference coverage: 5,826 / 5,826",
        "source gap exception remaining count: 0",
        "raw Historical Gold matchups: 5,826",
        "raw missing Gold for Silver: 0",
        "Gold dataset complete for governed five-season scope: true",
        "workflow run: 29976204693",
        "Artifact: 8551587005",
        "Gold point-in-time violations: 0",
        "formal Stake: 0",
        "market backtesting",
        "model retraining",
    )
    for fragment in required:
        if fragment not in text:
            raise RuntimeError(f"required synchronized fragment missing: {fragment}")

    stale_current = (
        "eligible Historical Gold corpus for future policy design: 5,824",
        "documented exceptions excluded from Gold eligibility: 2",
        "raw Historical Gold matchups: 5,824",
        "raw missing Gold for Silver: 2",
        "HISTORICAL_GOLD_5824_ELIGIBLE_CORPUS_FREEZE_AND_EXCEPTION_EXCLUSION_POLICY_READY_FOR_DESIGN",
    )
    for fragment in stale_current:
        if fragment in text[: text.index("## Completed Evidence")]:
            raise RuntimeError(f"stale current-state fragment remains: {fragment}")

    if len(text.splitlines()) <= len(before.splitlines()):
        raise RuntimeError("status update must preserve prior history and add recovery evidence")

    STATUS.write_text(text, encoding="utf-8")
    print({
        "formal_state": "PROJECT_STATUS_OFFICIAL_CDN_RECOVERY_SYNCHRONIZED",
        "before_lines": len(before.splitlines()),
        "after_lines": len(text.splitlines()),
        "silver_games": 5826,
        "gold_matchups": 5826,
        "remaining_exceptions": 0,
        "next_research_step": NEXT_STEP,
        "formal_stake": 0,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
