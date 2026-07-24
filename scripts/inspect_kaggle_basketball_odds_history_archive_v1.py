#!/usr/bin/env python3
"""Aggregate-only local inspector for a manually downloaded Kaggle odds archive.

The inspector performs no network requests and emits no quote-level rows or prices.
It reads only archive member names, CSV headers, row counts and small notebook
metadata needed to assess whether NBA files may contain auditable timestamp,
bookmaker, event and team fields.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

ROOT = Path(__file__).resolve().parents[1]

TIMESTAMP_TOKENS = (
    "observed",
    "snapshot",
    "scrape",
    "timestamp",
    "updated",
    "last_update",
    "collected",
    "captured",
    "fetched",
    "created_at",
    "time",
    "date",
)
BOOKMAKER_TOKENS = ("bookmaker", "sportsbook", "provider", "book", "site")
EVENT_TOKENS = ("event_id", "game_id", "match_id", "fixture_id", "event")
TEAM_TOKENS = (
    "home_team",
    "away_team",
    "team_home",
    "team_away",
    "home",
    "away",
    "participant",
)
PRICE_TOKENS = ("odds", "price", "moneyline", "home_ml", "away_ml", "decimal")
NBA_NAME_TOKENS = ("nba", "national_basketball_association")
PLACEHOLDER_COLUMNS = {"", "unnamed", "column", "field"}


class ArchiveInspectionError(ValueError):
    """Raised when a local archive cannot be safely inspected."""


@dataclass(frozen=True)
class Member:
    name: str
    size: int
    read_bytes: callable


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _is_within_repo(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def _safe_relative_name(name: str) -> str:
    normalized = name.replace("\\", "/").lstrip("/")
    if not normalized or ".." in Path(normalized).parts:
        raise ArchiveInspectionError("archive contains unsafe member path")
    return normalized


def _iter_zip_members(path: Path) -> Iterator[Member]:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ArchiveInspectionError("source is not a valid ZIP archive") from exc
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = _safe_relative_name(info.filename)
            yield Member(
                name=name,
                size=int(info.file_size),
                read_bytes=lambda member=name, zpath=path: _read_zip_member(zpath, member),
            )


def _read_zip_member(path: Path, member: str) -> bytes:
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as stream:
            return stream.read()


def _iter_directory_members(path: Path) -> Iterator[Member]:
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        name = item.relative_to(path).as_posix()
        _safe_relative_name(name)
        yield Member(name=name, size=item.stat().st_size, read_bytes=item.read_bytes)


def _iter_members(path: Path) -> Iterator[Member]:
    if not path.exists():
        raise ArchiveInspectionError("source path does not exist")
    if _is_within_repo(path):
        raise ArchiveInspectionError("downloaded archive must remain outside the public repository")
    if path.is_dir():
        yield from _iter_directory_members(path)
        return
    if path.suffix.lower() == ".zip":
        yield from _iter_zip_members(path)
        return
    raise ArchiveInspectionError("source must be a ZIP archive or extracted directory")


def _normalize_header(raw: Sequence[str]) -> list[str]:
    columns: list[str] = []
    for value in raw:
        normalized = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
        columns.append(normalized)
    if not columns or all(column in PLACEHOLDER_COLUMNS for column in columns):
        raise ArchiveInspectionError("CSV header is empty or unusable")
    return columns


def _read_csv_metadata(member: Member) -> dict[str, object]:
    content = member.read_bytes()
    if not content:
        raise ArchiveInspectionError(f"{member.name} is empty")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise ArchiveInspectionError(f"{member.name} cannot be decoded as text") from exc

    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ArchiveInspectionError(f"{member.name} has no header") from exc
    columns = _normalize_header(header)
    row_count = sum(1 for row in reader if any(str(cell).strip() for cell in row))

    def matching(tokens: Iterable[str]) -> list[str]:
        return sorted({column for column in columns if any(token in column for token in tokens)})

    return {
        "filename": member.name,
        "size_bytes": member.size,
        "row_count": row_count,
        "column_count": len(columns),
        "columns": columns,
        "timestamp_columns": matching(TIMESTAMP_TOKENS),
        "bookmaker_columns": matching(BOOKMAKER_TOKENS),
        "event_columns": matching(EVENT_TOKENS),
        "team_columns": matching(TEAM_TOKENS),
        "price_columns": matching(PRICE_TOKENS),
        "content_sha256": sha256_bytes(content),
    }


def _is_nba_candidate(name: str) -> bool:
    lowered = name.lower().replace("-", "_")
    return any(token in lowered for token in NBA_NAME_TOKENS)


def _notebook_metadata(member: Member) -> dict[str, object]:
    content = member.read_bytes()
    try:
        notebook = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "filename": member.name,
            "valid_json": False,
            "cell_count": None,
            "content_sha256": sha256_bytes(content),
        }
    cells = notebook.get("cells")
    return {
        "filename": member.name,
        "valid_json": isinstance(cells, list),
        "cell_count": len(cells) if isinstance(cells, list) else None,
        "content_sha256": sha256_bytes(content),
    }


def inspect_archive(source: Path) -> dict[str, object]:
    members = list(_iter_members(source))
    if not members:
        raise ArchiveInspectionError("archive contains no files")

    csv_members = [member for member in members if member.name.lower().endswith(".csv")]
    nba_csv_members = [member for member in csv_members if _is_nba_candidate(member.name)]
    notebook_members = [member for member in members if member.name.lower().endswith(".ipynb")]

    nba_files: list[dict[str, object]] = []
    errors: list[str] = []
    for member in nba_csv_members:
        try:
            nba_files.append(_read_csv_metadata(member))
        except ArchiveInspectionError as exc:
            errors.append(f"{member.name}: {exc}")

    notebook = _notebook_metadata(notebook_members[0]) if notebook_members else None
    timestamp_file_count = sum(bool(item["timestamp_columns"]) for item in nba_files)
    bookmaker_file_count = sum(bool(item["bookmaker_columns"]) for item in nba_files)
    event_file_count = sum(bool(item["event_columns"]) for item in nba_files)
    team_file_count = sum(bool(item["team_columns"]) for item in nba_files)
    price_file_count = sum(bool(item["price_columns"]) for item in nba_files)

    schema_candidate = bool(nba_files) and all(
        count > 0
        for count in (
            timestamp_file_count,
            bookmaker_file_count,
            event_file_count,
            team_file_count,
            price_file_count,
        )
    )

    return {
        "schema_version": "kaggle-basketball-odds-history-local-inspection-v1",
        "formal_state": (
            "KAGGLE_BASKETBALL_ODDS_HISTORY_LOCAL_SCHEMA_CANDIDATE_FOUND"
            if schema_candidate
            else "KAGGLE_BASKETBALL_ODDS_HISTORY_LOCAL_SCHEMA_NOT_YET_QUALIFIED"
        ),
        "source_type": "local_manual_download",
        "source_path_in_public_repo": False,
        "archive_file_count": len(members),
        "csv_file_count": len(csv_members),
        "nba_csv_file_count": len(nba_csv_members),
        "nba_csv_files_inspected": len(nba_files),
        "nba_csv_errors": errors,
        "notebook_present": bool(notebook_members),
        "notebook_metadata": notebook,
        "field_presence": {
            "timestamp_file_count": timestamp_file_count,
            "bookmaker_file_count": bookmaker_file_count,
            "event_file_count": event_file_count,
            "team_file_count": team_file_count,
            "price_file_count": price_file_count,
        },
        "nba_files": nba_files,
        "schema_candidate": schema_candidate,
        "timestamp_semantics_verified": False,
        "bookmaker_identity_semantics_verified": False,
        "upstream_provenance_verified": False,
        "source_rights_verified_for_private_research": False,
        "point_in_time_qualified": False,
        "historical_backfill_qualified": False,
        "formal_history_write_authorized": False,
        "market_metrics_executed": False,
        "quote_rows_emitted": 0,
        "prices_emitted": 0,
        "provider_requests_executed": 0,
        "formal_stake": 0,
        "next_unique_mainline": (
            "REVIEW_KAGGLE_NBA_COLUMNS_TIMESTAMP_SEMANTICS_AND_UPSTREAM_PROVENANCE"
            if schema_candidate
            else "OBTAIN_COMPLETE_KAGGLE_BASKETBALL_ODDS_HISTORY_ARCHIVE_AND_REINSPECT"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path, help="manual Kaggle ZIP or extracted directory outside repo")
    parser.add_argument("--output", required=True, type=Path, help="aggregate-only inspection JSON outside repo")
    args = parser.parse_args()

    if _is_within_repo(args.output):
        raise ArchiveInspectionError("aggregate inspection output must remain outside the public repository until reviewed")
    report = inspect_archive(args.source)
    args.output.expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "formal_state": report["formal_state"],
        "nba_csv_file_count": report["nba_csv_file_count"],
        "schema_candidate": report["schema_candidate"],
        "quote_rows_emitted": 0,
        "prices_emitted": 0,
        "formal_stake": 0,
        "next_unique_mainline": report["next_unique_mainline"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
