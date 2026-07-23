#!/usr/bin/env python3
"""Recovery v2: restore the two missing game dates from official CDN timestamps."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import recover_historical_silver_two_game_official_cdn_pbp_v1 as base
from historical_silver_schema import gzip_file

DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


def official_cdn_game_date(event_rows: list[dict[str, str]]) -> str:
    if not event_rows:
        raise RuntimeError("official CDN target has no event rows")
    columns = base.canonical_columns(event_rows[0].keys())
    candidates = (
        "timeactual",
        "gamedate",
        "gametimeutc",
        "gameet",
    )
    for row in event_rows:
        for field in candidates:
            raw = base.value(row, columns, field)
            match = DATE_RE.search(raw)
            if match:
                return match.group(1)
    raise RuntimeError("official CDN events do not expose a recoverable game date")


def patch_season_silver(
    gzip_path: Path,
    cdn_csv: Path,
    cdn_sha256: str,
    working_dir: Path,
) -> dict[str, Any]:
    sqlite_path = working_dir / "historical-silver-2023-recovery.sqlite"
    with gzip.open(gzip_path, "rb") as src, sqlite_path.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    db = sqlite3.connect(sqlite_path)
    try:
        target_ids = base.missing_feature_game_ids(db)
        if len(target_ids) != 2:
            raise RuntimeError(f"expected exactly two target games, found {len(target_ids)}")
        games = base.official_game_rows(db, target_ids)
        if len(games) != 2:
            raise RuntimeError("official game records missing")
        events_by_game, scan = base.extract_target_rows(cdn_csv, set(target_ids))
        if set(events_by_game) != set(target_ids):
            raise RuntimeError("official CDN archive does not cover both target games")

        before_features = int(db.execute("SELECT COUNT(*) FROM team_game_features").fetchone()[0])
        before_possessions = int(db.execute("SELECT COUNT(*) FROM possessions").fetchone()[0])
        diagnostics: list[dict[str, Any]] = []
        total_feature_rows: list[tuple[Any, ...]] = []
        total_possession_rows: list[tuple[Any, ...]] = []
        recovered_dates = 0
        for game_id in target_ids:
            recovered_date = official_cdn_game_date(events_by_game[game_id])
            game = games[game_id]
            existing_date = str(game.get("game_date") or "").strip()
            if existing_date and existing_date[:10] != recovered_date:
                raise RuntimeError("official CDN date disagrees with existing game date")
            game["game_date"] = recovered_date
            features, possessions, diagnostic = base.parse_game(game, events_by_game[game_id])
            total_feature_rows.extend(features)
            total_possession_rows.extend(possessions)
            diagnostics.append(diagnostic)
            db.execute("UPDATE games SET game_date=? WHERE game_id=?", (recovered_date, game_id))
            recovered_dates += 1

        db.executemany(
            "INSERT INTO possessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            total_possession_rows,
        )
        db.executemany(
            "INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            total_feature_rows,
        )
        for game_id in target_ids:
            possession_count = int(
                db.execute("SELECT COUNT(*) FROM possessions WHERE game_id=?", (game_id,)).fetchone()[0]
            )
            current_flags = str(
                db.execute("SELECT quality_flags FROM games WHERE game_id=?", (game_id,)).fetchone()[0] or ""
            )
            flags = ",".join(filter(None, (current_flags, base.RECOVERY_FLAG, "official_cdn_game_date_recovered_v2")))
            db.execute(
                "UPDATE games SET possession_count=?, score_match=1, quality_flags=? WHERE game_id=?",
                (possession_count, flags, game_id),
            )
        metadata = {
            "official_cdnnba_recovery_version": "v2",
            "official_cdnnba_recovery_archive_sha256": cdn_sha256,
            "official_cdnnba_recovery_game_count": "2",
            "official_cdnnba_recovery_game_dates": "2",
            "official_cdnnba_recovery_team_feature_rows": "4",
            "official_cdnnba_recovery_possession_rows": str(len(total_possession_rows)),
            "official_cdnnba_recovery_raw_archives_committed": "false",
        }
        db.executemany("INSERT OR REPLACE INTO metadata VALUES (?,?)", metadata.items())
        db.commit()

        after_features = int(db.execute("SELECT COUNT(*) FROM team_game_features").fetchone()[0])
        after_possessions = int(db.execute("SELECT COUNT(*) FROM possessions").fetchone()[0])
        remaining_missing = len(base.missing_feature_game_ids(db))
        remaining_missing_dates = int(
            db.execute(
                """
                SELECT COUNT(*) FROM games g
                JOIN team_game_features f ON f.game_id=g.game_id
                WHERE g.season_label='2023-24' AND (g.game_date IS NULL OR TRIM(g.game_date)='')
                  AND f.quality_flags LIKE ?
                """,
                (f"%{base.RECOVERY_FLAG}%",),
            ).fetchone()[0]
        )
        duplicate_features = int(
            db.execute(
                "SELECT COUNT(*)-COUNT(DISTINCT game_id || ':' || team_abbr) FROM team_game_features"
            ).fetchone()[0]
        )
        recovered_rows = int(
            db.execute(
                "SELECT COUNT(*) FROM team_game_features WHERE quality_flags LIKE ?",
                (f"%{base.RECOVERY_FLAG}%",),
            ).fetchone()[0]
        )
        if (
            after_features - before_features != 4
            or recovered_rows != 4
            or recovered_dates != 2
            or remaining_missing != 0
            or remaining_missing_dates != 0
            or duplicate_features != 0
        ):
            raise RuntimeError("post-patch Silver/date invariants failed")
        db.execute("VACUUM")
    finally:
        db.close()

    gzip_file(sqlite_path, gzip_path)
    sqlite_path.unlink()
    return {
        **scan,
        "target_games": 2,
        "recovered_games": 2,
        "recovered_game_dates": 2,
        "team_feature_rows_before": before_features,
        "team_feature_rows_after": after_features,
        "team_feature_rows_added": 4,
        "possession_rows_before": before_possessions,
        "possession_rows_after": after_possessions,
        "possession_rows_added": after_possessions - before_possessions,
        "remaining_games_without_team_features": remaining_missing,
        "remaining_recovered_games_without_dates": remaining_missing_dates,
        "duplicate_team_feature_rows": duplicate_features,
        "per_game_diagnostics": diagnostics,
        "game_identifiers_emitted_in_report": False,
        "game_dates_emitted_in_report": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    if args.self_test:
        report = base.self_test(args.output_root / "recovery-self-test-v2.json")
        report["recovery_version"] = "v2"
        base.write_json(args.output_root / "recovery-self-test-v2.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    # build_all resolves this module-global function through the imported v1 module.
    base.patch_season_silver = patch_season_silver
    try:
        report = base.build_all(args.output_root)
        report["schema_version"] = "historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2"
        report["recovery_version"] = "v2"
        report["recovery"]["recovered_game_dates"] = 2
        base.write_json(
            args.output_root / "artifacts" / "two-game-official-cdn-pbp-recovery-result-v2.json",
            report,
        )
        legacy = args.output_root / "artifacts" / "two-game-official-cdn-pbp-recovery-result-v1.json"
        if legacy.exists():
            legacy.unlink()
        print(
            json.dumps(
                {
                    "formal_state": report["formal_state"],
                    "recovered_games": report["recovery"]["recovered_games"],
                    "recovered_game_dates": report["recovery"]["recovered_game_dates"],
                    "silver_games": report["final_outputs"]["silver_games"],
                    "gold_matchups": report["final_outputs"]["gold_matchup_features"],
                    "formal_stake": 0,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        blocked = {
            "schema_version": "historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2",
            "created_at": base.utc_now(),
            "formal_state": base.FORMAL_BLOCKED,
            "recovery_version": "v2",
            "error_type": type(exc).__name__,
            "error_summary": str(exc).replace("/tmp/", "<temporary>/")[:1500],
            "decision": {
                "two_source_exceptions_resolved": False,
                "historical_silver_complete_for_governed_five_season_scope": False,
                "historical_gold_complete_for_governed_five_season_scope": False,
                "ready_for_market_backtest": False,
                "ready_for_model_retraining": False,
                "formal_stake": 0,
            },
            "boundaries": {
                "repository_database_modified": False,
                "source_archives_committed": False,
                "raw_game_identifiers_emitted_in_aggregate_report": False,
                "raw_game_dates_emitted_in_aggregate_report": False,
                "market_backtest_executed": False,
                "model_retraining_executed": False,
                "formal_stake": 0,
            },
        }
        base.write_json(
            args.output_root / "artifacts" / "two-game-official-cdn-pbp-recovery-result-v2.json",
            blocked,
        )
        print(json.dumps(blocked, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
