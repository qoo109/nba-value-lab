"use strict";

// V4.6 keeps V3.1 and G1 independent. It does not average probabilities or
// silently collapse the two engines into one grade.
let runtimeCoordination = null;

const FALLBACK_V31 = {
  engine_id: "V", version: "3.1", revision_id: "V3.1-20260716",
  odds_scope: { min: 1.40, max: 1.60 }, required_margin_pp: 5,
  preview_policy: { snapshot: "T-24h", maximum_grade: "ㄆ", extra_margin_pp: null },
  price_policy: {
    price_segments: [
      { id: "extreme_low_excluded", min: 1.20, max: 1.30, min_inclusive: true, max_inclusive: false, label: "極低價格區", required_margin_pp: 5, eligible_b: false, maximum_conclusion: "排除・極低價格" },
      { id: "low_extension", min: 1.30, max: 1.40, min_inclusive: true, max_inclusive: false, label: "低價延伸研究區", required_margin_pp: 5, eligible_b: false, maximum_conclusion: "ㄆ級・延伸研究" },
      { id: "core", min: 1.40, max: 1.60, min_inclusive: true, max_inclusive: true, label: "核心決策區", required_margin_pp: 5, eligible_b: true, maximum_conclusion: "ㄅ級・研究候選" },
      { id: "high_extension", min: 1.60, max: 1.75, min_inclusive: false, max_inclusive: true, label: "高價延伸研究區", required_margin_pp: 5, eligible_b: false, maximum_conclusion: "ㄆ級・延伸研究" },
      { id: "separate_calibration", min: 1.75, max: 2.00, min_inclusive: false, max_inclusive: false, label: "另行校準區", required_margin_pp: 5, eligible_b: false, maximum_conclusion: "另行校準" },
    ],
    outside_conclusion: "範圍外",
  },
  grading: { watch_gap_min_pp: -3, risk_2_maximum_grade: "ㄆ", low_confidence_maximum_grade: "ㄆ" },
};

const FALLBACK_G1_FINAL = {
  engine_id: "G", version: "1.0", revision_id: "G1-FINAL-20260716",
  price_bands: [
    { id: "extreme_low", min: 1.01, max: 1.20, min_inclusive: true, max_inclusive: false, label: "極低價層", required_margin_pp: null, eligible: false, maximum_conclusion: "只記錄" },
    { id: "low_research", min: 1.20, max: 1.35, min_inclusive: true, max_inclusive: false, label: "低價研究層", required_margin_pp: 7, eligible: false, maximum_conclusion: "ㄆ級・延伸研究" },
    { id: "favorite_core", min: 1.35, max: 1.60, min_inclusive: true, max_inclusive: true, label: "偏熱門核心層", required_margin_pp: 5, eligible: true, maximum_conclusion: "ㄅ級・研究候選" },
    { id: "near_even_core", min: 1.60, max: 2.20, min_inclusive: false, max_inclusive: true, label: "接近盤／小冷核心層", required_margin_pp: 6, eligible: true, maximum_conclusion: "ㄅ級・研究候選" },
    { id: "medium_high_extension", min: 2.20, max: 3.50, min_inclusive: false, max_inclusive: true, label: "中高價研究層", required_margin_pp: 8, eligible: false, maximum_conclusion: "ㄆ級・延伸研究" },
    { id: "high_volatility", min: 3.50, max: null, min_inclusive: false, max_inclusive: false, label: "高波動研究層", required_margin_pp: null, eligible: false, maximum_conclusion: "只記錄" },
  ],
  grading: { watch_gap_min_pp: -3 },
  core_gate: {
    coverage_min_pct: 85, interval_width_max_pp: 6, comparison_sources_min: 3,
    threshold_buffer_min_pp: 1, model_market_gap_max_pp: 5,
    independent_evidence_min_if_gap_exceeded: 2, news_risk_max: 1,
    confidence_required: "高", core_max: 1,
  },
  selection: { official_main_max: 1, allow_zero_main: true, ui_priority_candidates_max: 2, ui_priority_is_official_g1_grade: false },
};

const FALLBACK_COORDINATION = {
  coordination_id: "V3.1_X_G1-FINAL-20260716", version: "1.0.0",
  no_probability_blending: true,
  combined_policy: {
    v_core_and_g_core_requires_both_pass: true,
    dual_side_conflict_blocks_combined_b: true,
    formal_stake_fraction: 0,
  },
  ui_policy: { official_main_max: 1, priority_display_max: 2, priority_display_is_not_official_g1_grade: true },
};

