(() => {
  "use strict";

  const DATA_URL = "./data/public/odds-alignment-summary-2025-26-v1.json";

  function formatNumber(value, digits = 0) {
    return new Intl.NumberFormat("zh-TW", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(value);
  }

  function card(label, value, note = "") {
    return `
      <article class="odds-card">
        <div class="odds-card__label">${label}</div>
        <div class="odds-card__value">${value}</div>
        ${note ? `<div class="odds-card__note">${note}</div>` : ""}
      </article>`;
  }

  function render(data) {
    const summary = data.summary;
    const root = document.querySelector("[data-odds-alignment-root]");
    const status = document.querySelector("[data-odds-alignment-status]");
    if (!root || !status) return;

    status.textContent = "公開安全摘要已載入";
    status.dataset.state = "ready";

    root.innerHTML = `
      <section class="odds-grid" aria-label="賠率時間對齊摘要">
        ${card("正規賽成功配對", formatNumber(summary.regular_season_events_matched), "未配對 0 場")}
        ${card("T-60 ±5 分鐘候選", formatNumber(summary.t60_candidate_counts["5"]), "批次候選，非精確報價時間")}
        ${card("T-60 ±15 分鐘候選", formatNumber(summary.t60_candidate_counts["15"]))}
        ${card("T-60 ±30 分鐘候選", formatNumber(summary.t60_candidate_counts["30"]))}
        ${card("T-60 ±60 分鐘候選", formatNumber(summary.t60_candidate_counts["60"]))}
        ${card("T-60 中位誤差", `${formatNumber(summary.median_t60_batch_error_minutes, 2)} 分鐘`, "原始 timestamp 保留")}
      </section>
      <section class="odds-panel">
        <h2>目前可以做什麼</h2>
        <p>網站可顯示官方賽程配對、資料覆蓋與批次時間品質。公開檔案不包含逐筆賠率、來源連結、source event ID 或 collector timestamp。</p>
      </section>
      <section class="odds-panel odds-panel--warning">
        <h2>仍未解鎖</h2>
        <p>provider-origin quote time、精確 T-60、正式 Point-in-Time、Market Backtest、CLV、ROI 與投注優勢聲明仍未通過。Formal Stake 維持 ${summary.formal_stake}。</p>
      </section>`;
  }

  async function init() {
    const status = document.querySelector("[data-odds-alignment-status]");
    try {
      const response = await fetch(DATA_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.formal_state !== "PUBLIC_SAFE_ODDS_ALIGNMENT_METADATA_VALID") {
        throw new Error("Unexpected public data state");
      }
      render(data);
    } catch (error) {
      if (status) {
        status.textContent = `資料載入失敗：${error.message}`;
        status.dataset.state = "error";
      }
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
