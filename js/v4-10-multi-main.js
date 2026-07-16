"use strict";

(function () {
  function thirdSlotEligible(candidate) {
    const policy = modelG().selection?.third_slot_policy || {};
    if (!policy.enabled || !mainGateEligible(candidate)) return false;
    const game = candidate.game;
    const decision = gDecision(candidate);
    const sources = simulatedGateValue(game, "comparisonSources", game.coreReady ? 4 : 2);
    return game.coverage >= (policy.coverage_min_pct ?? 90)
      && intervalWidth(candidate) !== null
      && intervalWidth(candidate) <= (policy.interval_width_max_pp ?? 5)
      && sources >= (policy.comparison_sources_min ?? 4)
      && decision.gap !== null
      && decision.gap >= (policy.threshold_buffer_min_pp ?? 2)
      && game.newsRisk <= (policy.news_risk_max ?? 0)
      && game.confidence === (policy.confidence_required || "高");
  }

  window.selectionBoard = function selectionBoardV410() {
    const qualified = rankedQualified();
    const selection = modelG().selection || {};
    const target = Math.max(0, Math.min(3, selection.official_main_target ?? 2));
    const maximum = Math.max(target, Math.min(3, selection.official_main_max ?? 3));
    const eligible = qualified.filter(mainGateEligible);
    const mains = eligible.slice(0, target);
    if (mains.length >= target && mains.length < maximum) {
      const chosen = new Set(mains.map((candidate) => candidate.id));
      const third = eligible.find((candidate) => !chosen.has(candidate.id) && thirdSlotEligible(candidate));
      if (third) mains.push(third);
    }
    const priorityMax = selection.ui_priority_candidates_max ?? coordinationPolicy().ui_policy?.priority_display_max ?? 2;
    const mainIds = new Set(mains.map((candidate) => candidate.id));
    const priority = qualified.filter((candidate) => !mainIds.has(candidate.id)).slice(0, Math.max(0, priorityMax));
    const priorityIds = new Set(priority.map((candidate) => candidate.id));
    const general = qualified.filter((candidate) => !mainIds.has(candidate.id) && !priorityIds.has(candidate.id));
    return { core: mains[0] || null, mains, priority, general, qualified };
  };

  window.candidateTier = function candidateTierV410(candidate) {
    const board = selectionBoard();
    const index = board.mains.findIndex((item) => item.id === candidate.id);
    if (index >= 0) return `G1 主要場次 ${index + 1}/${board.mains.length}`;
    if (board.priority.some((item) => item.id === candidate.id)) return "網站優先候選（非 G1 正式分級）";
    if (gDecision(candidate).grade === "ㄅ") return "一般 G1 ㄅ級";
    if (gDecision(candidate).grade === "ㄆ") return "條件觀察";
    if (gDecision(candidate).grade === "資料不足") return "資料不足";
    return "跳過";
  };

  window.mainCandidate = function mainCandidateV410() {
    const board = selectionBoard();
    return board.mains[0] || board.priority[0] || board.qualified[0] || candidates[0];
  };

  window.renderMultiMainSummary = function renderMultiMainSummary() {
    const host = document.querySelector("#topPick");
    if (!host) return;
    document.querySelector("#multiMainSummary")?.remove();
    const board = selectionBoard();
    const note = document.createElement("section");
    note.id = "multiMainSummary";
    note.className = "selection-note";
    if (!board.mains.length) {
      note.innerHTML = "<strong>主要場次：0 場</strong><span>本批沒有候選通過全部硬閘門；不為了湊滿兩場而降低標準。</span>";
    } else {
      const list = board.mains.map((candidate, index) => `${index + 1}. ${candidate.target.code} ${candidate.target.odds.toFixed(2)}`).join("　");
      note.innerHTML = `<strong>主要場次：${board.mains.length} 場</strong><span>${list}。一般目標 2 場、硬上限 3 場；第 3 場需通過額外嚴格門檻。</span>`;
    }
    host.insertAdjacentElement("afterend", note);
  };
}());
