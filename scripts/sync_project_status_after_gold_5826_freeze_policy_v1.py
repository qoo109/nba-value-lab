#!/usr/bin/env python3
"""Synchronize PROJECT_STATUS after the validated Gold 5,826 freeze policy."""
from pathlib import Path

STATUS = Path("PROJECT_STATUS.md")
POLICY_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED"
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_DESIGN"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    before = STATUS.read_text(encoding="utf-8")
    text = before

    text = replace_once(
        text,
        """Gold dataset complete for governed five-season scope: true
silver builder repair required: false
""",
        """Gold dataset complete for governed five-season scope: true
complete corpus freeze policy: VALIDATED / DESIGN ONLY
complete corpus freeze policy id: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001
complete corpus freeze policy formal state: HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED
complete corpus freeze policy recording PR: 135
complete corpus freeze policy recording merge: b6edf9b8acaf51b1287d6976c6e42cac056dc726
complete corpus freeze policy validation run: 29978555275
complete corpus freeze policy validation artifact: 8552326235
complete corpus freeze policy validation digest: sha256:96fdcee4b39f6ca03b9597677aa01db2e47b15d6d8f780f2e4525be978dd3722
freeze manifest implementation created: false
semantic freeze manifest created: false
corpus freeze executed: false
adopted Gold Artifact expiry: 2026-08-06T03:14:00Z
timestamped bookmaker odds: POLICY ONLY / REAL OBSERVED_AT DATA NOT ACQUIRED
injury panel activation: 41 independent games / 31 T-60 selected / below 100-game gate
team submission completeness ledger: REQUIRED BEFORE FORMAL INJURY HOLDOUT
silver builder repair required: false
""",
        "freeze policy control block",
    )

    text = replace_once(
        text,
        """## Next Unique Mainline

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN
```

The two documented `2023-24` source exceptions were recovered from archived official `cdn.nba.com` play-by-play, their missing dates and possession-derived team features were restored, and the five-season Silver and strict point-in-time Gold references were rebuilt to `5,826 / 5,826` with zero point-in-time violations. The next controlled lane is complete-corpus freeze policy design only; market backtesting, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        """## Next Unique Mainline

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_DESIGN
```

The complete `5,826`-matchup Gold corpus freeze policy is validated. The next controlled lane is design of a read-only semantic freeze-manifest implementation that excludes only volatile `feature_generated_at`, produces aggregate table/metadata/corpus SHA-256 digests, and emits no game IDs, dates, team codes, raw rows or row-level hashes. Real Artifact execution remains separately gated; market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        "next unique mainline",
    )

    evidence_anchor = "\n## Consumed One-time Scopes\n"
    evidence = """
### Historical Gold 5,826 complete corpus freeze policy

```text
policy id: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001
formal state: HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED
Silver games / team rows: 5,826 / 11,652
Gold matchups / team rows: 5,826 / 11,652
remaining source exceptions: 0
Gold point-in-time violations: 0
policy role: DESIGN ONLY / NO FREEZE EXECUTION
corpus freeze executed: false
formal Stake: 0
```

Evidence and validation:

```text
recording PR: 135
recording merge: b6edf9b8acaf51b1287d6976c6e42cac056dc726
validation run: 29978555275
validation job: 89115413805 / validate-freeze-policy / success
validation Artifact: 8552326235
validation digest: sha256:96fdcee4b39f6ca03b9597677aa01db2e47b15d6d8f780f2e4525be978dd3722
```

Immutable execution-input bindings:

```text
adopted recovery Artifact: 8551587005
adopted Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
Artifact expiry: 2026-08-06T03:14:00Z
Gold binary SHA-256: a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085
Silver binary SHA-256: 48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8
recovery result SHA-256: 97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30
```

Scientific identity design:

```text
binary hash role: execution evidence, not sole permanent semantic identity
required stable tables: gold_team_game_features / gold_matchup_features / gold_metadata
excluded volatile column: feature_generated_at only
required digests: team table / matchup table / metadata / corpus SHA-256
partial freeze: prohibited
row exclusions: prohibited
public row values or identifiers: prohibited
```

Remaining downstream data gaps do not block this freeze policy:

```text
timestamped bookmaker odds: real legal auditable observed_at data still missing
injury panel: 41 independent games / 31 selected T-60 games / below 100-game gate
team submission-completeness ledger: still required before formal injury holdout
```

Formal records:

- `data/research/historical-gold-5826-complete-corpus-freeze-policy-v1.json`
- `data/research/historical-gold-5826-complete-corpus-freeze-policy-current-status-v1.json`
- `docs/historical-gold-5826-complete-corpus-freeze-policy-v1.md`
- `scripts/validate_historical_gold_5826_complete_corpus_freeze_policy_v1.py`
- `.github/workflows/validate-historical-gold-5826-complete-corpus-freeze-policy-v1.yml`

"""
    if text.count(evidence_anchor) != 1:
        raise RuntimeError("Consumed One-time Scopes anchor must exist exactly once")
    if "### Historical Gold 5,826 complete corpus freeze policy" in text:
        raise RuntimeError("freeze policy evidence already exists")
    text = text.replace(evidence_anchor, "\n" + evidence + "## Consumed One-time Scopes\n", 1)

    text = replace_once(
        text,
        """- complete `5,826`-matchup corpus freeze before a separately validated freeze policy and implementation;
""",
        """- freeze-manifest implementation before a separately validated implementation design;
- real Artifact freeze execution before a separately approved one-time workflow;
- any unbound rebuild after Artifact `8551587005` expires;
""",
        "still blocked freeze line",
    )

    important_anchor = """- `.github/workflows/validate-historical-silver-two-game-official-cdn-pbp-recovery-result-v2.yml`
"""
    important_addition = important_anchor + """- `data/research/historical-gold-5826-complete-corpus-freeze-policy-v1.json`
- `data/research/historical-gold-5826-complete-corpus-freeze-policy-current-status-v1.json`
- `docs/historical-gold-5826-complete-corpus-freeze-policy-v1.md`
- `scripts/validate_historical_gold_5826_complete_corpus_freeze_policy_v1.py`
- `.github/workflows/validate-historical-gold-5826-complete-corpus-freeze-policy-v1.yml`
"""
    text = replace_once(text, important_anchor, important_addition, "important freeze policy files")

    required = (
        POLICY_STATE,
        NEXT,
        "complete corpus freeze policy recording PR: 135",
        "complete corpus freeze policy validation run: 29978555275",
        "semantic freeze manifest created: false",
        "corpus freeze executed: false",
        "timestamped bookmaker odds: POLICY ONLY / REAL OBSERVED_AT DATA NOT ACQUIRED",
        "injury panel activation: 41 independent games / 31 T-60 selected / below 100-game gate",
        "formal stake: 0",
    )
    for fragment in required:
        if fragment not in text:
            raise RuntimeError(f"required synchronized fragment missing: {fragment}")

    current = text.split("## Completed Evidence", 1)[0]
    stale = (
        "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN",
        "complete `5,826`-matchup corpus freeze before a separately validated freeze policy and implementation",
    )
    for fragment in stale:
        if fragment in current:
            raise RuntimeError(f"stale current-state fragment remains: {fragment}")

    if len(text.splitlines()) <= len(before.splitlines()):
        raise RuntimeError("status update must preserve history and add policy evidence")

    STATUS.write_text(text, encoding="utf-8")
    print({
        "formal_state": "PROJECT_STATUS_GOLD_5826_FREEZE_POLICY_SYNCHRONIZED",
        "before_lines": len(before.splitlines()),
        "after_lines": len(text.splitlines()),
        "policy_validated": True,
        "corpus_freeze_executed": False,
        "next_research_step": NEXT,
        "formal_stake": 0,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
