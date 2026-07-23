#!/usr/bin/env python3
"""Synchronize PROJECT_STATUS after the validated Gold 5,826 freeze-manifest design."""
from pathlib import Path

STATUS = Path("PROJECT_STATUS.md")
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_SYNTHETIC_VALIDATION"


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
        """freeze manifest implementation created: false
semantic freeze manifest created: false
corpus freeze executed: false
""",
        """freeze manifest implementation design: VALIDATED / DESIGN ONLY
freeze manifest implementation design id: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-IMPLEMENTATION-DESIGN-2026-07-23-001
freeze manifest implementation design recording PR: 137
freeze manifest implementation design recording merge: 1730859888bd21cf7727ef6c5cbf348fb7aeddeb
freeze manifest implementation design validation run: 29982518227
freeze manifest implementation design validation artifact: 8553727483
freeze manifest implementation design validation digest: sha256:b752398847700bfc4a09831bbab069451606ecce2615cdcb511b5ddab06d3dc7
freeze manifest implementation module created: false
freeze manifest synthetic validation executed: false
real Artifact freeze workflow created: false
real Artifact execution approved: false
semantic freeze manifest created: false
corpus freeze executed: false
""",
        "freeze manifest implementation state",
    )

    text = replace_once(
        text,
        """## Next Unique Mainline

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_DESIGN
```

The complete `5,826`-matchup Gold corpus freeze policy is validated. The next controlled lane is design of a read-only semantic freeze-manifest implementation that excludes only volatile `feature_generated_at`, produces aggregate table/metadata/corpus SHA-256 digests, and emits no game IDs, dates, team codes, raw rows or row-level hashes. Real Artifact execution remains separately gated; market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        f"""## Next Unique Mainline

```text
{NEXT}
```

The read-only semantic freeze-manifest implementation design is validated. The next controlled lane may create the builder module and test it only against miniature synthetic SQLite databases. Artifact `8551587005` must not be downloaded or read, and no canonical manifest or corpus freeze may occur without a later separate explicit approval. Market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        "next unique mainline",
    )

    evidence = """
### Historical Gold 5,826 freeze-manifest implementation design

```text
formal state: HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_DESIGN_VALIDATED
design ID: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-IMPLEMENTATION-DESIGN-2026-07-23-001
Gold matchups / team rows: 5,826 / 11,652
remaining source exceptions: 0
point-in-time violations: 0
read-only SQLite required: true
policy-driven stable columns required: true
canonical type-tagged JSON Lines: true
incremental SHA-256: true
aggregate output maximum: 1 MiB
real Artifact read: false
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

Validation evidence:

```text
recording PR: 137
recording merge: 1730859888bd21cf7727ef6c5cbf348fb7aeddeb
workflow run: 29982518227
job: 89127261444 / validate-implementation-design / success
Artifact: 8553727483
Artifact digest: sha256:b752398847700bfc4a09831bbab069451606ecce2615cdcb511b5ddab06d3dc7
```

The design requires SQLite URI read-only mode with `immutable=1`, `query_only=ON`, pre/post database hash equality, policy-derived stable columns, type-tagged canonical encoding, table/schema/metadata/corpus digests, and an aggregate-only privacy boundary. The real Gold Artifact was not downloaded or read.

Formal records:

- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-implementation-design-v1.json`
- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-implementation-current-status-v1.json`
- `docs/historical-gold-5826-complete-corpus-freeze-manifest-implementation-design-v1.md`
- `scripts/validate_historical_gold_5826_freeze_manifest_implementation_design_v1.py`
- `.github/workflows/validate-historical-gold-5826-freeze-manifest-implementation-design-v1.yml`

"""
    anchor = "## Completed Evidence\n"
    if text.count(anchor) != 1:
        raise RuntimeError("Completed Evidence anchor must exist exactly once")
    if "### Historical Gold 5,826 freeze-manifest implementation design" in text:
        raise RuntimeError("freeze-manifest implementation design evidence already exists")
    text = text.replace(anchor, anchor + "\n" + evidence, 1)

    required = (
        "freeze manifest implementation design: VALIDATED / DESIGN ONLY",
        "freeze manifest implementation design recording PR: 137",
        "freeze manifest implementation design validation run: 29982518227",
        "real Artifact execution approved: false",
        NEXT,
        "real Artifact read: false",
        "formal Stake: 0",
    )
    for fragment in required:
        if fragment not in text:
            raise RuntimeError(f"required fragment missing: {fragment}")

    stale_current = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_DESIGN"
    current = text.split("## Completed Evidence", 1)[0]
    if stale_current in current:
        raise RuntimeError("stale next mainline remains in current state")

    if len(text.splitlines()) <= len(before.splitlines()):
        raise RuntimeError("status history must be preserved and extended")

    STATUS.write_text(text, encoding="utf-8")
    print({
        "formal_state": "PROJECT_STATUS_GOLD_5826_FREEZE_MANIFEST_DESIGN_SYNCHRONIZED",
        "before_lines": len(before.splitlines()),
        "after_lines": len(text.splitlines()),
        "next_research_step": NEXT,
        "formal_stake": 0,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
