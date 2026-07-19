function renderTopPick() {
  const candidate = mainCandidate();
  const game = candidate.game;
  const tier = candidateTier(candidate);
  $("#topPick").innerHTML = `
    <div class="top-pick-main">
      <div class="pick-heading">${gradeBadge(candidateGrade(candidate))}<span>${tier}・台灣 ${game.start}</span></div>
      <div class="engine-tags"><span>${engineLabel(candidate)}</span><span>模擬 T−60m</span></div>
      <h1>${game.matchup}</h1>
      <p>目標邊 <strong>${candidate.target.code}</strong>・賠率 <strong>${candidate.target.odds.toFixed(2)}</strong></p>
      <button class="primary-button" data-open-candidate="${candidate.id}">查看完整分析 →</button>
    </div>
    <div class="top-pick-numbers">
      ${metric("保守勝率", `${candidate.target.conservative}%`, true)}
      ${metric("損益平衡", percent(breakEven(candidate.target.odds)))}
      ${metric("距離門檻", signed(thresholdGap(candidate)), true)}
    </div>
    <div class="verification">
      <div>${game.injury}</div><div>${game.confidence}信心</div>
      <small>資料覆蓋率 ${game.coverage}%<br>區間寬度 ${intervalWidth(candidate) ?? "—"}pp<br>${game.snapshot}</small>
    </div>`;
}

function candidateCard(candidate) {
  const game = candidate.game;
  const tier = candidateTier(candidate);
  const tierClass = tier === "核心主推" ? "tier-core" : tier === "優先候選" ? "tier-priority" : "";
  return `<button class="game-card ${tierClass}" data-open-candidate="${candidate.id}" aria-label="查看 ${game.matchup} ${candidate.target.code} 完整分析">
    <div class="game-card-top">${gradeBadge(candidateGrade(candidate))}<span class="game-time">台灣 ${game.start}</span></div>
    <div class="engine-tags"><span>${engineLabel(candidate)}</span><span>${tier}</span></div>
    <div class="matchup-row"><h3>${game.matchup}</h3><span>${oddsText(candidate.target.odds)}</span></div>
    <p class="target-line">目標邊 ${candidate.target.code}・${candidate.target.name}</p>
    <div class="mini-metrics">
      ${metric("保守", candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`)}
      ${metric("損益平衡", percent(breakEven(candidate.target.odds)))}
      ${metric("距門檻", signed(thresholdGap(candidate)), thresholdGap(candidate) !== null && thresholdGap(candidate) >= 0)}
    </div>
    <div class="game-card-footer"><span>${priceBand(candidate.target.odds).label}</span><span>覆蓋 ${game.coverage}%</span></div>
  </button>`;
}

function renderCards() {
  const visible = activeFilter === "全部" ? candidates : candidates.filter((candidate) => candidateGrade(candidate) === activeFilter);
  $("#gamesGrid").innerHTML = visible.map(candidateCard).join("");
  $("#noResults").hidden = visible.length > 0;

  const board = selectionBoard();
  $("#coreCandidateGrid").innerHTML = board.core ? candidateCard(board.core) : "";
  $("#noCoreCandidate").hidden = Boolean(board.core);
  $("#priorityCandidateGrid").innerHTML = board.priority.map(candidateCard).join("");
  $("#noPriorityCandidate").hidden = board.priority.length > 0;
  $("#candidateGrid").innerHTML = board.qualified.map(candidateCard).join("");
  $("#coreCount").textContent = `${board.core ? 1 : 0} 場`;
  $("#priorityCount").textContent = `${board.priority.length} 場`;
  $("#candidateCount").textContent = `${board.qualified.length} 邊`;
}

function renderTable() {
  $("#marketRows").innerHTML = candidates.map((candidate) => {
    const game = candidate.game;
    const band = priceBand(candidate.target.odds);
    const tier = candidateTier(candidate);
    return `
      <tr data-open-candidate="${candidate.id}" tabindex="0">
        <td><strong>${game.matchup}</strong><small>台灣 ${game.start}</small></td>
        <td>${candidate.target.code}<small>${candidate.side === "home" ? "主隊" : "客隊"}</small></td>
        <td><span class="engine-pill">${engineLabel(candidate)}</span></td>
        <td>${oddsText(candidate.target.odds)}</td><td>${band.label}</td><td>${percent(breakEven(candidate.target.odds))}</td>
        <td>${percent(noVig(candidate))}</td>
        <td>${candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`}</td>
        <td>${candidate.target.neutral === null ? "—" : `${candidate.target.neutral}%`}</td>
        <td>${candidate.target.optimistic === null ? "—" : `${candidate.target.optimistic}%`}</td>
        <td>${signed(scenarioEv(candidate.target.conservative, candidate.target.odds), "%")}</td>
        <td>${band.margin === null ? "—" : `${band.margin.toFixed(1)}pp`}</td>
        <td>${signed(thresholdGap(candidate))}</td><td>${oddsText(minimumOdds(candidate), 3)}</td>
        <td>${game.coverage}%</td><td>${game.confidence}</td><td><strong>${tier}</strong></td><td>${gradeBadge(candidateGrade(candidate))}</td>
      </tr>`;
  }).join("");
}

function renderCalculatorOptions() {
  $("#calculatorGame").innerHTML = candidates.map((candidate) => `<option value="${candidate.id}">${candidate.game.matchup}・${candidate.target.code}</option>`).join("");
}

