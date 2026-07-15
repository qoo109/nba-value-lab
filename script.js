const gradeInfo = {
  ㄅ: { label: "ㄅ級・正式入選", tone: "qualified", rule: "保守優勢 ≥ 5.0pp" },
  ㄆ: { label: "ㄆ級・條件觀察", tone: "watch", rule: "保守優勢 2.0–4.9pp" },
  ㄇ: { label: "ㄇ級・價格合理", tone: "fair", rule: "保守優勢 0–1.9pp" },
  不支持: { label: "模型不支持", tone: "reject", rule: "保守優勢低於0" },
  資料不足: { label: "資料不足", tone: "insufficient", rule: "無法可靠建立勝率" },
};

const probabilityBuild = {
  "den-phx": {
    base: 68,
    adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 2], ["傷病與輪替", 1], ["賽程休息", 1], ["教練風格", 0], ["主場與移動", 1]],
  },
  "bos-nyk": {
    base: 67,
    adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病與輪替", -1], ["賽程休息", 1], ["教練風格", 0], ["主場與移動", 2]],
  },
  "lal-gsw": {
    base: 66,
    adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病與輪替", 0], ["賽程休息", 0], ["教練風格", 0], ["主場與移動", 1]],
  },
  "okc-sas": {
    base: 69,
    adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病與輪替", 0], ["賽程休息", 0], ["教練風格", 0], ["主場與移動", 0]],
  },
};

const games = [
  {
    id: "den-phx",
    matchup: "DEN @ PHX",
    start: "10:00",
    favorite: "DEN",
    favoriteName: "丹佛金塊",
    odds: 1.58,
    underdogOdds: 2.5,
    conservative: 70,
    neutral: 74,
    optimistic: 77,
    noVig: 61.3,
    coverage: 91,
    confidence: "高",
    injury: "傷病已確認",
    marketSource: "網路市場共識",
    marketUpdated: "示範 09:40",
    bookmakerCount: 7,
    bestOdds: 1.61,
    grade: "ㄅ",
    headline: "保守情境仍跨過5個百分點安全邊際",
    reasons: ["長期調整後淨效率與半場進攻均佔優", "休息日與核心輪替完整度符合模型門檻", "目前價格仍高於最低可接受賠率1.538"],
    risks: ["PHX大量三分出手可能放大單場變異", "若熱門方賠率跌破1.538則取消入選"],
  },
  {
    id: "bos-nyk",
    matchup: "BOS @ NYK",
    start: "07:30",
    favorite: "NYK",
    favoriteName: "紐約尼克",
    odds: 1.52,
    underdogOdds: 2.55,
    conservative: 68,
    neutral: 71,
    optimistic: 74,
    noVig: 62.7,
    coverage: 83,
    confidence: "中",
    injury: "一名輪替待確認",
    marketSource: "網路市場共識",
    marketUpdated: "示範 09:38",
    bookmakerCount: 6,
    bestOdds: 1.55,
    grade: "ㄆ",
    headline: "模型略有優勢，但價格尚未提供完整緩衝",
    reasons: ["主場半場防守與籃板對位略有優勢", "保守勝率仍高於損益平衡勝率"],
    risks: ["核心側翼出賽狀態尚未完全確認", "最低可接受賠率為1.587，高於目前價格"],
  },
  {
    id: "lal-gsw",
    matchup: "LAL @ GSW",
    start: "10:30",
    favorite: "GSW",
    favoriteName: "金州勇士",
    odds: 1.56,
    underdogOdds: 2.42,
    conservative: 65,
    neutral: 69,
    optimistic: 73,
    noVig: 60.8,
    coverage: 79,
    confidence: "中",
    injury: "主力可出賽",
    marketSource: "網路市場共識",
    marketUpdated: "示範 09:34",
    bookmakerCount: 8,
    bestOdds: 1.58,
    grade: "ㄇ",
    headline: "可能贏球，但目前價格沒有足夠安全邊際",
    reasons: ["主場與外線創造能力支持熱門方", "中性勝率略高於市場要求"],
    risks: ["兩隊三分出手量高，波動明顯", "保守優勢不到1個百分點"],
  },
  {
    id: "okc-sas",
    matchup: "OKC @ SAS",
    start: "09:00",
    favorite: "OKC",
    favoriteName: "奧克拉荷馬雷霆",
    odds: 1.45,
    underdogOdds: 2.8,
    conservative: 67,
    neutral: 71,
    optimistic: 75,
    noVig: 65.9,
    coverage: 88,
    confidence: "高",
    injury: "傷病已確認",
    marketSource: "網路市場共識",
    marketUpdated: "示範 09:41",
    bookmakerCount: 7,
    bestOdds: 1.47,
    grade: "不支持",
    headline: "球隊較強不代表1.45是合理價格",
    reasons: ["長期實力支持熱門方", "防守失誤製造能力具備對位優勢"],
    risks: ["損益平衡勝率高達69.0%", "保守勝率低於市場要求"],
  },
  {
    id: "mil-mia",
    matchup: "MIL @ MIA",
    start: "08:00",
    favorite: "MIL",
    favoriteName: "密爾瓦基公鹿",
    odds: 1.67,
    underdogOdds: 2.2,
    conservative: null,
    neutral: null,
    optimistic: null,
    noVig: null,
    coverage: 46,
    confidence: "不足",
    injury: "核心傷病資訊不足",
    marketSource: "網路市場共識",
    marketUpdated: "示範 09:29",
    bookmakerCount: 4,
    bestOdds: null,
    grade: "資料不足",
    headline: "關鍵球員狀態足以改變勝率中心值",
    reasons: ["市場價格與比賽身分已確認"],
    risks: ["核心球員出賽與上場限制皆未確認", "資料覆蓋率低於50%"],
  },
];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
let activeFilter = "全部";

