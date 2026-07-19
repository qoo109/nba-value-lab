"use strict";

const MODEL_VERSION = "2.6";
const APP_VERSION = "2.6.2";
const REQUIRED_MARGIN = 5;
const THEME_KEY = "nba-value-lab-theme";

const gradeInfo = {
  "ㄅ": { label: "ㄅ級・研究候選", tone: "qualified", rule: "保守優勢通過研究門檻" },
  "ㄆ": { label: "ㄆ級・條件觀察", tone: "watch", rule: "距門檻 −3～0pp 或仍有條件" },
  "ㄇ": { label: "ㄇ級・賠率合理", tone: "fair", rule: "賠率略有優勢但緩衝不足" },
  "不支持": { label: "模型不支持", tone: "reject", rule: "保守勝率低於損益平衡" },
  "資料不足": { label: "資料不足", tone: "insufficient", rule: "無法可靠建立勝率" },
};

const games = [
  {
    id: "den-phx", matchup: "DEN @ PHX", start: "10:00", favorite: "DEN", favoriteName: "丹佛金塊",
    odds: 1.58, underdogOdds: 2.50, conservative: 70, neutral: 74, optimistic: 77, noVig: 61.3,
    coverage: 91, confidence: "高", injury: "傷病已確認", newsRisk: 0, snapshot: "示範 T−60m 09:32",
    grade: "ㄅ", headline: "保守情境仍跨過校準前 5pp 研究門檻",
    build: { base: 68, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 2], ["傷病輪替", 1], ["賽程休息", 1], ["戰術風格", 0], ["主場移動", 1]] },
    reasons: ["長期調整後淨效率與半場進攻均佔優", "休息日與核心輪替完整度符合模型門檻", "目前賠率高於最低可接受賠率"],
    risks: ["PHX 大量三分出手可能放大單場變異", "若賠率跌破最低接受賠率則取消候選"],
  },
  {
    id: "bos-nyk", matchup: "BOS @ NYK", start: "07:30", favorite: "NYK", favoriteName: "紐約尼克",
    odds: 1.52, underdogOdds: 2.55, conservative: 68, neutral: 71, optimistic: 74, noVig: 62.7,
    coverage: 83, confidence: "中", injury: "一名輪替待確認", newsRisk: 2, snapshot: "示範 T−60m 09:30",
    grade: "ㄆ", headline: "模型略有優勢，但賠率尚未提供完整緩衝",
    build: { base: 67, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", -1], ["賽程休息", 1], ["戰術風格", 0], ["主場移動", 2]] },
    reasons: ["主場半場防守與籃板對位略有優勢", "保守勝率仍高於損益平衡勝率"],
    risks: ["核心側翼出賽狀態尚未完全確認", "最低可接受賠率高於目前賠率"],
  },
  {
    id: "lal-gsw", matchup: "LAL @ GSW", start: "10:30", favorite: "GSW", favoriteName: "金州勇士",
    odds: 1.56, underdogOdds: 2.42, conservative: 65, neutral: 69, optimistic: 73, noVig: 60.8,
    coverage: 79, confidence: "中", injury: "主力預計出賽", newsRisk: 1, snapshot: "示範 T−60m 09:27",
    grade: "ㄇ", headline: "可能贏球，但目前賠率沒有足夠安全邊際",
    build: { base: 66, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", 0], ["賽程休息", 0], ["戰術風格", 0], ["主場移動", 1]] },
    reasons: ["主場與外線創造能力支持熱門方", "中性勝率略高於市場要求"],
    risks: ["兩隊三分出手量高，單場波動明顯", "保守優勢未達完整研究門檻"],
  },
  {
    id: "okc-sas", matchup: "OKC @ SAS", start: "09:00", favorite: "OKC", favoriteName: "奧克拉荷馬雷霆",
    odds: 1.45, underdogOdds: 2.80, conservative: 67, neutral: 71, optimistic: 75, noVig: 65.9,
    coverage: 88, confidence: "高", injury: "傷病已確認", newsRisk: 0, snapshot: "示範 T−60m 09:35",
    grade: "不支持", headline: "球隊較強，不代表 1.45 是合理賠率",
    build: { base: 69, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", 0], ["賽程休息", 0], ["戰術風格", 0], ["主場移動", 0]] },
    reasons: ["長期實力支持熱門方", "防守失誤製造能力具備對位優勢"],
    risks: ["損益平衡勝率接近 69%", "保守勝率低於市場要求"],
  },
  {
    id: "mil-mia", matchup: "MIL @ MIA", start: "08:00", favorite: "MIL", favoriteName: "密爾瓦基公鹿",
    odds: 1.67, underdogOdds: 2.20, conservative: null, neutral: null, optimistic: null, noVig: null,
    coverage: 46, confidence: "不足", injury: "核心狀態未知", newsRisk: 3, snapshot: "未鎖定",
    grade: "資料不足", headline: "核心球員狀態足以改變勝率中心值",
    build: null, reasons: ["市場賠率與比賽身分已確認"],
    risks: ["核心球員出賽與上場限制皆未確認", "資料覆蓋率低於 50%"],
  },
];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
let activeFilter = "全部";

function loadReadabilityStyles() {
  if (document.querySelector("link[data-readability-css]")) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = `./readability.css?v=${APP_VERSION}`;
  link.dataset.readabilityCss = "true";
  document.head.appendChild(link);
}

function updateVersionText() {
  document.title = `NBA Value Lab V${APP_VERSION}`;
  const footerVersion = document.querySelector("footer > span:first-child");
  if (footerVersion) footerVersion.textContent = `NBA VALUE LAB V${APP_VERSION}`;
}

function breakEven(odds) { return odds && odds > 1 ? 100 / odds : null; }
function rawImplied(odds) { return breakEven(odds); }
function edge(game, odds = game.odds) {
  const be = breakEven(odds);
  return game.conservative !== null && be !== null ? game.conservative - be : null;
}
function thresholdGap(game, odds = game.odds) {
  const value = edge(game, odds);
  return value === null ? null : value - REQUIRED_MARGIN;
}
function scenarioEv(probability, odds) {
  return probability !== null && odds !== null ? (probability / 100) * odds * 100 - 100 : null;
}
function minimumOdds(game) {
  return game.conservative !== null && game.conservative > REQUIRED_MARGIN
    ? 1 / (game.conservative / 100 - REQUIRED_MARGIN / 100)
    : null;
}
function overround(game) {
  const favorite = rawImplied(game.odds);
  const underdog = rawImplied(game.underdogOdds);
  return favorite !== null && underdog !== null ? favorite + underdog - 100 : null;
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
    try { localStorage.setItem(THEME_KEY, nextTheme); } catch (_) { /* Storage may be unavailable. */ }
  }
}

function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", true);
}

