#!/usr/bin/env python3
"""Hotfix entrypoint for the approved Legacy Market Archive real-file audit.

The first approved run reached the reference rebuild after validating approval and
locating the exact candidate, but failed because the temporary reference root did
not exist before ``config-2019.json`` was written. This wrapper preserves the
reviewed v1 executor and adds only the missing deterministic directory creation.
"""
from __future__ import annotations

from pathlib import Path

import run_user_supplied_legacy_market_archive_real_file_audit_once_v1 as base

_ORIGINAL_REFERENCE_BUILD = base.reference_build


def prepare_reference_root(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    return root


def reference_build_with_root(root: Path):
    return _ORIGINAL_REFERENCE_BUILD(prepare_reference_root(root))


def main() -> int:
    base.reference_build = reference_build_with_root
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