function breakEven(odds) {
  return odds ? 100 / odds : null;
}

function rawImplied(odds) {
  return odds ? 100 / odds : null;
}

function overround(game) {
  const favorite = rawImplied(game.odds);
  const underdog = rawImplied(game.underdogOdds);
  return favorite !== null && underdog !== null ? favorite + underdog : null;
}

function edge(game, odds = game.odds) {
  const be = breakEven(odds);
  return game.conservative !== null && be !== null ? game.conservative - be : null;
}

function scenarioEv(probability, odds) {
  return probability !== null && odds !== null ? (probability / 100) * odds * 100 - 100 : null;
}

function minimumOdds(game) {
  return game.conservative !== null && game.conservative > 5 ? 1 / (game.conservative / 100 - 0.05) : null;
}

function signed(value, suffix = "pp") {
  if (value === null || Number.isNaN(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
}

function gradeBadge(grade) {
  const info = gradeInfo[grade];
  return `<span class="grade-badge ${info.tone}">${info.label}</span>`;
}

function metric(label, value, emphasis = false) {
  return `<div class="metric ${emphasis ? "metric-emphasis" : ""}"><span>${label}</span><strong>${value}</strong></div>`;
}

function priceStatus(safeEdge) {
  if (safeEdge === null) return "無法判定";
  if (safeEdge >= 5) return "符合ㄅ級價格";
  if (safeEdge >= 2) return "僅達ㄆ級觀察";
  if (safeEdge >= 0) return "價格接近合理";
  return "價格不合格";
}

function renderTopPick() {
  const game = games[0];
  $("#topPick").innerHTML = `
    <div class="top-pick-accent"></div>
    <div class="top-pick-main">
      <div class="pick-heading">${gradeBadge(game.grade)}<span>台灣 ${game.start}</span></div>
      <h1>${game.matchup}</h1>
      <p>熱門方 <strong>${game.favorite}</strong><span></span>賠率 <strong>${game.odds?.toFixed(2) ?? "—"}</strong></p>
      <button class="primary-button" data-open="${game.id}">查看完整分析 →</button>
    </div>
    <div class="top-pick-numbers">
      ${metric("保守勝率", `${game.conservative}%`, true)}
      ${metric("損益平衡", `${breakEven(game.odds).toFixed(1)}%`)}
      ${metric("安全邊際", signed(edge(game)), true)}
    </div>
    <div class="verification">
      <div><span class="icon">☑</span><span>${game.injury}</span></div>
      <div><span class="icon">🛡</span><span>${game.confidence}信心</span></div>
      <small>資料覆蓋率 ${game.coverage}%</small>
    </div>
  `;
}

function renderMarketRows() {
  $("#marketRows").innerHTML = games.map((game) => `
    <tr data-open="${game.id}">
      <td><strong>${game.matchup}</strong><small>台灣 ${game.start}</small></td>
      <td>${game.favorite}</td>
      <td>${game.bookmakerCount} 家・${game.marketUpdated}</td>
      <td>${game.odds?.toFixed(2) ?? "—"}</td>
      <td>${game.bestOdds?.toFixed(2) ?? "—"}</td>
      <td>${breakEven(game.odds)?.toFixed(1) ?? "—"}%</td>
      <td>${game.noVig !== null ? `${game.noVig.toFixed(1)}%` : "—"}</td>
      <td>${game.conservative ?? "—"}${game.conservative !== null ? "%" : ""}</td>
      <td>${game.neutral ?? "—"}${game.neutral !== null ? "%" : ""}</td>
      <td>${game.optimistic ?? "—"}${game.optimistic !== null ? "%" : ""}</td>
      <td class="${scenarioEv(game.conservative, game.odds) !== null && scenarioEv(game.conservative, game.odds) > 0 ? "positive" : "negative"}">${signed(scenarioEv(game.conservative, game.odds), "%")}</td>
      <td>${minimumOdds(game)?.toFixed(3) ?? "—"}</td>
      <td>${game.confidence}</td>
      <td>${gradeBadge(game.grade)}</td>
    </tr>
  `).join("");
}

function gameCard(game) {
  return `
    <button class="game-card" data-open="${game.id}" aria-label="查看${game.matchup}完整分析">
      <div class="game-card-top">${gradeBadge(game.grade)}<span class="game-time">台灣 ${game.start}</span></div>
      <div class="matchup-row"><h3>${game.matchup}</h3><span>${game.odds?.toFixed(2) ?? "—"}</span></div>
      <p class="favorite-line">熱門方 ${game.favorite}・${game.favoriteName}</p>
      <div class="mini-metrics">
        ${metric("保守勝率", game.conservative !== null ? `${game.conservative}%` : "—")}
        ${metric("損益平衡", breakEven(game.odds) !== null ? `${breakEven(game.odds).toFixed(1)}%` : "—")}
        ${metric("安全邊際", signed(edge(game)), edge(game) !== null && edge(game) >= 5)}
      </div>
      <div class="game-card-footer"><span>${game.injury}</span><span>${game.confidence}信心</span></div>
    </button>
  `;
}

function renderGameGrids() {
  const visible = activeFilter === "全部" ? games : games.filter((game) => game.grade === activeFilter);
  $("#gamesGrid").innerHTML = visible.map(gameCard).join("");
  $("#noResults").hidden = visible.length > 0;
  $("#qualifiedGrid").innerHTML = games.filter((game) => game.grade === "ㄅ").map(gameCard).join("");
}

function renderCalculatorOptions() {
  $("#calculatorGame").innerHTML = games.map((game) => `<option value="${game.id}">${game.matchup}・${game.favorite}</option>`).join("");
}

function updateCalculator(resetOdds = false) {
  const game = games.find((item) => item.id === $("#calculatorGame").value) ?? games[0];
  if (resetOdds) $("#oddsInput").value = game.odds?.toFixed(2) ?? "";
  $("#oddsLabel").textContent = `${game.favorite} 獨贏賠率`;
  const odds = Number($("#oddsInput").value);
  const valid = Number.isFinite(odds) && odds > 1;
  const be = valid ? breakEven(odds) : null;
  const safeEdge = valid ? edge(game, odds) : null;
  const expected = valid ? scenarioEv(game.conservative, odds) : null;
  $("#calcBreakeven").textContent = be !== null ? `${be.toFixed(1)}%` : "—";
  $("#calcEdge").textContent = signed(safeEdge);
  $("#calcEv").textContent = signed(expected, "%");
  $("#calcEdge").className = safeEdge !== null && safeEdge >= 5 ? "positive" : safeEdge !== null && safeEdge < 0 ? "negative" : "";
  $("#calcEv").className = expected !== null && expected > 0 ? "positive" : expected !== null && expected < 0 ? "negative" : "";
  $("#calcStatus").className = `calculator-status ${safeEdge !== null && safeEdge >= 5 ? "pass" : ""}`;
  $("#calcStatus").textContent = `${$("#bookmakerInput").value || "我的莊家"}：${priceStatus(safeEdge)}`;
  $("#calcNote").textContent = `市場共識 ${game.odds?.toFixed(2) ?? "—"}・共識安全邊際 ${signed(edge(game))}・最低接受 ${minimumOdds(game)?.toFixed(3) ?? "—"}`;
}

function openDetail(id) {
  const game = games.find((item) => item.id === id);
  if (!game) return;
  const favoriteRaw = rawImplied(game.odds);
  const underdogRaw = rawImplied(game.underdogOdds);
  const marketTotal = overround(game);
  const build = probabilityBuild[game.id];
  $("#modalContent").innerHTML = `
    <div class="detail-header">
      <div>
        ${gradeBadge(game.grade)}
        <h2>${game.matchup}</h2>
        <p>${game.headline}</p>
      </div>
    </div>
    <div class="detail-metrics">
      ${metric("目前賠率", game.odds?.toFixed(2) ?? "—")}
      ${metric("保守勝率", game.conservative !== null ? `${game.conservative}%` : "—", true)}
      ${metric("中性勝率", game.neutral !== null ? `${game.neutral}%` : "—")}
      ${metric("損益平衡", breakEven(game.odds) !== null ? `${breakEven(game.odds).toFixed(1)}%` : "—")}
      ${metric("保守優勢", signed(edge(game)), edge(game) !== null && edge(game) >= 5)}
      ${metric("保守EV", signed(scenarioEv(game.conservative, game.odds), "%"))}
    </div>
    <div class="scenario-band">
      <div><span>保守情境</span><strong>${game.conservative !== null ? `${game.conservative}%` : "—"}</strong><small>EV ${signed(scenarioEv(game.conservative, game.odds), "%")}</small></div>
      <div><span>中性情境</span><strong>${game.neutral !== null ? `${game.neutral}%` : "—"}</strong><small>EV ${signed(scenarioEv(game.neutral, game.odds), "%")}</small></div>
      <div><span>樂觀情境</span><strong>${game.optimistic !== null ? `${game.optimistic}%` : "—"}</strong><small>EV ${signed(scenarioEv(game.optimistic, game.odds), "%")}</small></div>
    </div>
    <div class="market-math">
      <div class="subsection-title"><span class="eyebrow">MARKET MATH</span><strong>盤口拆解</strong></div>
      <div class="market-math-grid">
        ${metric("熱門方原始隱含", favoriteRaw !== null ? `${favoriteRaw.toFixed(1)}%` : "—")}
        ${metric("冷門方原始隱含", underdogRaw !== null ? `${underdogRaw.toFixed(1)}%` : "—")}
        ${metric("莊家總水位", marketTotal !== null ? `${marketTotal.toFixed(1)}%` : "—")}
        ${metric("熱門方去水機率", game.noVig !== null ? `${game.noVig.toFixed(1)}%` : "—")}
        ${metric("中性公平賠率", game.neutral ? (100 / game.neutral).toFixed(3) : "—")}
        ${metric("最佳示範價", game.bestOdds?.toFixed(2) ?? "—")}
      </div>
    </div>
    <div class="probability-build">
      <div class="subsection-title"><span class="eyebrow">MODEL BUILD</span><strong>勝率形成過程</strong></div>
      ${build ? `
        <div class="build-list">
          <div><span>長期實力基準</span><strong>${build.base}%</strong></div>
          ${build.adjustments.map(([label, value]) => `<div><span>${label}修正</span><strong class="${value > 0 ? "positive" : value < 0 ? "negative" : ""}">${value > 0 ? "+" : ""}${value}%</strong></div>`).join("")}
          <div class="build-total"><span>最終中性勝率</span><strong>${game.neutral !== null ? `${game.neutral}%` : "—"}</strong></div>
        </div>
      ` : `<p class="build-unavailable">關鍵資訊不足，因此不強行建立勝率修正鏈。</p>`}
    </div>
    <div class="detail-grid">
      <article><span class="eyebrow">支持證據</span><ul>${game.reasons.map((item) => `<li>${item}</li>`).join("")}</ul></article>
      <article><span class="eyebrow">主要風險</span><ul>${game.risks.map((item) => `<li>${item}</li>`).join("")}</ul></article>
    </div>
    <div class="detail-footer">
      <span>資料覆蓋率 ${game.coverage}%・${game.injury}</span>
      <strong>${minimumOdds(game) ? `最低接受賠率 ${minimumOdds(game).toFixed(3)}・${game.marketSource}` : "資料不足，不建立價格門檻"}</strong>
    </div>
  `;
  $("#detailModal").showModal();
}

function setTab(tab) {
  $$(".tab-button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  $(".analysis-panel").hidden = tab !== "analysis";
  $(".qualified-panel").hidden = tab !== "qualified";
  $(".history-panel").hidden = tab !== "history";
}

function bindEvents() {
  document.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-open]");
    if (opener) openDetail(opener.dataset.open);
  });
  $$(".tab-button").forEach((button) => button.addEventListener("click", () => setTab(button.dataset.tab)));
  $$(".filter-button").forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter;
      $$(".filter-button").forEach((item) => item.classList.toggle("active", item === button));
      renderGameGrids();
    });
  });
  $("#calculatorGame").addEventListener("change", () => updateCalculator(true));
  $("#bookmakerInput").addEventListener("input", () => updateCalculator(false));
  $("#oddsInput").addEventListener("input", () => updateCalculator(false));
  $("#closeModal").addEventListener("click", () => $("#detailModal").close());
}

function init() {
  renderTopPick();
  renderMarketRows();
  renderGameGrids();
  renderCalculatorOptions();
  updateCalculator(true);
  bindEvents();
}

init();