function gradeAtPrice(game, odds) {
  if (game.confidence === "不足" || game.newsRisk >= 3 || game.conservative === null) return "資料不足";
  const e = edge(game, odds);
  if (e === null) return "資料不足";
  const gap = e - REQUIRED_MARGIN;
  if (gap >= 0 && game.newsRisk <= 1 && game.confidence !== "低") return "ㄅ";
  if (gap >= -3) return "ㄆ";
  if (e >= 0) return "ㄇ";
  return "不支持";
}

function renderTopPick() {
  const game = games[0];
  $("#topPick").innerHTML = `
    <div class="top-pick-main">
      <div class="pick-heading">${gradeBadge(game.grade)}<span>台灣 ${game.start}</span></div>
      <h1>${game.matchup}</h1>
      <p>熱門方 <strong>${game.favorite}</strong>・賠率 <strong>${game.odds.toFixed(2)}</strong></p>
      <button class="primary-button" data-open-game="${game.id}">查看完整分析 →</button>
    </div>
    <div class="top-pick-numbers">
      ${metric("保守勝率", `${game.conservative}%`, true)}
      ${metric("損益平衡", percent(breakEven(game.odds)))}
      ${metric("距離門檻", signed(thresholdGap(game)), true)}
    </div>
    <div class="verification">
      <div>${game.injury}</div><div>${game.confidence}信心</div>
      <small>資料覆蓋率 ${game.coverage}%<br>新聞風險 ${game.newsRisk}/3<br>${game.snapshot}</small>
    </div>`;
}

