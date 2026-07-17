# Kaggle Closing Market Benchmark v1

Updated: 2026-07-17

## Purpose

This workflow downloads an approved public Kaggle NBA odds dataset into GitHub Actions temporary storage, normalizes closing moneyline prices, and compares the closing market with the existing five-season walk-forward predictions.

The default dataset is:

```text
christophertreasure/nba-odds-data
```

The dataset page describes NBA moneylines, spreads, totals and second-half lines for 2008–2023 regular seasons, with 2023 incomplete. Its license is shown as `Other (specified in description)`, so raw files and normalized game-level odds are not committed or uploaded as workflow artifacts.

## Authentication

The workflow first attempts a public KaggleHub download. KaggleHub documentation states that authentication is only required for private resources or public resources requiring consent.

If Kaggle rejects anonymous access, create a free Kaggle API token and save it in the repository secret:

```text
KAGGLE_API_TOKEN
```

The token is never printed or stored in an artifact.

## Workflow

```text
Actions
→ Build Kaggle closing market benchmark
→ Run workflow
```

Inputs:

```text
source_run_id: 29551715399
dataset_handle: christophertreasure/nba-odds-data
```

The workflow:

1. downloads `model-walk-forward-v2` from the selected run;
2. downloads the Kaggle dataset into a temporary directory;
3. scans CSV, XLSX and XLS files;
4. selects the file with the largest valid normalized moneyline coverage;
5. converts American odds to decimal prices and proportional no-vig probabilities;
6. matches by game date, home team and away team;
7. compares model and closing-market Log Loss, Brier Score and accuracy;
8. deletes raw and normalized game-level files;
9. uploads reports and hashes only.

## Artifact

```text
kaggle-closing-market-benchmark-v1
```

Expected report files:

```text
kaggle-run-status.json
kaggle-candidate-manifest.json
kaggle-selected-import-report.json
closing-benchmark-report.json
```

## Guardrails

This is a closing-market forecast benchmark, not a betting backtest.

```text
ROI computed: false
CLV computed: false
Exact observation timestamp available: false
Betting-edge claim allowed: false
```

Closing-label archives cannot be treated as T-60m entry prices. They may show whether the model approaches or exceeds closing-market forecast accuracy, but they do not establish executable profitability.

## Data handling

- Kaggle raw files: GitHub Actions temporary storage only.
- Normalized game-level closing odds: temporary storage only.
- Public repository: code, documentation and source registry only.
- Artifact: aggregate reports, file hashes, detected schemas and coverage counts only.
