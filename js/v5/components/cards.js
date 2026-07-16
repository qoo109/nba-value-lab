"use strict";

(function () {
  const v5 = window.NBAVL.v5;
  const fmt = v5.modules.format;

  function reasonList(candidate) {
    const reasons = fmt.reasons(candidate);
    if (!reasons.length) return "<li>等待更多賽前資料確認</li>";
    return reasons.map((item) => `<li>${item}</li>`).join("");
  }

  function mainCard(candidate, index, total, formal) {
    const tone = fmt.tone(candidate);
    const label = formal ? `主要場次 ${index + 1}/${total}` : "最高順位觀察";
    return `<button class="v5-main-card tone-${tone}" data-open-candidate="${candidate.id}" aria-label="查看 ${candidate.game.matchup} ${candidate.target.code} 分析">
      <div class="v5-main-card-head">
        <span class="v5-rank">${String(index + 1).padStart(2, "0")}</span>
        <span class="v5-main-label">${label}</span>
        <span class="v5-game-time">台灣 ${candidate.game.start}</span>
      </div>
      <div class="v5-main-card-body">
        <div>
          <span class="v5-team-code">${candidate.target.code}</span>
          <h2>${candidate.game.matchup}</h2>
          <p>${candidate.target.name}・獨贏 ${oddsText(candidate.target.odds)}</p>
        </div>
        <div class="v5-primary-number">
          <strong>${fmt.probability(candidate)}</strong>
          <span>保守勝率</span>
        </div>
      </div>
      <div class="v5-main-card-meta">
        <span class="v5-stars" aria-label="研究強度 ${fmt.stars(candidate)} 星">${fmt.starText(candidate)}</span>
        <span>${engineLabel(candidate)}</span>
        <span>覆蓋 ${candidate.game.coverage}%</span>
        <span>賠率 ${oddsText(candidate.target.odds)}</span>
      </div>
      <ul class="v5-reason-list">${reasonList(candidate)}</ul>
      <span class="v5-card-action">查看完整分析 →</span>
    </button>`;
  }

  function candidateCardV5(candidate) {
    const tone = fmt.tone(candidate);
    return `<button class="v5-candidate-card tone-${tone}" data-open-candidate="${candidate.id}" aria-label="查看 ${candidate.game.matchup} ${candidate.target.code} 完整分析">
      <div class="v5-candidate-top">
        <div>
          <span class="v5-candidate-tier">${candidateTier(candidate)}</span>
          <h3>${candidate.target.code}</h3>
          <p>${candidate.game.matchup}</p>
        </div>
        <span class="v5-grade-chip">${candidateGrade(candidate)}</span>
      </div>
      <div class="v5-candidate-key">
        <div><strong>${fmt.probability(candidate)}</strong><span>保守勝率</span></div>
        <div><strong>${oddsText(candidate.target.odds)}</strong><span>獨贏賠率</span></div>
        <div><strong>${signed(thresholdGap(candidate))}</strong><span>距門檻</span></div>
      </div>
      <div class="v5-candidate-bottom">
        <span class="v5-stars">${fmt.starText(candidate)}</span>
        <span>覆蓋 ${candidate.game.coverage}%</span>
        <span>台灣 ${candidate.game.start}</span>
      </div>
    </button>`;
  }

  function renderTopPickV5() {
    const board = selectionBoard();
    const formal = board.mains.length > 0;
    const display = formal
      ? board.mains
      : [board.priority[0] || board.qualified[0] || mainCandidate()].filter(Boolean);
    const title = formal ? `今日主要場次 ${display.length} 場` : "今日沒有正式主要場次";
    const note = formal
      ? "一般目標 2 場・最多 3 場・第 3 場採額外嚴格門檻"
      : "目前沒有候選通過全部硬 Gate，不為了湊數降低標準";

    $("#topPick").innerHTML = `<div class="v5-hero-heading v52-compact-decision">
      <div class="v52-decision-copy">
        <span class="eyebrow">今日決策</span>
        <strong>${title}</strong>
        <span class="v52-decision-note">${note}</span>
      </div>
      <div class="v5-model-pill"><span>MODEL</span><strong>${activeModelLabel()}</strong></div>
    </div>
    <div class="v5-main-grid">${display.map((candidate, index) => mainCard(candidate, index, display.length, formal)).join("")}</div>`;
  }

  function renderCardsV5() {
    const visible = activeFilter === "全部"
      ? candidates
      : candidates.filter((candidate) => candidateGrade(candidate) === activeFilter);
    $("#gamesGrid").innerHTML = visible.map(candidateCardV5).join("");
    $("#noResults").hidden = visible.length > 0;

    const board = selectionBoard();
    $("#coreCandidateGrid").innerHTML = board.mains.map(candidateCardV5).join("");
    $("#noCoreCandidate").hidden = board.mains.length > 0;
    $("#priorityCandidateGrid").innerHTML = board.priority.map(candidateCardV5).join("");
    $("#noPriorityCandidate").hidden = board.priority.length > 0;
    $("#candidateGrid").innerHTML = board.qualified.map(candidateCardV5).join("");
    $("#coreCount").textContent = `${board.mains.length} 場`;
    $("#priorityCount").textContent = `${board.priority.length} 場`;
    $("#candidateCount").textContent = `${board.qualified.length} 邊`;
  }

  v5.modules.cards = { mainCard, candidateCard: candidateCardV5 };
  window.candidateCard = candidateCardV5;
  window.renderTopPick = renderTopPickV5;
  window.renderCards = renderCardsV5;
}());