function coordinationPolicy() { return runtimeCoordination || FALLBACK_COORDINATION; }
function activeModelLabel() { return `V${modelV().version} × G${modelG().version}`; }
function activeRevisionLabel() { return `${modelV().revision_id || `V${modelV().version}`}・${modelG().revision_id || `G${modelG().version}`}`; }

function validateLoadedModelConfig(engine, config) {
  if (!config || typeof config !== "object") throw new Error(`${engine} config must be an object`);
  if (config.engine_id !== engine) throw new Error(`${engine} config engine_id mismatch`);
  if (!config.version) throw new Error(`${engine} config missing version`);
  if (engine === "V" && !Array.isArray(config.price_policy?.price_segments)) throw new Error("V3.1 config missing price segments");
  if (engine === "G" && !Array.isArray(config.price_bands)) throw new Error("G1 config missing price bands");
  return config;
}

async function loadModelRegistry() {
  try {
    const manifest = await fetchJsonNoStore("./models/manifest.json");
    const vEntry = manifest?.active?.V;
    const gEntry = manifest?.active?.G;
    const coordinationEntry = manifest?.coordination;
    if (!vEntry?.config || !gEntry?.config) throw new Error("manifest active V/G config paths are missing");
    const requests = [
      fetchJsonNoStore(`./${vEntry.config}`),
      fetchJsonNoStore(`./${gEntry.config}`),
      coordinationEntry?.config ? fetchJsonNoStore(`./${coordinationEntry.config}`) : Promise.resolve(FALLBACK_COORDINATION),
    ];
    const [vConfig, gConfig, coordinationConfig] = await Promise.all(requests);
    runtimeModelRegistry = {
      manifest,
      V: validateLoadedModelConfig("V", vConfig),
      G: validateLoadedModelConfig("G", gConfig),
    };
    runtimeCoordination = coordinationConfig;
    modelRegistryLoadState = { status: "loaded", error: null, loaded_at: new Date().toISOString() };
  } catch (error) {
    runtimeModelRegistry = { manifest: {}, V: FALLBACK_V31, G: FALLBACK_G1_FINAL };
    runtimeCoordination = FALLBACK_COORDINATION;
    modelRegistryLoadState = { status: "fallback", error: String(error), loaded_at: new Date().toISOString() };
    console.warn("NBA Value Lab V4.6 registry fallback:", error);
  }
  document.documentElement.dataset.modelRegistry = modelRegistryLoadState.status;
  document.documentElement.dataset.vModelVersion = modelV().version;
  document.documentElement.dataset.gModelVersion = modelG().version;
  document.documentElement.dataset.coordinationVersion = coordinationPolicy().version;
  return runtimeModelRegistry;
}

function segmentContains(segment, odds) {
  const above = segment.min_inclusive === false ? odds > segment.min : odds >= segment.min;
  const below = segment.max == null ? true : (segment.max_inclusive === false ? odds < segment.max : odds <= segment.max);
  return above && below;
}

function vPriceSegment(odds) {
  if (!Number.isFinite(odds) || odds <= 1) return { id: "invalid", label: "無效價格", required_margin_pp: null, eligible_b: false, maximum_conclusion: "價格資料不足" };
  return modelV().price_policy.price_segments.find((segment) => segmentContains(segment, odds)) || {
    id: "outside", label: "範圍外", required_margin_pp: null, eligible_b: false,
    maximum_conclusion: modelV().price_policy.outside_conclusion || "範圍外",
  };
}

function gPriceSegment(odds) {
  if (!Number.isFinite(odds) || odds <= 1) return { id: "invalid", label: "無效價格", required_margin_pp: null, eligible: false, maximum_conclusion: "價格資料不足" };
  return modelG().price_bands.find((segment) => segmentContains(segment, odds)) || {
    id: "outside", label: "範圍外", required_margin_pp: null, eligible: false, maximum_conclusion: "只記錄",
  };
}

function priceBand(odds) {
  const band = gPriceSegment(odds);
  return { label: band.label, margin: band.required_margin_pp, eligible: Boolean(band.eligible), id: band.id, cap: band.maximum_conclusion };
}