function updateCalculator(resetOdds = false) {
  const candidate = candidates.find((item) => item.id === $("#calculatorGame").value) || candidates[0];
  if (resetOdds) $("#oddsInput").value = candidate.target.odds === null ? "" : candidate.target.odds.toFixed(2);
  $("#oddsLabel").textContent = `${candidate.target.code} 獨贏賠率`;
  const odds = Number($("#oddsInput").value);
  const valid = Number.isFinite(odds) && odds > 1;
  const be = valid ? breakEven(odds) : null;
  const gap = valid ? thresholdGap(candidate, odds) : null;
  const ev = valid ? scenarioEv(candidate.target.conservative, odds) : null;
  const grade = valid ? gradeAtPrice(candidate, odds) : "資料不足";
  const band = valid ? priceBand(odds) : priceBand(NaN);
  $("#calcBreakeven").textContent = percent(be);
  $("#calcGap").textContent = signed(gap);
  $("#calcGap").className = gap !== null && gap >= 0 ? "positive" : gap !== null && gap < -(band.margin ?? 0) ? "negative" : "";
  $("#calcEv").textContent = signed(ev, "%");
  $("#calcStatus").textContent = `${$("#bookmakerInput").value || "我的莊家"}：${gradeInfo[grade].label}`;
  $("#calcStatus").classList.toggle("pass", grade === "ㄅ");
  const marginText = band.margin === null ? "未開放研究邊際" : `${band.margin.toFixed(1)}pp 安全邊際`;
  $("#calcNote").textContent = `${engineLabel(candidate)}・${candidateTier(candidate)}・${band.label}・最低接受賠率 ${oddsText(minimumOdds(candidate, odds), 3)}・${marginText}・正式投注額固定為 0。`;
}

function buildSummary(candidate) {
  const game = candidate.game;
  if (!game.build || candidate.target.neutral === null) return "<p><strong>勝率形成：</strong>關鍵資訊不足，因此停止建立整場雙向機率。</p>";
  if (candidate.side !== game.focusSide) {
    return `<p><strong>勝率形成：</strong>由同一場機率向量的對邊互補結果產生；中性勝率為 100% − ${candidate.opponent.neutral}% = ${candidate.target.neutral}%。保守與樂觀端使用相同重抽樣與情境來源。</p>`;
  }
  return `<p><strong>勝率形成：</strong>長期基準 ${game.build.base}%；${game.build.adjustments.map(([label, value]) => `${label} ${value >= 0 ? "+" : ""}${value}%`).join("；")}；中性 ${candidate.target.neutral}%。</p>`;
}

function showDetail(candidate) {
  const game = candidate.game;
  const band = priceBand(candidate.target.odds);
  $("#modalContent").innerHTML = `
    <div class="detail-header">${gradeBadge(candidateGrade(candidate))}<div class="engine-tags"><span>${engineLabel(candidate)}</span><span>${candidateTier(candidate)}</span></div><h2>${game.matchup}・${candidate.target.code}</h2><p>${game.headline}</p></div>
    <div class="detail-metrics">
      ${metric("目前賠率", oddsText(candidate.target.odds))}${metric("保守勝率", candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`, true)}
      ${metric("損益平衡", percent(breakEven(candidate.target.odds)))}${metric("保守優勢", signed(edge(candidate)))}
      ${metric("要求邊際", band.margin === null ? "—" : `${band.margin.toFixed(1)}pp`)}
      ${metric("距離門檻", signed(thresholdGap(candidate)), thresholdGap(candidate) !== null && thresholdGap(candidate) >= 0)}
      ${metric("最低接受", oddsText(minimumOdds(candidate), 3))}${metric("區間寬度", intervalWidth(candidate) === null ? "—" : `${intervalWidth(candidate)}pp`)}
    </div>
    <div class="scenario-band">
      <div><span>保守情境</span><strong>${candidate.target.conservative === null ? "—" : `${candidate.target.conservative}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.conservative, candidate.target.odds), "%")}</small></div>
      <div><span>中性情境</span><strong>${candidate.target.neutral === null ? "—" : `${candidate.target.neutral}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.neutral, candidate.target.odds), "%")}</small></div>
      <div><span>樂觀情境</span><strong>${candidate.target.optimistic === null ? "—" : `${candidate.target.optimistic}%`}</strong><small>EV ${signed(scenarioEv(candidate.target.optimistic, candidate.target.odds), "%")}</small></div>
    </div>
    <div class="detail-grid">
      <article><span class="eyebrow">市場數學</span><ul><li>${candidate.target.code} 原始隱含 ${percent(rawImplied(candidate.target.odds))}</li><li>${candidate.opponent.code} 原始隱含 ${percent(rawImplied(candidate.opponent.odds))}</li><li>理論超額水位 ${percent(overround(candidate))}</li><li>${candidate.target.code} 比例去水機率 ${percent(noVig(candidate))}</li><li>賠率分層 ${band.label}</li></ul></article>
      <article><span class="eyebrow">模型帳本</span>${buildSummary(candidate)}</article>
      <article><span class="eyebrow">支持證據</span><ul>${game.reasons.map((item) => `<li>${item}</li>`).join("")}</ul></article>
      <article><span class="eyebrow">主要風險</span><ul>${game.risks.map((item) => `<li>${item}</li>`).join("")}</ul></article>
    </div>
    <div class="detail-footer"><span>覆蓋率 ${game.coverage}%・新聞風險 ${game.newsRisk}/3・${game.injury}</span><strong>${candidateTier(candidate)}・${game.snapshot}</strong></div>`;
  $("#detailModal").showModal();
}
