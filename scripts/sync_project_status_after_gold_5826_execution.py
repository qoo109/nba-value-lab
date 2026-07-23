#!/usr/bin/env python3
from pathlib import Path

path = Path("PROJECT_STATUS.md")
text = path.read_text(encoding="utf-8")

old_block = """real Artifact freeze workflow created: false
real Artifact execution approved: false
real Artifact execution count: 0
semantic freeze manifest created: false
corpus freeze executed: false"""
new_block = """real Artifact freeze workflow created: true / RETIRED AFTER CONSUMPTION
real Artifact execution approved: true
real Artifact execution count: 1 / 1
real Artifact execution run: 30000293169
real Artifact execution job: 89183633328
real Artifact execution artifact: 8560678596
real Artifact execution artifact digest: sha256:a6bfa2afbd2aef32f7e3f87078caaf620d94c744cf1eec74760d20ae4d0d5531
real Artifact execution formal outcome: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_PASS_CONSUMED
real Artifact request consumed: true
real Artifact repeat execution: disabled
semantic freeze manifest created: true
semantic freeze manifest SHA-256: sha256:dcd9522e7ee55669d5b4fd413e424aa01ac9182a1330d51c6f9bf6b13ad8059d
semantic corpus SHA-256: sha256:c0c48fe17d843714209c822422b9675eadbff8b6be048782a599b2085bc20cbd
corpus freeze executed: true / SEMANTIC MANIFEST ONLY"""

if old_block in text:
    text = text.replace(old_block, new_block, 1)
elif new_block not in text:
    raise SystemExit("Current Control Block replacement target not found")

old_next = """```text
HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_EXPLICIT_USER_APPROVAL_REQUIRED
```

The governed request is validated and bound to the exact adopted Artifact and computed SHA-256 approval evidence. The next controlled lane requires separate explicit user approval. Until that approval is recorded, no approval evidence, execution workflow, Artifact download/read, semantic manifest or corpus freeze may be created. Market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized."""

new_next = """```text
TIMESTAMPED_BOOKMAKER_ODDS_REAL_OBSERVED_AT_DATA_ACQUISITION_REQUIRED
```

The complete governed five-season Historical Gold corpus is now bound by a validated semantic freeze manifest. The one-time request was consumed successfully and its executor was retired. Market backtesting remains blocked because real timestamped bookmaker odds with `observed_at`, bookmaker provenance and opening/closing identity have not been acquired or separately authorized. Injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized."""

if old_next in text:
    text = text.replace(old_next, new_next, 1)
elif new_next not in text:
    raise SystemExit("Next Unique Mainline replacement target not found")

section = """### Historical Gold 5,826 real Artifact semantic freeze execution

```text
formal outcome: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_PASS_CONSUMED
request ID: HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001
approval granted: true
execution count: 1 / 1
request consumed: true
repeat execution allowed: false
workflow rerun allowed: false
executor retired: true
real Artifact read: true
semantic manifest created: true
corpus frozen by semantic manifest: true
market backtest executed: false
model retraining executed: false
formal Stake: 0
```

Execution evidence:

```text
approval recording PR: 146
approval recording merge: 5eb4bd9c11740ed0f68b5b3806ede24335796c6f
workflow run: 30000293169
job: 89183633328 / execute-once / success
source Artifact: 8551587005
source Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
output Artifact: 8560678596
output Artifact digest: sha256:a6bfa2afbd2aef32f7e3f87078caaf620d94c744cf1eec74760d20ae4d0d5531
output Artifact expiry: 2026-08-06T10:42:27Z
manifest SHA-256: sha256:dcd9522e7ee55669d5b4fd413e424aa01ac9182a1330d51c6f9bf6b13ad8059d
execution receipt SHA-256: sha256:a0b6ceba02d5cd7d4987dc293f1c41e3dd78d53f583ea5ab1474c469e17bd134
corpus semantic SHA-256: sha256:c0c48fe17d843714209c822422b9675eadbff8b6be048782a599b2085bc20cbd
```

Canonical aggregate result:

```text
Gold matchups: 5,826
Gold team-game rows: 11,652
seasons: 2019-20 through 2023-24
point-in-time violations: 0
duplicate matchup keys: 0
duplicate team-game keys: 0
database integrity: PASS
database SHA-256 unchanged: true
database modified: false
raw rows emitted: 0
```

Formal records:

- `data/research/historical-gold-5826-complete-corpus-freeze-manifest-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-result-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-current-status-v2.json`
- `docs/historical-gold-5826-freeze-manifest-real-artifact-execution-result-v1.md`

"""

marker = "## Completed Evidence\n\n"
if section not in text:
    if marker not in text:
        raise SystemExit("Completed Evidence marker not found")
    text = text.replace(marker, marker + "\n" + section, 1)

path.write_text(text, encoding="utf-8")
