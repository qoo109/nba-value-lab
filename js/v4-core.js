function loadReadabilityStyles() {
  if (document.querySelector("link[data-readability-css]")) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = `./readability.css?v=${APP_VERSION}`;
  link.dataset.readabilityCss = "true";
  document.head.appendChild(link);
}

function updateVersionText() {
  document.title = `NBA Value Lab ${APP_VERSION}｜V3 × G1`;
  const footerVersion = document.querySelector("footer > span:first-child");
  if (footerVersion) footerVersion.textContent = `NBA VALUE LAB ${APP_VERSION}`;
}

function breakEven(odds) { return odds && odds > 1 ? 100 / odds : null; }
function rawImplied(odds) { return breakEven(odds); }
function overround(candidate) {
  const target = rawImplied(candidate.target.odds);
  const opponent = rawImplied(candidate.opponent.odds);
  return target !== null && opponent !== null ? target + opponent - 100 : null;
}
function noVig(candidate) {
  const target = rawImplied(candidate.target.odds);
  const opponent = rawImplied(candidate.opponent.odds);
  return target !== null && opponent !== null ? target / (target + opponent) * 100 : null;
}
function priceBand(odds) {
  if (!Number.isFinite(odds) || odds <= 1) return { label: "無效價格", margin: null, eligible: false };
  if (odds < 1.20) return { label: "極低價層", margin: null, eligible: false };
  if (odds < 1.35) return { label: "低價研究層", margin: 7, eligible: false };
  if (odds <= 1.60) return { label: "偏熱門核心層", margin: 5, eligible: true };
  if (odds <= 2.20) return { label: "接近盤／小冷核心層", margin: 6, eligible: true };
  if (odds <= 3.50) return { label: "中高價研究層", margin: 8, eligible: false };
  return { label: "高波動研究層", margin: null, eligible: false };
}
function edge(candidate, odds = candidate.target.odds) {
  const be = breakEven(odds);
  return candidate.target.conservative !== null && be !== null ? candidate.target.conservative - be : null;
}
function thresholdGap(candidate, odds = candidate.target.odds) {
  const value = edge(candidate, odds);
  const margin = priceBand(odds).margin;
  return value === null || margin === null ? null : value - margin;
}
function scenarioEv(probability, odds) {
  return probability !== null && odds !== null ? (probability / 100) * odds * 100 - 100 : null;
}
function minimumOdds(candidate, odds = candidate.target.odds) {
  const margin = priceBand(odds).margin;
  return candidate.target.conservative !== null && margin !== null && candidate.target.conservative > margin
    ? 1 / (candidate.target.conservative / 100 - margin / 100)
    : null;
}
function signed(value, suffix = "pp") {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
}
function percent(value) { return value === null ? "—" : `${value.toFixed(1)}%`; }
function oddsText(value, digits = 2) { return value === null ? "—" : value.toFixed(digits); }
function gradeBadge(grade) {
  const info = gradeInfo[grade];
  return `<span class="grade-badge ${info.tone}">${info.label}</span>`;
}
function metric(label, value, emphasis = false) {
  return `<div class="metric ${emphasis ? "metric-emphasis" : ""}"><span>${label}</span><strong>${value}</strong></div>`;
}
function gradeAtPrice(candidate, odds = candidate.target.odds) {
  const game = candidate.game;
  if (game.confidence === "不足" || game.newsRisk >= 3 || candidate.target.conservative === null) return "資料不足";
  const value = edge(candidate, odds);
  if (value === null) return "資料不足";
  if (value < 0) return "不支持";
  const band = priceBand(odds);
  const gap = thresholdGap(candidate, odds);
  if (gap !== null && gap >= 0) {
    if (band.eligible && game.newsRisk <= 1 && game.confidence !== "低") return "ㄅ";
    return "ㄆ";
  }
  if (gap !== null && gap >= -3) return "ㄆ";
  return "ㄇ";
}
function candidateGrade(candidate) { return gradeAtPrice(candidate); }

function applyTheme(theme, persist = false) {
  const nextTheme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = nextTheme;
  const isDark = nextTheme === "dark";
  $("#themeToggle").setAttribute("aria-pressed", String(isDark));
  $("#themeToggle").setAttribute("aria-label", isDark ? "切換至淺色模式" : "切換至深色模式");
  $("#themeLabel").textContent = isDark ? "淺色" : "深色";
  $(".theme-toggle-icon").textContent = isDark ? "☀" : "☾";
  $("#themeColor").setAttribute("content", isDark ? "#0a101a" : "#e9edf2");
  if (persist) {
    try { localStorage.setItem(THEME_KEY, nextTheme); } catch (_) { }
  }
}

function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", true);
}

function engineLabel(candidate) {
  const odds = candidate.target.odds;
  return Number.isFinite(odds) && odds >= 1.40 && odds <= 1.60 ? "V3＋G1" : "G1";
}

function intervalWidth(candidate) {
  return candidate.target.conservative === null || candidate.target.optimistic === null
    ? null
    : candidate.target.optimistic - candidate.target.conservative;
}

function mainGateEligible(candidate) {
  const game = candidate.game;
  const gap = thresholdGap(candidate);
  return candidateGrade(candidate) === "ㄅ"
    && game.coreReady === true
    && game.confidence === "高"
    && game.coverage >= 85
    && intervalWidth(candidate) !== null
    && intervalWidth(candidate) <= 6
    && gap !== null
    && gap >= 1
    && game.newsRisk <= 1;
}

function rankedQualified() {
  return candidates
    .filter((candidate) => candidateGrade(candidate) === "ㄅ")
    .sort((a, b) => {
      const fresh = Number(Boolean(b.game.coreReady)) - Number(Boolean(a.game.coreReady));
      if (fresh) return fresh;
      if (b.game.coverage !== a.game.coverage) return b.game.coverage - a.game.coverage;
      const aw = intervalWidth(a) ?? 99;
      const bw = intervalWidth(b) ?? 99;
      if (aw !== bw) return aw - bw;
      return (thresholdGap(b) ?? -Infinity) - (thresholdGap(a) ?? -Infinity);
    });
}

function selectionBoard() {
  const qualified = rankedQualified();
  const core = qualified.find(mainGateEligible) || null;
  const priority = qualified.filter((candidate) => !core || candidate.id !== core.id).slice(0, 2);
  const general = qualified.filter((candidate) => !core || candidate.id !== core.id)
    .filter((candidate) => !priority.some((item) => item.id === candidate.id));
  return { core, priority, general, qualified };
}

function candidateTier(candidate) {
  const board = selectionBoard();
  if (board.core && board.core.id === candidate.id) return "核心主推";
  if (board.priority.some((item) => item.id === candidate.id)) return "優先候選";
  if (candidateGrade(candidate) === "ㄅ") return "一般 ㄅ級";
  if (candidateGrade(candidate) === "ㄆ") return "條件觀察";
  if (candidateGrade(candidate) === "資料不足") return "資料不足";
  return "跳過";
}

function mainCandidate() {
  const board = selectionBoard();
  return board.core || board.priority[0] || board.qualified[0] || candidates[0];
}
