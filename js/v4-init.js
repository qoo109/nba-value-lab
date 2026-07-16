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