function engineGap(candidate, odds, margin) {
  const value = edge(candidate, odds);
  return value === null || margin == null ? null : value - margin;
}

function engineMinimumOdds(candidate, margin) {
  return candidate.target.conservative !== null && margin != null && candidate.target.conservative > margin
    ? 1 / (candidate.target.conservative / 100 - margin / 100)
    : null;
}

function baseGradeFromGap(candidate, odds, margin, watchMin = -3) {
  if (candidate.game.confidence === "不足" || candidate.game.newsRisk >= 3 || candidate.target.conservative === null) return "資料不足";
  const value = edge(candidate, odds);
  if (value === null) return "資料不足";
  if (value < 0) return "不支持";
  const gap = engineGap(candidate, odds, margin);
  if (margin == null) return "ㄆ";
  if (gap >= 0) return "ㄅ";
  if (gap >= watchMin) return "ㄆ";
  return "ㄇ";
}

function applyRiskCap(candidate, grade) {
  if (grade === "資料不足" || grade === "不支持") return grade;
  if (candidate.game.newsRisk >= 3 || candidate.game.confidence === "不足") return "資料不足";
  if (candidate.game.newsRisk === 2 || candidate.game.confidence === "低") return grade === "ㄅ" ? "ㄆ" : grade;
  return grade;
}

function vDecision(candidate, odds = candidate.target.odds) {
  const segment = vPriceSegment(odds);
  let grade = baseGradeFromGap(candidate, odds, segment.required_margin_pp, modelV().grading?.watch_gap_min_pp ?? -3);
  grade = applyRiskCap(candidate, grade);
  let conclusion = gradeInfo[grade]?.label || grade;
  if (grade !== "資料不足" && grade !== "不支持") {
    if (segment.id === "extreme_low_excluded") { grade = "ㄆ"; conclusion = "排除・極低價格"; }
    else if (segment.id === "separate_calibration") { grade = grade === "ㄇ" ? "ㄇ" : "ㄆ"; conclusion = grade === "ㄇ" ? gradeInfo[grade].label : "另行校準"; }
    else if (segment.id === "outside") { grade = "ㄆ"; conclusion = "範圍外"; }
    else if (!segment.eligible_b && grade === "ㄅ") { grade = "ㄆ"; conclusion = segment.maximum_conclusion || "ㄆ級・延伸研究"; }
    else if (!segment.eligible_b && grade === "ㄆ") conclusion = segment.maximum_conclusion || "ㄆ級・延伸研究";
  }
  return {
    engine: "V", grade, conclusion, segment,
    margin: segment.required_margin_pp,
    gap: engineGap(candidate, odds, segment.required_margin_pp),
    minimumOdds: engineMinimumOdds(candidate, segment.required_margin_pp),
  };
}

function gDecision(candidate, odds = candidate.target.odds) {
  const segment = gPriceSegment(odds);
  let grade = baseGradeFromGap(candidate, odds, segment.required_margin_pp, modelG().grading?.watch_gap_min_pp ?? -3);
  grade = applyRiskCap(candidate, grade);
  let conclusion = gradeInfo[grade]?.label || grade;
  if (grade !== "資料不足" && grade !== "不支持") {
    if (segment.required_margin_pp == null) { grade = "ㄆ"; conclusion = segment.maximum_conclusion || "只記錄"; }
    else if (!segment.eligible && grade === "ㄅ") { grade = "ㄆ"; conclusion = segment.maximum_conclusion || "ㄆ級・延伸研究"; }
    else if (!segment.eligible && grade === "ㄆ") conclusion = segment.maximum_conclusion || "ㄆ級・延伸研究";
  }
  return {
    engine: "G", grade, conclusion, segment,
    margin: segment.required_margin_pp,
    gap: engineGap(candidate, odds, segment.required_margin_pp),
    minimumOdds: engineMinimumOdds(candidate, segment.required_margin_pp),
  };
}

function candidatesForGame(candidate) { return candidates.filter((item) => item.game.id === candidate.game.id); }
function dualSideConflict(candidate) {
  const sameGame = candidatesForGame(candidate);
  return sameGame.length === 2 && sameGame.every((item) => gDecision(item).grade === "ㄅ");
}

