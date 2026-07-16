"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function clean(values) {
    return values.map(Number).filter(Number.isFinite);
  }

  function points(values, width, height, padding) {
    const data = clean(values);
    if (!data.length) return [];
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const usableWidth = width - padding * 2;
    const usableHeight = height - padding * 2;
    return data.map((value, index) => ({
      x: padding + (data.length === 1 ? usableWidth / 2 : index * usableWidth / (data.length - 1)),
      y: padding + usableHeight - ((value - min) / range) * usableHeight,
      value,
    }));
  }

  function polyline(data) {
    return data.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  }

  function areaPath(data, height, padding) {
    if (!data.length) return "";
    const first = data[0];
    const last = data.at(-1);
    return `M ${first.x.toFixed(1)} ${(height - padding).toFixed(1)} L ${polyline(data).replaceAll(",", " ")} L ${last.x.toFixed(1)} ${(height - padding).toFixed(1)} Z`;
  }

  function svg(values, options = {}) {
    const width = options.width || 260;
    const height = options.height || 72;
    const padding = options.padding || 6;
    const label = options.label || "趨勢圖";
    const data = points(values, width, height, padding);
    if (!data.length) return `<div class="v52-sparkline-empty">尚無趨勢資料</div>`;
    const line = polyline(data);
    const area = areaPath(data, height, padding);
    const last = data.at(-1);
    return `<svg class="v52-sparkline" viewBox="0 0 ${width} ${height}" role="img" aria-label="${label}">
      <path class="v52-sparkline-area" d="${area}"></path>
      <polyline class="v52-sparkline-line" points="${line}"></polyline>
      <circle class="v52-sparkline-point" cx="${last.x.toFixed(1)}" cy="${last.y.toFixed(1)}" r="3.5"></circle>
    </svg>`;
  }

  function delta(values) {
    const data = clean(values);
    if (data.length < 2) return null;
    return data.at(-1) - data[0];
  }

  v5.modules.sparkline = { clean, points, svg, delta };
}());
