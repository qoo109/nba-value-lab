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

function loadV46Coordination() {
  return loadScriptOnce(
    "./js/v4-6-model-coordination.js?v=4.8",
    "data-v46-coordination",
    () => typeof vDecision === "function" && typeof gDecision === "function",
  );
}

function loadV47ResearchLog() {
  return loadScriptOnce(
    "./js/v4-7-research-log.js?v=4.8",
    "data-v47-research-log",
    () => typeof initResearchLog === "function",
  );
}

function loadV48LockStatus() {
  return loadScriptOnce(
    "./js/v4-8-lock-status.js?v=4.8",
    "data-v48-lock-status",
    () => typeof initT60LockStatus === "function",
  );
}

function updateV48Shell() {
  document.title = `NBA Value Lab V4.8｜${activeModelLabel()}`;
  const header = document.querySelector(".header-status");
  if (header) header.innerHTML = `<span class="status-dot"></span>V4.8・${activeModelLabel()}`;
  const footerVersion = document.querySelector("footer > span:first-child");
  if (footerVersion) footerVersion.textContent = "NBA VALUE LAB V4.8";
  const methodTitle = document.querySelector(".method-card h2");
  if (methodTitle) methodTitle.textContent = "V3.1 與 G1 分開判定，由 T−60m 鎖定流程保存";
}

async function init() {
  loadReadabilityStyles();
  await loadV46Coordination();
  await loadModelRegistry();
  await loadV47ResearchLog();
  await loadV48LockStatus();
  updateV48Shell();
  applyTheme(document.documentElement.dataset.theme || "light");
  renderTopPick();
  renderTable();
  renderCards();
  renderCalculatorOptions();
  renderModelRegistryStatus();
  await initResearchLog();
  await initT60LockStatus();
  bindEvents();
  updateCalculator(true);
  document.documentElement.dataset.modelVersion = activeModelLabel();
  document.documentElement.dataset.appVersion = "V4.8";
}

init().catch((error) => {
  console.error("NBA Value Lab initialization failed:", error);
  const header = document.querySelector(".header-status");
  if (header) header.innerHTML = '<span class="status-dot"></span>V4.8・初始化失敗';
});
