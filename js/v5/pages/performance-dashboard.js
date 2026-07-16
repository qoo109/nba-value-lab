"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function eventTime(record) {
    return record.price_evaluated_at || record.evaluation_cutoff || record.predicted_at || record.observed_at || "";
  }

  function latestResolvedMainRecords(records) {
    const latest = new Map();
    records
      .filter((record) => record.main_candidate && typeof record.won === "boolean")
      .sort((a, b) => eventTime(a).localeCompare(eventTime(b)))
      .forEach((record) => latest.set(record.prediction_id || record.price_evaluation_id, record));
    return [...latest.values()].sort((a, b) => eventTime(a).localeCompare(eventTime(b)));
  }

  function calculate(records) {
    const resolved = latestResolvedMainRecords(records);
    if (!resolved.length) {
      return { sample: 0, roiSample: 0, wins: 0, losses: 0, hitRate: null, roi: null, avgClv: null, brier: null, maxDrawdown: null };
    }

    let profit = 0;
    let equity = 0;
    let peak = 0;
    let maxDrawdown = 0;
    let roiSample = 0;
    const clvValues = [];
    const brierValues = [];
    let wins = 0;

    resolved.forEach((record) => {
      const won = Boolean(record.won);
      const odds = Number(record.target_odds);
      const validOdds = Number.isFinite(odds) && odds > 1;
      if (won) wins += 1;

      if (validOdds) {
        const result = won ? odds - 1 : -1;
        roiSample += 1;
        profit += result;
        equity += result;
        peak = Math.max(peak, equity);
        maxDrawdown = Math.max(maxDrawdown, peak - equity);
      }

      if (record.clv_odds != null && Number.isFinite(Number(record.clv_odds))) clvValues.push(Number(record.clv_odds));
      if (record.p_neutral != null && Number.isFinite(Number(record.p_neutral))) {
        const outcome = won ? 1 : 0;
        brierValues.push((Number(record.p_neutral) - outcome) ** 2);
      }
    });

    return {
      sample: resolved.length,
      roiSample,
      wins,
      losses: resolved.length - wins,
      hitRate: wins / resolved.length,
      roi: roiSample ? profit / roiSample : null,
      avgClv: clvValues.length ? clvValues.reduce((sum, value) => sum + value, 0) / clvValues.length : null,
      brier: brierValues.length ? brierValues.reduce((sum, value) => sum + value, 0) / brierValues.length : null,
      maxDrawdown: roiSample ? maxDrawdown : null,
    };
  }

  function percent(value, digits = 1) {
    if (value == null || !Number.isFinite(value)) return "—";
    return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
  }

  function number(value, digits = 3) {
    return value == null || !Number.isFinite(value) ? "—" : value.toFixed(digits);
  }

  function card(label, value, note, tone = "neutral") {
    return `<article class="v51-performance-card tone-${tone}"><span>${label}</span><strong>${value}</strong><small>${note}</small></article>`;
  }

  function ensureShell() {
    const panel = document.querySelector('[data-panel="research"]');
    const summary = panel?.querySelector(".research-log-summary");
    if (!panel || !summary || document.querySelector("#v51PerformanceDashboard")) return;
    const section = document.createElement("section");
    section.id = "v51PerformanceDashboard";
    section.className = "v51-performance";
    section.innerHTML = `<div class="section-heading"><div><span class="eyebrow">PAPER PERFORMANCE</span><h2>歷史績效 Dashboard</h2><p>只統計已有賽果的正式主要場次；同一 prediction 的多次價格評估只計一次。</p></div><span class="v51-sample-label" id="v51PerformanceSample">樣本 0</span></div><div class="v51-performance-grid" id="v51PerformanceGrid"></div>`;
    summary.insertAdjacentElement("afterend", section);
  }

  function render() {
    ensureShell();
    const records = Array.isArray(window.__NBA_RESEARCH_HISTORY__?.records) ? window.__NBA_RESEARCH_HISTORY__.records : [];
    const stats = calculate(records);
    const grid = document.querySelector("#v51PerformanceGrid");
    const sample = document.querySelector("#v51PerformanceSample");
    if (!grid || !sample) return;
    sample.textContent = `樣本 ${stats.sample}`;

    if (!stats.sample) {
      grid.innerHTML = `<div class="v51-performance-empty"><strong>等待正式結果累積</strong><span>目前不以示範賽事製造命中率或 ROI。正式主要場次有賽果後才開始顯示。</span></div>`;
      return;
    }

    grid.innerHTML = [
      card("命中率", percent(stats.hitRate), `${stats.wins} 勝 ${stats.losses} 負`, stats.hitRate >= 0.5 ? "positive" : "negative"),
      card("紙上 ROI", percent(stats.roi), `有效賠率樣本 ${stats.roiSample}；固定 1 單位`, stats.roi == null ? "neutral" : stats.roi >= 0 ? "positive" : "negative"),
      card("平均 CLV", percent(stats.avgClv), "只使用已有 Closing 的紀錄", stats.avgClv == null ? "neutral" : stats.avgClv >= 0 ? "positive" : "negative"),
      card("Brier Score", number(stats.brier), "越低越好；以中性勝率計算"),
      card("最大回撤", stats.maxDrawdown == null ? "—" : `${stats.maxDrawdown.toFixed(2)}u`, "只使用具有有效賠率的紙上序列", stats.maxDrawdown > 3 ? "warning" : "neutral"),
      card("有效樣本", String(stats.sample), "正式主要場次且已有賽果"),
    ].join("");
  }

  function afterRender() {
    ensureShell();
    render();
  }

  v5.modules.performanceDashboard = { afterRender, render, calculate };
}());