function gameCard(game) {
  return `<button class="game-card" data-open-game="${game.id}" aria-label="查看 ${game.matchup} 完整分析">
    <div class="game-card-top">${gradeBadge(game.grade)}<span class="game-time">台灣 ${game.start}</span></div>
    <div class="matchup-row"><h3>${game.matchup}</h3><span>${oddsText(game.odds)}</span></div>
    <p class="favorite-line">熱門方 ${game.favorite}・${game.favoriteName}</p>
    <div class="mini-metrics">
      ${metric("保守", game.conservative === null ? "—" : `${game.conservative}%`)}
      ${metric("損益平衡", percent(breakEven(game.odds)))}
      ${metric("距門檻", signed(thresholdGap(game)), thresholdGap(game) !== null && thresholdGap(game) >= 0)}
    </div>
    <div class="game-card-footer"><span>風險 ${game.newsRisk}/3</span><span>覆蓋 ${game.coverage}%</span></div>
  </button>`;
}

function renderCards() {
  const visible = activeFilter === "全部" ? games : games.filter((game) => game.grade === activeFilter);
  $("#gamesGrid").innerHTML = visible.map(gameCard).join("");
  $("#noResults").hidden = visible.length > 0;
  const candidates = games.filter((game) => game.grade === "ㄅ");
  $("#candidateGrid").innerHTML = candidates.map(gameCard).join("");
  $("#candidateCount").textContent = `${candidates.length} 場`;
}

function renderTable() {
  $("#marketRows").innerHTML = games.map((game) => `
    <tr data-open-game="${game.id}" tabindex="0">
      <td><strong>${game.matchup}</strong><small>台灣 ${game.start}</small></td>
      <td>${game.favorite}</td><td>${oddsText(game.odds)}</td><td>${percent(breakEven(game.odds))}</td>
      <td>${game.noVig === null ? "—" : `${game.noVig.toFixed(1)}%`}</td>
      <td>${game.conservative === null ? "—" : `${game.conservative}%`}</td>
      <td>${game.neutral === null ? "—" : `${game.neutral}%`}</td>
      <td>${game.optimistic === null ? "—" : `${game.optimistic}%`}</td>
      <td>${signed(scenarioEv(game.conservative, game.odds), "%")}</td>
      <td>${signed(thresholdGap(game))}</td><td>${oddsText(minimumOdds(game), 3)}</td>
      <td>${game.coverage}%</td><td>${game.confidence}</td><td>${gradeBadge(game.grade)}</td>
    </tr>`).join("");
}

function renderCalculatorOptions() {
  $("#calculatorGame").innerHTML = games.map((game) => `<option value="${game.id}">${game.matchup}・${game.favorite}</option>`).join("");
}

function updateCalculator(resetOdds = false) {
  const game = games.find((item) => item.id === $("#calculatorGame").value) || games[0];
  if (resetOdds) $("#oddsInput").value = game.odds === null ? "" : game.odds.toFixed(2);
  $("#oddsLabel").textContent = `${game.favorite} 獨贏賠率`;
  const odds = Number($("#oddsInput").value);
  const valid = Number.isFinite(odds) && odds > 1;
  const be = valid ? breakEven(odds) : null;
  const gap = valid ? thresholdGap(game, odds) : null;
  const ev = valid ? scenarioEv(game.conservative, odds) : null;
  const grade = valid ? gradeAtPrice(game, odds) : "資料不足";
  $("#calcBreakeven").textContent = percent(be);
  $("#calcGap").textContent = signed(gap);
  $("#calcGap").className = gap !== null && gap >= 0 ? "positive" : gap !== null && gap < -REQUIRED_MARGIN ? "negative" : "";
  $("#calcEv").textContent = signed(ev, "%");
  $("#calcStatus").textContent = `${$("#bookmakerInput").value || "我的莊家"}：${gradeInfo[grade].label}`;
  $("#calcStatus").classList.toggle("pass", grade === "ㄅ");
  $("#calcNote").textContent = `最低接受賠率 ${oddsText(minimumOdds(game), 3)}・研究緩衝 ${REQUIRED_MARGIN.toFixed(1)}pp・模型尚未校準，正式投注額固定為 0。`;
}

