function handleOpenTarget(target) {
  const node = target.closest("[data-open-candidate]");
  if (!node) return;
  const candidate = candidates.find((item) => item.id === node.dataset.openCandidate);
  if (candidate) showDetail(candidate);
}

function bindEvents() {
  $$(".tab-button").forEach((button) => button.addEventListener("click", () => {
    $$(".tab-button").forEach((item) => item.classList.toggle("active", item === button));
    $$('[data-panel]').forEach((panel) => { panel.hidden = panel.dataset.panel !== button.dataset.tab; });
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

function loadScriptOnce(src, marker, ready) {
  if (ready()) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[${marker}]`);
    if (existing) {
      if (ready()) resolve();
      else {
        existing.addEventListener("load", resolve, { once: true });
        existing.addEventListener("error", reject, { once: true });
      }
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.setAttribute(marker, "true");
    script.onload = resolve;
    script.onerror = () => reject(new Error(`Unable to load ${src}`));
    document.head.appendChild(script);
  });
}

function loadStylesheetOnce(href, marker) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`link[${marker}]`);
    if (existing) {
      resolve();
      return;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.setAttribute(marker, "true");
    link.onload = resolve;
    link.onerror = () => reject(new Error(`Unable to load ${href}`));
    document.head.appendChild(link);
  });
}

function loadV46Coordination() {
  return loadScriptOnce("./js/v4-6-model-coordination.js?v=5.2", "data-v46-coordination", () => typeof vDecision === "function" && typeof gDecision === "function");
}

function loadV410MultiMain() {
  return loadScriptOnce("./js/v4-10-multi-main.js?v=5.2", "data-v410-multi-main", () => typeof renderMultiMainSummary === "function");
}

function loadV47ResearchLog() {
  return loadScriptOnce("./js/v4-7-research-log.js?v=5.2", "data-v47-research-log", () => typeof initResearchLog === "function");
}

function loadV49LockStatus() {
  return loadScriptOnce("./js/v4-8-lock-status.js?v=5.2", "data-v49-lock-status", () => typeof initT60LockStatus === "function");
}

async function loadV5Ui() {
  await Promise.all([
    loadStylesheetOnce("./css/v5-tokens.css?v=5.2", "data-v5-tokens"),
    loadStylesheetOnce("./css/v5-layout.css?v=5.2", "data-v5-layout"),
    loadStylesheetOnce("./css/v5-components.css?v=5.2", "data-v5-components"),
    loadStylesheetOnce("./css/v5-theme-p1.css?v=5.2", "data-v51-theme"),
    loadStylesheetOnce("./css/v5-research-p1.css?v=5.2", "data-v51-research"),
    loadStylesheetOnce("./css/v5-mobile-p1.css?v=5.2", "data-v51-mobile"),
    loadStylesheetOnce("./css/v5-routing-p2.css?v=5.2", "data-v52-routing"),
    loadStylesheetOnce("./css/v5-trends-p2.css?v=5.2", "data-v52-trends"),
    loadStylesheetOnce("./css/v5-compact-decision.css?v=5.3.1", "data-v521-compact-decision"),
    loadStylesheetOnce("./css/v5-density-v53.css?v=5.3", "data-v53-density"),
    loadStylesheetOnce("./css/v5-decision-group-v532.css?v=5.3.2", "data-v532-decision-group"),
    loadStylesheetOnce("./css/v5-explanations-v533.css?v=5.3.3", "data-v533-explanations"),
  ]);
  await loadScriptOnce("./js/v5/core/namespace.js?v=5.2", "data-v5-namespace", () => Boolean(window.NBAVL?.v5));
  await loadScriptOnce("./js/v5/utils/format.js?v=5.2", "data-v5-format", () => Boolean(window.NBAVL?.v5?.modules?.format));
  await loadScriptOnce("./js/v5/utils/history.js?v=5.2", "data-v52-history", () => Boolean(window.NBAVL?.v5?.modules?.history));
  await loadScriptOnce("./js/v5/utils/sparkline.js?v=5.2", "data-v52-sparkline", () => Boolean(window.NBAVL?.v5?.modules?.sparkline));
  await loadScriptOnce("./js/v5/components/cards.js?v=5.3.1", "data-v5-cards", () => Boolean(window.NBAVL?.v5?.modules?.cards));
  await loadScriptOnce("./js/v5/components/drawer.js?v=5.2", "data-v5-drawer", () => Boolean(window.NBAVL?.v5?.modules?.drawer));
  await loadScriptOnce("./js/v5/pages/dashboard.js?v=5.3.3", "data-v5-dashboard", () => Boolean(window.NBAVL?.v5?.modules?.dashboard));
  await loadScriptOnce("./js/v5/pages/performance-dashboard.js?v=5.2", "data-v51-performance", () => Boolean(window.NBAVL?.v5?.modules?.performanceDashboard));
  await loadScriptOnce("./js/v5/pages/performance-trends.js?v=5.2", "data-v52-performance-trends", () => Boolean(window.NBAVL?.v5?.modules?.performanceTrends));
  await loadScriptOnce("./js/v5/pages/research-timeline.js?v=5.2", "data-v51-timeline", () => Boolean(window.NBAVL?.v5?.modules?.researchTimeline));
  await loadScriptOnce("./js/v5/pages/market-trends.js?v=5.2", "data-v52-market-trends", () => Boolean(window.NBAVL?.v5?.modules?.marketTrends));
  await loadScriptOnce("./js/v5/core/router.js?v=5.2", "data-v52-router", () => Boolean(window.NBAVL?.v5?.modules?.router));
  await loadScriptOnce("./js/v5/bootstrap.js?v=5.2", "data-v5-bootstrap", () => typeof window.NBAVL?.v5?.prepare === "function");
}

function updateFallbackShell() {
  document.title = `NBA Value Lab V4.10｜${activeModelLabel()}`;
  const header = document.querySelector(".header-status");
  if (header) header.innerHTML = `<span class="status-dot"></span>V4.10・${activeModelLabel()}・主要 2／最多 3`;
  const footerVersion = document.querySelector("footer > span:first-child");
  if (footerVersion) footerVersion.textContent = "NBA VALUE LAB V4.10";
}

async function init() {
  loadReadabilityStyles();
  await loadV46Coordination();
  await loadModelRegistry();
  await loadV410MultiMain();
  await loadV47ResearchLog();
  await loadV49LockStatus();

  let v5Ready = false;
  try {
    await loadV5Ui();
    window.NBAVL.v5.prepare();
    v5Ready = true;
  } catch (error) {
    console.warn("V5 UI failed to load; continuing with V4.10 UI:", error);
    updateFallbackShell();
  }

  applyTheme(document.documentElement.dataset.theme || "light");
  renderTopPick();
  renderMultiMainSummary();
  renderTable();
  renderCards();
  renderCalculatorOptions();
  renderModelRegistryStatus();
  await initResearchLog();
  await initT60LockStatus();
  if (v5Ready) window.NBAVL.v5.afterRender();
  bindEvents();
  updateCalculator(true);
  document.documentElement.dataset.modelVersion = activeModelLabel();
  document.documentElement.dataset.appVersion = v5Ready ? "V5.3.3" : "V4.10";
}

init().catch((error) => {
  console.error("NBA Value Lab initialization failed:", error);
  const header = document.querySelector(".header-status");
  if (header) header.innerHTML = '<span class="status-dot"></span>初始化失敗';
});
