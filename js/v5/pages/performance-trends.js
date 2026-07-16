"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function percent(value, digits = 1) {
    if (value == null || !Number.isFinite(value)) return "—";
    return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
  }

  function signed(value, suffix = "") {
    if (value == null || !Number.isFinite(value)) return "—";
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}${suffix}`;
  }

  function chart(label, value, note, values, tone = "neutral") {
    return `<article class="v52-trend-card tone-${tone}">
      <div class="v52-trend-head"><span>${label}</span><strong>${value}</strong></div>
      ${v5.modules.sparkline.svg(values, { label })}
      <small>${note}</small>
    </article>`;
  }

  function ensureShell() {
    const performance = document.querySelector("#v51PerformanceDashboard");
    if (!performance || document.querySelector("#v52PerformanceTrends")) return;
    const section = document.createElement("section");
    section.id = "v52PerformanceTrends";
    section.className = "v52-trends-section";
    section.innerHTML = `<div class="section-heading"><div><span class="eyebrow">PERFORMANCE TRENDS</span><h2>歷史績效趨勢</h2><p>只使用正式主要場次，呈現紙上淨值、累積命中率與 Closing 價值變化。</p></div></div><div class="v52-trend-grid" id="v52PerformanceTrendGrid"></div>`;
    performance.insertAdjacentElement("afterend", section);
  }

  function render() {
    ensureShell();
    const target = document.querySelector("#v52PerformanceTrendGrid");
    if (!target) return;
    const records = Array.isArray(window.__NBA_RESEARCH_HISTORY__?.records) ? window.__NBA_RESEARCH_HISTORY__.records : [];
    const history = v5.modules.history;
    const resolved = history.latestResolvedMainRecords(records);
    if (!resolved.length) {
      target.innerHTML = `<div class="v52-trends-empty"><strong>尚無可繪製績效曲線</strong><span>正式主要場次累積賽果後，才會顯示淨值、命中率與 CLV 趨勢。</span></div>`;
      return;
    }

    const equity = history.cumulativeEquity(records);
    const hitRate = history.cumulativeHitRate(records);
    const clv = resolved.map((record) => history.numeric(record.clv_odds)).filter((value) => value !== null);
    const equityDelta = v5.modules.sparkline.delta(equity);
    const hitLatest = hitRate.at(-1) ?? null;
    const clvAverage = clv.length ? clv.reduce((sum, value) => sum + value, 0) / clv.length : null;

    target.innerHTML = [
      chart("紙上淨值", signed(equity.at(-1), "u"), `本段變化 ${signed(equityDelta, "u")}・固定 1 單位`, equity, (equity.at(-1) || 0) >= 0 ? "positive" : "negative"),
      chart("累積命中率", percent(hitLatest), `正式主要場次 ${resolved.length} 場`, hitRate, hitLatest >= 0.5 ? "positive" : "warning"),
      chart("CLV 序列", percent(clvAverage), `已有 Closing ${clv.length} 筆`, clv, clvAverage == null ? "neutral" : clvAverage >= 0 ? "positive" : "negative"),
    ].join("");
  }

  function afterRender() {
    ensureShell();
    render();
  }

  v5.modules.performanceTrends = { afterRender, render };
}());
