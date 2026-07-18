#!/usr/bin/env python3
"""Run the official NBA participation importer with browser-compatible parallel fetches.

NBA.com periodically rejects non-browser or stale HTTP headers. This runner preserves the
frozen label and validation logic in import_official_nba_participation_labels.py while fetching
the 176 official game payloads with current browser-style headers and bounded concurrency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import import_official_nba_participation_labels as core

BROWSER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Origin": "https://www.nba.com",
    "Pragma": "no-cache",
    "Referer": "https://www.nba.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def browser_fetch_json(
    url: str,
    *,
    attempts: int = 2,
    timeout_seconds: int = 30,
) -> tuple[dict[str, Any], dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers=BROWSER_HEADERS)
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read()
                status = int(getattr(response, "status", 200))
            if status != 200:
                raise ValueError(f"unexpected HTTP status {status}")
            parsed = json.loads(payload.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("official JSON root is not an object")
            return parsed, {
                "retrieved_at": utc_now(),
                "source_bytes": len(payload),
                "source_sha256": hashlib.sha256(payload).hexdigest(),
                "http_status": status,
                "attempts": attempt,
                "request_profile": "nba_browser_headers_v1",
            }
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(
        f"official source fetch failed after {attempts} attempts: {last_error}"
    )


def prefetch(
    selected_rows: list[dict[str, str]],
    *,
    url_template: str,
    max_workers: int,
) -> dict[str, tuple[dict[str, Any], dict[str, Any]] | Exception]:
    urls = []
    seen = set()
    for row in selected_rows:
        historical_id = str(row.get("historical_game_id") or "").strip()
        if not historical_id:
            continue
        official_id = core.normalize_official_game_id(historical_id)
        url = url_template.format(official_game_id=official_id)
        if url not in seen:
            urls.append(url)
            seen.add(url)

    cache: dict[str, tuple[dict[str, Any], dict[str, Any]] | Exception] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(browser_fetch_json, url): url for url in urls}
        completed = 0
        for future in as_completed(futures):
            url = futures[future]
            try:
                cache[url] = future.result()
            except Exception as exc:  # preserved for the core importer report
                cache[url] = exc
            completed += 1
            if completed % 25 == 0 or completed == len(urls):
                success = sum(not isinstance(value, Exception) for value in cache.values())
                print(
                    json.dumps(
                        {
                            "prefetch_completed": completed,
                            "prefetch_total": len(urls),
                            "prefetch_success": success,
                            "prefetch_failed": completed - success,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
    return cache


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-games", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--url-template", default=core.DEFAULT_URL_TEMPLATE)
    parser.add_argument("--max-workers", type=int, default=6)
    args = parser.parse_args()

    if not 1 <= args.max_workers <= 12:
        parser.error("--max-workers must be between 1 and 12")

    selected_rows = core.read_csv(args.selected_games)
    cache = prefetch(
        selected_rows,
        url_template=args.url_template,
        max_workers=args.max_workers,
    )

    def cached_fetcher(url: str):
        value = cache.get(url)
        if value is None:
            raise RuntimeError(f"official URL was not prefetched: {url}")
        if isinstance(value, Exception):
            raise value
        return value

    report = core.run(
        selected_rows,
        args.output_dir,
        url_template=args.url_template,
        fetcher=cached_fetcher,
    )
    report["source"]["request_profile"] = "nba_browser_headers_v1"
    report["source"]["parallel_fetch_workers"] = args.max_workers
    (args.output_dir / "official-player-participation-import-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_player_participation_join"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
