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
    "css/v5-density-v53.css": 360,
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
    "css/v5-density-v53.css",
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
    require('dataset.appVersion = v5Ready ? "V5.3.1"' in init_text, "V5.3.1 app version is not active")
    require("dashboard.js?v=5.3.1" in init_text, "V5.3.1 dashboard cache version is missing")
    require("cards.js?v=5.3.1" in init_text, "V5.3.1 cards cache version is missing")
    require("v5-density-v53.css?v=5.3" in init_text, "V5.3 density stylesheet cache version is missing")
    require("window.showDetail = open" in (ROOT / "js/v5/components/drawer.js").read_text(encoding="utf-8"), "Drawer does not replace showDetail")

    cards = (ROOT / "js/v5/components/cards.js").read_text(encoding="utf-8")
    require("window.renderTopPick" in cards, "V5 cards do not replace top-pick renderer")
    require("window.renderCards" in cards, "V5 cards do not replace candidate renderer")
    require("v52-compact-decision" not in cards, "Decision strip must not remain inside the main-pick renderer")

    compact = (ROOT / "css/v5-compact-decision.css").read_text(encoding="utf-8")
    require("grid-template-columns: minmax(0, 1fr) !important" in compact, "Top-pick layout is not forced to one column")
    require("white-space: nowrap" in compact, "Decision strip is not kept to one line")

    density = (ROOT / "css/v5-density-v53.css").read_text(encoding="utf-8")
    for token in (
        ".v5-ui .panel",
        ".v5-ui .v5-main-card",
        ".v5-ui .v5-candidate-card",
        ".v5-ui .market-table td",
        ".v5-ui .v5-disclosure > summary",
        "@media (max-width: 719px)",
    ):
        require(token in density, f"V5.3 density rule missing: {token}")
    require("min-height: 258px" in density, "Main card height was not compacted")
    require("padding: 9px 10px" in density, "Market table rows were not compacted")
    require("--v53-gap-page" in density and "--v53-pad-card" in density, "V5.3 spacing tokens are missing")

    dashboard = (ROOT / "js/v5/pages/dashboard.js").read_text(encoding="utf-8")
    dashboard_order = [
        "decisionStrip,",
        'analysis.querySelector(".date-rail")',
        'analysis.querySelector(".timing-strip")',
        'analysis.querySelector(".games-section")',
        "market,",
        'analysis.querySelector(".hero-grid")',
        'sectionShell(analysis.querySelector(".calculator"))',
        'analysis.querySelector(".v5-model-disclosure")',
        'sectionShell(analysis.querySelector(".source-card"))',
        'sectionShell(analysis.querySelector(".weights-card"))',
        'sectionShell(analysis.querySelector(".pipeline-card"))',
    ]
    order_positions = [dashboard.index(token) for token in dashboard_order]
    require(order_positions == sorted(order_positions), "Dashboard sections are not in decision-candidate-market-result order")
    require('strip.id = "v531DecisionStrip"' in dashboard, "Top decision strip id is missing")
    require('className = "v5-hero-heading v52-compact-decision"' in dashboard, "Top decision strip styling is missing")
    require("今日決策" in dashboard and "今日主要場次" in dashboard, "Top decision wording is missing")
    require("if (market?.matches(\"details\")) market.open = true" in dashboard, "Market table must open by default")
    require('document.documentElement.dataset.visualDensity = "balanced"' in dashboard, "Balanced density marker is missing")
    require('document.documentElement.dataset.uiVersion = "5.3.1"' in dashboard, "V5.3.1 UI version is missing")

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

    print("V5.3.1 top decision strip valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
