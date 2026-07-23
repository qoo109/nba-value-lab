#!/usr/bin/env python3
"""Synchronize PROJECT_STATUS.md after the consumed real-reference validation result.

This script performs guarded, deterministic text replacements only. It preserves all
previous evidence sections and fails closed when the expected pre-sync text is absent
or duplicated.
"""
from __future__ import annotations

from pathlib import Path

STATUS_PATH = Path("PROJECT_STATUS.md")
REQUEST_ID = (
    "HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-"
    "REAL-REFERENCE-VALIDATION-2026-07-22-001"
)
RESULT_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_PASS_CONSUMED"
)
NEXT_STEP = (
    "HISTORICAL_GOLD_5824_ELIGIBLE_CORPUS_FREEZE_AND_"
    "EXCEPTION_EXCLUSION_POLICY_READY_FOR_DESIGN"
)
RESULT_SHA = "sha256:048149cd058c74c1ab441a99f3a4eec0972668500e469ff81ce663b3e5264340"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    before = STATUS_PATH.read_text(encoding="utf-8")
    text = before

    text = replace_once(
        text,
        "狀態核對日期：2026-07-22  ",
        "狀態核對日期：2026-07-23  ",
        "status date",
    )

    old_control = """candidate formal result: BLOCKED BY REFERENCE COVERAGE
Gold/Silver reconciliation result: SOURCE_DATA_GAP_CONFIRMED
"""
    new_control = """candidate formal result: CROSS-SOURCE GATES PASS / MARKET EVALUATION NOT AUTHORIZED
Gold/Silver reconciliation result: SOURCE_DATA_GAP_CONFIRMED / DOCUMENTED EXCEPTIONS RECOGNIZED
"""
    text = replace_once(text, old_control, new_control, "candidate control state")

    old_validation_control = """real-reference validation request design: VALIDATED
real-reference validation request: VALID / AWAITING EXPLICIT USER APPROVAL
real-reference validation request id: HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001
real-reference validation request execution count: 0 / 1
real-reference validation approval granted: false
real-reference validation execution enabled: false
real-reference validation executed: false
raw Historical Silver games: 5,826
"""
    new_validation_control = """real-reference validation request design: VALIDATED
real-reference validation request: EXECUTED / PASS / CONSUMED
real-reference validation request id: HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001
real-reference validation request execution count: 1 / 1
real-reference validation approval granted: true
real-reference validation execution enabled: false
real-reference validation executed: true
real-reference validation repeat execution: disabled
real-reference validation formal state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_PASS_CONSUMED
real-reference validation result record: data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.json
real-reference validation result payload SHA-256: sha256:048149cd058c74c1ab441a99f3a4eec0972668500e469ff81ce663b3e5264340
real-reference validation recording PR: 131
real-reference validation recording merge: ce39a8f39032c5aebe07c2c6734ebc58b02e2108
real-reference validation result QA run: 29972975866
real-reference validation result QA artifact: 8550389215
real-reference validation result QA artifact digest: sha256:5ce4c745b0262b30d9d1f390338b2bbce3bb9a60ef4428e3268d634f274de081
eligible Historical Gold corpus for future policy design: 5,824
documented exceptions excluded from Gold eligibility: 2
raw Historical Silver games: 5,826
"""
    text = replace_once(
        text,
        old_validation_control,
        new_validation_control,
        "real-reference validation control block",
    )

    old_mainline = """## Next Unique Mainline

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_EXPLICIT_USER_APPROVAL_REQUIRED
```

The immutable one-time request is ready and its validator computes exact SHA-256 bindings for the request file and transformer implementation. The next controlled lane is a separate explicit approval record. Approval has not been granted, no execution workflow exists, and real-reference validation remains disabled.
"""
    new_mainline = """## Next Unique Mainline

```text
HISTORICAL_GOLD_5824_ELIGIBLE_CORPUS_FREEZE_AND_EXCEPTION_EXCLUSION_POLICY_READY_FOR_DESIGN
```

The aggregate-only real-reference validation passed and Request `001` is permanently consumed. The validated research interpretation is `5,824` Gold-eligible matchups plus `2` documented upstream source exceptions excluded from Gold eligibility. Gold remains formally incomplete. The next controlled lane is policy design only; it does not freeze data, rebuild Gold, rerun the cross-source audit, authorize market backtesting, or change Stake from `0`.
"""
    text = replace_once(text, old_mainline, new_mainline, "next unique mainline")

    evidence_anchor = "\n## Consumed One-time Scopes\n"
    evidence = f"""
### Source gap exception real-reference validation result

```text
request id: {REQUEST_ID}
execution workflow run number: 2
execution workflow run id: unavailable / not guessed
execution head SHA: 596ade65cd26cb148f8a3b9a0ffa6092b16a6737
job: execute-once / success
observed duration: 20 seconds
observed execution Artifacts: 1
formal execution state: HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_PASS
recording PR: 131
recording merge: ce39a8f39032c5aebe07c2c6734ebc58b02e2108
result QA run: 29972975866
result QA artifact: 8550389215
result QA artifact digest: sha256:5ce4c745b0262b30d9d1f390338b2bbce3bb9a60ef4428e3268d634f274de081
result payload SHA-256: {RESULT_SHA}
validation checks: 88 / 88
mutation tests: 12 / 12
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
formal stake: 0
```

Aggregate interpretation:

```text
raw Historical Silver games: 5,826
raw Historical Gold matchups: 5,824
raw missing Gold for Silver: 2
documented source-gap exceptions: 2
unexplained missing after documentation: 0
covered or documented: 5,826
Gold dataset complete: false
recognition gate passed: true
exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
```

The result contains aggregate evidence only. It does not create the two missing Gold rows or rewrite Gold as complete. The execution result export did not include the GitHub workflow run ID, Artifact ID, or Artifact archive digest; those execution metadata values remain explicitly unavailable rather than inferred. The separately generated result-QA run and Artifact are recorded above.

Formal records:

- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-current-status-v3.json`
- `docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.md`

"""
    if text.count(evidence_anchor) != 1:
        raise RuntimeError("consumed scopes anchor must exist exactly once")
    if "### Source gap exception real-reference validation result" in text:
        raise RuntimeError("result evidence section already exists")
    text = text.replace(evidence_anchor, "\n" + evidence + "## Consumed One-time Scopes\n", 1)

    consumed_anchor = """HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
```"""
    consumed_replacement = f"""HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001
{REQUEST_ID}
```"""
    text = replace_once(text, consumed_anchor, consumed_replacement, "consumed request list")

    old_blocked = """- production analyzer integration or replacement before separately approved real-reference validation;
- real-reference validation or execution of exception recognition without separate approval;
"""
    new_blocked = """- reuse, rerun, or re-dispatch of consumed real-reference validation Request `001`;
- treating the two documented exceptions as Gold-eligible rows without genuinely new governed source evidence;
- eligible-corpus freeze before a separately validated policy design and implementation;
"""
    text = replace_once(text, old_blocked, new_blocked, "still blocked validation items")

    important_anchor = """- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-current-status-v2.json`
"""
    important_replacement = important_anchor + """- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.json`
- `data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-current-status-v3.json`
"""
    text = replace_once(text, important_anchor, important_replacement, "important result files")

    docs_anchor = """- `docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-v1.md`
"""
    docs_replacement = docs_anchor + """- `docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.md`
"""
    text = replace_once(text, docs_anchor, docs_replacement, "important result documentation")

    scripts_anchor = """- `scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_request_v1.py`
"""
    scripts_replacement = scripts_anchor + """- `scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_result_v1.py`
"""
    text = replace_once(text, scripts_anchor, scripts_replacement, "important result validator")

    workflow_anchor = """- `.github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-request-v1.yml`
"""
    workflow_replacement = workflow_anchor + """- `.github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-result-v1.yml`
"""
    text = replace_once(text, workflow_anchor, workflow_replacement, "important result workflow")

    required_fragments = (
        RESULT_STATE,
        NEXT_STEP,
        REQUEST_ID,
        RESULT_SHA,
        "request consumed: true",
        "eligible Historical Gold corpus for future policy design: 5,824",
        "documented exceptions excluded from Gold eligibility: 2",
        "Gold dataset complete: false",
        "formal stake: 0",
        "workflow run: 29810347326",
        "source archive reconciliation run: 29901869841",
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise RuntimeError(f"required fragment missing after sync: {fragment}")

    forbidden_current_fragments = (
        "real-reference validation request: VALID / AWAITING EXPLICIT USER APPROVAL",
        "real-reference validation request execution count: 0 / 1",
        "real-reference validation approval granted: false",
        "real-reference validation executed: false",
        "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_EXPLICIT_USER_APPROVAL_REQUIRED",
    )
    for fragment in forbidden_current_fragments:
        if fragment in text:
            raise RuntimeError(f"stale current-state fragment remains: {fragment}")

    if len(text.splitlines()) <= len(before.splitlines()):
        raise RuntimeError("status sync must preserve history and add result evidence")

    STATUS_PATH.write_text(text, encoding="utf-8")
    print(
        {
            "status": "PROJECT_STATUS_SYNCED",
            "before_lines": len(before.splitlines()),
            "after_lines": len(text.splitlines()),
            "request_consumed": True,
            "next_research_step": NEXT_STEP,
            "formal_stake": 0,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
