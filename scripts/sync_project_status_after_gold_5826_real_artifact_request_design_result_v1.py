#!/usr/bin/env python3
"""Synchronize PROJECT_STATUS after Gold 5,826 real-Artifact request-design validation."""
from pathlib import Path

STATUS = Path("PROJECT_STATUS.md")
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DRAFT"


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
        """real Artifact execution request design created: false
real Artifact execution request created: false
real Artifact freeze workflow created: false
real Artifact execution approved: false
real Artifact execution count: 0
semantic freeze manifest created: false
corpus freeze executed: false
""",
        """real Artifact execution request design: VALIDATED / DESIGN ONLY
real Artifact execution request design recording PR: 141
real Artifact execution request design recording merge: 5c6431110b7085dec1663cf6303df5393fd4dd97
real Artifact execution request design validation run: 29986783982
real Artifact execution request design validation job: 89140319716
real Artifact execution request design validation artifact: 8555320565
real Artifact execution request design validation digest: sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9
real Artifact execution request design validated: true
real Artifact execution request created: false
real Artifact freeze workflow created: false
real Artifact execution approved: false
real Artifact execution count: 0
semantic freeze manifest created: false
corpus freeze executed: false
""",
        "request-design state",
    )

    text = replace_once(
        text,
        """## Next Unique Mainline

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DESIGN
```

The offline read-only semantic freeze-manifest builder passed all `20 / 20` synthetic SQLite tests. The next controlled lane may design a one-time real Artifact execution request, but it may not create the request, approval, execution workflow, download Artifact `8551587005`, read the real Gold database, create the canonical manifest, or freeze the corpus. Market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        f"""## Next Unique Mainline

```text
{NEXT}
```

The one-time exact GitHub Artifact request design is validated. The next controlled lane may create the governed request draft, but it may not grant approval, create or dispatch the execution workflow, download Artifact `8551587005`, read the real Gold database, create the canonical manifest, or freeze the corpus. Market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
""",
        "next unique mainline",
    )

    evidence = """
### Historical Gold 5,826 real Artifact execution request design

```text
formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED
exact Artifact ID: 8551587005
exact Artifact expiry: 2026-08-06T03:14:00Z
maximum execution attempts: 1
manual workflow_dispatch on main only: true
separate explicit user approval required: true
request consumed after any execution attempt: true
rerun allowed: false
automatic dispatch allowed: false
GitHub Artifact transport only: true
Silver database read allowed: false
request draft created: false
approval created: false
execution workflow created: false
real Artifact downloaded: false
real Artifact read: false
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

Validation evidence:

```text
design PR: 141
design merge: 5c6431110b7085dec1663cf6303df5393fd4dd97
validated head: f84a217b0f4b2d144c58032f5edc793a2b92553b
workflow run: 29986783982
job: 89140319716 / validate-request-design / success
Artifact: 8555320565
Artifact digest: sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9
Artifact expiry: 2026-08-06T06:59:00Z
```

The validated contract binds the exact adopted Artifact, exact three-file set and hashes, builder Git blob, separate approval evidence, one-time consumption, expiry fail-closed behavior, GitHub-Artifact-only transport, Silver no-read, Gold read-only execution and two-file aggregate output under 1 MiB. No request, approval or execution workflow was created.

Formal records:

- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-result-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-current-status-v1.json`
- `docs/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-result-v1.md`

"""
    anchor = "## Completed Evidence\n"
    if text.count(anchor) != 1:
        raise RuntimeError("Completed Evidence anchor must exist exactly once")
    if "### Historical Gold 5,826 real Artifact execution request design" in text:
        raise RuntimeError("request-design evidence already exists")
    text = text.replace(anchor, anchor + "\n" + evidence, 1)

    required = (
        "real Artifact execution request design: VALIDATED / DESIGN ONLY",
        "real Artifact execution request design recording PR: 141",
        "real Artifact execution request design validation run: 29986783982",
        "real Artifact execution request created: false",
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
    stale = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DESIGN"
    if stale in current:
        raise RuntimeError("stale request-design mainline remains")
    if len(text.splitlines()) <= len(before.splitlines()):
        raise RuntimeError("status history must be preserved and extended")

    STATUS.write_text(text, encoding="utf-8")
    print({
        "formal_state": "PROJECT_STATUS_GOLD_5826_REAL_ARTIFACT_REQUEST_DESIGN_RESULT_SYNCHRONIZED",
        "before_lines": len(before.splitlines()),
        "after_lines": len(text.splitlines()),
        "next_research_step": NEXT,
        "formal_stake": 0,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
