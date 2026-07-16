"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function wrapSection(section, label, options = {}) {
    if (!section || section.closest(".v5-disclosure")) return;
    const details = document.createElement("details");
    details.className = `v5-disclosure ${options.className || ""}`.trim();
    details.open = Boolean(options.open);
    const summary = document.createElement("summary");
    summary.innerHTML = `<span>${label}</span><small>${options.hint || "點擊展開"}</small>`;
    section.parentNode.insertBefore(details, section);
    details.append(summary, section);
  }

  function updateNavigation() {
    const labels = {
      analysis: "今日分析",
      candidates: "主要場次",
      validation: "模型驗證",
      sources: "資料來源",
      research: "研究紀錄",
    };
    document.querySelectorAll(".tab-button").forEach((button) => {
      if (labels[button.dataset.tab]) button.textContent = labels[button.dataset.tab];
    });
  }

  function sectionShell(section) {
    if (!section) return null;
    return section.closest(".v5-disclosure") || section.closest(".v5-model-disclosure") || section;
  }

  function reorderAnalysis(analysis) {
    const market = sectionShell(analysis.querySelector(".market-table-section"));
    if (market?.matches("details")) market.open = true;

    const priorityOrder = [
      analysis.querySelector(".date-rail"),
      analysis.querySelector(".timing-strip"),
      analysis.querySelector(".games-section"),
      market,
      analysis.querySelector(".hero-grid"),
      sectionShell(analysis.querySelector(".calculator")),
      analysis.querySelector(".v5-model-disclosure"),
      sectionShell(analysis.querySelector(".source-card")),
      sectionShell(analysis.querySelector(".weights-card")),
      sectionShell(analysis.querySelector(".pipeline-card")),
    ].filter(Boolean);

    priorityOrder.forEach((section) => analysis.appendChild(section));
    analysis.dataset.sectionOrder = "candidates-market-results-tools-model-sources";
  }

  function simplifyAnalysis() {
    const analysis = document.querySelector('[data-panel="analysis"]');
    if (!analysis) return;
    const heroGrid = analysis.querySelector(".hero-grid");
    const topPick = analysis.querySelector("#topPick");
    if (heroGrid && topPick) {
      heroGrid.classList.add("v5-hero-shell");
      topPick.classList.add("v5-top-pick");
    }

    const method = analysis.querySelector(".method-card");
    if (method && !method.closest(".v5-model-disclosure")) {
      const details = document.createElement("details");
      details.className = "v5-model-disclosure";
      const summary = document.createElement("summary");
      summary.innerHTML = `<span>模型與分級規則</span><small>${activeModelLabel()}</small>`;
      method.parentNode.insertBefore(details, method);
      details.append(summary, method);
    }

    wrapSection(analysis.querySelector(".market-table-section"), "完整市場總表", {
      hint: "Gap、EV、Coverage 與全部雙向候選",
      open: true,
      className: "v5-market-disclosure",
    });
    wrapSection(analysis.querySelector(".calculator"), "賠率即時試算", { hint: "只重算價格，不改模型勝率" });
    wrapSection(analysis.querySelector(".source-card"), "資料來源策略", { hint: "目標莊家、比較來源與快照" });
    wrapSection(analysis.querySelector(".weights-card"), "證據覆蓋權重", { hint: "資料完整度，不是直接勝率係數" });
    wrapSection(analysis.querySelector(".pipeline-card"), "研究快照流程", { hint: "T−60m、T−5m 與 Closing" });
    reorderAnalysis(analysis);
  }

  function updateCandidatePanel() {
    const panel = document.querySelector('[data-panel="candidates"]');
    if (!panel) return;
    const heroTitle = panel.querySelector(".view-hero h1");
    const heroCopy = panel.querySelector(".view-hero p");
    if (heroTitle) heroTitle.textContent = "主要場次以 2 場為目標，最多 3 場";
    if (heroCopy) heroCopy.textContent = "所有主要場次都必須通過 G1.1 硬 Gate；第 3 場還要通過更嚴格的資料完整度、區間與風險門檻。";

    const stateCards = panel.querySelectorAll(".candidate-summary .state-card");
    if (stateCards[0]) {
      stateCards[0].querySelector("span").textContent = "主要場次";
      stateCards[0].querySelector("small").textContent = "目標 2 場・最多 3 場";
    }
    if (stateCards[1]) {
      stateCards[1].querySelector("span").textContent = "網站優先";
      stateCards[1].querySelector("small").textContent = "非 G1 正式分級";
    }

    const coreHeading = panel.querySelector("#coreCandidateGrid")?.closest(".candidate-tier")?.querySelector("h2");
    const coreHint = panel.querySelector("#coreCandidateGrid")?.closest(".candidate-tier")?.querySelector(".table-hint");
    if (coreHeading) coreHeading.textContent = "主要場次";
    if (coreHint) coreHint.textContent = "前兩場通過全部 Gate；第 3 場需通過額外嚴格門檻";
  }

  function updateResearchPanel() {
    const panel = document.querySelector('[data-panel="research"]');
    if (!panel) return;
    const title = panel.querySelector(".view-hero h1");
    const copy = panel.querySelector(".view-hero p");
    const recordsHeading = panel.querySelector("#historyGeneratedAt")?.closest("section")?.querySelector("h2");
    if (title) title.textContent = "研究 Timeline、績效與價格趨勢";
    if (copy) copy.textContent = "依時間查看鎖定、價格、基本面、Closing 與賽果，並追蹤紙上淨值、CLV、勝率與盤口變化。";
    if (recordsHeading) recordsHeading.textContent = "研究事件 Timeline";
  }

  function updateShell() {
    document.documentElement.classList.add("v5-ui");
    document.documentElement.dataset.uiVersion = "5.3";
    document.documentElement.dataset.visualDensity = "balanced";
    document.title = `NBA Value Lab V5.3｜${activeModelLabel()}`;
    const header = document.querySelector(".header-status");
    if (header) header.innerHTML = `<span class="status-dot"></span>V5.3・${activeModelLabel()}・主要 2／最多 3`;
    const footer = document.querySelector("footer > span:first-child");
    if (footer) footer.textContent = "NBA VALUE LAB V5.3";
  }

  function afterRender() {
    updateShell();
    updateNavigation();
    simplifyAnalysis();
    updateCandidatePanel();
    updateResearchPanel();
    document.querySelector("#multiMainSummary")?.setAttribute("hidden", "");
  }

  v5.modules.dashboard = { afterRender, wrapSection, reorderAnalysis };
}());
