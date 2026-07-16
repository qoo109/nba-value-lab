#!/usr/bin/env python3
"""Validate V5 UI modules, loading order and file-size policy."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "js/v5/core/namespace.js": 120,
    "js/v5/core/router.js": 220,
    "js/v5/utils/format.js": 180,
    "js/v5/utils/history.js": 220,
    "js/v5/utils/sparkline.js": 180,
    "js/v5/components/cards.js": 300,
    "js/v5/components/drawer.js": 320,
    "js/v5/pages/dashboard.js": 280,
    "js/v5/pages/performance-dashboard.js": 260,
    "js/v5/pages/performance-trends.js": 220,
    "js/v5/pages/research-timeline.js": 260,
    "js/v5/pages/market-trends.js": 240,
    "js/v5/bootstrap.js": 140,
    "css/v5-tokens.css": 160,
    "css/v5-layout.css": 300,
    "css/v5-components.css": 500,
    "css/v5-theme-p1.css": 260,
    "css/v5-research-p1.css": 340,
    "css/v5-mobile-p1.css": 300,
    "css/v5-routing-p2.css": 180,
    "css/v5-trends-p2.css": 360,
    "css/v5-compact-decision.css": 180,
}

LOAD_ORDER = [
    "js/v5/core/namespace.js",
    "js/v5/utils/format.js",
    "js/v5/utils/history.js",
    "js/v5/utils/sparkline.js",
    "js/v5/components/cards.js",
    "js/v5/components/drawer.js",
    "js/v5/pages/dashboard.js",
    "js/v5/pages/performance-dashboard.js",
    "js/v5/pages/performance-trends.js",
    "js/v5/pages/research-timeline.js",
    "js/v5/pages/market-trends.js",
    "js/v5/core/router.js",
    "js/v5/bootstrap.js",
]

STYLES = [
    "css/v5-tokens.css",
    "css/v5-layout.css",
    "css/v5-components.css",
    "css/v5-theme-p1.css",
    "css/v5-research-p1.css",
    "css/v5-mobile-p1.css",
    "css/v5-routing-p2.css",
    "css/v5-trends-p2.css",
    "css/v5-compact-decision.css",
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
    require('dataset.appVersion = v5Ready ? "V5.2"' in init_text, "V5.2 app version is not active")
    require("window.showDetail = open" in (ROOT / "js/v5/components/drawer.js").read_text(encoding="utf-8"), "Drawer does not replace showDetail")

    cards = (ROOT / "js/v5/components/cards.js").read_text(encoding="utf-8")
    require("window.renderTopPick" in cards, "V5 cards do not replace top-pick renderer")
    require("window.renderCards" in cards, "V5 cards do not replace candidate renderer")
    require("v52-compact-decision" in cards and "v52-decision-note" in cards, "Compact decision-strip markup is missing")

    compact = (ROOT / "css/v5-compact-decision.css").read_text(encoding="utf-8")
    require("grid-template-columns: minmax(0, 1fr) !important" in compact, "Top-pick layout is not forced to one column")
    require("white-space: nowrap" in compact, "Decision strip is not kept to one line")
    require("v52-decision-note" in compact, "Compact decision note styling is missing")

    bootstrap = (ROOT / "js/v5/bootstrap.js").read_text(encoding="utf-8")
    for module in ("performanceDashboard", "performanceTrends", "researchTimeline", "marketTrends", "router"):
        require(f"{module}?." in bootstrap, f"{module} is not initialized")

    history = (ROOT / "js/v5/utils/history.js").read_text(encoding="utf-8")
    require('record.main_candidate && typeof record.won === "boolean"' in history, "History utility is not limited to resolved main records")
    require("entityKey(record)" in history, "History utility does not deduplicate by game and selection")

    sparkline = (ROOT / "js/v5/utils/sparkline.js").read_text(encoding="utf-8")
    require('role="img"' in sparkline and "aria-label" in sparkline, "Sparkline accessibility labels are missing")

    router = (ROOT / "js/v5/core/router.js").read_text(encoding="utf-8")
    require("history.pushState" in router and "popstate" in router, "Router lacks browser history support")
    require("#/" in router, "Router does not use static-host-safe hash routes")

    timeline = (ROOT / "js/v5/pages/research-timeline.js").read_text(encoding="utf-8")
    require("示範 slate 不會出現在 Timeline" in timeline, "Timeline empty state must reject demo records")

    theme = (ROOT / "css/v5-theme-p1.css").read_text(encoding="utf-8")
    require(':root[data-theme="dark"]' in theme, "Dark theme tokens are missing")
    require("color-scheme: light" in theme and "color-scheme: dark" in theme, "Theme color schemes are incomplete")

    mobile = (ROOT / "css/v5-mobile-p1.css").read_text(encoding="utf-8")
    require("env(safe-area-inset-bottom)" in mobile, "Mobile safe-area support is missing")
    require("position: fixed" in mobile, "Mobile bottom navigation is missing")

    print("V5.2.1 compact decision strip valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