function coordinationDecision(candidate, odds = candidate.target.odds) {
  const v = vDecision(candidate, odds);
  const g = gDecision(candidate, odds);
  if (dualSideConflict(candidate)) return { grade: "ㄆ", label: "雙邊價值衝突・停止主要場次", tone: "watch", v, g };
  if (v.segment.id === "core" && v.grade === "ㄅ" && g.grade === "ㄅ") return { grade: "ㄅ", label: "V3.1 × G1 雙引擎通過", tone: "qualified", v, g };
  if (g.grade === "ㄅ") return { grade: "ㄅ", label: "G1 通過・V3.1 獨立顯示", tone: "qualified", v, g };
  if (v.grade === "ㄅ") return { grade: "ㄆ", label: "V3.1 通過・G1 Gate 未通過", tone: "watch", v, g };
  if (g.grade === "資料不足" || v.grade === "資料不足") return { grade: "資料不足", label: "資料不足", tone: "insufficient", v, g };
  if (g.grade === "不支持" && v.grade === "不支持") return { grade: "不支持", label: "雙引擎皆不支持", tone: "reject", v, g };
  const order = { "ㄅ": 4, "ㄆ": 3, "ㄇ": 2, "不支持": 1, "資料不足": 0 };
  const grade = order[g.grade] <= order[v.grade] ? g.grade : v.grade;
  return { grade, label: `V：${v.conclusion}・G：${g.conclusion}`, tone: gradeInfo[grade]?.tone || "watch", v, g };
}

function candidateGrade(candidate) { return gDecision(candidate).grade; }
function thresholdGap(candidate, odds = candidate.target.odds) { return gDecision(candidate, odds).gap; }
function minimumOdds(candidate, odds = candidate.target.odds) { return gDecision(candidate, odds).minimumOdds; }

function engineLabel(candidate) {
  const v = vDecision(candidate);
  return v.segment.id === "core" ? `V${modelV().version}＋G${modelG().version}` : `G${modelG().version}／V${modelV().version} ${v.segment.label}`;
}

function simulatedGateValue(game, key, fallback) {
  return Object.prototype.hasOwnProperty.call(game, key) ? game[key] : fallback;
}

function mainGateEligible(candidate) {
  const game = candidate.game;
  const decision = gDecision(candidate);
  const gate = modelG().core_gate;
  const comparisonSources = simulatedGateValue(game, "comparisonSources", game.coreReady ? 4 : 2);
  const modelMarketGap = simulatedGateValue(game, "modelMarketGap", game.coreReady ? 4 : 6);
  const evidenceCount = simulatedGateValue(game, "independentEvidenceCount", game.coreReady ? 2 : 0);
  const gapExplained = modelMarketGap <= gate.model_market_gap_max_pp || evidenceCount >= gate.independent_evidence_min_if_gap_exceeded;
  return decision.grade === "ㄅ"
    && !dualSideConflict(candidate)
    && game.coreReady === true
    && game.confidence === gate.confidence_required
    && game.coverage >= gate.coverage_min_pct
    && intervalWidth(candidate) !== null
    && intervalWidth(candidate) <= gate.interval_width_max_pp
    && decision.gap !== null
    && decision.gap >= gate.threshold_buffer_min_pp
    && game.newsRisk <= gate.news_risk_max
    && comparisonSources >= gate.comparison_sources_min
    && gapExplained
    && simulatedGateValue(game, "outOfDistribution", false) === false
    && simulatedGateValue(game, "reversePathResolved", true) === true
    && simulatedGateValue(game, "staleWarning", false) === false;
}

function rankedQualified() {
  return candidates.filter((candidate) => gDecision(candidate).grade === "ㄅ" && !dualSideConflict(candidate)).sort((a, b) => {
    const fresh = Number(Boolean(b.game.coreReady)) - Number(Boolean(a.game.coreReady));
    if (fresh) return fresh;
    if (b.game.coverage !== a.game.coverage) return b.game.coverage - a.game.coverage;
    const aw = intervalWidth(a) ?? 99;
    const bw = intervalWidth(b) ?? 99;
    if (aw !== bw) return aw - bw;
    return (gDecision(b).gap ?? -Infinity) - (gDecision(a).gap ?? -Infinity);
  });
}

