#!/usr/bin/env python3
"""Core full-file scanner for NBA historical archive pilots."""

import csv
import hashlib
import math
import statistics
import tarfile
import urllib.request
from collections import Counter

UA = "NBA-Value-Lab-historical-pilot/2.0"


def missing(value):
    return value is None or str(value).strip().lower() in {"", "nan", "none", "null"}


def lookup(columns):
    return {column.upper(): column for column in columns}


def download(url, path, limit):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    digest, size = hashlib.sha256(), 0
    with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as target:
        content_type = response.headers.get("Content-Type")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ValueError(f"download exceeded {limit} bytes")
            digest.update(chunk)
            target.write(chunk)
    return {
        "bytes": size,
        "megabytes": round(size / 1048576, 2),
        "sha256": digest.hexdigest(),
        "content_type": content_type,
    }


def extract(archive, destination):
    root = destination.resolve()
    with tarfile.open(archive, "r:xz") as handle:
        members = handle.getmembers()
        for member in members:
            resolved = (root / member.name).resolve()
            if root not in resolved.parents and resolved != root:
                raise ValueError(f"unsafe archive path: {member.name}")
            if member.issym() or member.islnk():
                raise ValueError(f"archive link rejected: {member.name}")
        handle.extractall(root, members=members, filter="data")
    return len(members)


def quantile(values, q):
    if not values:
        return None
    position = (len(values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return float(values[low])
    return values[low] + (values[high] - values[low]) * (position - low)


def row_summary(counts):
    values = sorted(counts.values())
    return {
        "game_count": len(counts),
        "row_count": sum(values),
        "min_rows_per_game": values[0] if values else None,
        "p25_rows_per_game": round(quantile(values, 0.25), 2) if values else None,
        "median_rows_per_game": round(statistics.median(values), 2) if values else None,
        "p75_rows_per_game": round(quantile(values, 0.75), 2) if values else None,
        "p95_rows_per_game": round(quantile(values, 0.95), 2) if values else None,
        "max_rows_per_game": values[-1] if values else None,
    }


def select_csv(root, source):
    files = list(root.rglob("*.csv"))
    preferred = source.get("preferred_filename_contains", "").lower()
    matches = [path for path in files if preferred and preferred in path.name.lower()]
    candidates = matches or files
    if not candidates:
        raise ValueError("no CSV found in archive")
    return max(candidates, key=lambda path: path.stat().st_size)


def scan_csv(path, source, sample_limit):
    expected = source["expected_fields_any"]
    game_candidates = source["game_id_fields"]
    key_candidates = source["candidate_primary_keys"]
    sample_fields = source["silver_sample_fields"]
    games, nulls = Counter(), Counter()
    key_states, samples, sample_games = [], [], []

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        names = lookup(columns)
        game_field = next(
            (names.get(name.upper()) for name in game_candidates if names.get(name.upper())),
            None,
        )
        if not game_field:
            raise ValueError("game id field missing")
        for fields in key_candidates:
            resolved = [names.get(field.upper()) for field in fields]
            key_states.append({
                "fields": fields,
                "available": all(resolved),
                "resolved": resolved,
                "seen": set(),
                "duplicates": 0,
                "incomplete": 0,
            })

        for row_number, row in enumerate(reader, 1):
            game_id = str(row.get(game_field, "")).strip()
            if game_id:
                games[game_id] += 1
            for field in expected:
                actual = names.get(field.upper())
                if actual and missing(row.get(actual)):
                    nulls[field] += 1
            for state in key_states:
                if not state["available"]:
                    continue
                values = tuple(str(row.get(field, "")).strip() for field in state["resolved"])
                if any(missing(value) for value in values):
                    state["incomplete"] += 1
                elif values in state["seen"]:
                    state["duplicates"] += 1
                else:
                    state["seen"].add(values)
            if game_id and len(samples) < sample_limit:
                if game_id not in sample_games and len(sample_games) < 3:
                    sample_games.append(game_id)
                if game_id in sample_games:
                    item = {"source_game_id": game_id, "source_row_number": row_number}
                    for field in sample_fields:
                        actual = names.get(field.upper())
                        value = row.get(actual, "") if actual else ""
                        item[field.lower()] = None if missing(value) else str(value).strip()
                    samples.append(item)

    total = sum(games.values())
    checks = []
    for state in key_states:
        result = {"fields": state["fields"], "available": state["available"]}
        if state["available"]:
            result.update({
                "unique_key_count": len(state["seen"]),
                "duplicate_rows": state["duplicates"],
                "incomplete_rows": state["incomplete"],
                "unique": state["duplicates"] == 0 and state["incomplete"] == 0,
            })
        checks.append(result)
    return {
        "file": {
            "name": path.name,
            "bytes": path.stat().st_size,
            "megabytes": round(path.stat().st_size / 1048576, 2),
        },
        "columns": columns,
        "column_count": len(columns),
        "expected_fields_missing": [field for field in expected if field.upper() not in names],
        "expected_field_null_counts": dict(nulls),
        "expected_field_null_rates": {
            field: round(count / total, 6) for field, count in nulls.items() if total
        },
        "rows": row_summary(games),
        "game_ids": sorted(games),
        "candidate_key_checks": checks,
        "silver_sample_rows": samples,
        "silver_sample_game_ids": sample_games,
    }


def audit_source(key, source, root, max_mb, sample_limit):
    archive = root / f"{key}.tar.xz"
    target = root / f"{key}-raw"
    target.mkdir()
    archive_info = download(source["url"], archive, max_mb * 1048576)
    archive_info["member_count"] = extract(archive, target)
    return {
        "source_key": key,
        "provider": source["provider"],
        "source_role": source["source_role"],
        "season_label": source["season_label"],
        "license_status": source["license_status"],
        "archive": archive_info,
        "scan": scan_csv(select_csv(target, source), source, sample_limit),
    }
