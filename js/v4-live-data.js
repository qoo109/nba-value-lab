"use strict";

(function () {
  const formatTaipei = (value) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("zh-TW", {
      timeZone: "Asia/Taipei",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  };

  const sourceLabel = (status) => ({
    ok: "正常",
    stale: "過期",
    pending_first_run: "等待首次執行",
    error: "錯誤",
  }[status] || status || "未知");

  function renderSchedule(payload) {
    const panel = document.querySelector('[data-panel="analysis"]');
    const rail = panel?.querySelector(".date-rail");
    if (!panel || !rail || document.querySelector("#liveScheduleStatus")) return;

    const count = payload?.meta?.game_count ?? 0;
    const source = payload?.meta?.active_source || "目前無賽程來源";
    const generated = formatTaipei(payload?.meta?.generated_at);
    const banner = document.createElement("section");
    banner.id = "liveScheduleStatus";
    banner.className = "selection-note";
    banner.innerHTML = count > 0
      ? `<strong>真實賽程資料層已連線</strong><span>未來 72 小時取得 ${count} 場比賽・來源 ${source}・更新 ${generated}。目前模型卡仍是示範資料，尚未直接轉成 V3／G1 預測。</span>`
      : `<strong>真實賽程資料層已連線</strong><span>未來 72 小時目前沒有 NBA 比賽，或賽季尚未排定。更新 ${generated}；網站保留模擬 slate 測試 V3／G1 流程。</span>`;
    rail.insertAdjacentElement("afterend", banner);

    const dataCell = rail.querySelector("div:nth-child(3) span:last-child");
    if (dataCell) dataCell.textContent = `自動資料層・${count} 場・${source}`;
  }

  function renderHealth(payload) {
    const panel = document.querySelector('[data-panel="sources"]');
    if (!panel || document.querySelector("#liveSourceHealth")) return;

    const hero = panel.querySelector(".sources-hero");
    const meta = payload?.meta || {};
    const sources = Array.isArray(payload?.sources) ? payload.sources : [];
    const section = document.createElement("section");
    section.id = "liveSourceHealth";
    section.className = "storage-card";

    const cards = sources.map((source) => {
      const good = source.status === "ok";
      return `<article class="registry-card ${good ? "licensed" : "restricted"}">
        <div><span>${source.source_id}</span><em>${sourceLabel(source.status)}</em></div>
        <h2>${good ? "來源可存取" : "來源需要注意"}</h2>
        <dl>
          <div><dt>最後抓取</dt><dd>${formatTaipei(source.fetched_at)}</dd></div>
          <div><dt>資料年齡</dt><dd>${source.data_age_hours == null ? "—" : `${source.data_age_hours} 小時`}</dd></div>
          <div><dt>Adapter</dt><dd>${source.adapter_version || "—"}</dd></div>
          <div><dt>狀態</dt><dd>${source.error || source.notes || "正常"}</dd></div>
        </dl>
      </article>`;
    }).join("");

    section.innerHTML = `<div>
      <span class="eyebrow">LIVE SOURCE HEALTH</span>
      <h2>自動來源健康度</h2>
      <p>整體狀態：${meta.overall_status === "ok" ? "可用" : "降級"}・更新 ${formatTaipei(meta.generated_at)}。目前只代表賽程與狀態資料層，尚未代表模型可以正式發布。</p>
    </div><div class="registry-grid">${cards || '<article class="registry-card restricted"><h2>尚無來源紀錄</h2></article>'}</div>`;

    if (hero) hero.insertAdjacentElement("afterend", section);
    else panel.prepend(section);

    const header = document.querySelector(".header-status");
    if (header) header.innerHTML = `<span class="status-dot"></span>V4.5・資料層${meta.overall_status === "ok" ? "正常" : "降級"}`;
  }

  async function load() {
    try {
      const [gamesResponse, statusResponse] = await Promise.all([
        fetch("./data/current/games.json", { cache: "no-store" }),
        fetch("./data/current/source-status.json", { cache: "no-store" }),
      ]);
      if (!gamesResponse.ok || !statusResponse.ok) throw new Error("current data fetch failed");
      const [games, status] = await Promise.all([gamesResponse.json(), statusResponse.json()]);
      renderSchedule(games);
      renderHealth(status);
    } catch (error) {
      const header = document.querySelector(".header-status");
      if (header) header.innerHTML = '<span class="status-dot"></span>V4.5・資料層讀取失敗';
      console.warn("NBA Value Lab live data layer:", error);
    }
  }

  load();
}());
