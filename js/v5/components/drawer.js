"use strict";

(function () {
  const v5 = window.NBAVL.v5;
  let previousFocus = null;

  function ensureDrawer() {
    if (document.querySelector("#v5Drawer")) return;
    const overlay = document.createElement("div");
    overlay.id = "v5DrawerOverlay";
    overlay.className = "v5-drawer-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `<aside class="v5-drawer" id="v5Drawer" role="dialog" aria-modal="true" aria-labelledby="v5DrawerTitle">
      <div class="v5-drawer-toolbar">
        <span>完整賽前分析</span>
        <button type="button" class="v5-drawer-close" id="v5DrawerClose" aria-label="關閉分析">×</button>
      </div>
      <div class="v5-drawer-content" id="v5DrawerContent"></div>
    </aside>`;
    document.body.appendChild(overlay);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) close();
    });
    overlay.querySelector("#v5DrawerClose").addEventListener("click", close);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !overlay.hidden) close();
    });
  }

  function metricItem(label, value, emphasis = false) {
    return `<div class="v5-drawer-metric${emphasis ? " emphasis" : ""}"><span>${label}</span><strong>${value}</strong></div>`;
  }

  function list(items, emptyText) {
    const values = Array.isArray(items) && items.length ? items : [emptyText];
    return `<ul>${values.map((item) => `<li>${item}</li>`).join("")}</ul>`;
  }

  function render(candidate) {
    const game = candidate.game;
    const band = priceBand(candidate.target.odds);
    const content = document.querySelector("#v5DrawerContent");
    content.innerHTML = `<header class="v5-drawer-header">
      <div class="v5-drawer-badges">
        ${gradeBadge(candidateGrade(candidate))}
        <span class="engine-pill">${engineLabel(candidate)}</span>
        <span class="v5-tier-pill">${candidateTier(candidate)}</span>
      </div>
      <h2 id="v5DrawerTitle">${game.matchup}・${candidate.target.code}</h2>
      <p>${game.headline}</p>
    </header>
    <section class="v5-drawer-metrics">
      ${metricItem("目前賠率", oddsText(candidate.target.odds))}
      ${metricItem("保守勝率", candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`, true)}
      ${metricItem("損益平衡", percent(breakEven(candidate.target.odds)))}
      ${metricItem("距離門檻", signed(thresholdGap(candidate)), thresholdGap(candidate) !== null && thresholdGap(candidate) >= 0)}
      ${metricItem("最低接受", oddsText(minimumOdds(candidate), 3))}
      ${metricItem("覆蓋率", `${game.coverage}%`)}
    </section>
    <section class="v5-scenario-grid">
      <div><span>保守</span><strong>${candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.conservative, candidate.target.odds), "%")}</small></div>
      <div><span>中性</span><strong>${candidate.target.neutral === null ? "—" : `${candidate.target.neutral}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.neutral, candidate.target.odds), "%")}</small></div>
      <div><span>樂觀</span><strong>${candidate.target.optimistic === null ? "—" : `${candidate.target.optimistic}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.optimistic, candidate.target.odds), "%")}</small></div>
    </section>
    <section class="v5-drawer-section">
      <span class="eyebrow">WHY IT RANKS HERE</span>
      <h3>支持證據</h3>
      ${list(game.reasons, "等待更多賽前資料")}
    </section>
    <section class="v5-drawer-section risk">
      <span class="eyebrow">WHAT CAN GO WRONG</span>
      <h3>主要風險</h3>
      ${list(game.risks, "目前沒有額外風險註記")}
    </section>
    <section class="v5-drawer-section">
      <span class="eyebrow">ODDS & DATA</span>
      <h3>賠率與資料狀態</h3>
      <dl class="v5-data-list">
        <div><dt>賠率分層</dt><dd>${band.label}</dd></div>
        <div><dt>要求邊際</dt><dd>${band.margin === null ? "—" : `${band.margin.toFixed(1)}pp`}</dd></div>
        <div><dt>去水機率</dt><dd>${percent(noVig(candidate))}</dd></div>
        <div><dt>信心水準</dt><dd>${game.confidence}</dd></div>
        <div><dt>傷病狀態</dt><dd>${game.injury}</dd></div>
        <div><dt>資料快照</dt><dd>${game.snapshot}</dd></div>
      </dl>
    </section>
    <footer class="v5-drawer-footer">
      <strong>研究模式・正式投注額固定為 0</strong>
      <span>賠率改變只重算賠率層，不回頭改寫模型勝率。</span>
    </footer>`;
  }

  function open(candidate) {
    ensureDrawer();
    previousFocus = document.activeElement;
    render(candidate);
    const overlay = document.querySelector("#v5DrawerOverlay");
    overlay.hidden = false;
    requestAnimationFrame(() => overlay.classList.add("is-open"));
    document.body.classList.add("v5-drawer-open");
    overlay.querySelector("#v5DrawerClose").focus();
  }

  function close() {
    const overlay = document.querySelector("#v5DrawerOverlay");
    if (!overlay || overlay.hidden) return;
    overlay.classList.remove("is-open");
    document.body.classList.remove("v5-drawer-open");
    window.setTimeout(() => { overlay.hidden = true; }, 180);
    if (previousFocus && typeof previousFocus.focus === "function") previousFocus.focus();
  }

  v5.modules.drawer = { ensure: ensureDrawer, open, close };
  window.showDetail = open;
}());
