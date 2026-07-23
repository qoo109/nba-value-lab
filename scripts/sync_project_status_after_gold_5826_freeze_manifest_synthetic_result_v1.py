#!/usr/bin/env python3
"""Synchronize PROJECT_STATUS after Gold 5,826 freeze-manifest synthetic validation."""
from pathlib import Path

STATUS = Path("PROJECT_STATUS.md")
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DESIGN"


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
        """freeze manifest implementation module created: false
freeze manifest synthetic validation executed: false
real Artifact freeze workflow created: false
real Artifact execution approved: false
semantic freeze manifest created: false
corpus freeze executed: false
""",
        """freeze manifest implementation module created: true
freeze manifest synthetic validation: PASS / 20 OF 20
freeze manifest synthetic implementation recording PR: 139
freeze manifest synthetic implementation recording merge: b561c941b5fc27a0bda3fa790244ff92c35b5c0b
freeze manifest synthetic validation run: 29984329419
freeze manifest synthetic validation job: 89132779309
freeze manifest synthetic validation artifact: 8554394051
freeze manifest synthetic validation digest: sha256:1ecf4862ff87c3eb23ccb8d6b1c9860a229b54b8c76c469930dd2723da213f6f
real Artifact execution request design created: false
real Artifact execution request created: false
real Artifact freeze workflow created: false
real Artifact execution approved: false
real Artifact execution count: 0
semantic freeze manifest created: false
corpus freeze executed: false
""",
        "freeze manifest implementation state",
    )

    text = replace_once(
        text,
        """## Next Unique Mainline

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_SYNTHETIC_VALIDATION
```

The read-only semantic freeze-manifest implementation design is validated. The next controlled lane may create the builder module and test it only against miniature synthetic SQLite databases. Artifact `8551587005` must not be downloaded or read, and no canonical manifest or corpus freeze may occur without a later separate explicit approval. Market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        f"""## Next Unique Mainline

```text
{NEXT}
```

The offline read-only semantic freeze-manifest builder passed all `20 / 20` synthetic SQLite tests. The next controlled lane may design a one-time real Artifact execution request, but it may not create the request, approval, execution workflow, download Artifact `8551587005`, read the real Gold database, create the canonical manifest, or freeze the corpus. Market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        "next unique mainline",
    )

    evidence = """
### Historical Gold 5,826 freeze-manifest synthetic implementation validation

```text
formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALID
implementation module created: true
synthetic SQLite tests: 20 / 20 PASS
Gold matchups / team rows: 5,826 / 11,652
remaining source exceptions: 0
point-in-time violations: 0
real Artifact downloaded: false
real Artifact read: false
real execution workflow created: false
real execution approved: false
real execution count: 0
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

Validation evidence:

```text
recording PR: 139
recording merge: b561c941b5fc27a0bda3fa790244ff92c35b5c0b
validated head: 04fdbe44f642af85bc287a02a2f978f12bf62cb0
workflow run: 29984329419
job: 89132779309 / validate-synthetic-implementation / success
Artifact: 8554394051
Artifact digest: sha256:1ecf4862ff87c3eb23ccb8d6b1c9860a229b54b8c76c469930dd2723da213f6f
Artifact expiry: 2026-08-06T06:12:27Z
```

The builder uses SQLite `mode=ro&immutable=1`, `query_only=ON`, integrity checking, exact schema and relationship gates, policy-only volatile exclusions, type-tagged canonical JSON Lines, incremental SHA-256, pre/post database hash equality and aggregate-only output under 1 MiB. The validation Artifact contains one aggregate report and no real Gold rows or identifiers.

Formal records:

- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-synthetic-implementation-result-v1.json`
- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-implementation-current-status-v1.json`
- `docs/historical-gold-5826-freeze-manifest-synthetic-validation-result-v1.md`
- `scripts/build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py`
- `scripts/test_build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py`

"""
    anchor = "## Completed Evidence\n"
    if text.count(anchor) != 1:
        raise RuntimeError("Completed Evidence anchor must exist exactly once")
    if "### Historical Gold 5,826 freeze-manifest synthetic implementation validation" in text:
        raise RuntimeError("synthetic validation evidence already exists")
    text = text.replace(anchor, anchor + "\n" + evidence, 1)

    required = (
        "freeze manifest synthetic validation: PASS / 20 OF 20",
        "freeze manifest synthetic implementation recording PR: 139",
        "freeze manifest synthetic validation run: 29984329419",
        "real Artifact execution request design created: false",
        "real Artifact execution approved: false",
        "real Artifact execution count: 0",
        NEXT,
        "real Artifact read: false",
        "formal Stake: 0",
    )
    for fragment in required:
        if fragment not in text:
            raise RuntimeError(f"required fragment missing: {fragment}")

    current = text.split("## Completed Evidence", 1)[0]
    stale = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_SYNTHETIC_VALIDATION"
    if stale in current:
        raise RuntimeError("stale synthetic implementation mainline remains in current state")
    if len(text.splitlines()) <= len(before.splitlines()):
        raise RuntimeError("status history must be preserved and extended")

    STATUS.write_text(text, encoding="utf-8")
    print({
        "formal_state": "PROJECT_STATUS_GOLD_5826_FREEZE_MANIFEST_SYNTHETIC_RESULT_SYNCHRONIZED",
        "before_lines": len(before.splitlines()),
        "after_lines": len(text.splitlines()),
        "next_research_step": NEXT,
        "formal_stake": 0,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
