"use strict";

(function () {
  const v5 = window.NBAVL.v5;
  const routes = {
    dashboard: { tab: "analysis", title: "今日分析" },
    picks: { tab: "candidates", title: "主要場次" },
    validation: { tab: "validation", title: "模型驗證" },
    sources: { tab: "sources", title: "資料來源" },
    research: { tab: "research", title: "研究紀錄" },
  };
  const tabToRoute = Object.fromEntries(Object.entries(routes).map(([route, config]) => [config.tab, route]));
  let initialized = false;

  function routeFromLocation() {
    const route = location.hash.replace(/^#\/?/, "").split(/[?&]/)[0];
    return routes[route] ? route : "dashboard";
  }

  function apply(route, options = {}) {
    const resolved = routes[route] ? route : "dashboard";
    const config = routes[resolved];
    document.querySelectorAll(".tab-button").forEach((button) => {
      const active = button.dataset.tab === config.tab;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    document.querySelectorAll("[data-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.panel !== config.tab;
    });
    document.documentElement.dataset.route = resolved;
    document.title = `${config.title}｜NBA Value Lab V5.2`;
    if (options.scroll !== false) window.scrollTo({ top: 0, behavior: options.instant ? "auto" : "smooth" });
    window.dispatchEvent(new CustomEvent("nbavl:route", { detail: { route: resolved, tab: config.tab } }));
    return resolved;
  }

  function navigate(route, options = {}) {
    const resolved = routes[route] ? route : "dashboard";
    const hash = `#/${resolved}`;
    if (options.replace) history.replaceState({ route: resolved }, "", hash);
    else if (location.hash !== hash) history.pushState({ route: resolved }, "", hash);
    apply(resolved, { instant: options.instant, scroll: options.scroll });
  }

  function bind() {
    if (initialized) return;
    initialized = true;
    document.querySelectorAll(".tab-button").forEach((button) => {
      const route = tabToRoute[button.dataset.tab];
      if (!route) return;
      button.dataset.route = route;
      button.addEventListener("click", () => navigate(route));
    });
    window.addEventListener("popstate", () => apply(routeFromLocation(), { instant: true }));
    window.addEventListener("hashchange", () => apply(routeFromLocation(), { instant: true }));
  }

  function init() {
    bind();
    const route = routeFromLocation();
    navigate(route, { replace: !location.hash, instant: true, scroll: false });
  }

  v5.modules.router = { routes, init, apply, navigate, routeFromLocation };
}());
