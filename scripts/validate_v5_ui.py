#!/usr/bin/env python3
"""Validate V5 UI modules, loading order and file-size policy."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "js/v5/core/namespace.js": 120,
    "js/v5/utils/format.js": 180,
    "js/v5/components/cards.js": 300,
    "js/v5/components/drawer.js": 320,
    "js/v5/pages/dashboard.js": 280,
    "js/v5/bootstrap.js": 100,
    "css/v5-tokens.css": 160,
    "css/v5-layout.css": 300,
    "css/v5-components.css": 500,
}

LOAD_ORDER = [
    "js/v5/core/namespace.js",
    "js/v5/utils/format.js",
    "js/v5/components/cards.js",
    "js/v5/components/drawer.js",
    "js/v5/pages/dashboard.js",
    "js/v5/bootstrap.js",
]

STYLES = [
    "css/v5-tokens.css",
    "css/v5-layout.css",
    "css/v5-components.css",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    for relative, maximum in FILES.items():
        path = ROOT / relative
        require(path.is_file(), f"Missing V5 UI file: {relative}")
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        require(line_count <= maximum, f"{relative} has {line_count} lines; policy maximum is {maximum}")
        print(f"validated {relative}: {line_count}/{maximum} lines")

    init_text = (ROOT / "js/v4-init.js").read_text(encoding="utf-8")
    positions = []
    for relative in LOAD_ORDER:
        require(relative in init_text, f"V5 loader is missing {relative}")
        positions.append(init_text.index(relative))
    require(positions == sorted(positions), "V5 JavaScript modules are loaded in the wrong order")

    for relative in STYLES:
        require(relative in init_text, f"V5 loader is missing stylesheet {relative}")

    require("V5 UI failed to load; continuing with V4.10 UI" in init_text, "V4.10 fallback is missing")
    require("window.showDetail = open" in (ROOT / "js/v5/components/drawer.js").read_text(encoding="utf-8"), "Drawer does not replace showDetail")
    require("window.renderTopPick" in (ROOT / "js/v5/components/cards.js").read_text(encoding="utf-8"), "V5 cards do not replace top-pick renderer")
    require("window.renderCards" in (ROOT / "js/v5/components/cards.js").read_text(encoding="utf-8"), "V5 cards do not replace candidate renderer")

    print("V5 UI architecture valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
