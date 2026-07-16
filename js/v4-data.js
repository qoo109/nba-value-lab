"use strict";

const MODEL_VERSION = "V3 × G1";
const APP_VERSION = "V4.4";
const THEME_KEY = "nba-value-lab-theme";

const gradeInfo = {
  "ㄅ": { label: "ㄅ級・研究候選", tone: "qualified", rule: "核心價格層通過對應安全邊際" },
  "ㄆ": { label: "ㄆ級・條件觀察", tone: "watch", rule: "接近門檻或該價格層尚未開放" },
  "ㄇ": { label: "ㄇ級・價格合理", tone: "fair", rule: "保守優勢為正但緩衝不足" },
  "不支持": { label: "模型不支持", tone: "reject", rule: "保守勝率低於損益平衡" },
  "資料不足": { label: "資料不足", tone: "insufficient", rule: "無法可靠建立勝率" },
};

const games = [
  {
    id: "den-phx", matchup: "DEN @ PHX", start: "10:00", focusSide: "away", coreReady: true,
    away: { code: "DEN", name: "丹佛金塊", odds: 1.58, conservative: 70, neutral: 74, optimistic: 76 },
    home: { code: "PHX", name: "鳳凰城太陽", odds: 2.50, conservative: 24, neutral: 26, optimistic: 30 },
    coverage: 91, confidence: "高", injury: "核心傷病與先發已確認", newsRisk: 0, snapshot: "模擬 T−60m 09:32",
    headline: "V3 與 G1 同時通過，DEN 符合核心主推硬 Gate",
    build: { base: 68, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 2], ["傷病輪替", 1], ["賽程休息", 1], ["戰術風格", 0], ["主場移動", 1]] },
    reasons: ["長期調整後淨效率與半場進攻支持 DEN", "覆蓋率、傷病確認與區間寬度通過核心條件", "目前價格高於最低可接受賠率"],
    risks: ["PHX 大量三分出手可能放大單場變異", "若價格跌破最低接受賠率則取消候選"],
  },
  {
    id: "bos-nyk", matchup: "BOS @ NYK", start: "07:30", focusSide: "home", coreReady: false,
    away: { code: "BOS", name: "波士頓塞爾提克", odds: 2.55, conservative: 23, neutral: 26, optimistic: 28 },
    home: { code: "NYK", name: "紐約尼克", odds: 1.52, conservative: 72, neutral: 74, optimistic: 77 },
    coverage: 83, confidence: "中", injury: "次要輪替待確認", newsRisk: 1, snapshot: "模擬 T−60m 09:30",
    headline: "NYK 通過價格門檻，但覆蓋率未達核心主推標準",
    build: { base: 69, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", 0], ["賽程休息", 1], ["戰術風格", 0], ["主場移動", 2]] },
    reasons: ["主場半場防守與籃板對位略有優勢", "保守勝率通過 V3 與 G1 核心價格門檻"],
    risks: ["資料覆蓋率低於核心主推 85% 門檻", "次要輪替仍需在 T−5m 複核"],
  },
  {
    id: "lal-gsw", matchup: "LAL @ GSW", start: "10:30", focusSide: "home", coreReady: false,
    away: { code: "LAL", name: "洛杉磯湖人", odds: 2.42, conservative: 25, neutral: 28, optimistic: 30 },
    home: { code: "GSW", name: "金州勇士", odds: 1.56, conservative: 70, neutral: 72, optimistic: 75 },
    coverage: 79, confidence: "中", injury: "主力預計出賽", newsRisk: 1, snapshot: "模擬 T−60m 09:27",
    headline: "GSW 通過價格門檻，但資料完整度只適合列優先候選",
    build: { base: 68, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", 0], ["賽程休息", 0], ["戰術風格", 0], ["主場移動", 2]] },
    reasons: ["主場與外線創造能力支持 GSW", "目前價格仍高於最低接受賠率"],
    risks: ["兩隊三分出手量高，單場波動明顯", "資料覆蓋率未達核心主推標準"],
  },
  {
    id: "okc-sas", matchup: "OKC @ SAS", start: "09:00", focusSide: "away", coreReady: false,
    away: { code: "OKC", name: "奧克拉荷馬雷霆", odds: 1.45, conservative: 72, neutral: 75, optimistic: 78 },
    home: { code: "SAS", name: "聖安東尼奧馬刺", odds: 2.80, conservative: 22, neutral: 25, optimistic: 28 },
    coverage: 88, confidence: "高", injury: "傷病已確認", newsRisk: 0, snapshot: "模擬 T−60m 09:35",
    headline: "OKC 勝率較高，但 1.45 的價格仍未達 5pp 研究門檻",
    build: { base: 72, adjustments: [["近期狀態", 1], ["對手品質", 0], ["攻防對位", 1], ["傷病輪替", 0], ["賽程休息", 0], ["戰術風格", 0], ["主場移動", 1]] },
    reasons: ["長期實力支持 OKC", "防守失誤製造能力具備對位優勢"],
    risks: ["低賠造成損益平衡勝率過高", "需要更高賠率才能升級為 ㄅ級"],
  },
  {
    id: "mil-mia", matchup: "MIL @ MIA", start: "08:00", focusSide: "away", coreReady: false,
    away: { code: "MIL", name: "密爾瓦基公鹿", odds: 1.67, conservative: null, neutral: null, optimistic: null },
    home: { code: "MIA", name: "邁阿密熱火", odds: 2.20, conservative: null, neutral: null, optimistic: null },
    coverage: 46, confidence: "不足", injury: "核心狀態未知", newsRisk: 3, snapshot: "未鎖定",
    headline: "核心球員狀態足以改變整場雙向機率",
    build: null, reasons: ["市場價格與比賽身分已確認"],
    risks: ["核心球員出賽與上場限制皆未確認", "資料覆蓋率低於 50%"],
  },
];

const candidates = games.flatMap((game) => ["away", "home"].map((side) => {
  const opponentSide = side === "home" ? "away" : "home";
  return {
    id: `${game.id}-${side}`,
    game,
    side,
    opponentSide,
    target: game[side],
    opponent: game[opponentSide],
  };
}));

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
let activeFilter = "全部";
