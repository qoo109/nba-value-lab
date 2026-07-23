#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const context = {
  console,
  Date,
  document: {
    documentElement: { dataset: {} },
    createElement: () => ({
      dataset: {},
      textContent: "",
      href: "",
      download: false,
      setAttribute(name, value) { this[name] = value || true; },
    }),
    querySelector: () => null,
    querySelectorAll: () => [],
  },
};
context.window = context;
vm.createContext(context);

for (const path of ["js/v4-data.js", "js/v4-core.js", "js/v4-6-model-coordination.js", "js/v4-11-g1-2-0-ev-primary.js"]) {
  vm.runInContext(fs.readFileSync(path, "utf8"), context, { filename: path });
}

context.testV = JSON.parse(fs.readFileSync("models/v3/3.1.1/config.json", "utf8"));
context.testG = JSON.parse(fs.readFileSync("models/g1/1.1.1/config.json", "utf8"));
context.testG120 = JSON.parse(fs.readFileSync("models/g1/1.2.0/config.json", "utf8"));
context.testCoordination = JSON.parse(fs.readFileSync("models/coordination/v3.1.1-g1.1.1/config.json", "utf8"));
context.testManifest = JSON.parse(fs.readFileSync("models/manifest.json", "utf8"));
vm.runInContext(
  "runtimeModelRegistry = { manifest: testManifest, V: testV, G: testG }; runtimeCoordination = testCoordination;",
  context,
);

function candidate(id, odds, conservative) {
  return {
    id,
    game: { id, confidence: "高", newsRisk: 0 },
    target: { odds, conservative, neutral: conservative, optimistic: conservative },
    opponent: { odds: 2.5 },
  };
}

context.testCandidate = candidate("frontend-core", 1.50, 75);
let result = vm.runInContext("coordinationDecision(testCandidate)", context);
assert.equal(result.v.grade, "ㄅ");
assert.equal(result.g.grade, "ㄅ");
assert.equal(result.grade, "ㄅ");
assert.equal(result.label, context.testCoordination.combined_policy.v_and_g_label);

context.testCandidate = candidate("frontend-extension", 1.65, 70);
result = vm.runInContext("coordinationDecision(testCandidate)", context);
assert.equal(result.v.grade, "ㄆ");
assert.equal(result.g.grade, "ㄅ");
assert.equal(result.grade, "ㄆ");
assert.equal(result.label, context.testCoordination.combined_policy.g_only_label);

vm.runInContext("runtimeModelRegistry.G = testG120;", context);
context.testCandidate = candidate("frontend-g120-b", 2.00, 55);
result = vm.runInContext("gDecision(testCandidate)", context);
assert.equal(result.grade, "ㄅ");
assert.equal(result.decisionMetric, "conservative_ev");
assert.equal(Math.round(result.conservativeEv * 1000) / 1000, 0.1);
assert.equal(result.ppGuardPass, true);
vm.runInContext("runtimeModelRegistry.G = testG; runtimeScheduledGConfig = testG120;", context);
result = vm.runInContext("scheduledGDecision(testCandidate)", context);
assert.equal(result.grade, "ㄅ");

const downloadState = JSON.parse(JSON.stringify(vm.runInContext(`
  function mockLink(text) {
    return {
      dataset: {},
      textContent: text,
      href: "",
      download: false,
      setAttribute(name, value) { this[name] = value || true; },
    };
  }
  const downloads = {
    children: [
      mockLink("下載 V3 規格"),
      mockLink("下載 G1 規格"),
      mockLink("下載來源登錄"),
      mockLink("下載來源 JSON"),
    ],
    querySelector(selector) {
      if (selector === "a") return this.children[0] || null;
      const match = selector.match(/^a\\[data-download-id="([^"]+)"\\]$/);
      if (match) return this.children.find((link) => link.dataset.downloadId === match[1]) || null;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === "a:not([data-download-id])") return this.children.filter((link) => !link.dataset.downloadId);
      if (selector === "a") return this.children;
      return [];
    },
    insertBefore(link, beforeNode) {
      const index = this.children.indexOf(beforeNode);
      if (index >= 0) this.children.splice(index, 0, link);
      else this.children.push(link);
    },
    append(link) { this.children.push(link); },
  };
  const panel = { querySelector(selector) { return selector === ".downloads" ? downloads : null; } };
  refreshRuleDownloads(panel, testManifest);
  downloads.children.map((link) => ({ id: link.dataset.downloadId, text: link.textContent, href: link.href }));
`, context)));

assert.deepEqual(
  downloadState.map((link) => link.id),
  ["complete-rules", "v-spec", "g-spec", "source-registry", "source-json", "coordination-spec", "g120-spec"],
);
assert.equal(downloadState[0].text, "下載完整統整規則");
assert.equal(downloadState[0].href, "./models/releases/v3.1.1-g1.1.1-complete/spec.md");
assert.equal(downloadState[5].href, "./models/coordination/v3.1.1-g1.1.1/spec.md");
assert.equal(downloadState[6].href, "./models/g1/1.2.0/spec.md");

console.log("Frontend model coordination tests passed");
