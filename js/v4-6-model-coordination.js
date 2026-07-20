"use strict";

// V4.6 keeps V3.1 and G1 independent. It does not average probabilities or
// silently collapse the two engines into one grade.
let runtimeCoordination = null;

const FALLBACK_V31 = {
  engine_id: "V", version: "3.1.1", revision_id: "V3.1.1-20260719",
  core_odds_scope: { min: 1.40, max: 1.60, semantics: "b_eligible_core_range_only" }, required_margin_pp: 5,
  preview_policy: { snapshot: "T-24h", maximum_grade: "ㄆ", extra_margin_pp: null },
  price_policy: {
    price_segments: [
      { id: "extreme_low_excluded", min: 1.20, max: 1.30, min_inclusive: true, max_inclusive: false, label: "極低市場賠率區", required_margin_pp: 5, eligible_b: false, maximum_conclusion: "排除・極低市場賠率" },
      { id: "low_extension", min: 1.30, max: 1.40, min_inclusive: true, max_inclusive: false, label: "低市場賠率延伸研究區", required_margin_pp: 5, eligible_b: false, maximum_conclusion: "ㄆ級・延伸研究" },
      { id: "core", min: 1.40, max: 1.60, min_inclusive: true, max_inclusive: true, label: "核心決策區", required_margin_pp: 5, eligible_b: true, maximum_conclusion: "ㄅ級・研究候選" },
      { id: "high_extension", min: 1.60, max: 1.75, min_inclusive: false, max_inclusive: true, label: "高市場賠率延伸研究區", required_margin_pp: 5, eligible_b: false, maximum_conclusion: "ㄆ級・延伸研究" },
      { id: "separate_calibration", min: 1.75, max: 2.00, min_inclusive: false, max_inclusive: false, label: "另行校準區", required_margin_pp: 5, eligible_b: false, maximum_conclusion: "另行校準" },
    ],
    outside_conclusion: "範圍外",
  },
  grading: { edge_support_min_pp: 0, b_gap_min_pp: 0, watch_gap_min_pp: -3, risk_2_maximum_grade: "ㄆ", low_confidence_maximum_grade: "ㄆ" },
};

const FALLBACK_G1_FINAL = {
  engine_id: "G", version: "1.1.1", revision_id: "G1.1.1-20260719",
  price_bands: [
    { id: "extreme_low", min: 1.01, max: 1.20, min_inclusive: true, max_inclusive: false, label: "極低市場賠率層", required_margin_pp: null, eligible: false, maximum_conclusion: "只記錄" },
    { id: "low_research", min: 1.20, max: 1.35, min_inclusive: true, max_inclusive: false, label: "低市場賠率研究層", required_margin_pp: 7, eligible: false, maximum_conclusion: "ㄆ級・延伸研究" },
    { id: "favorite_core", min: 1.35, max: 1.60, min_inclusive: true, max_inclusive: true, label: "偏熱門核心層", required_margin_pp: 5, eligible: true, maximum_conclusion: "ㄅ級・研究候選" },
    { id: "near_even_core", min: 1.60, max: 2.20, min_inclusive: false, max_inclusive: true, label: "接近盤／小冷核心層", required_margin_pp: 6, eligible: true, maximum_conclusion: "ㄅ級・研究候選" },
    { id: "medium_high_extension", min: 2.20, max: 3.50, min_inclusive: false, max_inclusive: true, label: "中高市場賠率研究層", required_margin_pp: 8, eligible: false, maximum_conclusion: "ㄆ級・延伸研究" },
    { id: "high_volatility", min: 3.50, max: null, min_inclusive: false, max_inclusive: false, label: "高波動研究層", required_margin_pp: null, eligible: false, maximum_conclusion: "只記錄" },
  ],
  grading: { edge_support_min_pp: 0, b_gap_min_pp: 0, watch_gap_min_pp: -3 },
  core_gate: {
    coverage_min_pct: 85, interval_width_max_pp: 6, comparison_sources_min: 3,
    threshold_buffer_min_pp: 1, model_market_gap_max_pp: 5,
    independent_evidence_min_if_gap_exceeded: 2, news_risk_max: 1,
    confidence_required: "高", core_max: 3,
  },
  selection: { official_main_target: 2, official_main_max: 3, allow_zero_main: true, ui_priority_candidates_max: 2, ui_priority_is_official_g1_grade: false },
};

