"use strict";

(function () {
  const LOCKS_URL = "./data/locks/index.json";

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("zh-TW", {
      timeZone: "Asia/Taipei",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  }

  function ensureCard() {
    const panel = document.querySelector('[data-panel="research"]');
    if (!panel || document.querySelector("#t60LockStatus")) return;
    const summary = panel.querySelector(".research-log-summary");
    const card = document.createElement("section");
    card.id = "t60LockStatus";
    card.className = "selection-note";
    card.innerHTML = `
      <strong>T−60m／T−5m 鎖定系統</strong>
      <span id="t60LockStatusText">尚未建立正式鎖定。Fixture 只用於測試，不會寫入研究紀錄。</span>`;
    if (summary) summary.insertAdjacentElement("afterend", card);
    else panel.prepend(card);
  }

  function render(payload) {
    ensureCard();
    const target = document.querySelector("#t60LockStatusText");
    if (!target) return;
    const count = Number(payload?.lock_count || 0);
    if (!count) {
      target.textContent = "尚未建立正式 T−60m／T−5m 鎖定。Fixture 只用於測試，不會寫入研究紀錄。";
      return;
    }
    const latest = Array.isArray(payload.locks) ? payload.locks[0] : null;
    const stage = latest?.evaluation_stage || "未知階段";
    const main = payload.latest_selected_prediction_id
      ? `${stage === "T-5m" ? "最終主要場次" : "待複核主要場次"} ${payload.latest_selected_prediction_id}`
      : `最近 ${stage} 沒有主要場次`;
    target.textContent = `已保存 ${count} 個鎖定批次・最近階段 ${stage}・更新 ${formatDate(payload.latest_lock_at)}・${main}。`;
  }

  async function initT60LockStatus() {
    ensureCard();
    try {
      const response = await fetch(LOCKS_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      window.__NBA_T60_LOCKS__ = payload;
      render(payload);
    } catch (error) {
      render({ lock_count: 0 });
      console.warn("NBA Value Lab lock status:", error);
    }
  }

  window.initT60LockStatus = initT60LockStatus;
}());
