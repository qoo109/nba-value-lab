# NBA Value Lab — G1.2.0 EV-Primary Specification

- 文件日期：2026-07-23
- 版本：`G1.2.0`
- Revision：`G1.2.0-20260723`
- 狀態：**Approved for 2026-27 Season Activation / Research & Paper Only**
- 前一正式基準：`G1.1.1-20260719`
- 正式 Stake：`0`

## 1. 版本目的

G1.2.0 將 G 系統的主要價值判斷由固定 `PP Edge / ThresholdDistancePP` 改為
`ConservativeEV` 主導；`EdgePP` 不刪除，改為最低安全線。

本版本不修改 V3.1.1 的勝率模型，也不得使用目標莊家價格回寫模型機率。

```text
P_C = 保守勝率
O = 同一莊家、同一市場、同一 observed_at 的十進位賠率
P_BE = 1 / O
EdgePP = (P_C - P_BE) × 100
ConservativeEV = P_C × O - 1
```

## 2. 啟用規則

- 使用者已批准 G1.2.0 成為 2026-27 NBA 例行賽起的主要 G 規則。
- 啟用觸發：第一場具備完整 T-60 資料 Gate 的 2026-27 NBA 例行賽。
- G1.1.1 保留為不可覆寫的 Control／Shadow，不再主導新賽季主要選場。
- 若新賽季資料 Gate 不完整，允許輸出 `資料不足`，不得回退成無 Gate 的選場。
- 正式 Stake 固定為 `0`；此啟用不等於投注授權。

## 3. EV 分級

在所有資料與風險 Gate 通過後，依 `ConservativeEV` 分級：

| 結論 | 條件 |
|---|---|
| ㄅ級・EV 核心候選 | `ConservativeEV >= 10%` 且 `EdgePP >= 2pp` |
| ㄆ級・EV 觀察候選 | `7% <= ConservativeEV < 10%` 且 `EdgePP >= 2pp` |
| ㄇ級・最低正 EV | `5% <= ConservativeEV < 7%` 且 `EdgePP >= 2pp` |
| 觀察／不列主要場次 | EV 為正但未達 5%，或 PP 安全線未通過 |
| 不支持 | `ConservativeEV <= 0` |
| 資料不足／跳過 | 任一硬 Gate 失敗 |

固定門檻：

```text
最低候選 EV：5%
ㄆ級 EV：7%
ㄅ級 EV：10%
最低 PP 安全線：2pp
```

不得因短期結果事後調整門檻；任何門檻變更必須建立新版本。

## 4. 價格範圍

沿用 G1.1.1 價格研究架構：

- 正式核心：`1.35–1.60` 與 `(1.60–2.20]`
- `1.20–1.35`、`2.20–3.50`：延伸研究，不得因 EV 高直接升為正式核心
- `<1.20`、`>3.50`：只記錄

舊版各價格帶 `required_margin_pp` 僅保留作 Control 診斷欄位，
不再作為 G1.2.0 的主要分級門檻。

## 5. 不可放寬的硬 Gate

G1.2.0 必須沿用並保留：

- Coverage 核心門檻 `>=85%`
- 高信心與預測區間寬度限制
- 傷病與輪替確認
- 新聞風險限制
- OOD／未建模反向路徑阻擋
- 同一莊家、同一市場、同一時間的雙邊價格
- 至少 3 個比較來源
- 來源血緣與時間戳
- 雙邊價值衝突阻擋主要場次
- T-60 鎖定、T-5 重選與 Closing 僅驗證

EV 很高不會覆蓋任何資料或風險 Gate。

## 6. 排序與主要場次

所有硬 Gate 通過後，排序優先順序：

1. 資料新鮮度與無關鍵缺口
2. 傷病與輪替確定性
3. 較窄的模型區間
4. 較高 `ConservativeEV`
5. 較高 `EdgePP` 安全餘裕
6. 較可解釋的模型／市場差異
7. 較少未解決反向路徑
8. 相似案例校準與 CLV 穩定性

正式主要場次目標 2 場、上限 3 場，允許 0 場。
不得只因 EV 最高就列為主要場次。

## 7. V × G 協調

- V3.1.1 與 G1.2.0 必須獨立產生機率與分級。
- 不做機率平均、加權或融合。
- 同一 cutoff、同一資料版本、同一價格時間。
- 雙引擎候選必須兩邊都通過各自 Gate。
- G-only 或 V-only 最高維持 ㄆ級研究候選。
- 資料不足優先於任何分級。

## 8. 新賽季監測

新賽季必須同時保存：

- G1.2.0 primary 結果
- G1.1.1 control 結果
- 入選場數、勝率、平均賠率
- realized ROI（僅紙上研究）
- CLV
- 最大回撤與最長連敗
- 月份、主客場、賠率帶與 bookmaker 穩定性
- 兩版本選場重疊率與新增／移除場次表現

G1.1.1 的 Control 結果不得影響 G1.2.0 當日主要輸出，但必須保存供審計。

## 9. 發布邊界

```text
external status: 模型驗證與紙上測試
formal Stake: 0
real-money execution: prohibited
betting edge claim: prohibited until governed validation
```

G1.2.0 的啟用代表規則版本切換，不代表已證明能獲利。
