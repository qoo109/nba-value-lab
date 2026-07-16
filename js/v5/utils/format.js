"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function stars(candidate) {
    const gap = thresholdGap(candidate);
    const coverage = Number(candidate.game.coverage || 0);
    const confidence = candidate.game.confidence;
    const grade = candidateGrade(candidate);
    let score = grade === "ㄅ" ? 3 : grade === "ㄆ" ? 2 : grade === "ㄇ" ? 1 : 0;
    if (gap !== null && gap >= 2) score += 1;
    if (coverage >= 90 && confidence === "高") score += 1;
    return Math.max(1, Math.min(5, score));
  }

  function starText(candidate) {
    const count = stars(candidate);
    return `${"★".repeat(count)}${"☆".repeat(5 - count)}`;
  }

  function tone(candidate) {
    const grade = candidateGrade(candidate);
    if (grade === "ㄅ") return "strong";
    if (grade === "ㄆ") return "watch";
    if (grade === "ㄇ") return "fair";
    if (grade === "資料不足") return "muted";
    return "reject";
  }

  function probability(candidate) {
    return candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`;
  }

  function reasons(candidate, limit = 3) {
    const items = Array.isArray(candidate.game.reasons) ? candidate.game.reasons : [];
    return items.slice(0, limit);
  }

  function safeText(value, fallback = "—") {
    return value === null || value === undefined || value === "" ? fallback : String(value);
  }

  v5.modules.format = {
    stars,
    starText,
    tone,
    probability,
    reasons,
    safeText,
  };
}());
