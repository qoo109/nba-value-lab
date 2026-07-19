"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function formatDate(value) {
    if (!value) return { date: "—", time: "—" };
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return { date: "—", time: "—" };
    return {
      date: new Intl.DateTimeFormat("zh-TW", { timeZone: "Asia/Taipei", month: "2-digit", day: "2-digit" }).format(date),
      time: new Intl.DateTimeFormat("zh-TW", { timeZone: "Asia/Taipei", hour: "2-digit", minute: "2-digit", hour12: false }).format(date),
    };
  }

  function eventMeta(record) {
    if (record.won !== null && record.won !== undefined) {
      return { label: record.won ? "賽果確認・勝" : "賽果確認・負", tone: record.won ? "positive" : "negative" };
    }
    if (record.evaluation_stage === "Closing") return { label: "Closing／CLV", tone: "neutral" };
    if (record.change_type === "fundamental_update") return { label: "基本面更新", tone: "warning" };
    if (record.change_type === "price_only") return { label: "賠率更新", tone: "info" };
    if (record.evaluation_stage === "T-5m") return { label: "T−5m 最終複核", tone: "strong" };
    if (record.evaluation_stage === "T-60m") return { label: "T−60m 鎖定", tone: "strong" };
    return { label: record.evaluation_stage || "研究快照", tone: "neutral" };
  }

  function probability(record) {
    const value = v5.modules.history.numeric(record.p_conservative);
    return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
  }

  function odds(record) {
    const value = v5.modules.history.numeric(record.target_odds);
    return value === null ? "—" : value.toFixed(3);
  }

  function clv(record) {
    const value = v5.modules.history.numeric(record.clv_odds);
    if (value === null) return "—";
    return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
  }

  function matchesFilters(record) {
    const stage = document.querySelector("#historyStageFilter")?.value || "全部";
    const grade = document.querySelector("#historyGradeFilter")?.value || "全部";
    const query = (document.querySelector("#historySearch")?.value || "").trim().toLowerCase();
    const stageOk = stage === "全部" || record.evaluation_stage === stage;
    const gradeOk = grade === "全部" || record.g_grade === grade;
    const haystack = [record.game_id, record.selection_team_id, record.prediction_id, record.price_evaluation_id, record.main_status]
      .filter(Boolean).join(" ").toLowerCase();
    return stageOk && gradeOk && (!query || haystack.includes(query));
  }

  function item(record) {
    const format = v5.modules.format;
    const stamp = formatDate(v5.modules.history.eventTime(record));
    const meta = eventMeta(record);
    const model = `V${record.model_v || "—"} × G${record.model_g || "—"}`;
    const team = format.escapeHtml(record.selection_team_id || record.target || "—");
    const game = format.escapeHtml(record.game_id || "—");
    const status = format.escapeHtml(record.main_status || (record.ui_priority_candidate ? "網站優先候選" : "一般研究紀錄"));
    const id = format.escapeHtml(record.price_evaluation_id || record.prediction_id || "—");
    return `<article class="v51-timeline-item tone-${meta.tone}">
      <div class="v51-timeline-time"><strong>${stamp.time}</strong><span>${stamp.date}</span></div>
      <div class="v51-timeline-dot" aria-hidden="true"></div>
      <div class="v51-timeline-card">
        <div class="v51-timeline-head"><span class="v51-event-chip">${format.escapeHtml(meta.label)}</span><span>${model}</span></div>
        <div class="v51-timeline-main"><div><strong>${team}</strong><span>${game}</span></div><div><strong>${probability(record)}</strong><span>保守勝率</span></div></div>
        <div class="v51-timeline-metrics"><span>賠率 <strong>${odds(record)}</strong></span><span>G1 <strong>${format.escapeHtml(record.g_grade || "—")}</strong></span><span>CLV <strong>${clv(record)}</strong></span></div>
        <div class="v51-timeline-foot"><span>${status}</span><code>${id}</code></div>
      </div>
    </article>`;
  }

  function ensureShell() {
    const wrap = document.querySelector(".research-table-wrap");
    if (!wrap || document.querySelector("#v51ResearchTimeline")) return;
    wrap.classList.add("v51-table-fallback");
    const timeline = document.createElement("div");
    timeline.id = "v51ResearchTimeline";
    timeline.className = "v51-research-timeline";
    wrap.insertAdjacentElement("afterend", timeline);
  }

  function render() {
    ensureShell();
    const target = document.querySelector("#v51ResearchTimeline");
    if (!target) return;
    const records = Array.isArray(window.__NBA_RESEARCH_HISTORY__?.records) ? window.__NBA_RESEARCH_HISTORY__.records : [];
    const filtered = records.filter(matchesFilters).sort((a, b) => v5.modules.history.eventTime(b).localeCompare(v5.modules.history.eventTime(a)));
    target.innerHTML = filtered.length
      ? filtered.map(item).join("")
      : `<div class="v51-timeline-empty"><strong>尚無正式研究事件</strong><span>示範 slate 不會出現在 Timeline。正式 T−60m、T−5m、Closing 與賽果追加後才會顯示。</span></div>`;
  }

  function afterRender() {
    ensureShell();
    render();
    ["#historyStageFilter", "#historyGradeFilter", "#historySearch"].forEach((selector) => {
      const node = document.querySelector(selector);
      if (!node || node.dataset.v51TimelineBound) return;
      node.dataset.v51TimelineBound = "true";
      node.addEventListener("input", render);
      node.addEventListener("change", render);
    });
  }

  v5.modules.researchTimeline = { afterRender, render };
}());
