"use strict";

(function () {
  const STATUS = {
    appVersion: "V5.3.10",
    model: "V3.1 x G1.1",
    updated: "2026-07-19",
    state: "Research Candidate / Pre-Market-Backtest",
    stake: "0",
  };

  const GITHUB_AUTOMATION = {
    owner: "qoo109",
    repo: "nba-value-lab",
    workflow: "run-eoin-cross-source-audit-v1.yml",
    defaultRef: "main",
    defaultDataset: "eoinamoore/historical-nba-data-and-player-box-scores",
    defaultMaxDownloadMb: "600",
    apiVersion: "2026-03-10",
  };

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function setText(node, text) {
    if (node) node.textContent = text;
  }

  function ensureStylesheet() {
    if (qs('link[data-current-research-status-css]')) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "./css/current-research-status.css?v=20260719";
    link.setAttribute("data-current-research-status-css", "true");
    document.head.appendChild(link);
  }

  function ensureHeader() {
    document.documentElement.dataset.appVersion = STATUS.appVersion;
    document.documentElement.dataset.modelVersion = STATUS.model;
    document.title = `NBA Value Lab ${STATUS.appVersion} | ${STATUS.model}`;
    const header = qs(".header-status");
    if (header) {
      header.innerHTML = `<span class="status-dot"></span>${STATUS.appVersion}・${STATUS.state}・Stake ${STATUS.stake}`;
    }
    const footerVersion = qs("footer > span:first-child");
    setText(footerVersion, `NBA VALUE LAB ${STATUS.appVersion}`);
    const footerMode = qs("footer > span:last-child");
    setText(footerMode, `台灣時間・${STATUS.model}・正式投注額 ${STATUS.stake}`);
  }

  function updateRail() {
    const rail = qs('[data-panel="analysis"] .date-rail');
    if (!rail) return;
    const cells = qsa(":scope > div", rail);
    if (cells[0]) cells[0].innerHTML = '<span class="rail-code">STATE</span><span><strong>Research Candidate</strong>・Pre-Market-Backtest</span>';
    if (cells[1]) cells[1].innerHTML = '<span class="rail-code">QUEUE</span><span>Wyatt blocked・Eoin adapter self-test・Market odds 暫停</span>';
    if (cells[2]) cells[2].innerHTML = '<span class="rail-code">STAKE</span><span>正式投注額 0・不宣稱 edge / ROI / CLV</span>';
  }

  function statusCard(label, title, copy, tone, details) {
    const list = details.map((item) => `<li>${item}</li>`).join("");
    return `<article class="current-status-card ${tone}">
      <div><span>${label}</span><em>${toneLabel(tone)}</em></div>
      <h3>${title}</h3>
      <p>${copy}</p>
      <ul>${list}</ul>
    </article>`;
  }

  function toneLabel(tone) {
    return {
      blocked: "BLOCKED",
      waiting: "WAITING",
      paused: "PAUSED",
      ready: "READY",
    }[tone] || "INFO";
  }

  function ensureAnalysisStatus() {
    const panel = qs('[data-panel="analysis"]');
    const timing = panel?.querySelector(".timing-strip");
    if (!panel || qs("#currentResearchStatus")) return;

    const section = document.createElement("section");
    section.id = "currentResearchStatus";
    section.className = "current-status-section";
    section.innerHTML = `<div class="current-status-heading">
      <div>
        <span class="eyebrow">CURRENT CONTROL BLOCK</span>
        <h2>現在先做資料進件，不產生正式投注建議</h2>
        <p>Wyatt 已完成真實檔 aggregate audit 並正式 blocked；Eoin 已通過 cross-source audit，adapter predeclaration 已凍結，且 role-limited adapter self-test implementation 已建立。市場 PIT odds 尚未解鎖，因此 CLV、EV、ROI、Drawdown 與投注決策層仍關閉。</p>
      </div>
      <div class="current-status-pill"><span>STAKE</span><strong>${STATUS.stake}</strong></div>
    </div>
    <div class="current-status-grid">
      ${statusCard("WYATT", "SQLite / DuckDB 不再重跑同一份", "實體檔與 235-table metadata 不一致，不能作為 2023-24 secondary source qualification。", "blocked", [
        "SQLite: 16 tables, latest game date 2023-06-12",
        "DuckDB: 12 KB empty shell",
        "2023-24 pilot games: 0",
      ])}
      ${statusCard("EOIN", "Adapter self-test 已建立", "Eoin adapter 目前只跑 synthetic fixture；完整 bundle execution 仍關閉，需等 CI artifact 通過後再開 preflight。", "ready", [
        "Matched games: 1,230 / 1,230",
        "Local self-test: passed",
        "CI: Parquet fixture validation",
        "Player boxscore: coverage-only",
      ])}
      ${statusCard("MARKET", "PIT odds line 暫停", "沒有合法且可核對 timestamp / bookmaker semantics 的 odds source 前，不做 market backtest。", "paused", [
        "No paid pilot approved",
        "No CLV / ROI / Drawdown claim",
        "Manual price calculator remains research-only",
      ])}
    </div>`;

    if (timing) timing.insertAdjacentElement("afterend", section);
    else panel.prepend(section);
  }

  function automationStatus(text, tone = "muted") {
    const node = qs("#githubAutomationStatus");
    if (!node) return;
    node.textContent = text;
    node.dataset.tone = tone;
  }

  function classifyDispatchError(status, detail) {
    if (status === 401) return "GitHub token 無效或已過期。";
    if (status === 403) return "GitHub token 權限不足；需要此 repo 的 Actions read/write。";
    if (status === 404) return "找不到 repo、branch 或 workflow；請確認 workflow 已經在該 branch。";
    if (status === 422) return "workflow input 或 branch 不符合設定。";
    return detail || `GitHub API 回應 ${status}`;
  }

  async function githubJson(url, token, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "X-GitHub-Api-Version": GITHUB_AUTOMATION.apiVersion,
        ...(options.headers || {}),
      },
    });
    if (!response.ok) {
      let detail = "";
      try {
        const body = await response.json();
        detail = body.message || "";
      } catch (_) {
        detail = response.statusText;
      }
      throw new Error(classifyDispatchError(response.status, detail));
    }
    if (response.status === 204) return null;
    return response.json();
  }

  async function findLatestWorkflowRun(token, ref, submittedAt) {
    const params = new URLSearchParams({
      event: "workflow_dispatch",
      branch: ref,
      per_page: "5",
    });
    const url = `https://api.github.com/repos/${GITHUB_AUTOMATION.owner}/${GITHUB_AUTOMATION.repo}/actions/workflows/${GITHUB_AUTOMATION.workflow}/runs?${params}`;
    const data = await githubJson(url, token);
    const runs = Array.isArray(data?.workflow_runs) ? data.workflow_runs : [];
    const threshold = submittedAt.getTime() - 60000;
    return runs.find((run) => new Date(run.created_at).getTime() >= threshold) || runs[0] || null;
  }

  async function pollLatestRun(token, ref, submittedAt) {
    for (const delay of [1800, 3200, 5200]) {
      await new Promise((resolve) => window.setTimeout(resolve, delay));
      const run = await findLatestWorkflowRun(token, ref, submittedAt);
      if (run?.html_url) return run;
    }
    return null;
  }

  async function handleGithubAutomationSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const token = qs("#githubAutomationToken", form)?.value.trim();
    const ref = qs("#githubAutomationRef", form)?.value.trim() || GITHUB_AUTOMATION.defaultRef;
    const dataset = qs("#githubAutomationDataset", form)?.value.trim() || GITHUB_AUTOMATION.defaultDataset;
    const maxDownloadMb = qs("#githubAutomationMaxDownloadMb", form)?.value.trim() || GITHUB_AUTOMATION.defaultMaxDownloadMb;
    const submitButton = qs('button[type="submit"]', form);
    const runLink = qs("#githubAutomationRunLink");

    if (!token) {
      automationStatus("請先貼上 GitHub fine-grained token。", "warn");
      return;
    }

    if (runLink) {
      runLink.hidden = true;
      runLink.removeAttribute("href");
    }

    const submittedAt = new Date();
    submitButton.disabled = true;
    automationStatus("正在送出 GitHub Actions 執行請求...", "working");

    try {
      const url = `https://api.github.com/repos/${GITHUB_AUTOMATION.owner}/${GITHUB_AUTOMATION.repo}/actions/workflows/${GITHUB_AUTOMATION.workflow}/dispatches`;
      const dispatchResult = await githubJson(url, token, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ref,
          inputs: {
            dataset_handle: dataset,
            max_download_mb: maxDownloadMb,
          },
        }),
      });

      if (dispatchResult?.html_url && runLink) {
        runLink.href = dispatchResult.html_url;
        runLink.hidden = false;
        automationStatus("已建立 workflow run，可等待 artifact 產生。", "ok");
      } else {
        automationStatus("已送出，正在抓最新 workflow run...", "ok");
      }

      const run = dispatchResult?.html_url ? null : await pollLatestRun(token, ref, submittedAt);
      if (run?.html_url && runLink) {
        runLink.href = run.html_url;
        runLink.hidden = false;
        automationStatus(`已建立 run #${run.run_number}，可等待 artifact 產生。`, "ok");
      } else if (!dispatchResult?.html_url) {
        automationStatus("已送出，但 GitHub 還沒回傳最新 run；稍等一分鐘再查。", "ok");
      }
      const tokenInput = qs("#githubAutomationToken", form);
      if (tokenInput) tokenInput.value = "";
    } catch (error) {
      automationStatus(error.message || "啟動失敗。", "error");
    } finally {
      submitButton.disabled = false;
    }
  }

  function ensureGithubAutomationLauncher() {
    const panel = qs('[data-panel="analysis"]');
    const anchor = qs("#currentResearchStatus");
    if (!panel || qs("#githubAutomationLauncher")) return;

    const section = document.createElement("section");
    section.id = "githubAutomationLauncher";
    section.className = "github-automation-launcher";
    section.innerHTML = `<div class="github-automation-copy">
      <span class="eyebrow">GITHUB WEBSITE RUNNER</span>
      <h2>從網站直接啟動 cross-source audit</h2>
      <p>目前 Eoin v1 已通過；這個工具保留給未來重新驗證新版資料。Token 只留在這次瀏覽器請求中。</p>
    </div>
    <form class="github-automation-form">
      <label>
        <span>Dataset handle</span>
        <input id="githubAutomationDataset" value="${GITHUB_AUTOMATION.defaultDataset}" autocomplete="off" />
      </label>
      <label>
        <span>Max reference download MB</span>
        <input id="githubAutomationMaxDownloadMb" value="${GITHUB_AUTOMATION.defaultMaxDownloadMb}" inputmode="numeric" autocomplete="off" />
      </label>
      <label>
        <span>Branch</span>
        <input id="githubAutomationRef" value="${GITHUB_AUTOMATION.defaultRef}" autocomplete="off" />
      </label>
      <label class="github-token-field">
        <span>GitHub token</span>
        <input id="githubAutomationToken" type="password" autocomplete="off" placeholder="fine-grained token: Actions read/write" />
      </label>
      <div class="github-automation-actions">
        <button type="submit">啟動 Eoin audit</button>
        <a id="githubAutomationRunLink" href="#" target="_blank" rel="noopener" hidden>查看最新 run</a>
      </div>
      <div class="github-automation-status" id="githubAutomationStatus" data-tone="muted">Eoin v1 已通過；僅在新版資料需要重驗時啟動。</div>
    </form>`;

    if (anchor) anchor.insertAdjacentElement("afterend", section);
    else panel.prepend(section);

    const form = qs(".github-automation-form", section);
    if (form) form.addEventListener("submit", handleGithubAutomationSubmit);
  }

  function ensureSourceQueue() {
    const panel = qs('[data-panel="sources"]');
    if (!panel || qs("#secondarySourceQueue")) return;
    const modelStatus = qs("#modelRegistryStatus", panel);
    const hero = qs(".sources-hero", panel);
    const section = document.createElement("section");
    section.id = "secondarySourceQueue";
    section.className = "storage-card current-source-queue";
    section.innerHTML = `<div>
      <span class="eyebrow">SECONDARY SOURCE QUEUE</span>
      <h2>資料來源進件分工</h2>
      <p>系統只跑 aggregate census、internal qualification 與 cross-source frozen gates，不把原始資料 commit 進 GitHub。</p>
    </div>
    <div class="registry-grid">
      <article class="registry-card restricted">
        <div><span>Wyatt Walsh</span><em>STRUCTURAL_BLOCKED</em></div>
        <h2>同一份 SQLite / DuckDB 停止重試</h2>
        <dl>
          <div><dt>SQLite</dt><dd>16 tables, ends 2023-06-12</dd></div>
          <div><dt>DuckDB</dt><dd>12 KB empty shell</dd></div>
          <div><dt>重開條件</dt><dd>必須是 materially new bundle</dd></div>
        </dl>
      </article>
      <article class="registry-card licensed">
        <div><span>Eoin A Moore</span><em>ROLE_LIMITED_ELIGIBLE</em></div>
        <h2>adapter self-test implementation 已建立</h2>
        <dl>
          <div><dt>已完成</dt><dd>predeclaration + local synthetic self-test</dd></div>
          <div><dt>下一步</dt><dd>GitHub CI artifact review</dd></div>
          <div><dt>限制</dt><dd>full adapter execution disabled</dd></div>
        </dl>
      </article>
      <article class="registry-card odds">
        <div><span>Odds</span><em>PAUSED</em></div>
        <h2>市場資料線維持關閉</h2>
        <dl>
          <div><dt>缺口</dt><dd>lawful PIT bookmaker odds</dd></div>
          <div><dt>不能宣稱</dt><dd>CLV, EV, ROI, Drawdown</dd></div>
          <div><dt>Stake</dt><dd>0</dd></div>
        </dl>
      </article>
    </div>`;

    if (modelStatus) modelStatus.insertAdjacentElement("afterend", section);
    else if (hero) hero.insertAdjacentElement("afterend", section);
    else panel.prepend(section);
  }

  function updateValidationCopy() {
    const panel = qs('[data-panel="validation"]');
    if (!panel) return;
    const title = qs(".view-hero h1", panel);
    const copy = qs(".view-hero p", panel);
    const card = qs(".view-hero .state-card", panel);
    setText(title, "研究驗證中心");
    setText(copy, "Historical model 已小幅優於 Elo，但在 1,894 場 closing benchmark 明顯輸給 Closing Market。PIT odds join 前，網站只保留研究展示與資料進件流程。");
    if (card) {
      const strong = qs("strong", card);
      const small = qs("small", card);
      setText(strong, "Pre-Market-Backtest");
      setText(small, "正式投注模式關閉");
    }
  }

  function apply() {
    ensureStylesheet();
    ensureHeader();
    updateRail();
    ensureAnalysisStatus();
    ensureGithubAutomationLauncher();
    ensureSourceQueue();
    updateValidationCopy();
    document.documentElement.dataset.currentResearchStatus = "applied";
  }

  function boot() {
    apply();
    [150, 500, 1000, 2000, 4000].forEach((delay) => window.setTimeout(apply, delay));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
}());
