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
    "js/v5/pages/performance-dashboard.js": 260,
    "js/v5/pages/research-timeline.js": 260,
    "js/v5/bootstrap.js": 120,
    "css/v5-tokens.css": 160,
    "css/v5-layout.css": 300,
    "css/v5-components.css": 500,
    "css/v5-theme-p1.css": 260,
    "css/v5-research-p1.css": 340,
    "css/v5-mobile-p1.css": 300,
}

LOAD_ORDER = [
    "js/v5/core/namespace.js",
    "js/v5/utils/format.js",
    "js/v5/components/cards.js",
    "js/v5/components/drawer.js",
    "js/v5/pages/dashboard.js",
    "js/v5/pages/performance-dashboard.js",
    "js/v5/pages/research-timeline.js",
    "js/v5/bootstrap.js",
]

STYLES = [
    "css/v5-tokens.css",
    "css/v5-layout.css",
    "css/v5-components.css",
    "css/v5-theme-p1.css",
    "css/v5-research-p1.css",
    "css/v5-mobile-p1.css",
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
    require('dataset.appVersion = v5Ready ? "V5.1"' in init_text, "V5.1 app version is not active")
    require("window.showDetail = open" in (ROOT / "js/v5/components/drawer.js").read_text(encoding="utf-8"), "Drawer does not replace showDetail")
    require("window.renderTopPick" in (ROOT / "js/v5/components/cards.js").read_text(encoding="utf-8"), "V5 cards do not replace top-pick renderer")
    require("window.renderCards" in (ROOT / "js/v5/components/cards.js").read_text(encoding="utf-8"), "V5 cards do not replace candidate renderer")

    bootstrap = (ROOT / "js/v5/bootstrap.js").read_text(encoding="utf-8")
    require("performanceDashboard?.afterRender" in bootstrap, "Performance dashboard is not initialized")
    require("researchTimeline?.afterRender" in bootstrap, "Research timeline is not initialized")

    performance = (ROOT / "js/v5/pages/performance-dashboard.js").read_text(encoding="utf-8")
    require("latestResolvedMainRecords" in performance, "Performance dashboard does not deduplicate predictions")
    require("record.main_candidate" in performance, "Performance dashboard is not limited to official main records")

    timeline = (ROOT / "js/v5/pages/research-timeline.js").read_text(encoding="utf-8")
    require("示範 slate 不會出現在 Timeline" in timeline, "Timeline empty state must reject demo records")

    theme = (ROOT / "css/v5-theme-p1.css").read_text(encoding="utf-8")
    require(':root[data-theme="dark"]' in theme, "Dark theme tokens are missing")
    require("color-scheme: light" in theme and "color-scheme: dark" in theme, "Theme color schemes are incomplete")

    mobile = (ROOT / "css/v5-mobile-p1.css").read_text(encoding="utf-8")
    require("env(safe-area-inset-bottom)" in mobile, "Mobile safe-area support is missing")
    require("position: fixed" in mobile, "Mobile bottom navigation is missing")

    print("V5.1 UI P1 architecture valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
