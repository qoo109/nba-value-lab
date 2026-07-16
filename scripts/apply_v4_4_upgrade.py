#!/usr/bin/env python3
"""Wire the V4 dual-engine modules and live data status into index.html."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA_JS = ROOT / "js" / "v4-data.js"


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    replacements = {
        "NBA Value Lab V4.3｜V3 × G1 資料接入版": "NBA Value Lab V4.4｜V3 × G1 自動資料層",
        "V4.3・免費資料接入模式": "V4.4・自動資料層啟用",
        "FREE DATA REGISTRY V4.3": "FREE DATA REGISTRY V4.4",
        "V4.3 之後最重要的不是": "V4.4 之後最重要的不是",
        "NBA VALUE LAB V4.3": "NBA VALUE LAB V4.4",
        "readability.css?v=4.3": "readability.css?v=4.4",
    }
    for old, new in replacements.items():
        html = html.replace(old, new)

    module_tags = (
        '<script src="./js/v4-data.js?v=4.4"></script>'
        '<script src="./js/v4-core.js?v=4.4"></script>'
        '<script src="./js/v4-render.js?v=4.4"></script>'
        '<script src="./js/v4-init.js?v=4.4"></script>'
        '<script src="./js/v4-live-data.js?v=4.4"></script>'
    )
    html, count = re.subn(
        r'<script src="\./script\.js\?v=[^"]+"></script>',
        module_tags,
        html,
        count=1,
    )
    if count != 1 and "./js/v4-live-data.js?v=4.4" not in html:
        raise SystemExit("Could not find the legacy script tag in index.html")
    INDEX.write_text(html, encoding="utf-8")

    data_js = DATA_JS.read_text(encoding="utf-8")
    data_js, version_count = re.subn(
        r'const APP_VERSION = "V[^"]+";',
        'const APP_VERSION = "V4.4";',
        data_js,
        count=1,
    )
    if version_count != 1:
        raise SystemExit("Could not update APP_VERSION in js/v4-data.js")
    DATA_JS.write_text(data_js, encoding="utf-8")

    print("V4.4 frontend wiring applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
