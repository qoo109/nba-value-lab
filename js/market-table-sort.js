"use strict";

(function () {
  const TABLE_SELECTOR = ".market-table";
  const SORTABLE_HEADERS = new Map([
    ["市場賠率", { type: "number", defaultDirection: "desc" }],
    ["保守", { type: "number", defaultDirection: "desc" }],
    ["中性", { type: "number", defaultDirection: "desc" }],
    ["樂觀", { type: "number", defaultDirection: "desc" }],
    ["保守EV", { type: "number", defaultDirection: "desc" }],
    ["信心", { type: "confidence", defaultDirection: "desc" }],
  ]);
  const CONFIDENCE_RANK = new Map([
    ["不足", 0],
    ["低", 1],
    ["中", 2],
    ["高", 3],
  ]);

  function normalizeHeaderText(header) {
    const label = header.querySelector(".market-sort-label");
    return (label?.textContent || header.textContent || "").trim();
  }

  function parseNumber(text) {
    const cleaned = String(text || "")
      .replace(/,/g, "")
      .replace(/[％%]/g, "")
      .replace(/pp/gi, "")
      .replace(/[＋+]/g, "")
      .trim();
    if (!cleaned || cleaned === "—" || cleaned === "-") return null;
    const match = cleaned.match(/-?\d+(?:\.\d+)?/);
    return match ? Number(match[0]) : null;
  }

  function cellValue(row, columnIndex, type) {
    const text = row.cells[columnIndex]?.textContent?.trim() || "";
    if (type === "confidence") return CONFIDENCE_RANK.get(text) ?? null;
    return parseNumber(text);
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
    table.querySelectorAll("thead th[data-sortable-market]").forEach((header) => {
      const button = header.querySelector(".market-sort-button");
      const indicator = header.querySelector(".market-sort-indicator");
      const active = header === activeHeader;
      header.setAttribute("aria-sort", active ? (direction === "asc" ? "ascending" : "descending") : "none");
      if (button) button.setAttribute("aria-label", `${normalizeHeaderText(header)}，目前${active ? (direction === "asc" ? "由低到高" : "由高到低") : "未排序"}；點擊切換排序`);
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
    table.dataset.sortColumn = normalizeHeaderText(header);
    table.dataset.sortDirection = direction;
  }

  function ensureStyles() {
    if (document.querySelector("style[data-market-table-sort-css]")) return;
    const style = document.createElement("style");
    style.dataset.marketTableSortCss = "true";
    style.textContent = `
      .market-table th[data-sortable-market] { padding: 0; }
      .market-sort-button {
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
      .market-sort-button:hover,
      .market-sort-button:focus-visible {
        background: color-mix(in srgb, currentColor 8%, transparent);
        outline: none;
      }
      .market-sort-button:focus-visible {
        box-shadow: inset 0 0 0 2px currentColor;
      }
      .market-sort-indicator {
        min-width: 1em;
        opacity: .58;
        font-size: .92em;
        line-height: 1;
      }
      .market-table th.is-sorted .market-sort-indicator { opacity: 1; }
      .market-table th.is-sorted .market-sort-button { color: var(--text, currentColor); }
      @media (max-width: 760px) {
        .market-sort-button { min-height: 38px; padding: 8px 10px; }
      }
    `;
    document.head.appendChild(style);
  }

  function enhanceTable(table) {
    if (!table || table.dataset.marketSortEnhanced === "true") return false;
    const headerRow = table.tHead?.rows[0];
    if (!headerRow) return false;

    let enhancedCount = 0;
    Array.from(headerRow.cells).forEach((header) => {
      const label = (header.textContent || "").trim();
      const config = SORTABLE_HEADERS.get(label);
      if (!config) return;

      header.dataset.sortableMarket = "true";
      header.setAttribute("aria-sort", "none");
      header.innerHTML = `<button type="button" class="market-sort-button"><span class="market-sort-label">${label}</span><span class="market-sort-indicator" aria-hidden="true">↕</span></button>`;
      header.querySelector("button")?.addEventListener("click", () => sortTable(table, header, config));
      enhancedCount += 1;
    });

    if (!enhancedCount) return false;
    table.dataset.marketSortEnhanced = "true";
    const hint = table.closest(".market-table-section")?.querySelector(".table-hint");
    if (hint) hint.textContent = "點欄位可切換由高到低／由低到高；表格可橫向滑動";
    return true;
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
    document.documentElement.dataset.marketTableSort = "enabled";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
}());
