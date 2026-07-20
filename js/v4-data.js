"use strict";

const MODEL_VERSION = "V3.1 × G1 FINAL";
const APP_VERSION = "V4.6";
const THEME_KEY = "nba-value-lab-theme";

const gradeInfo = {
  "ㄅ": { label: "ㄅ級・研究候選", tone: "qualified", rule: "核心市場賠率層通過對應安全邊際" },
  "ㄆ": { label: "ㄆ級・條件觀察", tone: "watch", rule: "接近門檻或該市場賠率層尚未開放" },
  "ㄇ": { label: "ㄇ級・市場賠率合理", tone: "fair", rule: "保守優勢為正但緩衝不足" },
  "不支持": { label: "模型不支持", tone: "reject", rule: "保守勝率低於損益平衡" },
  "資料不足": { label: "資料不足", tone: "insufficient", rule: "無法可靠建立勝率" },
};

const games = [
  {
    id: "den-phx", matchup: "DEN @ PHX", start: "10:00", focusSide: "away", coreReady: true,
    away: { code: "DEN", name: "丹佛金塊", odds: 1.58, conservative: 70, neutral: 74, optimistic: 76 },
    home: { code: "PHX", name: "鳳凰城太陽", odds: 2.50, conservative: 24, neutral: 26, optimistic: 30 },
    coverage: 91, confidence: "高", injury: "核心傷病與先發已確認", newsRisk: 0, snapshot: "模擬 T−60m 09:32",
    headline: "V3 與 G1 同時通過，DEN 符合核心主推硬 Gate",
    build: { base: 68, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 2], ["傷病輪替", 1], ["賽程休息", 1], ["戰術風格", 0], ["主場移動", 1]] },
    reasons: ["長期調整後淨效率與半場進攻支持 DEN", "覆蓋率、傷病確認與區間寬度通過核心條件", "目前市場賠率高於最低可接受賠率"],
    risks: ["PHX 大量三分出手可能放大單場變異", "若市場賠率跌破最低接受賠率則取消候選"],
  },
  {
    id: "bos-nyk", matchup: "BOS @ NYK", start: "07:30", focusSide: "home", coreReady: false,
    away: { code: "BOS", name: "波士頓塞爾提克", odds: 2.55, conservative: 23, neutral: 26, optimistic: 28 },
    home: { code: "NYK", name: "紐約尼克", odds: 1.52, conservative: 72, neutral: 74, optimistic: 77 },
    coverage: 83, confidence: "中", injury: "次要輪替待確認", newsRisk: 1, snapshot: "模擬 T−60m 09:30",
    headline: "NYK 通過市場賠率門檻，但覆蓋率未達核心主推標準",
    build: { base: 69, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", 0], ["賽程休息", 1], ["戰術風格", 0], ["主場移動", 2]] },
    reasons: ["主場半場防守與籃板對位略有優勢", "保守勝率通過 V3 與 G1 核心市場賠率門檻"],
    risks: ["資料覆蓋率低於核心主推 85% 門檻", "次要輪替仍需在 T−5m 複核"],
  },
  {
    id: "lal-gsw", matchup: "LAL @ GSW", start: "10:30", focusSide: "home", coreReady: false,
    away: { code: "LAL", name: "洛杉磯湖人", odds: 2.42, conservative: 25, neutral: 28, optimistic: 30 },
    home: { code: "GSW", name: "金州勇士", odds: 1.56, conservative: 70, neutral: 72, optimistic: 75 },
    coverage: 79, confidence: "中", injury: "主力預計出賽", newsRisk: 1, snapshot: "模擬 T−60m 09:27",
    headline: "GSW 通過市場賠率門檻，但資料完整度只適合列優先候選",
    build: { base: 68, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", 0], ["賽程休息", 0], ["戰術風格", 0], ["主場移動", 2]] },
    reasons: ["主場與外線創造能力支持 GSW", "目前市場賠率仍高於最低接受賠率"],
    risks: ["兩隊三分出手量高，單場波動明顯", "資料覆蓋率未達核心主推標準"],
  },
  {
    id: "okc-sas", matchup: "OKC @ SAS", start: "09:00", focusSide: "away", coreReady: false,
    away: { code: "OKC", name: "奧克拉荷馬雷霆", odds: 1.45, conservative: 72, neutral: 75, optimistic: 78 },
    home: { code: "SAS", name: "聖安東尼奧馬刺", odds: 2.80, conservative: 22, neutral: 25, optimistic: 28 },
    coverage: 88, confidence: "高", injury: "傷病已確認", newsRisk: 0, snapshot: "模擬 T−60m 09:35",
    headline: "OKC 勝率較高，但 1.45 的市場賠率仍未達 5pp 研究門檻",
    build: { base: 72, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", 0], ["賽程休息", 0], ["戰術風格", 0], ["主場移動", 1]] },
    reasons: ["長期實力支持 OKC", "防守失誤製造能力具備對位優勢"],
    risks: ["低市場賠率造成損益平衡勝率過高", "需要更高市場賠率才能升級為 ㄅ級"],
  },
  {
    id: "mil-mia", matchup: "MIL @ MIA", start: "08:00", focusSide: "away", coreReady: false,
    away: { code: "MIL", name: "密爾瓦基公鹿", odds: 1.67, conservative: null, neutral: null, optimistic: null },
    home: { code: "MIA", name: "邁阿密熱火", odds: 2.20, conservative: null, neutral: null, optimistic: null },
    coverage: 46, confidence: "不足", injury: "核心狀態未知", newsRisk: 3, snapshot: "未鎖定",
    headline: "核心球員狀態足以改變整場雙向機率",
    build: null, reasons: ["市場賠率與比賽身分已確認"],
    risks: ["核心球員出賽與上場限制皆未確認", "資料覆蓋率低於 50%"],
  },
];

const candidates = games.flatMap((game) => ["away", "home"].map((side) => {
  const opponentSide = side === "home" ? "away" : "home";
  return {
    id: `${game.id}-${side}`,
    game,
    side,
    opponentSide,
    target: game[side],
    opponent: game[opponentSide],
  };
}));

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
let activeFilter = "全部";


// MODEL_REGISTRY_V4_5
const DEFAULT_MODEL_REGISTRY = {
  manifest: {
    schema_version: 2,
    active: {
      V: { engine_id: "V", version: "3.1.1", config: "models/v3/3.1.1/config.json", spec: "models/v3/3.1.1/spec.md" },
      G: { engine_id: "G", version: "1.1.1", config: "models/g1/1.1.1/config.json", spec: "models/g1/1.1.1/spec.md" },
    },
    coordination: { config: "models/coordination/v3.1.1-g1.1.1/config.json" },
  },
  V: {
    engine_id: "V", version: "3.1.1",
    core_odds_scope: { min: 1.40, max: 1.60, semantics: "b_eligible_core_range_only" },
    required_margin_pp: 5,
    early_preview_extra_margin_pp: 0,
  },
  G: {
    engine_id: "G", version: "1.1.1",
    price_bands: [
      { min: 1.01, max: 1.20, min_inclusive: true, max_inclusive: false, label: "極低市場賠率層", required_margin_pp: 5, eligible: false },
      { min: 1.20, max: 1.35, min_inclusive: true, max_inclusive: false, label: "低市場賠率研究層", required_margin_pp: 7, eligible: false },
      { min: 1.35, max: 1.60, min_inclusive: true, max_inclusive: true, label: "偏熱門核心層", required_margin_pp: 5, eligible: true },
      { min: 1.60, max: 2.20, min_inclusive: false, max_inclusive: true, label: "接近盤／小冷核心層", required_margin_pp: 6, eligible: true },
      { min: 2.20, max: 3.50, min_inclusive: false, max_inclusive: true, label: "中高市場賠率研究層", required_margin_pp: 8, eligible: false },
      { min: 3.50, max: 100, min_inclusive: false, max_inclusive: true, label: "高波動研究層", required_margin_pp: 99, eligible: false },
    ],
    grading: { edge_support_min_pp: 0, b_gap_min_pp: 0, watch_gap_min_pp: -3 },
    core_gate: {
      coverage_min_pct: 85,
      interval_width_max_pp: 6,
      threshold_buffer_min_pp: 1,
      news_risk_max: 1,
      confidence_required: "高",
      comparison_sources_min: 3,
      model_market_gap_review_pp: 5,
      core_max: 3,
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
        <h2>市場賠率價值與最低接受賠率</h2>
        <dl>
          <div><dt>核心市場賠率範圍</dt><dd>${(modelV().core_odds_scope || modelV().odds_scope).min.toFixed(2)}～${(modelV().core_odds_scope || modelV().odds_scope).max.toFixed(2)}</dd></div>
          <div><dt>安全邊際</dt><dd>${modelV().required_margin_pp.toFixed(1)}pp</dd></div>
          <div><dt>預覽限制</dt><dd>T−24h 原則最高 ㄆ級</dd></div>
        </dl>
      </article>
      <article class="registry-card ${loaded ? "licensed" : "restricted"}">
        <div><span>G ENGINE</span><em>G${modelG().version}</em></div>
        <h2>資料 Gate 與優先序</h2>
        <dl>
          <div><dt>核心覆蓋率</dt><dd>≥ ${modelG().core_gate.coverage_min_pct}%</dd></div>
          <div><dt>區間寬度</dt><dd>≤ ${modelG().core_gate.interval_width_max_pp}pp</dd></div>
          <div><dt>主要場次</dt><dd>${modelG().core_gate.core_max} 場上限</dd></div>
        </dl>
      </article>
    </div>`;
  if (hero) hero.insertAdjacentElement("afterend", section);
  else panel.prepend(section);
}
