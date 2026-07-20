"use strict";

(function () {
  const STATUS = {
    appVersion: "V5.3.14",
    model: "V3.1 x G1.1",
    updated: "2026-07-20",
    state: "Research Candidate / Pre-Market-Backtest",
    stake: "0",
  };

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function setText(node, text) {
    if (node) node.textContent = text;
  }

  function ensureStylesheet() {
    if (qs('link[data-current-research-status-css]')) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "./css/current-research-status.css?v=20260719h";
    link.setAttribute("data-current-research-status-css", "true");
    document.head.appendChild(link);
  }

  function ensureMarketTableSorting() {
    if (qs('script[data-market-table-sort]')) return;
    const script = document.createElement("script");
    script.src = "./js/market-table-sort.js?v=20260720b";
    script.defer = true;
    script.setAttribute("data-market-table-sort", "true");
    document.head.appendChild(script);
    document.documentElement.dataset.marketTableSortLoader = "requested";
  }

  function ensureHeader() {
    document.documentElement.dataset.appVersion = STATUS.appVersion;
    document.documentElement.dataset.modelVersion = STATUS.model;
    document.title = `NBA Value Lab ${STATUS.appVersion} | ${STATUS.model}`;
    const header = qs(".header-status");
    if (header) {
      header.innerHTML = `<span class="status-dot"></span>${STATUS.appVersion}・${STATUS.state}・Stake ${STATUS.stake}`;
    }
    const footerVersion = qs("footer > span:first-child");
    setText(footerVersion, `NBA VALUE LAB ${STATUS.appVersion}`);
    const footerMode = qs("footer > span:last-child");
    setText(footerMode, `台灣時間・${STATUS.model}・正式投注額 ${STATUS.stake}`);
  }

  function updateRail() {
    const rail = qs('[data-panel="analysis"] .date-rail');
    if (!rail) return;
    const cells = qsa(":scope > div", rail);
    if (cells[0]) cells[0].innerHTML = '<span class="rail-code">STATE</span><span><strong>Research Candidate</strong>・Pre-Market-Backtest</span>';
    if (cells[1]) cells[1].innerHTML = '<span class="rail-code">QUEUE</span><span>Wyatt blocked・Eoin preflight ready・Market odds 暫停</span>';
    if (cells[2]) cells[2].innerHTML = '<span class="rail-code">STAKE</span><span>正式投注額 0・不宣稱 edge / ROI / CLV</span>';
  }

  function statusCard(label, title, copy, tone, details) {
    const list = details.map((item) => `<li>${item}</li>`).join("");
    return `<article class="current-status-card ${tone}">
      <div><span>${label}</span><em>${toneLabel(tone)}</em></div>
      <h3>${title}</h3>
      <p>${copy}</p>
      <ul>${list}</ul>
    </article>`;
  }

  function toneLabel(tone) {
    return {
      blocked: "BLOCKED",
      waiting: "WAITING",
      paused: "PAUSED",
      ready: "READY",
    }[tone] || "INFO";
  }

  function ensureAnalysisStatus() {
    const panel = qs('[data-panel="analysis"]');
    const timing = panel?.querySelector(".timing-strip");
    if (!panel || qs("#currentResearchStatus")) return;

    const section = document.createElement("section");
    section.id = "currentResearchStatus";
    section.className = "current-status-section";
    section.innerHTML = `<div class="current-status-heading">
      <div>
        <span class="eyebrow">CURRENT CONTROL BLOCK</span>
        <h2>現在先做資料進件，不產生正式投注建議</h2>
        <p>Wyatt 已完成真實檔 aggregate audit 並正式 blocked；Eoin 已通過 cross-source audit、adapter self-test 與 full adapter execution preflight。完整 Eoin bundle execution 仍關閉；市場 PIT odds 尚未解鎖，因此 CLV、EV、ROI、Drawdown 與投注決策層仍關閉。</p>
      </div>
      <div class="current-status-pill"><span>STAKE</span><strong>${STATUS.stake}</strong></div>
    </div>
    <div class="current-status-grid">
      ${statusCard("WYATT", "SQLite / DuckDB 不再重跑同一份", "實體檔與 235-table metadata 不一致，不能作為 2023-24 secondary source qualification。", "blocked", [
        "SQLite: 16 tables, latest game date 2023-06-12",
        "DuckDB: 12 KB empty shell",
        "2023-24 pilot games: 0",
      ])}
      ${statusCard("EOIN", "Full adapter preflight 已建立", "Eoin 現在可跑 aggregate-only preflight；完整 bundle execution 仍關閉，下一步必須另立 execution policy。", "ready", [
        "Matched games: 1,230 / 1,230",
        "Adapter self-test: passed",
        "Preflight: ready but disabled",
        "Player boxscore: coverage-only",
      ])}
      ${statusCard("MARKET", "PIT odds line 暫停", "沒有合法且可核對 timestamp / bookmaker semantics 的 odds source 前，不做 market backtest。", "paused", [
        "No paid pilot approved",
        "No CLV / ROI / Drawdown claim",
        "Manual odds calculator remains research-only",
      ])}
    </div>`;

    if (timing) timing.insertAdjacentElement("afterend", section);
    else panel.prepend(section);
  }

  function ensureSourceQueue() {
    const panel = qs('[data-panel="sources"]');
    if (!panel || qs("#secondarySourceQueue")) return;
    const modelStatus = qs("#modelRegistryStatus", panel);
    const hero = qs(".sources-hero", panel);
    const section = document.createElement("section");
    section.id = "secondarySourceQueue";
    section.className = "storage-card current-source-queue";
    section.innerHTML = `<div>
      <span class="eyebrow">SECONDARY SOURCE QUEUE</span>
      <h2>資料來源進件分工</h2>
      <p>系統只跑 aggregate census、internal qualification 與 cross-source frozen gates，不把原始資料 commit 進 GitHub。</p>
    </div>
    <div class="registry-grid">
      <article class="registry-card restricted">
        <div><span>Wyatt Walsh</span><em>STRUCTURAL_BLOCKED</em></div>
        <h2>同一份 SQLite / DuckDB 停止重試</h2>
        <dl>
          <div><dt>SQLite</dt><dd>16 tables, ends 2023-06-12</dd></div>
          <div><dt>DuckDB</dt><dd>12 KB empty shell</dd></div>
          <div><dt>重開條件</dt><dd>必須是 materially new bundle</dd></div>
        </dl>
      </article>
      <article class="registry-card licensed">
        <div><span>Eoin A Moore</span><em>ROLE_LIMITED_ELIGIBLE</em></div>
        <h2>full adapter execution preflight 已建立</h2>
        <dl>
          <div><dt>已完成</dt><dd>predeclaration + self-test + preflight</dd></div>
          <div><dt>下一步</dt><dd>separate execution policy only</dd></div>
          <div><dt>限制</dt><dd>full adapter execution disabled</dd></div>
        </dl>
      </article>
      <article class="registry-card odds">
        <div><span>Odds</span><em>PAUSED</em></div>
        <h2>市場資料線維持關閉</h2>
        <dl>
          <div><dt>缺口</dt><dd>lawful PIT bookmaker odds</dd></div>
          <div><dt>不能宣稱</dt><dd>CLV, EV, ROI, Drawdown</dd></div>
          <div><dt>Stake</dt><dd>0</dd></div>
        </dl>
      </article>
    </div>`;

    if (modelStatus) modelStatus.insertAdjacentElement("afterend", section);
    else if (hero) hero.insertAdjacentElement("afterend", section);
    else panel.prepend(section);
  }

  function updateValidationCopy() {
    const panel = qs('[data-panel="validation"]');
    if (!panel) return;
    const title = qs(".view-hero h1", panel);
    const copy = qs(".view-hero p", panel);
    const card = qs(".view-hero .state-card", panel);
    setText(title, "研究驗證中心");
    setText(copy, "Historical model 已小幅優於 Elo，但在 1,894 場 closing benchmark 明顯輸給 Closing Market。PIT odds join 前，網站只保留研究展示與資料進件流程。");
    if (card) {
      const strong = qs("strong", card);
      const small = qs("small", card);
      setText(strong, "Pre-Market-Backtest");
      setText(small, "正式投注模式關閉");
    }
  }

  function apply() {
    ensureStylesheet();
    ensureMarketTableSorting();
    ensureHeader();
    updateRail();
    ensureAnalysisStatus();
    ensureSourceQueue();
    updateValidationCopy();
    document.documentElement.dataset.currentResearchStatus = "applied";
  }

  function boot() {
    apply();
    [150, 500, 1000, 2000, 4000].forEach((delay) => window.setTimeout(apply, delay));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
}());
