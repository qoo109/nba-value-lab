"use strict";

// Scheduled G1.2.0 support. Active G1.1.1 remains primary until the
// Registry is switched after the governed 2026-27 T-60 trigger.
let runtimeScheduledGConfig = null;
let runtimeScheduledCoordination = null;
let scheduledGLoadState = { status: "not_loaded", error: null };

const legacyLoadModelRegistryG120 = loadModelRegistry;
const legacyGDecisionG120 = gDecision;
const legacyDecisionPillsG120 = decisionPills;
const legacyRefreshRuleDownloadsG120 = refreshRuleDownloads;
const legacyRenderModelRegistryStatusG120 = renderModelRegistryStatus;

function g120Segment(config, odds) {
  if (!Number.isFinite(odds) || odds <= 1) return { id: "invalid", label: "無效市場賠率", eligible: false, required_margin_pp: null, maximum_conclusion: "資料不足" };
  return config.price_bands.find((segment) => segmentContains(segment, odds)) || { id: "outside", label: "範圍外", eligible: false, required_margin_pp: null, maximum_conclusion: "只記錄" };
}

function g120Decision(candidate, odds = candidate.target.odds, config = modelG()) {
  const segment = g120Segment(config, odds);
  const pRaw = candidate.target.conservative;
  const risk = candidate.game.newsRisk ?? candidate.game.news_risk_level ?? 0;
  const insufficient = candidate.game.confidence === "不足" || candidate.game.confidence === "資料不足" || risk >= 3 || pRaw === null;
  const policy = config.ev_policy;
  if (!policy || insufficient || !Number.isFinite(odds) || odds <= 1) {
    return { engine: "G", grade: "資料不足", conclusion: "資料不足", segment, margin: null, gap: null, minimumOdds: null, decisionMetric: "conservative_ev", conservativeEv: null, ppGuardPass: false };
  }
  const p = pRaw > 1 ? pRaw / 100 : pRaw;
  const ev = p * odds - 1;
  const edgePP = (p - 1 / odds) * 100;
  const guardPass = edgePP + 1e-12 >= policy.pp_guard_min;
  let grade, conclusion, threshold;
  if (ev <= 0) { grade = "不支持"; conclusion = "模型不支持"; threshold = 0; }
  else if (!guardPass) { grade = "ㄆ"; conclusion = "觀察・PP 安全線未通過"; threshold = policy.candidate_min_ev; }
  else if (ev < policy.candidate_min_ev) { grade = "ㄆ"; conclusion = "觀察・EV 未達 5%"; threshold = policy.candidate_min_ev; }
  else if (ev < policy.grade_p_min_ev) { grade = "ㄇ"; conclusion = "ㄇ級・最低正 EV"; threshold = policy.grade_m_min_ev; }
  else if (ev < policy.grade_b_min_ev) { grade = "ㄆ"; conclusion = "ㄆ級・EV 觀察候選"; threshold = policy.grade_p_min_ev; }
  else { grade = "ㄅ"; conclusion = "ㄅ級・EV 核心候選"; threshold = policy.grade_b_min_ev; }
  if (grade === "ㄅ" && (risk === 2 || candidate.game.confidence === "低")) { grade = "ㄆ"; conclusion = "ㄆ級・風險降級"; threshold = policy.grade_p_min_ev; }
  if (!["資料不足", "不支持"].includes(grade)) {
    if (segment.required_margin_pp == null) { grade = "ㄆ"; conclusion = segment.maximum_conclusion || "只記錄"; }
    else if (!segment.eligible && grade === "ㄅ") { grade = "ㄆ"; conclusion = segment.maximum_conclusion || "ㄆ級・延伸研究"; }
  }
  const surplusPP = ((grade === "ㄅ" ? ev - policy.grade_b_min_ev : ev - threshold) * 100);
  const minimumOdds = p > 0 ? (1 + (threshold || policy.candidate_min_ev)) / p : null;
  return {
    engine: "G", grade, conclusion, segment,
    margin: (threshold || policy.candidate_min_ev) * 100,
    gap: surplusPP,
    minimumOdds,
    decisionMetric: "conservative_ev",
    conservativeEv: ev,
    edgePP,
    ppGuardPass: guardPass,
    ppGuardMinPP: policy.pp_guard_min,
    ppGuardSurplusPP: edgePP - policy.pp_guard_min,
    evCandidate: ev >= policy.candidate_min_ev && guardPass && Boolean(segment.eligible),
  };
}