const FALLBACK_COORDINATION = {
  coordination_id: "V3.1.1_X_G1.1.1-20260719", version: "1.2.0",
  no_probability_blending: true,
  combined_policy: {
    data_insufficient_has_priority: true,
    v_core_and_g_core_requires_both_pass: true,
    v_extension_caps_combined_at_watch: true,
    g_only_research_allowed_outside_v_core: true,
    g_only_maximum_combined_grade: "ㄆ",
    g_only_label: "G1.1.1 單引擎研究候選",
    v_only_maximum_combined_grade: "ㄆ",
    v_only_label: "V3.1.1 通過・G1.1.1 Gate 未通過",
    v_and_g_label: "V3.1.1 × G1.1.1 雙引擎候選",
    dual_side_conflict_blocks_combined_b: true,
    dual_side_conflict_grade: "ㄆ",
    dual_side_conflict_label: "雙邊價值衝突・停止主要場次",
    formal_stake_fraction: 0,
  },
  ui_policy: { official_main_target: 2, official_main_max: 3, priority_display_max: 2, priority_display_is_not_official_g1_grade: true },
};

function coordinationPolicy() { return runtimeCoordination || FALLBACK_COORDINATION; }
function activeModelLabel() { return `V${modelV().version} × G${modelG().version}`; }
function activeRevisionLabel() { return `${modelV().revision_id || `V${modelV().version}`}・${modelG().revision_id || `G${modelG().version}`}`; }
function vCoreOddsScope() { return modelV().core_odds_scope || modelV().odds_scope; }

function validateLoadedModelConfig(engine, config, entry) {
  if (!config || typeof config !== "object") throw new Error(`${engine} config must be an object`);
  if (config.engine_id !== engine) throw new Error(`${engine} config engine_id mismatch`);
  if (!config.version) throw new Error(`${engine} config missing version`);
  if (String(config.version) !== String(entry?.version)) throw new Error(`${engine} config version mismatch`);
  if (entry?.revision_id && config.revision_id !== entry.revision_id) throw new Error(`${engine} config revision mismatch`);
  if (engine === "V" && !Array.isArray(config.price_policy?.price_segments)) throw new Error("V config missing price segments");
  if (engine === "V" && !config.core_odds_scope && !config.odds_scope) throw new Error("V config missing core odds scope");
  if (engine === "G" && !Array.isArray(config.price_bands)) throw new Error("G1 config missing price bands");
  return config;
}

function validateLoadedCoordinationConfig(config, entry, vEntry, gEntry) {
  if (!config || typeof config !== "object") throw new Error("coordination config must be an object");
  if (config.coordination_id !== entry?.coordination_id) throw new Error("coordination id mismatch");
  if (String(config.version) !== String(entry?.version)) throw new Error("coordination version mismatch");
  if (String(config.engine_versions?.V) !== String(vEntry?.version)) throw new Error("coordination V version mismatch");
  if (String(config.engine_versions?.G) !== String(gEntry?.version)) throw new Error("coordination G version mismatch");
  const policy = config.combined_policy || {};
  if (policy.v_core_and_g_core_requires_both_pass !== true) throw new Error("coordination must require both engines for combined B");
  if (policy.v_extension_caps_combined_at_watch !== true) throw new Error("coordination must cap V extensions at watch");
  if (policy.formal_stake_fraction !== 0) throw new Error("formal stake must remain zero");
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
      V: validateLoadedModelConfig("V", vConfig, vEntry),
      G: validateLoadedModelConfig("G", gConfig, gEntry),
    };
    runtimeCoordination = validateLoadedCoordinationConfig(coordinationConfig, coordinationEntry, vEntry, gEntry);
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
  if (!Number.isFinite(odds) || odds <= 1) return { id: "invalid", label: "無效市場賠率", required_margin_pp: null, eligible_b: false, maximum_conclusion: "市場賠率資料不足" };
  return modelV().price_policy.price_segments.find((segment) => segmentContains(segment, odds)) || {
    id: "outside", label: "範圍外", required_margin_pp: null, eligible_b: false,
    maximum_conclusion: modelV().price_policy.outside_conclusion || "範圍外",
  };
}

