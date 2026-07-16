#!/usr/bin/env python3
"""Migrate the V4 frontend from hard-coded model thresholds to Model Registry."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "js" / "v4-data.js"
CORE = ROOT / "js" / "v4-core.js"
INIT = ROOT / "js" / "v4-init.js"
LIVE = ROOT / "js" / "v4-live-data.js"
MARKER = "// MODEL_REGISTRY_V4_5"

REGISTRY_JS = r'''

// MODEL_REGISTRY_V4_5
const DEFAULT_MODEL_REGISTRY = {
  manifest: {
    schema_version: 1,
    active: {
      V: { engine_id: "V", version: "3.0", config: "models/v3/3.0/config.json", spec: "models/v3/3.0/spec.md" },
      G: { engine_id: "G", version: "1.0", config: "models/g1/1.0/config.json", spec: "models/g1/1.0/spec.md" },
    },
  },
  V: {
    engine_id: "V", version: "3.0",
    odds_scope: { min: 1.40, max: 1.60 },
    required_margin_pp: 5,
    early_preview_extra_margin_pp: 2,
  },
  G: {
    engine_id: "G", version: "1.0",
    price_bands: [
      { min: 1.20, max: 1.35, min_inclusive: true, max_inclusive: false, label: "低價研究層", required_margin_pp: 7, eligible: false },
      { min: 1.35, max: 1.60, min_inclusive: true, max_inclusive: true, label: "偏熱門核心層", required_margin_pp: 5, eligible: true },
      { min: 1.60, max: 2.20, min_inclusive: false, max_inclusive: true, label: "接近盤／小冷核心層", required_margin_pp: 6, eligible: true },
      { min: 2.20, max: 3.50, min_inclusive: false, max_inclusive: true, label: "中高價研究層", required_margin_pp: 8, eligible: false },
    ],
    grading: { watch_gap_min_pp: -3 },
    core_gate: {
      coverage_min_pct: 85,
      interval_width_max_pp: 6,
      threshold_buffer_min_pp: 1,
      news_risk_max: 1,
      confidence_required: "高",
      core_max: 1,
      priority_max: 2,
    },
  },
};

let runtimeModelRegistry = JSON.parse(JSON.stringify(DEFAULT_MODEL_REGISTRY));
let modelRegistryLoadState = { status: "fallback", error: null, loaded_at: null };

function modelV() { return runtimeModelRegistry.V || DEFAULT_MODEL_REGISTRY.V; }
function modelG() { return runtimeModelRegistry.G || DEFAULT_MODEL_REGISTRY.G; }
function activeModelLabel() { return `V${modelV().version} × G${modelG().version}`; }

function validateLoadedModelConfig(engine, config) {
  if (!config || typeof config !== "object") throw new Error(`${engine} config must be an object`);
  if (config.engine_id !== engine) throw new Error(`${engine} config engine_id mismatch`);
  if (!config.version) throw new Error(`${engine} config missing version`);
  if (engine === "G" && !Array.isArray(config.price_bands)) throw new Error("G config missing price_bands");
  return config;
}

async function fetchJsonNoStore(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

async function loadModelRegistry() {
  try {
    const manifest = await fetchJsonNoStore("./models/manifest.json");
    const vEntry = manifest?.active?.V;
    const gEntry = manifest?.active?.G;
    if (!vEntry?.config || !gEntry?.config) throw new Error("manifest active V/G config paths are missing");
    const [vConfig, gConfig] = await Promise.all([
      fetchJsonNoStore(`./${vEntry.config}`),
      fetchJsonNoStore(`./${gEntry.config}`),
    ]);
    runtimeModelRegistry = {
      manifest,
      V: validateLoadedModelConfig("V", vConfig),
      G: validateLoadedModelConfig("G", gConfig),
    };
    modelRegistryLoadState = { status: "loaded", error: null, loaded_at: new Date().toISOString() };
  } catch (error) {
    runtimeModelRegistry = JSON.parse(JSON.stringify(DEFAULT_MODEL_REGISTRY));
    modelRegistryLoadState = { status: "fallback", error: String(error), loaded_at: new Date().toISOString() };
    console.warn("NBA Value Lab model registry fallback:", error);
  }
  document.documentElement.dataset.modelRegistry = modelRegistryLoadState.status;
  document.documentElement.dataset.vModelVersion = modelV().version;
  document.documentElement.dataset.gModelVersion = modelG().version;
  return runtimeModelRegistry;
}

function renderModelRegistryStatus() {
  const panel = document.querySelector('[data-panel="sources"]');
  if (!panel || document.querySelector("#modelRegistryStatus")) return;
  const hero = panel.querySelector(".sources-hero");
  const section = document.createElement("section");
  section.id = "modelRegistryStatus";
  section.className = "storage-card";
  const loaded = modelRegistryLoadState.status === "loaded";
  section.innerHTML = `
    <div>
      <span class="eyebrow">MODEL REGISTRY</span>
      <h2>${activeModelLabel()}・${loaded ? "已從 GitHub 設定載入" : "使用內建安全預設"}</h2>
      <p>規格文件供人閱讀，config.json 供網站執行。更新 manifest 與設定後，GitHub Actions 會先驗證，再由 Pages 自動發布。</p>
    </div>
    <div class="registry-grid">
      <article class="registry-card ${loaded ? "licensed" : "restricted"}">
        <div><span>V ENGINE</span><em>V${modelV().version}</em></div>
        <h2>價格價值與最低接受賠率</h2>
        <dl>
          <div><dt>核心賠率範圍</dt><dd>${modelV().odds_scope.min.toFixed(2)}～${modelV().odds_scope.max.toFixed(2)}</dd></div>
          <div><dt>安全邊際</dt><dd>${modelV().required_margin_pp.toFixed(1)}pp</dd></div>
          <div><dt>21:00 額外邊際</dt><dd>+${modelV().early_preview_extra_margin_pp.toFixed(1)}pp</dd></div>
        </dl>
      </article>
      <article class="registry-card ${loaded ? "licensed" : "restricted"}">
        <div><span>G ENGINE</span><em>G${modelG().version}</em></div>
        <h2>資料 Gate 與優先序</h2>
        <dl>
          <div><dt>核心覆蓋率</dt><dd>≥ ${modelG().core_gate.coverage_min_pct}%</dd></div>
          <div><dt>區間寬度</dt><dd>≤ ${modelG().core_gate.interval_width_max_pp}pp</dd></div>
          <div><dt>核心／優先</dt><dd>${modelG().core_gate.core_max}／${modelG().core_gate.priority_max}</dd></div>
        </dl>
      </article>
    </div>`;
  if (hero) hero.insertAdjacentElement("afterend", section);
  else panel.prepend(section);
}
'''

NEW_PRICE_BAND = r'''function bandContains(band, odds) {
  const aboveMin = band.min_inclusive === false ? odds > band.min : odds >= band.min;
  const belowMax = band.max_inclusive === false ? odds < band.max : odds <= band.max;
  return aboveMin && belowMax;
}
function priceBand(odds) {
  if (!Number.isFinite(odds) || odds <= 1) return { label: "無效價格", margin: null, eligible: false };
  const configured = modelG().price_bands.find((band) => bandContains(band, odds));
  if (configured) return { label: configured.label, margin: configured.required_margin_pp, eligible: Boolean(configured.eligible) };
  if (odds < modelG().price_bands[0].min) return { label: "極低價層", margin: null, eligible: false };
  return { label: "高波動研究層", margin: null, eligible: false };
}'''

NEW_GATE = r'''function mainGateEligible(candidate) {
  const game = candidate.game;
  const gap = thresholdGap(candidate);
  const gate = modelG().core_gate;
  return candidateGrade(candidate) === "ㄅ"
    && game.coreReady === true
    && game.confidence === gate.confidence_required
    && game.coverage >= gate.coverage_min_pct
    && intervalWidth(candidate) !== null
    && intervalWidth(candidate) <= gate.interval_width_max_pp
    && gap !== null
    && gap >= gate.threshold_buffer_min_pp
    && game.newsRisk <= gate.news_risk_max;
}'''

NEW_SELECTION = r'''function selectionBoard() {
  const qualified = rankedQualified();
  const gate = modelG().core_gate;
  const core = gate.core_max > 0 ? qualified.find(mainGateEligible) || null : null;
  const priority = qualified.filter((candidate) => !core || candidate.id !== core.id).slice(0, Math.max(0, gate.priority_max));
  const general = qualified.filter((candidate) => !core || candidate.id !== core.id)
    .filter((candidate) => !priority.some((item) => item.id === candidate.id));
  return { core, priority, general, qualified };
}'''

NEW_INIT = r'''async function init() {
  loadReadabilityStyles();
  await loadModelRegistry();
  updateVersionText();
  applyTheme(document.documentElement.dataset.theme || "light");
  renderTopPick();
  renderTable();
  renderCards();
  renderCalculatorOptions();
  renderModelRegistryStatus();
  bindEvents();
  updateCalculator(true);
  document.documentElement.dataset.modelVersion = activeModelLabel();
  document.documentElement.dataset.appVersion = APP_VERSION;
}

init().catch((error) => {
  console.error("NBA Value Lab initialization failed:", error);
  const header = document.querySelector(".header-status");
  if (header) header.innerHTML = '<span class="status-dot"></span>V4.5・初始化失敗';
});'''


def replace_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"Could not migrate {label}; matches={count}")
    return updated


def main() -> int:
    data = DATA.read_text(encoding="utf-8")
    data = re.sub(r'const APP_VERSION = "V[^"]+";', 'const APP_VERSION = "V4.5";', data, count=1)
    data = re.sub(r'const MODEL_VERSION = "[^"]+";', 'const MODEL_VERSION = "V × G Registry";', data, count=1)
    if MARKER not in data:
        data += REGISTRY_JS
    DATA.write_text(data, encoding="utf-8")

    core = CORE.read_text(encoding="utf-8")
    core = replace_once(
        core,
        r'function updateVersionText\(\) \{.*?\n\}',
        'function updateVersionText() {\n  document.title = `NBA Value Lab ${APP_VERSION}｜${activeModelLabel()}`;\n  const footerVersion = document.querySelector("footer > span:first-child");\n  if (footerVersion) footerVersion.textContent = `NBA VALUE LAB ${APP_VERSION}`;\n}',
        "updateVersionText",
        re.S,
    )
    core = replace_once(core, r'function priceBand\(odds\) \{.*?\n\}', NEW_PRICE_BAND, "priceBand", re.S)
    core = core.replace('game.newsRisk <= 1 && game.confidence !== "低"', 'game.newsRisk <= modelG().core_gate.news_risk_max && game.confidence !== "低"')
    core = core.replace('if (gap !== null && gap >= -3) return "ㄆ";', 'if (gap !== null && gap >= modelG().grading.watch_gap_min_pp) return "ㄆ";')
    core = replace_once(
        core,
        r'function engineLabel\(candidate\) \{.*?\n\}',
        'function engineLabel(candidate) {\n  const odds = candidate.target.odds;\n  const scope = modelV().odds_scope;\n  return Number.isFinite(odds) && odds >= scope.min && odds <= scope.max ? `V${modelV().version}＋G${modelG().version}` : `G${modelG().version}`;\n}',
        "engineLabel",
        re.S,
    )
    core = replace_once(core, r'function mainGateEligible\(candidate\) \{.*?\n\}', NEW_GATE, "mainGateEligible", re.S)
    core = replace_once(core, r'function selectionBoard\(\) \{.*?\n\}', NEW_SELECTION, "selectionBoard", re.S)
    CORE.write_text(core, encoding="utf-8")

    init = INIT.read_text(encoding="utf-8")
    init = replace_once(init, r'function init\(\) \{.*?\n\}\n\ninit\(\);', NEW_INIT, "init", re.S)
    INIT.write_text(init, encoding="utf-8")

    live = LIVE.read_text(encoding="utf-8")
    live = live.replace("V4.4", "V4.5")
    LIVE.write_text(live, encoding="utf-8")

    print("V4.5 Model Registry frontend migration applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