gDecision = function routedGDecision(candidate, odds = candidate.target.odds) {
  return modelG().ev_policy ? g120Decision(candidate, odds, modelG()) : legacyGDecisionG120(candidate, odds);
};

function scheduledGDecision(candidate, odds = candidate.target.odds) {
  return runtimeScheduledGConfig ? g120Decision(candidate, odds, runtimeScheduledGConfig) : null;
}

loadModelRegistry = async function loadRegistryWithScheduledG() {
  const result = await legacyLoadModelRegistryG120();
  const manifest = runtimeModelRegistry.manifest || {};
  const gEntry = manifest.scheduled_next?.G;
  const coordinationEntry = manifest.scheduled_next?.coordination;
  try {
    if (gEntry?.config) {
      const config = await fetchJsonNoStore(`./${gEntry.config}`);
      runtimeScheduledGConfig = validateLoadedModelConfig("G", config, gEntry);
    }
    if (coordinationEntry?.config) runtimeScheduledCoordination = await fetchJsonNoStore(`./${coordinationEntry.config}`);
    scheduledGLoadState = { status: runtimeScheduledGConfig ? "loaded" : "not_scheduled", error: null };
  } catch (error) {
    runtimeScheduledGConfig = null;
    runtimeScheduledCoordination = null;
    scheduledGLoadState = { status: "error", error: String(error) };
    console.warn("Unable to load scheduled G1.2.0:", error);
  }
  document.documentElement.dataset.scheduledG = scheduledGLoadState.status;
  return result;
};

decisionPills = function decisionPillsWithScheduledG(candidate) {
  const current = legacyDecisionPillsG120(candidate);
  if (modelG().ev_policy || !runtimeScheduledGConfig) return current;
  const next = scheduledGDecision(candidate);
  const ev = next?.conservativeEv == null ? "—" : `${(next.conservativeEv * 100).toFixed(1)}%`;
  return `${current}<div class="engine-tags g120-preview"><span>NEXT G1.2.0：${next.conclusion}・EV ${ev}・PP ${next.ppGuardPass ? "PASS" : "FAIL"}</span></div>`;
};

refreshRuleDownloads = function refreshDownloadsWithScheduledG(panel, manifest) {
  legacyRefreshRuleDownloadsG120(panel, manifest);
  const container = panel.querySelector(".downloads");
  const entry = manifest.scheduled_next?.G;
  if (container && entry?.spec) upsertDownloadLink(container, "g120-spec", `下載 G${entry.version} EV 規格`, `./${entry.spec}`);
};

renderModelRegistryStatus = function renderRegistryWithScheduledG() {
  legacyRenderModelRegistryStatusG120();
  const section = document.querySelector("#modelRegistryStatus");
  const grid = section?.querySelector(".registry-grid");
  if (!grid || grid.querySelector("[data-scheduled-g120]")) return;
  const entry = runtimeModelRegistry.manifest?.scheduled_next?.G;
  if (!entry) return;
  const article = document.createElement("article");
  article.className = "registry-card licensed";
  article.dataset.scheduledG120 = "true";
  article.innerHTML = `<div><span>NEXT G ENGINE</span><em>G${entry.version}</em></div><h2>EV-primary・2026-27 T−60 啟用</h2><dl>
    <div><dt>候選最低 EV</dt><dd>5%</dd></div><div><dt>ㄅ級</dt><dd>EV ≥ 10%</dd></div><div><dt>PP 安全線</dt><dd>≥ 2pp</dd></div><div><dt>目前角色</dt><dd>${modelG().ev_policy ? "PRIMARY" : "SCHEDULED SHADOW"}</dd></div>
  </dl>`;
  grid.append(article);
};

window.g120Decision = g120Decision;
window.scheduledGDecision = scheduledGDecision;