function selectionBoard() {
  const qualified = rankedQualified();
  const officialMax = modelG().selection?.official_main_max ?? modelG().core_gate.core_max ?? 1;
  const core = officialMax > 0 ? qualified.find(mainGateEligible) || null : null;
  const priorityMax = coordinationPolicy().ui_policy?.priority_display_max ?? modelG().selection?.ui_priority_candidates_max ?? 2;
  const priority = qualified.filter((candidate) => !core || candidate.id !== core.id).slice(0, Math.max(0, priorityMax));
  const general = qualified.filter((candidate) => !core || candidate.id !== core.id).filter((candidate) => !priority.some((item) => item.id === candidate.id));
  return { core, priority, general, qualified };
}

function candidateTier(candidate) {
  const board = selectionBoard();
  if (board.core && board.core.id === candidate.id) return "G1 主要場次待 T−5m 確認";
  if (board.priority.some((item) => item.id === candidate.id)) return "網站優先候選（非 G1 正式分級）";
  if (gDecision(candidate).grade === "ㄅ") return "一般 G1 ㄅ級";
  if (gDecision(candidate).grade === "ㄆ") return "條件觀察";
  if (gDecision(candidate).grade === "資料不足") return "資料不足";
  return "跳過";
}

function decisionPills(candidate) {
  const v = vDecision(candidate);
  const g = gDecision(candidate);
  return `<div class="engine-tags"><span>V${modelV().version}：${v.conclusion}</span><span>G${modelG().version}：${g.conclusion}</span></div>`;
}