function showDetail(game) {
  const buildRows = game.build
    ? `<p><strong>勝率形成：</strong>長期基準 ${game.build.base}%；${game.build.adjustments.map(([label, value]) => `${label} ${value >= 0 ? "+" : ""}${value}%`).join("；")}；中性 ${game.neutral}%。</p>`
    : `<p><strong>勝率形成：</strong>關鍵資訊不足，因此停止建立勝率修正鏈。</p>`;
  $("#modalContent").innerHTML = `
    <div class="detail-header">${gradeBadge(game.grade)}<h2>${game.matchup}</h2><p>${game.headline}</p></div>
    <div class="detail-metrics">
      ${metric("目前賠率", oddsText(game.odds))}${metric("保守勝率", game.conservative === null ? "—" : `${game.conservative}%`, true)}
      ${metric("損益平衡", percent(breakEven(game.odds)))}${metric("保守優勢", signed(edge(game)))}
      ${metric("距離門檻", signed(thresholdGap(game)), thresholdGap(game) !== null && thresholdGap(game) >= 0)}
      ${metric("最低接受", oddsText(minimumOdds(game), 3))}
    </div>
    <div class="scenario-band">
      <div><span>保守情境</span><strong>${game.conservative === null ? "—" : `${game.conservative}%`}</strong><small>EV ${signed(scenarioEv(game.conservative, game.odds), "%")}</small></div>
      <div><span>中性情境</span><strong>${game.neutral === null ? "—" : `${game.neutral}%`}</strong><small>EV ${signed(scenarioEv(game.neutral, game.odds), "%")}</small></div>
      <div><span>樂觀情境</span><strong>${game.optimistic === null ? "—" : `${game.optimistic}%`}</strong><small>EV ${signed(scenarioEv(game.optimistic, game.odds), "%")}</small></div>
    </div>
    <div class="detail-grid">
      <article><span class="eyebrow">市場數學</span><ul><li>熱門方原始隱含 ${percent(rawImplied(game.odds))}</li><li>冷門方原始隱含 ${percent(rawImplied(game.underdogOdds))}</li><li>理論超額水位 ${percent(overround(game))}</li><li>比例去水機率 ${game.noVig === null ? "—" : `${game.noVig.toFixed(1)}%`}</li></ul></article>
      <article><span class="eyebrow">模型帳本</span>${buildRows}</article>
      <article><span class="eyebrow">支持證據</span><ul>${game.reasons.map((item) => `<li>${item}</li>`).join("")}</ul></article>
      <article><span class="eyebrow">主要風險</span><ul>${game.risks.map((item) => `<li>${item}</li>`).join("")}</ul></article>
    </div>
    <div class="detail-footer"><span>覆蓋率 ${game.coverage}%・新聞風險 ${game.newsRisk}/3・${game.injury}</span><strong>${game.snapshot}</strong></div>`;
  $("#detailModal").showModal();
}

function handleOpenTarget(target) {
  const node = target.closest("[data-open-game]");
  if (!node) return;
  const game = games.find((item) => item.id === node.dataset.openGame);
  if (game) showDetail(game);
}

function bindEvents() {
  $$(".tab-button").forEach((button) => button.addEventListener("click", () => {
    $$(".tab-button").forEach((item) => item.classList.toggle("active", item === button));
    $$("[data-panel]").forEach((panel) => { panel.hidden = panel.dataset.panel !== button.dataset.tab; });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }));
  $$(".filter-button").forEach((button) => button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    $$(".filter-button").forEach((item) => item.classList.toggle("active", item === button));
    renderCards();
  }));
  document.addEventListener("click", (event) => handleOpenTarget(event.target));
  $("#marketRows").addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") handleOpenTarget(event.target);
  });
  $("#calculatorGame").addEventListener("change", () => updateCalculator(true));
  $("#oddsInput").addEventListener("input", () => updateCalculator(false));
  $("#bookmakerInput").addEventListener("input", () => updateCalculator(false));
  $("#themeToggle").addEventListener("click", toggleTheme);
  $("#closeModal").addEventListener("click", () => $("#detailModal").close());
  $("#detailModal").addEventListener("click", (event) => { if (event.target === $("#detailModal")) $("#detailModal").close(); });
}

function init() {
  loadReadabilityStyles();
  updateVersionText();
  applyTheme(document.documentElement.dataset.theme || "light");
  renderTopPick();
  renderTable();
  renderCards();
  renderCalculatorOptions();
  bindEvents();
  updateCalculator(true);
  document.documentElement.dataset.modelVersion = MODEL_VERSION;
  document.documentElement.dataset.appVersion = APP_VERSION;
}

init();