function gPriceSegment(odds) {
  if (!Number.isFinite(odds) || odds <= 1) return { id: "invalid", label: "無效市場賠率", required_margin_pp: null, eligible: false, maximum_conclusion: "市場賠率資料不足" };
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

function baseGradeFromGap(candidate, odds, margin, grading = {}) {
  if (candidate.game.confidence === "不足" || candidate.game.newsRisk >= 3 || candidate.target.conservative === null) return "資料不足";
  const value = edge(candidate, odds);
  if (value === null) return "資料不足";
  if (value < (grading.edge_support_min_pp ?? 0)) return "不支持";
  const gap = engineGap(candidate, odds, margin);
  if (margin == null) return "ㄆ";
  if (gap >= (grading.b_gap_min_pp ?? 0)) return "ㄅ";
  if (gap >= (grading.watch_gap_min_pp ?? -3)) return "ㄆ";
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
  let grade = baseGradeFromGap(candidate, odds, segment.required_margin_pp, modelV().grading);
  grade = applyRiskCap(candidate, grade);
  let conclusion = gradeInfo[grade]?.label || grade;
  if (grade !== "資料不足" && grade !== "不支持") {
    if (segment.id === "extreme_low_excluded") { grade = "ㄆ"; conclusion = "排除・極低市場賠率"; }
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
  let grade = baseGradeFromGap(candidate, odds, segment.required_margin_pp, modelG().grading);
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
  const policy = coordinationPolicy().combined_policy || {};
  if (policy.data_insufficient_has_priority !== false && (g.grade === "資料不足" || v.grade === "資料不足")) {
    return { grade: "資料不足", label: "資料不足", tone: "insufficient", v, g };
  }
  if (dualSideConflict(candidate)) {
    const grade = policy.dual_side_conflict_grade || "ㄆ";
    return { grade, label: policy.dual_side_conflict_label || "雙邊價值衝突・停止主要場次", tone: gradeInfo[grade]?.tone || "watch", v, g };
  }
  if (v.segment.id === "core" && v.grade === "ㄅ" && g.grade === "ㄅ") {
    return { grade: "ㄅ", label: policy.v_and_g_label || `${activeModelLabel()} 雙引擎候選`, tone: "qualified", v, g };
  }
  if (g.grade === "ㄅ") {
    const grade = policy.g_only_maximum_combined_grade || "ㄆ";
    return { grade, label: policy.g_only_label || `G${modelG().version} 單引擎研究候選`, tone: gradeInfo[grade]?.tone || "watch", v, g };
  }
  if (v.grade === "ㄅ") {
    const grade = policy.v_only_maximum_combined_grade || "ㄆ";
    return { grade, label: policy.v_only_label || `V${modelV().version} 通過・G Gate 未通過`, tone: gradeInfo[grade]?.tone || "watch", v, g };
  }
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
      <p>目標邊 <strong>${candidate.target.code}</strong>・市場賠率 <strong>${candidate.target.odds.toFixed(2)}</strong></p>
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
  $("#oddsLabel").textContent = `${candidate.target.code} 市場獨贏賠率`;
  const odds = Number($("#oddsInput").value);
  const valid = Number.isFinite(odds) && odds > 1;
  const v = valid ? vDecision(candidate, odds) : vDecision(candidate, NaN);
  const g = valid ? gDecision(candidate, odds) : gDecision(candidate, NaN);
  const combined = valid ? coordinationDecision(candidate, odds) : { label: "市場賠率資料不足", tone: "insufficient" };
  $("#calcBreakeven").textContent = percent(valid ? breakEven(odds) : null);
  $("#calcGap").textContent = `V ${signed(v.gap)}／G ${signed(g.gap)}`;
  $("#calcGap").className = g.gap !== null && g.gap >= 0 ? "positive" : "";
  $("#calcEv").textContent = signed(valid ? scenarioEv(candidate.target.conservative, odds) : null, "%");
  $("#calcStatus").textContent = `${$("#bookmakerInput").value || "我的莊家"}：${combined.label}`;
  $("#calcStatus").classList.toggle("pass", combined.grade === "ㄅ");
  $("#calcNote").textContent = `V${modelV().version}：${v.conclusion}，最低 ${oddsText(v.minimumOdds, 3)}；G${modelG().version}：${g.conclusion}，最低 ${oddsText(g.minimumOdds, 3)}。單純市場賠率變動只新增 price_evaluation，不改模型勝率；正式投注額固定為 0。`;
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
      ${metric("目前市場賠率", oddsText(candidate.target.odds))}${metric("保守勝率", candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`, true)}
      ${metric("V3.1 區間", v.segment.label)}${metric("V3.1 結論", v.conclusion)}${metric("V3.1 距門檻", signed(v.gap))}${metric("V3.1 最低接受", oddsText(v.minimumOdds, 3))}
      ${metric("G1 區間", g.segment.label)}${metric("G1 結論", g.conclusion)}${metric("G1 距門檻", signed(g.gap), g.gap !== null && g.gap >= 0)}${metric("G1 最低接受", oddsText(g.minimumOdds, 3))}
    </div>
    <div class="scenario-band">
      <div><span>保守情境</span><strong>${candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.conservative, candidate.target.odds), "%")}</small></div>
      <div><span>中性情境</span><strong>${candidate.target.neutral === null ? "—" : `${candidate.target.neutral}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.neutral, candidate.target.odds), "%")}</small></div>
      <div><span>樂觀情境</span><strong>${candidate.target.optimistic === null ? "—" : `${candidate.target.optimistic}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.optimistic, candidate.target.odds), "%")}</small></div>
    </div>
    <div class="detail-grid">
      <article><span class="eyebrow">V3.1 市場賠率評估</span><ul><li>${v.segment.label}</li><li>${v.conclusion}</li><li>RequiredMargin ${v.margin == null ? "—" : `${v.margin}pp`}</li><li>市場賠率變動新增 price_evaluation_id，不改 prediction_id</li></ul></article>
      <article><span class="eyebrow">G1 Gate</span><ul><li>${g.segment.label}</li><li>${g.conclusion}</li><li>比較來源 ${comparisonSources} 家</li><li>模型市場差 ${modelMarketGap}pp</li><li>${dualSideConflict(candidate) ? "雙邊價值衝突：阻止主要場次" : "雙邊一致性未觸發衝突"}</li></ul></article>
      <article><span class="eyebrow">支持證據</span><ul>${game.reasons.map((item) => `<li>${item}</li>`).join("")}</ul></article>
      <article><span class="eyebrow">主要風險</span><ul>${game.risks.map((item) => `<li>${item}</li>`).join("")}</ul></article>
    </div>
    <div class="detail-footer"><span>覆蓋率 ${game.coverage}%・新聞風險 ${game.newsRisk}/3・${game.injury}</span><strong>${candidateTier(candidate)}・${game.snapshot}</strong></div>`;
  $("#detailModal").showModal();
}

function upsertDownloadLink(container, id, text, href, beforeNode = null) {
  let link = container.querySelector(`a[data-download-id="${id}"]`);
  if (!link) {
    link = document.createElement("a");
    link.dataset.downloadId = id;
    link.setAttribute("download", "");
    if (beforeNode) container.insertBefore(link, beforeNode);
    else container.append(link);
  }
  link.href = href;
  link.textContent = text;
  return link;
}

function refreshRuleDownloads(panel, manifest) {
  const container = panel.querySelector(".downloads");
  if (!container) return;
  const legacyLinks = Array.from(container.querySelectorAll("a:not([data-download-id])"));
  if (legacyLinks[0]) legacyLinks[0].dataset.downloadId = "v-spec";
  if (legacyLinks[1]) legacyLinks[1].dataset.downloadId = "g-spec";
  if (legacyLinks[2]) legacyLinks[2].dataset.downloadId = "source-registry";
  if (legacyLinks[3]) legacyLinks[3].dataset.downloadId = "source-json";

  const firstLink = container.querySelector("a");
  const completeSpec = manifest.release?.complete_rules?.spec || "models/releases/v3.1.1-g1.1.1-complete/spec.md";
  upsertDownloadLink(container, "complete-rules", "下載完整統整規則", `./${completeSpec}`, firstLink);
  upsertDownloadLink(container, "v-spec", `下載 V${modelV().version} 規格`, `./${manifest.active?.V?.spec || "models/v3/3.1.1/spec.md"}`);
  upsertDownloadLink(container, "g-spec", `下載 G${modelG().version} 規格`, `./${manifest.active?.G?.spec || "models/g1/1.1.1/spec.md"}`);
  upsertDownloadLink(container, "coordination-spec", "下載協調層規格", `./${manifest.coordination?.spec || "models/coordination/v3.1.1-g1.1.1/spec.md"}`);
}

function renderModelRegistryStatus() {
  const panel = document.querySelector('[data-panel="sources"]');
  if (!panel || document.querySelector("#modelRegistryStatus")) return;
  const hero = panel.querySelector(".sources-hero");
  const section = document.createElement("section");
  section.id = "modelRegistryStatus";
  section.className = "storage-card";
  const loaded = modelRegistryLoadState.status === "loaded";
  const manifest = runtimeModelRegistry.manifest || {};
  refreshRuleDownloads(panel, manifest);
  section.innerHTML = `
    <div><span class="eyebrow">MODEL REGISTRY V4.6</span><h2>${activeModelLabel()}・${loaded ? "已載入新版 Registry" : "使用安全預設"}</h2>
    <p>${activeRevisionLabel()}。兩套引擎分開判定，不做未驗證的勝率平均；網站協調層只負責顯示與候選分類。</p></div>
    <div class="registry-grid">
      <article class="registry-card ${loaded ? "licensed" : "restricted"}"><div><span>V ENGINE</span><em>V${modelV().version}</em></div><h2>Prediction／Odds Evaluation 分離</h2><dl>
        <div><dt>核心區</dt><dd>${vCoreOddsScope().min.toFixed(2)}～${vCoreOddsScope().max.toFixed(2)}</dd></div>
        <div><dt>Stage 0～2 邊際</dt><dd>${modelV().required_margin_pp.toFixed(1)}pp</dd></div>
        <div><dt>T-24h</dt><dd>最高 ㄆ級</dd></div>
        <div><dt>修訂</dt><dd>${modelV().revision_id || "—"}</dd></div>
      </dl></article>
      <article class="registry-card ${loaded ? "licensed" : "restricted"}"><div><span>G ENGINE</span><em>G${modelG().version}</em></div><h2>雙向 Gate 與多主要場次</h2><dl>
        <div><dt>核心研究區</dt><dd>1.35～2.20</dd></div>
        <div><dt>主要覆蓋率</dt><dd>≥ ${modelG().core_gate.coverage_min_pct}%</dd></div>
        <div><dt>比較來源</dt><dd>≥ ${modelG().core_gate.comparison_sources_min} 家</dd></div>
        <div><dt>修訂</dt><dd>${modelG().revision_id || "—"}</dd></div>
      </dl></article>
      <article class="registry-card licensed"><div><span>COORDINATION</span><em>${coordinationPolicy().version}</em></div><h2>不混合勝率，只協調顯示</h2><dl>
        <div><dt>正式主要場次</dt><dd>目標 ${coordinationPolicy().ui_policy?.official_main_target ?? 2}・最多 ${coordinationPolicy().ui_policy?.official_main_max ?? 3} 場</dd></div>
        <div><dt>網站優先候選</dt><dd>最多 ${coordinationPolicy().ui_policy?.priority_display_max ?? 2} 場</dd></div>
        <div><dt>正式投注額</dt><dd>0</dd></div>
      </dl></article>
    </div>`;
  if (hero) hero.insertAdjacentElement("afterend", section); else panel.prepend(section);
}
