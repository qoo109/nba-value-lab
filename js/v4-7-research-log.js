"use strict";

(function () {
  const HISTORY_URL = "./data/history/index.json";

  function ensureStyles() {
    if (document.querySelector("#researchLogStyles")) return;
    const style = document.createElement("style");
    style.id = "researchLogStyles";
    style.textContent = `
      .research-log-panel{display:grid;gap:22px}.research-log-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.research-stat{padding:18px;border:1px solid var(--line,#ccd3dc);border-radius:18px;background:var(--surface,#fff)}.research-stat span{display:block;font-size:.78rem;letter-spacing:.08em;color:var(--muted,#657080)}.research-stat strong{display:block;margin-top:8px;font-size:1.65rem}.research-toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.research-toolbar label{display:grid;gap:6px;min-width:150px}.research-toolbar select,.research-toolbar input{min-height:42px;padding:8px 11px;border:1px solid var(--line,#ccd3dc);border-radius:12px;background:var(--surface,#fff);color:inherit}.research-table-wrap{overflow:auto;border:1px solid var(--line,#ccd3dc);border-radius:18px}.research-table{width:100%;border-collapse:collapse;min-width:1080px}.research-table th,.research-table td{padding:12px 14px;text-align:left;border-bottom:1px solid var(--line,#e1e5eb);vertical-align:top}.research-table th{font-size:.76rem;letter-spacing:.06em;color:var(--muted,#657080);background:var(--surface-soft,#f5f7fa)}.research-empty{padding:34px;text-align:center;color:var(--muted,#657080)}.research-grade{display:inline-flex;padding:4px 9px;border-radius:999px;font-weight:700;background:var(--surface-soft,#eef2f6)}.research-id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.78rem}.research-policy{display:grid;grid-template-columns:1.2fr 1fr;gap:18px}.research-policy article{padding:20px;border:1px solid var(--line,#ccd3dc);border-radius:18px;background:var(--surface,#fff)}.research-policy ul{margin:12px 0 0;padding-left:18px}.research-policy li+li{margin-top:7px}@media(max-width:900px){.research-log-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.research-policy{grid-template-columns:1fr}}@media(max-width:560px){.research-log-summary{grid-template-columns:1fr}.research-toolbar label{width:100%}}
    `;
    document.head.appendChild(style);
  }

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("zh-TW", {
      timeZone: "Asia/Taipei", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(date);
  }

  function formatBytes(value) {
    const bytes = Number(value || 0);
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  }

  function injectShell() {
    const nav = document.querySelector('nav[aria-label="主要導覽"]');
    if (nav && !nav.querySelector('[data-tab="research"]')) {
      const button = document.createElement("button");
      button.className = "tab-button";
      button.dataset.tab = "research";
      button.textContent = "研究紀錄";
      nav.appendChild(button);
    }

    const main = document.querySelector("main.page-shell");
    if (!main || main.querySelector('[data-panel="research"]')) return;
    const panel = document.createElement("section");
    panel.className = "panel research-log-panel";
    panel.dataset.panel = "research";
    panel.hidden = true;
    panel.innerHTML = `
      <div class="view-hero compact">
        <div><span class="eyebrow">APPEND-ONLY LEDGER</span><h1>研究紀錄</h1><p>只保存賽前鎖定預測、價格評估、模型版本與最小賽後結果。示範 slate 不會被計入正式績效。</p></div>
        <div class="candidate-summary"><div class="state-card green"><span>目前模型</span><strong id="historyModelVersion">V3.1 × G1</strong><small>歷史紀錄綁定版本</small></div><div class="state-card amber"><span>儲存政策</span><strong>精簡追加</strong><small>不保存完整 Box Score／PBP</small></div></div>
      </div>
      <section class="research-log-summary" aria-label="研究紀錄摘要">
        <article class="research-stat"><span>鎖定預測</span><strong id="historyRecordCount">0</strong></article>
        <article class="research-stat"><span>價格評估</span><strong id="historyPriceCount">0</strong></article>
        <article class="research-stat"><span>已有結果</span><strong id="historyOutcomeCount">0</strong></article>
        <article class="research-stat"><span>約略容量</span><strong id="historyStorageSize">0 B</strong></article>
      </section>
      <section class="research-policy">
        <article><span class="eyebrow">IMMUTABLE RECORDS</span><h2>預測與價格分開保存</h2><ul><li>基本面或傷病改變：建立新 prediction_id。</li><li>只有賠率改變：新增 price_evaluation_id，不改勝率。</li><li>Closing 與結果只追加，不回寫原始判斷。</li></ul></article>
        <article><span class="eyebrow">SMALL STORAGE</span><h2>GitHub 只留必要欄位</h2><ul><li>不保存完整 Box Score、Play-by-play 或大型原始 PDF。</li><li>保留勝率、價格、分級、CLV、勝負與可選比分。</li><li>索引只載入最近紀錄，舊資料按月份分檔。</li></ul></article>
      </section>
      <section>
        <div class="section-heading"><div><span class="eyebrow">LOCKED RECORDS</span><h2>鎖定預測與價格評估</h2></div><span class="table-hint" id="historyGeneratedAt">尚未建立正式紀錄</span></div>
        <div class="research-toolbar">
          <label><span>階段</span><select id="historyStageFilter"><option value="全部">全部</option><option>T-24h</option><option>21:00</option><option>T-60m</option><option>T-5m</option><option>Closing</option></select></label>
          <label><span>G1 結論</span><select id="historyGradeFilter"><option value="全部">全部</option><option>ㄅ</option><option>ㄆ</option><option>ㄇ</option><option>不支持</option><option>資料不足</option></select></label>
          <label><span>搜尋</span><input id="historySearch" type="search" placeholder="球隊、game_id、prediction_id" /></label>
        </div>
        <div class="research-table-wrap"><table class="research-table"><thead><tr><th>時間／階段</th><th>比賽／選擇方</th><th>模型版本</th><th>三段勝率</th><th>賠率</th><th>V3.1</th><th>G1</th><th>主要狀態</th><th>結果／CLV</th><th>ID</th></tr></thead><tbody id="historyRows"></tbody></table><div class="research-empty" id="historyEmpty">目前沒有正式鎖定紀錄。網站中的示範比賽不會計入此處。</div></div>
      </section>`;
    main.appendChild(panel);
  }

  function row(record) {
    const probs = [record.p_conservative, record.p_neutral, record.p_optimistic]
      .map((value) => value == null ? "—" : `${(Number(value) * 100).toFixed(1)}%`).join(" / ");
    const result = record.won == null ? "待賽後" : (record.won ? "勝" : "負");
    const clv = record.clv_odds == null ? "—" : `${Number(record.clv_odds) >= 0 ? "+" : ""}${(Number(record.clv_odds) * 100).toFixed(1)}%`;
    return `<tr>
      <td>${formatDate(record.predicted_at)}<br><small>${record.evaluation_stage || "—"}</small></td>
      <td><strong>${record.game_id || "—"}</strong><br><small>${record.selection_team_id || record.target || "—"}</small></td>
      <td>V${record.model_v || "—"} × G${record.model_g || "—"}<br><small>${record.model_g_revision || ""}</small></td>
      <td>${probs}</td><td>${record.target_odds == null ? "—" : Number(record.target_odds).toFixed(3)}</td>
      <td><span class="research-grade">${record.v_grade || "—"}</span></td><td><span class="research-grade">${record.g_grade || "—"}</span></td>
      <td>${record.main_status || (record.ui_priority_candidate ? "網站優先候選" : "—")}</td>
      <td>${result}<br><small>CLV ${clv}</small></td>
      <td class="research-id">${record.prediction_id || "—"}<br>${record.price_evaluation_id || "—"}</td>
    </tr>`;
  }

  function render(payload) {
    const records = Array.isArray(payload.records) ? payload.records : [];
    const stage = document.querySelector("#historyStageFilter")?.value || "全部";
    const grade = document.querySelector("#historyGradeFilter")?.value || "全部";
    const query = (document.querySelector("#historySearch")?.value || "").trim().toLowerCase();
    const filtered = records.filter((record) => {
      const stageOk = stage === "全部" || record.evaluation_stage === stage;
      const gradeOk = grade === "全部" || record.g_grade === grade;
      const haystack = [record.game_id, record.selection_team_id, record.prediction_id, record.price_evaluation_id].filter(Boolean).join(" ").toLowerCase();
      return stageOk && gradeOk && (!query || haystack.includes(query));
    });
    const rows = document.querySelector("#historyRows");
    const empty = document.querySelector("#historyEmpty");
    if (rows) rows.innerHTML = filtered.map(row).join("");
    if (empty) empty.hidden = filtered.length > 0;
    document.querySelector("#historyRecordCount").textContent = String(payload.record_count || 0);
    document.querySelector("#historyPriceCount").textContent = String(payload.price_evaluation_count || 0);
    document.querySelector("#historyOutcomeCount").textContent = String(payload.outcome_count || 0);
    document.querySelector("#historyStorageSize").textContent = formatBytes(payload.approximate_bytes);
    document.querySelector("#historyGeneratedAt").textContent = payload.generated_at ? `索引更新 ${formatDate(payload.generated_at)}` : "尚未建立正式紀錄";
    const models = payload.active_models || {};
    document.querySelector("#historyModelVersion").textContent = `V${models.V || "3.1"} × G${models.G || "1.0"}`;
  }

  async function initResearchLog() {
    ensureStyles();
    injectShell();
    let payload;
    try {
      const response = await fetch(HISTORY_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      payload = await response.json();
    } catch (error) {
      payload = { record_count: 0, price_evaluation_count: 0, outcome_count: 0, approximate_bytes: 0, records: [] };
      console.warn("NBA Value Lab research history:", error);
    }
    window.__NBA_RESEARCH_HISTORY__ = payload;
    render(payload);
    ["#historyStageFilter", "#historyGradeFilter", "#historySearch"].forEach((selector) => {
      document.querySelector(selector)?.addEventListener("input", () => render(payload));
      document.querySelector(selector)?.addEventListener("change", () => render(payload));
    });
  }

  window.initResearchLog = initResearchLog;
}());
