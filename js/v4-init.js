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

function loadV46Coordination() {
  if (typeof vDecision === "function" && typeof gDecision === "function") return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-v46-coordination]');
    if (existing) {
      existing.addEventListener("load", resolve, { once: true });
      existing.addEventListener("error", reject, { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "./js/v4-6-model-coordination.js?v=4.6";
    script.dataset.v46Coordination = "true";
    script.onload = resolve;
    script.onerror = () => reject(new Error("Unable to load V4.6 model coordination"));
    document.head.appendChild(script);
  });
}

function updateV46Shell() {
  document.title = `NBA Value Lab V4.6｜${activeModelLabel()}`;
  const header = document.querySelector(".header-status");
  if (header) header.innerHTML = `<span class="status-dot"></span>V4.6・${activeModelLabel()}`;
  const footerVersion = document.querySelector("footer > span:first-child");
  if (footerVersion) footerVersion.textContent = "NBA VALUE LAB V4.6";
  const methodTitle = document.querySelector(".method-card h2");
  if (methodTitle) methodTitle.textContent = "V3.1 與 G1 分開判定，由協調層統整";
}

async function init() {
  loadReadabilityStyles();
  await loadV46Coordination();
  await loadModelRegistry();
  updateV46Shell();
  applyTheme(document.documentElement.dataset.theme || "light");
  renderTopPick();
  renderTable();
  renderCards();
  renderCalculatorOptions();
  renderModelRegistryStatus();
  bindEvents();
  updateCalculator(true);
  document.documentElement.dataset.modelVersion = activeModelLabel();
  document.documentElement.dataset.appVersion = "V4.6";
}

init().catch((error) => {
  console.error("NBA Value Lab initialization failed:", error);
  const header = document.querySelector(".header-status");
  if (header) header.innerHTML = '<span class="status-dot"></span>V4.6・初始化失敗';
});
