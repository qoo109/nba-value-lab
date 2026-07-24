#!/usr/bin/env python3
"""Build 2024-25 Silver and probe 2025-26 forward-feature sources.

This is a private research execution helper. It downloads public source archives
into temporary workflow storage, builds the governed 2024-25 Silver layer using
the existing adapters, and inspects the available 2025-26 official NBA-derived
archives for a future no-retraining forward-scoring adapter.

Raw archives and raw CSV rows are never emitted or committed. The only durable
outputs are aggregate QA plus the derived 2024-25 Silver SQLite artifact.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import historical_silver_runner as silver_builder
from historical_phase2_core import download, extract

ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = ROOT / "config" / "historical-source-pilot.json"

SOURCES_2025 = {
    "nbastatsv3_2025": {
        "url": "https://github.com/shufinskiy/nba_data/raw/main/datasets/nbastatsv3_2025.tar.xz",
        "role": "official_stats_v3_play_by_play",
    },
    "cdnnba_2025": {
        "url": "https://github.com/shufinskiy/nba_data/raw/main/datasets/cdnnba_2025.tar.xz",
        "role": "official_cdn_play_by_play",
    },
    "matchups_2025": {
        "url": "https://github.com/shufinskiy/nba_data/raw/main/datasets/matchups_2025.tar.xz",
        "role": "official_matchup_context_candidate",
    },
}

FALLBACK_INVENTORY = {
    "2024-25": {
        "pbpstats_2024": "https://github.com/shufinskiy/nba_data/raw/main/datasets/pbpstats_2024.tar.xz",
        "nbastats_2024": "https://github.com/shufinskiy/nba_data/raw/main/datasets/nbastats_2024.tar.xz",
        "nbastatsv3_2024": "https://github.com/shufinskiy/nba_data/raw/main/datasets/nbastatsv3_2024.tar.xz",
        "cdnnba_2024": "https://github.com/shufinskiy/nba_data/raw/main/datasets/cdnnba_2024.tar.xz",
        "matchups_2024": "https://github.com/shufinskiy/nba_data/raw/main/datasets/matchups_2024.tar.xz",
    },
    "2025-26": {key: value["url"] for key, value in SOURCES_2025.items()},
}

GAME_ID_CANDIDATES = ("gameid", "game_id")
DATE_CANDIDATES = (
    "gamedate",
    "game_date",
    "game_date_est",
    "game_date_time_utc",
    "game_datetime_utc",
    "timeactual",
)
TEAM_CANDIDATES = (
    "teamtricode",
    "team_abbreviation",
    "team_abbr",
    "home_team_abbreviation",
    "visitor_team_abbreviation",
    "away_team_abbreviation",
)

CDN_REQUIRED = {
    "gameid",
    "period",
    "actiontype",
    "scorehome",
    "scoreaway",
    "teamid",
    "teamtricode",
    "possession",
}
V3_REQUIRED_CORE = {
    "gameid",
    "period",
    "teamid",
    "teamtricode",
    "scorehome",
    "scoreaway",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical(name: Any) -> str:
    return str(name or "").strip().lower().replace(" ", "_")


def normalized_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def find_csv(root: Path, source_key: str) -> Path:
    files = sorted(root.rglob("*.csv"))
    if not files:
        raise RuntimeError(f"{source_key}: archive contains no CSV")
    preferred = [path for path in files if source_key.lower() in path.name.lower()]
    if len(preferred) == 1:
        return preferred[0]
    if len(files) == 1:
        return files[0]
    raise RuntimeError(
        f"{source_key}: archive contains multiple CSV files and no unique preferred file: "
        + ", ".join(path.name for path in files[:20])
    )


def inspect_csv(path: Path, source_key: str) -> dict[str, Any]:
    row_count = 0
    game_ids: set[str] = set()
    teams: set[str] = set()
    date_values: set[str] = set()
    nonempty = Counter()
    terminal_scores: dict[str, tuple[int, int]] = {}

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        original_fields = list(reader.fieldnames or [])
        fields = {canonical(name): name for name in original_fields}
        game_field = next((fields[name] for name in GAME_ID_CANDIDATES if name in fields), None)
        date_fields = [fields[name] for name in DATE_CANDIDATES if name in fields]
        team_fields = [fields[name] for name in TEAM_CANDIDATES if name in fields]
        score_home_field = fields.get("scorehome") or fields.get("score_home")
        score_away_field = fields.get("scoreaway") or fields.get("score_away")

        for row in reader:
            row_count += 1
            for canonical_name, actual_name in fields.items():
                if str(row.get(actual_name, "")).strip() not in {"", "nan", "None", "null"}:
                    nonempty[canonical_name] += 1
            game_id = normalized_id(row.get(game_field)) if game_field else ""
            if game_id:
                game_ids.add(game_id)
            for field in team_fields:
                value = str(row.get(field, "")).strip().upper()
                if value and len(value) <= 5:
                    teams.add(value)
            for field in date_fields:
                value = str(row.get(field, "")).strip()
                if value:
                    date_values.add(value)
            if game_id and score_home_field and score_away_field:
                try:
                    home = int(float(str(row.get(score_home_field, "")).strip()))
                    away = int(float(str(row.get(score_away_field, "")).strip()))
                except ValueError:
                    continue
                previous = terminal_scores.get(game_id)
                if previous is None or home + away >= sum(previous):
                    terminal_scores[game_id] = (home, away)

    canonical_fields = sorted(fields)
    critical_nonempty = {
        name: nonempty.get(name, 0)
        for name in sorted(
            {
                "gameid",
                "game_id",
                "period",
                "actionnumber",
                "actiontype",
                "teamid",
                "teamtricode",
                "possession",
                "scorehome",
                "scoreaway",
                "timeactual",
            }
            & set(canonical_fields)
        )
    }
    return {
        "source_key": source_key,
        "csv_name": path.name,
        "csv_bytes": path.stat().st_size,
        "row_count": row_count,
        "column_count": len(original_fields),
        "canonical_columns": canonical_fields,
        "unique_game_ids": len(game_ids),
        "game_ids": sorted(game_ids),
        "unique_team_codes": len(teams),
        "team_codes": sorted(teams),
        "date_value_count": len(date_values),
        "date_value_min_lexical": min(date_values) if date_values else None,
        "date_value_max_lexical": max(date_values) if date_values else None,
        "games_with_terminal_score_candidate": len(terminal_scores),
        "critical_nonempty_counts": critical_nonempty,
        "cdn_required_columns_present": CDN_REQUIRED <= set(canonical_fields),
        "cdn_required_columns_missing": sorted(CDN_REQUIRED - set(canonical_fields)),
        "v3_core_columns_present": V3_REQUIRED_CORE <= set(canonical_fields),
        "v3_core_columns_missing": sorted(V3_REQUIRED_CORE - set(canonical_fields)),
    }


def build_2024_25_silver(output_root: Path, max_download_mb: int) -> dict[str, Any]:
    config = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    config["sources"]["pbpstats_2023"].update(
        {
            "season_label": "2024-25",
            "url": FALLBACK_INVENTORY["2024-25"]["pbpstats_2024"],
        }
    )
    config["sources"]["nbastats_2023"].update(
        {
            "season_label": "2024-25",
            "url": FALLBACK_INVENTORY["2024-25"]["nbastats_2024"],
        }
    )
    config_path = output_root / "historical-source-2024-25-private-temp.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    silver_dir = output_root / "silver-2024-25"
    report = silver_builder.build(config_path, silver_dir, max_download_mb)
    config_path.unlink(missing_ok=True)
    return {
        "report": report,
        "silver_database": str(silver_dir / "historical-silver.sqlite.gz"),
        "silver_report": str(silver_dir / "silver-build-report.json"),
        "silver_sample": str(silver_dir / "silver-sample.json"),
    }


def probe_2025_26_sources(output_root: Path, max_download_mb: int) -> dict[str, Any]:
    source_reports: dict[str, Any] = {}
    game_sets: dict[str, set[str]] = {}
    with tempfile.TemporaryDirectory(prefix="nbavl-forward-source-probe-") as temp_name:
        temp = Path(temp_name)
        for source_key, source in SOURCES_2025.items():
            archive = temp / f"{source_key}.tar.xz"
            extracted = temp / f"{source_key}-raw"
            extracted.mkdir()
            download_info = download(source["url"], archive, max_download_mb * 1048576)
            member_count = extract(archive, extracted)
            csv_path = find_csv(extracted, source_key)
            inspection = inspect_csv(csv_path, source_key)
            game_sets[source_key] = set(inspection.pop("game_ids"))
            source_reports[source_key] = {
                "role": source["role"],
                "url": source["url"],
                "archive_sha256": download_info["sha256"],
                "archive_bytes": download_info["bytes"],
                "archive_member_count": member_count,
                **inspection,
            }

    keys = sorted(game_sets)
    pairwise = {}
    for index, left in enumerate(keys):
        for right in keys[index + 1 :]:
            pairwise[f"{left}__{right}"] = {
                "intersection": len(game_sets[left] & game_sets[right]),
                "left_only": len(game_sets[left] - game_sets[right]),
                "right_only": len(game_sets[right] - game_sets[left]),
            }
    all_intersection = set.intersection(*(game_sets[key] for key in keys)) if keys else set()
    union = set.union(*(game_sets[key] for key in keys)) if keys else set()

    cdn = source_reports["cdnnba_2025"]
    v3 = source_reports["nbastatsv3_2025"]
    readiness = {
        "official_cdn_adapter_schema_ready": cdn["cdn_required_columns_present"],
        "official_stats_v3_core_schema_ready": v3["v3_core_columns_present"],
        "all_three_source_game_id_overlap": len(all_intersection),
        "source_union_game_ids": len(union),
        "minimum_regular_season_game_coverage_candidate": min(
            source_reports[key]["unique_game_ids"] for key in keys
        ),
        "ready_for_full_2025_26_adapter_implementation": (
            cdn["cdn_required_columns_present"]
            and v3["v3_core_columns_present"]
            and len(game_sets["cdnnba_2025"] & game_sets["nbastatsv3_2025"]) >= 1200
        ),
    }
    return {
        "sources": source_reports,
        "cross_source_game_id_coverage": {
            "all_three_intersection": len(all_intersection),
            "union": len(union),
            "pairwise": pairwise,
        },
        "adapter_readiness": readiness,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-download-mb", type=int, default=600)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    silver = build_2024_25_silver(args.output_dir, args.max_download_mb)
    probe = probe_2025_26_sources(args.output_dir, args.max_download_mb)
    silver_report = silver["report"]
    silver_ready = bool(
        silver_report.get("decision", {}).get("ready_for_private_model_feature_pipeline")
    )
    adapter_ready = bool(
        probe["adapter_readiness"]["ready_for_full_2025_26_adapter_implementation"]
    )

    blockers = []
    if not silver_ready:
        blockers.append("2024_25_SILVER_QUALITY_GATE_FAILED")
    if not adapter_ready:
        blockers.append("2025_26_OFFICIAL_SOURCE_ADAPTER_SCHEMA_OR_COVERAGE_INCOMPLETE")

    formal_state = (
        "FORWARD_FEATURE_SOURCES_FOUND_2024_25_SILVER_VALID_2025_26_ADAPTER_READY"
        if not blockers
        else "FORWARD_FEATURE_SOURCE_PROBE_BLOCKED"
    )
    report = {
        "schema_version": "forward-feature-source-probe-2024-25-2025-26-v1",
        "generated_at_utc": utc_now(),
        "formal_state": formal_state,
        "execution": {
            "network_sources_downloaded": 5,
            "provider_api_requests": 0,
            "raw_archives_committed": False,
            "raw_rows_emitted": 0,
            "model_retraining_executed": False,
            "model_scoring_executed": False,
            "market_join_executed": False,
        },
        "source_inventory": FALLBACK_INVENTORY,
        "season_2024_25": {
            "silver_ready": silver_ready,
            "silver_report": silver_report,
            "derived_artifact_paths": {
                "historical_silver_sqlite_gzip": "silver-2024-25/historical-silver.sqlite.gz",
                "silver_build_report": "silver-2024-25/silver-build-report.json",
                "silver_sample": "silver-2024-25/silver-sample.json",
            },
        },
        "season_2025_26": probe,
        "blockers": blockers,
        "decision": (
            "IMPLEMENT_OFFICIAL_CDN_V3_2025_26_SILVER_ADAPTER_WITH_2024_25_STATE"
            if not blockers
            else "REPAIR_SOURCE_SCHEMA_OR_COVERAGE_BEFORE_FORWARD_ADAPTER"
        ),
        "qualification": {
            "ready_to_implement_2025_26_silver_adapter": adapter_ready,
            "ready_to_build_continuous_2024_25_to_2025_26_gold": False,
            "ready_to_score_2025_26_with_frozen_model": False,
            "market_backtest_allowed": False,
            "clv_allowed": False,
            "roi_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "next_unique_sub_mainline": (
            "IMPLEMENT_OFFICIAL_CDN_V3_2025_26_SILVER_ADAPTER_AND_CONTINUOUS_GOLD_STATE"
            if not blockers
            else "RESOLVE_FORWARD_FEATURE_SOURCE_PROBE_BLOCKERS"
        ),
    }
    report_path = args.output_dir / "forward-feature-source-probe-report-v1.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
