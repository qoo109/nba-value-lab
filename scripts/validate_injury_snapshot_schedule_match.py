#!/usr/bin/env python3
"""Match normalized official injury snapshots to historical Gold game IDs."""
from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "injury-snapshot-schedule-match-v1"
OFFICIAL_GAME_ID_RE = re.compile(
    r"^official:(?P<game_date>\d{4}-\d{2}-\d{2}):(?P<away>[A-Z]{3})@(?P<home>[A-Z]{3})$"
)
REQUIRED_SNAPSHOT_COLUMNS = {
    "game_id", "team_abbr", "opponent_abbr", "is_home",
    "observed_at", "source_report_time", "source_file_sha256",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_snapshots(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = sorted(REQUIRED_SNAPSHOT_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"snapshot CSV missing columns: {missing}")
    if frame.empty:
        raise ValueError("snapshot CSV is empty")
    return frame


def materialize_database(path: Path, destination: Path) -> Path:
    if path.suffix != ".gz":
        return path
    with gzip.open(path, "rb") as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target, length=1024 * 1024)
    return destination


def load_gold_schedule(path: Path) -> pd.DataFrame:
    with tempfile.TemporaryDirectory(prefix="nbavl-injury-match-gold-") as temp_name:
        database_path = materialize_database(path, Path(temp_name) / "historical-gold.sqlite")
        connection = sqlite3.connect(database_path)
        try:
            frame = pd.read_sql_query(
                """SELECT game_id, game_date, home_team_abbr, away_team_abbr
                   FROM gold_matchup_features
                   ORDER BY game_date, game_id""",
                connection,
            )
        finally:
            connection.close()
    if frame.empty:
        raise ValueError("Gold database has no matchup schedule rows")
    for column in ("game_id", "game_date", "home_team_abbr", "away_team_abbr"):
        frame[column] = frame[column].astype(str).str.strip()
    frame["game_date"] = frame["game_date"].str.slice(0, 10)
    return frame


def parse_official_game_id(value: Any) -> dict[str, str] | None:
    match = OFFICIAL_GAME_ID_RE.fullmatch(str(value).strip())
    if not match:
        return None
    return match.groupdict()


def validate_snapshot_games(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    games: list[dict[str, Any]] = []
    errors: list[str] = []
    for official_game_id, rows in frame.groupby("game_id", sort=True):
        parsed = parse_official_game_id(official_game_id)
        if parsed is None:
            errors.append(f"invalid official game_id: {official_game_id!r}")
            continue
        away, home = parsed["away"], parsed["home"]
        row_errors = []
        for index, row in rows.iterrows():
            team = str(row["team_abbr"]).strip().upper()
            opponent = str(row["opponent_abbr"]).strip().upper()
            try:
                is_home = int(float(str(row["is_home"]).strip()))
            except ValueError:
                row_errors.append(f"row {index + 2} has invalid is_home")
                continue
            expected_team = home if is_home == 1 else away
            expected_opponent = away if is_home == 1 else home
            if team != expected_team or opponent != expected_opponent:
                row_errors.append(
                    f"row {index + 2} side mismatch: team={team} opponent={opponent} is_home={is_home}"
                )
        if row_errors:
            errors.extend(f"{official_game_id}: {message}" for message in row_errors)
        games.append({
            "official_game_id": official_game_id,
            "game_date": parsed["game_date"],
            "away_team_abbr": away,
            "home_team_abbr": home,
            "snapshot_rows": int(len(rows)),
            "source_report_times": int(rows["source_report_time"].nunique()),
            "source_files": int(rows["source_file_sha256"].nunique()),
        })
    return pd.DataFrame(games), errors


def schedule_key(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["game_date"].astype(str)
        + "|" + frame["away_team_abbr"].astype(str)
        + "|" + frame["home_team_abbr"].astype(str)
    )


def match_games(snapshot_games: pd.DataFrame, gold: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if snapshot_games.empty:
        raise ValueError("no valid official games were parsed")
    snapshot_games = snapshot_games.copy()
    gold = gold.copy()
    snapshot_games["schedule_key"] = schedule_key(snapshot_games)
    gold["schedule_key"] = schedule_key(gold)

    duplicate_gold = gold[gold.duplicated("schedule_key", keep=False)].copy()
    gold_unique = gold.drop_duplicates("schedule_key", keep=False)
    joined = snapshot_games.merge(
        gold_unique[["schedule_key", "game_id"]].rename(columns={"game_id": "historical_game_id"}),
        on="schedule_key",
        how="left",
        validate="one_to_one",
    )
    joined["matched"] = joined["historical_game_id"].notna()
    unmatched = joined[~joined["matched"]]
    matched_rows = int(joined.loc[joined["matched"], "snapshot_rows"].sum())
    qa = {
        "snapshot_games": int(len(joined)),
        "matched_games": int(joined["matched"].sum()),
        "unmatched_games": int((~joined["matched"]).sum()),
        "game_match_rate": float(joined["matched"].mean()),
        "matched_snapshot_rows": matched_rows,
        "duplicate_gold_schedule_keys": int(duplicate_gold["schedule_key"].nunique()),
        "unmatched_examples": unmatched[
            ["official_game_id", "game_date", "away_team_abbr", "home_team_abbr"]
        ].head(20).to_dict(orient="records"),
        "duplicate_gold_examples": duplicate_gold[
            ["schedule_key", "game_id"]
        ].head(20).to_dict(orient="records"),
    }
    return joined, qa


def run(snapshot_csv: Path, gold_database: Path, output_dir: Path) -> dict[str, Any]:
    snapshots = load_snapshots(snapshot_csv)
    snapshot_games, snapshot_errors = validate_snapshot_games(snapshots)
    gold = load_gold_schedule(gold_database)
    mapping, match_qa = match_games(snapshot_games, gold)

    ready = (
        not snapshot_errors
        and match_qa["snapshot_games"] > 0
        and match_qa["unmatched_games"] == 0
        and match_qa["duplicate_gold_schedule_keys"] == 0
        and match_qa["matched_snapshot_rows"] == len(snapshots)
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "snapshot_rows": int(len(snapshots)),
            "snapshot_games": int(match_qa["snapshot_games"]),
            "matched_games": int(match_qa["matched_games"]),
            "matched_snapshot_rows": int(match_qa["matched_snapshot_rows"]),
            "gold_schedule_rows": int(len(gold)),
            "source_report_times": int(snapshots["source_report_time"].nunique()),
            "source_files": int(snapshots["source_file_sha256"].nunique()),
        },
        "quality": {
            "snapshot_side_errors": len(snapshot_errors),
            "snapshot_side_error_examples": snapshot_errors[:50],
            **match_qa,
        },
        "decision": {
            "ready_for_historical_game_id_join": bool(ready),
            "ready_for_player_identity_join": False,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": "Game schedule matching only; player identity and multi-report coverage remain unvalidated.",
        },
        "guardrails": {
            "match_key": "game_date + away_team_abbr + home_team_abbr",
            "fuzzy_team_matching": False,
            "duplicate_gold_keys_allowed": False,
            "unmatched_games_allowed": False,
            "player_rows_uploaded": False,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    export = mapping[
        [
            "official_game_id", "historical_game_id", "game_date",
            "away_team_abbr", "home_team_abbr", "snapshot_rows",
            "source_report_times", "source_files", "matched",
        ]
    ].copy()
    export.to_csv(output_dir / "injury-snapshot-game-id-map.csv", index=False)
    (output_dir / "injury-snapshot-schedule-match-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nbavl-injury-match-self-test-") as temp_name:
        root = Path(temp_name)
        database = root / "gold.sqlite"
        connection = sqlite3.connect(database)
        try:
            connection.execute(
                """CREATE TABLE gold_matchup_features (
                       game_id TEXT, game_date TEXT,
                       home_team_abbr TEXT, away_team_abbr TEXT
                   )"""
            )
            connection.executemany(
                "INSERT INTO gold_matchup_features VALUES (?, ?, ?, ?)",
                [
                    ("gold-1", "2023-12-18", "DEN", "DAL"),
                    ("gold-2", "2023-12-18", "LAL", "NYK"),
                ],
            )
            connection.commit()
        finally:
            connection.close()
        snapshots = pd.DataFrame([
            {
                "game_id": "official:2023-12-18:DAL@DEN", "team_abbr": "DAL",
                "opponent_abbr": "DEN", "is_home": "0",
                "observed_at": "2023-12-18T13:30:00Z",
                "source_report_time": "2023-12-18T13:30:00Z", "source_file_sha256": "a" * 64,
            },
            {
                "game_id": "official:2023-12-18:DAL@DEN", "team_abbr": "DEN",
                "opponent_abbr": "DAL", "is_home": "1",
                "observed_at": "2023-12-18T13:30:00Z",
                "source_report_time": "2023-12-18T13:30:00Z", "source_file_sha256": "a" * 64,
            },
            {
                "game_id": "official:2023-12-18:NYK@LAL", "team_abbr": "LAL",
                "opponent_abbr": "NYK", "is_home": "1",
                "observed_at": "2023-12-18T13:30:00Z",
                "source_report_time": "2023-12-18T13:30:00Z", "source_file_sha256": "a" * 64,
            },
        ])
        snapshot_path = root / "snapshots.csv"
        snapshots.to_csv(snapshot_path, index=False)
        report = run(snapshot_path, database, output_dir)
    assert report["decision"]["ready_for_historical_game_id_join"] is True, report
    assert report["coverage"]["matched_games"] == 2, report
    assert report["coverage"]["matched_snapshot_rows"] == 3, report
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-csv", type=Path)
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("Injury snapshot schedule-match self-test passed")
        return
    if not args.snapshot_csv or not args.gold:
        parser.error("--snapshot-csv and --gold are required unless --self-test is used")
    report = run(args.snapshot_csv, args.gold, args.output_dir)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_historical_game_id_join"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
