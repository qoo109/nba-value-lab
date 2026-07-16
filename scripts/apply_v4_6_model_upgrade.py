#!/usr/bin/env python3
"""Wire V3.1 and G1 final coordination into the static frontend."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA_JS = ROOT / "js" / "v4-data.js"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        if new in text:
            return text
        raise SystemExit(f"Missing {label}: {old}")
    return text.replace(old, new, 1)


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    html = html.replace("NBA Value Lab V4.5", "NBA Value Lab V4.6")
    html = html.replace("V4.5・Model Registry", "V4.6・V3.1 × G1 FINAL")
    html = html.replace("V4.5 MODEL REGISTRY", "V4.6 MODEL COORDINATION")
    html = html.replace("NBA VALUE LAB V4.5", "NBA VALUE LAB V4.6")
    html = html.replace("readability.css?v=4.5", "readability.css?v=4.6")
    html = html.replace("./js/v4-data.js?v=4.5", "./js/v4-data.js?v=4.6")
    html = html.replace("./js/v4-core.js?v=4.5", "./js/v4-core.js?v=4.6")
    html = html.replace("./js/v4-render.js?v=4.5", "./js/v4-render.js?v=4.6")
    html = html.replace("./js/v4-init.js?v=4.5", "./js/v4-init.js?v=4.6")
    html = html.replace("./js/v4-live-data.js?v=4.5", "./js/v4-live-data.js?v=4.6")

    patch_tag = '<script src="./js/v4-6-model-coordination.js?v=4.6"></script>'
    init_tag = '<script src="./js/v4-init.js?v=4.6"></script>'
    if patch_tag not in html:
        html = replace_once(html, init_tag, patch_tag + init_tag, "V4.6 init script tag")
    INDEX.write_text(html, encoding="utf-8")

    data_js = DATA_JS.read_text(encoding="utf-8")
    data_js, count = re.subn(r'const APP_VERSION = "V[^"]+";', 'const APP_VERSION = "V4.6";', data_js, count=1)
    if count != 1:
        raise SystemExit("Could not update APP_VERSION")
    data_js = data_js.replace('const MODEL_VERSION = "V × G Registry";', 'const MODEL_VERSION = "V3.1 × G1 FINAL";')
    DATA_JS.write_text(data_js, encoding="utf-8")

    print("V4.6 model coordination wiring applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
