#!/usr/bin/env python3
"""Wire V3.1 and G1 final coordination into the static frontend."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA_JS = ROOT / "js" / "v4-data.js"


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    html = re.sub(r"NBA Value Lab V4\.[0-9]+[^<\"]*", "NBA Value Lab V4.6｜V3.1 × G1 FINAL", html, count=1)
    html = re.sub(r"V4\.[0-9]+・[^<]+", "V4.6・V3.1 × G1 FINAL", html, count=1)
    html = html.replace("V3 判斷價值，G1 決定可靠性與優先序", "V3.1 與 G1 分開判定，由協調層統整")
    html = html.replace("V3 × G1", "V3.1 × G1")
    html = html.replace("NBA VALUE LAB V4.4", "NBA VALUE LAB V4.6")
    html = html.replace("NBA VALUE LAB V4.5", "NBA VALUE LAB V4.6")
    html = re.sub(r"readability\.css\?v=4\.[0-9]+", "readability.css?v=4.6", html)

    for script_name in ("v4-data", "v4-core", "v4-render", "v4-init", "v4-live-data"):
        html = re.sub(rf"\./js/{script_name}\.js\?v=4\.[0-9]+", f"./js/{script_name}.js?v=4.6", html)

    patch_tag = '<script src="./js/v4-6-model-coordination.js?v=4.6"></script>'
    if patch_tag not in html:
        init_pattern = r'(<script src="\./js/v4-init\.js\?v=4\.6"></script>)'
        html, count = re.subn(init_pattern, patch_tag + r"\1", html, count=1)
        if count != 1:
            raise SystemExit("Could not find v4-init script tag")
    INDEX.write_text(html, encoding="utf-8")

    data_js = DATA_JS.read_text(encoding="utf-8")
    data_js, count = re.subn(r'const APP_VERSION = "V[^"]+";', 'const APP_VERSION = "V4.6";', data_js, count=1)
    if count != 1:
        raise SystemExit("Could not update APP_VERSION")
    data_js = re.sub(r'const MODEL_VERSION = "[^"]+";', 'const MODEL_VERSION = "V3.1 × G1 FINAL";', data_js, count=1)
    DATA_JS.write_text(data_js, encoding="utf-8")

    print("V4.6 model coordination wiring applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
