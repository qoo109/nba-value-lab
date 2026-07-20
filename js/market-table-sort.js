"use strict";

(function () {
  const TABLE_SELECTOR = "table";
  const MISSING_TEXT = new Set(["", "—", "-", "–", "N/A", "NA", "null", "undefined"]);
  const CONFIDENCE_RANK = new Map([
    ["不足", 0],
    ["低", 1],
    ["中", 2],
    ["高", 3],
  ]);
  const GRADE_RANK = new Map([
    ["資料不足", 0],
    ["不支持", 1],
    ["ㄇ", 2],
    ["ㄇ級", 2],
    ["ㄆ", 3],
    ["ㄆ級", 3],
    ["ㄅ", 4],
    ["ㄅ級", 4],
  ]);
  const MAIN_STATUS_RANK = new Map([
    ["—", 0],
    ["觀察", 1],
    ["條件觀察", 1],
    ["合格候選", 2],
    ["網站優先候選", 3],
    ["優先候選", 3],
    ["主要場次", 4],
    ["核心主推", 5],
  ]);

  const EXPLICIT_HEADERS = new Map([
    ["市場賠率", { type: "number", defaultDirection: "desc" }],
    ["損益平衡", { type: "number", defaultDirection: "desc" }],
    ["去水機率", { type: "number", defaultDirection: "desc" }],
    ["保守", { type: "number", defaultDirection: "desc" }],
    ["中性", { type: "number", defaultDirection: "desc" }],
    ["樂觀", { type: "number", defaultDirection: "desc" }],
    ["保守EV", { type: "number", defaultDirection: "desc" }],
    ["要求邊際", { type: "max-number", defaultDirection: "desc" }],
    ["距離門檻", { type: "min-number", defaultDirection: "desc" }],
    ["最低接受", { type: "max-number", defaultDirection: "desc" }],
    ["覆蓋率", { type: "number", defaultDirection: "desc" }],
    ["信心", { type: "confidence", defaultDirection: "desc" }],
    ["結論", { type: "grade", defaultDirection: "desc" }],
    ["定位", { type: "main-status", defaultDirection: "desc" }],
    ["時間／階段", { type: "date", defaultDirection: "desc" }],
    ["三段勝率", { type: "middle-number", defaultDirection: "desc" }],
    ["結果／CLV", { type: "last-number", defaultDirection: "desc" }],
    ["V3.1", { type: "grade", defaultDirection: "desc" }],
    ["G1", { type: "grade", defaultDirection: "desc" }],
  ]);

  function cleanText(value) {
    return String(value ?? "").replace(/\s+/g, " ").trim();
  }

  function headerLabel(header) {
    const label = header.querySelector(".table-sort-label");
    return cleanText(label?.textContent || header.textContent);
  }

  function isMissing(text) {
    return MISSING_TEXT.has(cleanText(text));
  }

  function extractNumbers(text) {
    if (isMissing(text)) return [];
    const normalized = cleanText(text)
      .replace(/,/g, "")
      .replace(/[％%]/g, "")
      .replace(/pp/gi, "")
      .replace(/[＋+]/g, "+");
    const matches = normalized.match(/[+-]?\d+(?:\.\d+)?/g);
    return matches ? matches.map(Number).filter(Number.isFinite) : [];
  }

  function firstNumber(text) {
    const values = extractNumbers(text);
    return values.length ? values[0] : null;
  }

  function middleNumber(text) {
    const values = extractNumbers(text);
    if (!values.length) return null;
    return values[Math.floor(values.length / 2)];
  }

  function lastNumber(text) {
    const values = extractNumbers(text);
    return values.length ? values[values.length - 1] : null;
  }

  function maxNumber(text) {
    const values = extractNumbers(text);
    return values.length ? Math.max(...values) : null;
  }

  function minNumber(text) {
    const values = extractNumbers(text);
    return values.length ? Math.min(...values) : null;
  }

  function parseDate(text) {
    const cleaned = cleanText(text);
    if (isMissing(cleaned)) return null;
    const taiwanStyle = cleaned.match(/(\d{4})[\/.\-](\d{1,2})[\/.\-](\d{1,2})(?:\D+(\d{1,2}):(\d{2}))?/);
    if (taiwanStyle) {
      const [, year, month, day, hour = "0", minute = "0"] = taiwanStyle;
      const value = Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour) - 8, Number(minute));
      return Number.isFinite(value) ? value : null;
    }
    const value = Date.parse(cleaned);
    return Number.isNaN(value) ? null : value;
  }

  function rankByContains(text, rankMap) {
    const cleaned = cleanText(text);
    if (rankMap.has(cleaned)) return rankMap.get(cleaned);
    for (const [label, rank] of rankMap) {
      if (cleaned.includes(label)) return rank;
    }
    return null;
  }

  function cellValue(row, columnIndex, type) {
    const text = cleanText(row.cells[columnIndex]?.textContent);
    switch (type) {
      case "number": return firstNumber(text);
      case "middle-number": return middleNumber(text);
      case "last-number": return lastNumber(text);
      case "max-number": return maxNumber(text);
      case "min-number": return minNumber(text);
      case "date": return parseDate(text);
      case "confidence": return rankByContains(text, CONFIDENCE_RANK);
      case "grade": return rankByContains(text, GRADE_RANK);
      case "main-status": return rankByContains(text, MAIN_STATUS_RANK);
      default: return null;
    }
  }

  function lowerIsBetter(label) {
    return /(log\s*loss|brier|mae|rmse|誤差|錯誤|loss|drawdown|回撤|排名|rank)/i.test(label);
  }

  function excludedAutoLabel(label) {
    return /(比賽|球隊|選擇方|目標邊|名稱|來源|說明|原因|備註|ID|版本|引擎|狀態|結論|定位|市場賠率層)/i.test(label);
  }

  function detectConfig(table, header, columnIndex) {
    const label = headerLabel(header);
    if (EXPLICIT_HEADERS.has(label)) return EXPLICIT_HEADERS.get(label);
    if (!label || excludedAutoLabel(label)) return null;

    const rows = Array.from(table.tBodies).flatMap((body) => Array.from(body.rows));
    const samples = rows
      .map((row) => cleanText(row.cells[columnIndex]?.textContent))
      .filter((text) => !isMissing(text));

    if (samples.length < 2) return null;

    const dateCandidates = samples.map(parseDate).filter((value) => value !== null);
    if (/(日期|時間|更新|建立|鎖定|產生)/.test(label) && dateCandidates.length / samples.length >= 0.7) {
      return { type: "date", defaultDirection: "desc" };
    }

    const singleNumeric = samples.filter((text) => extractNumbers(text).length === 1);
    if (singleNumeric.length / samples.length >= 0.7) {
      return {
        type: "number",
        defaultDirection: lowerIsBetter(label) ? "asc" : "desc",
      };
    }

    return null;
  }

  function compareValues(a, b, direction) {
    const aMissing = a === null || Number.isNaN(a);
    const bMissing = b === null || Number.isNaN(b);
    if (aMissing && bMissing) return 0;
    if (aMissing) return 1;
    if (bMissing) return -1;
    const result = a - b;
    return direction === "asc" ? result : -result;
  }

  function updateHeaderStates(table, activeHeader, direction) {
    table.querySelectorAll("thead th[data-sortable-table]").forEach((header) => {
      const button = header.querySelector(".table-sort-button");
      const indicator = header.querySelector(".table-sort-indicator");
      const active = header === activeHeader;
      const label = headerLabel(header);
      const state = active ? (direction === "asc" ? "由低到高" : "由高到低") : "未排序";
      header.setAttribute("aria-sort", active ? (direction === "asc" ? "ascending" : "descending") : "none");
      if (button) button.setAttribute("aria-label", `${label}，目前${state}；點擊切換排序`);
      if (indicator) indicator.textContent = active ? (direction === "asc" ? "↑" : "↓") : "↕";
      header.classList.toggle("is-sorted", active);
    });
  }

  function sortTable(table, header, config) {
    const tbody = table.tBodies[0];
    if (!tbody) return;
    const headers = Array.from(table.tHead?.rows[0]?.cells || []);
    const columnIndex = headers.indexOf(header);
    if (columnIndex < 0) return;

    const currentDirection = header.dataset.sortDirection;
    const direction = currentDirection
      ? (currentDirection === "desc" ? "asc" : "desc")
      : config.defaultDirection;

    headers.forEach((item) => delete item.dataset.sortDirection);
    header.dataset.sortDirection = direction;

    const rows = Array.from(tbody.rows).map((row, index) => ({ row, index }));
    rows.sort((left, right) => {
      const leftValue = cellValue(left.row, columnIndex, config.type);
      const rightValue = cellValue(right.row, columnIndex, config.type);
      const compared = compareValues(leftValue, rightValue, direction);
      return compared || left.index - right.index;
    });

    const fragment = document.createDocumentFragment();
    rows.forEach(({ row }) => fragment.appendChild(row));
    tbody.appendChild(fragment);
    updateHeaderStates(table, header, direction);
    table.dataset.sortColumn = headerLabel(header);
    table.dataset.sortDirection = direction;
  }

  function ensureStyles() {
    if (document.querySelector("style[data-table-sort-css]")) return;
    const style = document.createElement("style");
    style.dataset.tableSortCss = "true";
    style.textContent = `
      table th[data-sortable-table] { padding: 0; }
      .table-sort-button {
        appearance: none;
        width: 100%;
        min-height: 42px;
        display: inline-flex;
        align-items: center;
        justify-content: flex-start;
        gap: 6px;
        padding: 10px 12px;
        border: 0;
        background: transparent;
        color: inherit;
        font: inherit;
        font-weight: 800;
        white-space: nowrap;
        cursor: pointer;
        text-align: left;
      }
      .table-sort-button:hover,
      .table-sort-button:focus-visible {
        background: color-mix(in srgb, currentColor 8%, transparent);
        outline: none;
      }
      .table-sort-button:focus-visible {
        box-shadow: inset 0 0 0 2px currentColor;
      }
      .table-sort-indicator {
        min-width: 1em;
        opacity: .58;
        font-size: .92em;
        line-height: 1;
      }
      table th.is-sorted .table-sort-indicator { opacity: 1; }
      table th.is-sorted .table-sort-button { color: var(--text, currentColor); }
      @media (max-width: 760px) {
        .table-sort-button { min-height: 38px; padding: 8px 10px; }
      }
    `;
    document.head.appendChild(style);
  }

  function enhanceTable(table) {
    const headerRow = table.tHead?.rows[0];
    if (!headerRow || !table.tBodies.length) return false;

    let enhanced = false;
    Array.from(headerRow.cells).forEach((header, columnIndex) => {
      if (header.dataset.sortableTable === "true") return;
      const config = detectConfig(table, header, columnIndex);
      if (!config) return;

      const label = headerLabel(header);
      header.dataset.sortableTable = "true";
      header.dataset.sortType = config.type;
      header.dataset.defaultDirection = config.defaultDirection;
      header.setAttribute("aria-sort", "none");
      header.innerHTML = `<button type="button" class="table-sort-button"><span class="table-sort-label">${label}</span><span class="table-sort-indicator" aria-hidden="true">↕</span></button>`;
      header.querySelector(".table-sort-button")?.addEventListener("click", () => sortTable(table, header, config));
      enhanced = true;
    });

    if (enhanced && table.matches(".market-table")) {
      const hint = table.closest(".market-table-section")?.querySelector(".table-hint");
      if (hint) hint.textContent = "點數值欄位可切換由高到低／由低到高；表格可橫向滑動";
    }
    return enhanced;
  }

  function enhanceAllTables() {
    ensureStyles();
    document.querySelectorAll(TABLE_SELECTOR).forEach(enhanceTable);
  }

  function boot() {
    enhanceAllTables();
    const observer = new MutationObserver(enhanceAllTables);
    observer.observe(document.body, { childList: true, subtree: true });
    [150, 500, 1000, 2000, 4000].forEach((delay) => window.setTimeout(enhanceAllTables, delay));
    document.documentElement.dataset.tableSort = "enabled";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
}());