function renderTopPick() {
  const candidate = mainCandidate();
  const game = candidate.game;
  const combined = coordinationDecision(candidate);
  const tier = candidateTier(candidate);
  $("#topPick").innerHTML = `
    <div class="top-pick-main">
      <div class="pick-heading"><span class="grade-badge ${combined.tone}">${combined.label}</span><span>${tier}・台灣 ${game.start}</span></div>
      ${decisionPills(candidate)}
      <h1>${game.matchup}</h1>
      <p>目標邊 <strong>${candidate.target.code}</strong>・賠率 <strong>${candidate.target.odds.toFixed(2)}</strong></p>
      <button class="primary-button" data-open-candidate="${candidate.id}">查看 V／G 完整分析 →</button>
    </div>
    <div class="top-pick-numbers">
      ${metric("保守勝率", candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`, true)}
      ${metric("V3.1 距門檻", signed(combined.v.gap))}
      ${metric("G1 距門檻", signed(combined.g.gap), true)}
    </div>
    <div class="verification">
      <div>${game.injury}</div><div>${game.confidence}信心</div>
      <small>資料覆蓋率 ${game.coverage}%<br>區間寬度 ${intervalWidth(candidate) ?? "—"}pp<br>${game.snapshot}</small>
    </div>`;
}

function candidateCard(candidate) {
  const game = candidate.game;
  const combined = coordinationDecision(candidate);
  const tier = candidateTier(candidate);
  const tierClass = tier.startsWith("G1 主要") ? "tier-core" : tier.startsWith("網站優先") ? "tier-priority" : "";
  return `<button class="game-card ${tierClass}" data-open-candidate="${candidate.id}" aria-label="查看 ${game.matchup} ${candidate.target.code} 完整分析">
    <div class="game-card-top"><span class="grade-badge ${combined.tone}">${combined.label}</span><span class="game-time">台灣 ${game.start}</span></div>
    ${decisionPills(candidate)}
    <div class="matchup-row"><h3>${game.matchup}</h3><span>${oddsText(candidate.target.odds)}</span></div>
    <p class="target-line">目標邊 ${candidate.target.code}・${candidate.target.name}</p>
    <div class="mini-metrics">
      ${metric("保守", candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`)}
      ${metric("V 距門檻", signed(combined.v.gap))}
      ${metric("G 距門檻", signed(combined.g.gap), combined.g.gap !== null && combined.g.gap >= 0)}
    </div>
    <div class="game-card-footer"><span>${tier}</span><span>覆蓋 ${game.coverage}%</span></div>
  </button>`;
}

function renderTable() {
  $("#marketRows").innerHTML = candidates.map((candidate) => {
    const game = candidate.game;
    const v = vDecision(candidate);
    const g = gDecision(candidate);
    const combined = coordinationDecision(candidate);
    return `<tr data-open-candidate="${candidate.id}" tabindex="0">
      <td><strong>${game.matchup}</strong><small>台灣 ${game.start}</small></td>
      <td>${candidate.target.code}<small>${candidate.side === "home" ? "主隊" : "客隊"}</small></td>
      <td><span class="engine-pill">V${modelV().version}／G${modelG().version}</span></td>
      <td>${oddsText(candidate.target.odds)}</td><td>V：${v.segment.label}<small>G：${g.segment.label}</small></td><td>${percent(breakEven(candidate.target.odds))}</td>
      <td>${percent(noVig(candidate))}</td><td>${candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`}</td>
      <td>${candidate.target.neutral === null ? "—" : `${candidate.target.neutral}%`}</td><td>${candidate.target.optimistic === null ? "—" : `${candidate.target.optimistic}%`}</td>
      <td>${signed(scenarioEv(candidate.target.conservative, candidate.target.odds), "%")}</td>
      <td>V ${v.margin == null ? "—" : `${v.margin.toFixed(1)}pp`}<small>G ${g.margin == null ? "—" : `${g.margin.toFixed(1)}pp`}</small></td>
      <td>V ${signed(v.gap)}<small>G ${signed(g.gap)}</small></td><td>V ${oddsText(v.minimumOdds, 3)}<small>G ${oddsText(g.minimumOdds, 3)}</small></td>
      <td>${game.coverage}%</td><td>${game.confidence}</td><td><strong>${candidateTier(candidate)}</strong></td><td><span class="grade-badge ${combined.tone}">${combined.label}</span></td>
    </tr>`;
  }).join("");
}

function updateCalculator(resetOdds = false) {
  const candidate = candidates.find((item) => item.id === $("#calculatorGame").value) || candidates[0];
  if (resetOdds) $("#oddsInput").value = candidate.target.odds === null ? "" : candidate.target.odds.toFixed(2);
  $("#oddsLabel").textContent = `${candidate.target.code} 獨贏賠率`;
  const odds = Number($("#oddsInput").value);
  const valid = Number.isFinite(odds) && odds > 1;
  const v = valid ? vDecision(candidate, odds) : vDecision(candidate, NaN);
  const g = valid ? gDecision(candidate, odds) : gDecision(candidate, NaN);
  const combined = valid ? coordinationDecision(candidate, odds) : { label: "價格資料不足", tone: "insufficient" };
  $("#calcBreakeven").textContent = percent(valid ? breakEven(odds) : null);
  $("#calcGap").textContent = `V ${signed(v.gap)}／G ${signed(g.gap)}`;
  $("#calcGap").className = g.gap !== null && g.gap >= 0 ? "positive" : "";
  $("#calcEv").textContent = signed(valid ? scenarioEv(candidate.target.conservative, odds) : null, "%");
  $("#calcStatus").textContent = `${$("#bookmakerInput").value || "我的莊家"}：${combined.label}`;
  $("#calcStatus").classList.toggle("pass", combined.grade === "ㄅ");
  $("#calcNote").textContent = `V${modelV().version}：${v.conclusion}，最低 ${oddsText(v.minimumOdds, 3)}；G${modelG().version}：${g.conclusion}，最低 ${oddsText(g.minimumOdds, 3)}。單純價格變動只新增 price_evaluation，不改模型勝率；正式投注額固定為 0。`;
}

function showDetail(candidate) {
  const game = candidate.game;
  const v = vDecision(candidate);
  const g = gDecision(candidate);
  const combined = coordinationDecision(candidate);
  const comparisonSources = simulatedGateValue(game, "comparisonSources", game.coreReady ? 4 : 2);
  const modelMarketGap = simulatedGateValue(game, "modelMarketGap", game.coreReady ? 4 : 6);
  $("#modalContent").innerHTML = `
    <div class="detail-header"><span class="grade-badge ${combined.tone}">${combined.label}</span>${decisionPills(candidate)}<h2>${game.matchup}・${candidate.target.code}</h2><p>${game.headline}</p></div>
    <div class="detail-metrics">
      ${metric("目前賠率", oddsText(candidate.target.odds))}${metric("保守勝率", candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`, true)}
      ${metric("V3.1 區間", v.segment.label)}${metric("V3.1 結論", v.conclusion)}${metric("V3.1 距門檻", signed(v.gap))}${metric("V3.1 最低接受", oddsText(v.minimumOdds, 3))}
      ${metric("G1 區間", g.segment.label)}${metric("G1 結論", g.conclusion)}${metric("G1 距門檻", signed(g.gap), g.gap !== null && g.gap >= 0)}${metric("G1 最低接受", oddsText(g.minimumOdds, 3))}
    </div>
    <div class="scenario-band">
      <div><span>保守情境</span><strong>${candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.conservative, candidate.target.odds), "%")}</small></div>
      <div><span>中性情境</span><strong>${candidate.target.neutral === null ? "—" : `${candidate.target.neutral}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.neutral, candidate.target.odds), "%")}</small></div>
      <div><span>樂觀情境</span><strong>${candidate.target.optimistic === null ? "—" : `${candidate.target.optimistic}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.optimistic, candidate.target.odds), "%")}</small></div>
    </div>
    <div class="detail-grid">
      <article><span class="eyebrow">V3.1 價格評估</span><ul><li>${v.segment.label}</li><li>${v.conclusion}</li><li>RequiredMargin ${v.margin == null ? "—" : `${v.margin}pp`}</li><li>價格變動新增 price_evaluation_id，不改 prediction_id</li></ul></article>
      <article><span class="eyebrow">G1 Gate</span><ul><li>${g.segment.label}</li><li>${g.conclusion}</li><li>比較來源 ${comparisonSources} 家</li><li>模型市場差 ${modelMarketGap}pp</li><li>${dualSideConflict(candidate) ? "雙邊價值衝突：阻止主要場次" : "雙邊一致性未觸發衝突"}</li></ul></article>
      <article><span class="eyebrow">支持證據</span><ul>${game.reasons.map((item) => `<li>${item}</li>`).join("")}</ul></article>
      <article><span class="eyebrow">主要風險</span><ul>${game.risks.map((item) => `<li>${item}</li>`).join("")}</ul></article>
    </div>
    <div class="detail-footer"><span>覆蓋率 ${game.coverage}%・新聞風險 ${game.newsRisk}/3・${game.injury}</span><strong>${candidateTier(candidate)}・${game.snapshot}</strong></div>`;
  $("#detailModal").showModal();
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
    <div><span class="eyebrow">MODEL REGISTRY V4.6</span><h2>${activeModelLabel()}・${loaded ? "已載入新版 Registry" : "使用安全預設"}</h2>
    <p>${activeRevisionLabel()}。兩套引擎分開判定，不做未驗證的勝率平均；網站協調層只負責顯示與候選分類。</p></div>
    <div class="registry-grid">
      <article class="registry-card ${loaded ? "licensed" : "restricted"}"><div><span>V ENGINE</span><em>V${modelV().version}</em></div><h2>Prediction／Price Evaluation 分離</h2><dl>
        <div><dt>核心區</dt><dd>${modelV().odds_scope.min.toFixed(2)}～${modelV().odds_scope.max.toFixed(2)}</dd></div>
        <div><dt>Stage 0～2 邊際</dt><dd>${modelV().required_margin_pp.toFixed(1)}pp</dd></div>
        <div><dt>T-24h</dt><dd>最高 ㄆ級</dd></div>
        <div><dt>修訂</dt><dd>${modelV().revision_id || "—"}</dd></div>
      </dl></article>
      <article class="registry-card ${loaded ? "licensed" : "restricted"}"><div><span>G ENGINE</span><em>G${modelG().version}</em></div><h2>雙向 Gate 與 0～1 場主要場次</h2><dl>
        <div><dt>核心研究區</dt><dd>1.35～2.20</dd></div>
        <div><dt>主要覆蓋率</dt><dd>≥ ${modelG().core_gate.coverage_min_pct}%</dd></div>
        <div><dt>比較來源</dt><dd>≥ ${modelG().core_gate.comparison_sources_min} 家</dd></div>
        <div><dt>修訂</dt><dd>${modelG().revision_id || "—"}</dd></div>
      </dl></article>
      <article class="registry-card licensed"><div><span>COORDINATION</span><em>${coordinationPolicy().version}</em></div><h2>不混合勝率，只協調顯示</h2><dl>
        <div><dt>正式主要場次</dt><dd>0～1 場</dd></div>
        <div><dt>網站優先候選</dt><dd>最多 ${coordinationPolicy().ui_policy?.priority_display_max ?? 2} 場</dd></div>
        <div><dt>正式投注額</dt><dd>0</dd></div>
      </dl></article>
    </div>`;
  if (hero) hero.insertAdjacentElement("afterend", section); else panel.prepend(section);
}
