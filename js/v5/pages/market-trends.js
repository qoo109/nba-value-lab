"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function decimal(value, digits = 3) {
    return value == null || !Number.isFinite(value) ? "—" : value.toFixed(digits);
  }

  function percentage(value) {
    return value == null || !Number.isFinite(value) ? "—" : `${(value * 100).toFixed(1)}%`;
  }

  function deltaText(values, scale = 1, suffix = "") {
    const value = v5.modules.sparkline.delta(values);
    if (value == null) return "尚無變化";
    const scaled = value * scale;
    return `${scaled >= 0 ? "+" : ""}${scaled.toFixed(scale === 100 ? 1 : 3)}${suffix}`;
  }

  function card(group) {
    const history = v5.modules.history;
    const records = group.records;
    const latest = records.at(-1);
    const probability = history.values(records, "p_neutral");
    const odds = history.values(records, "target_odds");
    const format = v5.modules.format;
    const team = format.escapeHtml(latest.selection_team_id || latest.target || "—");
    const game = format.escapeHtml(latest.game_id || "—");
    const stages = [...new Set(records.map((record) => record.evaluation_stage).filter(Boolean))].join(" → ");
    return `<article class="v52-market-trend-card">
      <div class="v52-market-title"><div><strong>${team}</strong><span>${game}</span></div><em>${records.length} 個快照</em></div>
      <div class="v52-market-chart"><div><span>中性勝率</span><strong>${percentage(probability.at(-1))}</strong></div>${v5.modules.sparkline.svg(probability, { label: `${team} 中性勝率趨勢`, height: 56 })}<small>變化 ${deltaText(probability, 100, "pp")}</small></div>
      <div class="v52-market-chart"><div><span>目標賠率</span><strong>${decimal(odds.at(-1))}</strong></div>${v5.modules.sparkline.svg(odds, { label: `${team} 賠率趨勢`, height: 56 })}<small>變化 ${deltaText(odds)}</small></div>
      <footer><span>${format.escapeHtml(stages || "研究快照")}</span><span>${latest.main_status ? format.escapeHtml(latest.main_status) : "一般研究"}</span></footer>
    </article>`;
  }

  function ensureShell() {
    const timeline = document.querySelector("#v51ResearchTimeline");
    if (!timeline || document.querySelector("#v52MarketTrends")) return;
    const section = document.createElement("section");
    section.id = "v52MarketTrends";
    section.className = "v52-market-trends";
    section.innerHTML = `<div class="section-heading"><div><span class="eyebrow">ODDS × PROBABILITY</span><h2>單場勝率與賠率軌跡</h2><p>同一場、同一選擇方至少累積兩個快照後才顯示，方便確認賠率變動有沒有錯誤改動模型勝率。</p></div></div><div class="v52-market-grid" id="v52MarketTrendGrid"></div>`;
    timeline.parentNode.insertBefore(section, timeline);
  }

  function render() {
    ensureShell();
    const target = document.querySelector("#v52MarketTrendGrid");
    if (!target) return;
    const records = Array.isArray(window.__NBA_RESEARCH_HISTORY__?.records) ? window.__NBA_RESEARCH_HISTORY__.records : [];
    const groups = v5.modules.history.groupEvaluations(records)
      .filter((group) => group.records.length >= 2)
      .slice(0, 8);
    target.innerHTML = groups.length
      ? groups.map(card).join("")
      : `<div class="v52-trends-empty"><strong>尚無雙快照趨勢</strong><span>同場累積 T−60m、T−5m 或 Closing 等至少兩個正式快照後，才會出現勝率與賠率軌跡。</span></div>`;
  }

  function afterRender() {
    ensureShell();
    render();
  }

  v5.modules.marketTrends = { afterRender, render };
}());
