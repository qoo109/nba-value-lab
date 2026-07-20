# NBA Value Lab 完整統整規則

## V3.1.1 x G1.1.1 x Coordination 1.2.0

- 發布識別碼：NVL-RULES-V3.1.1-G1.1.1-C1.2.0-20260719
- 文件日期：2026-07-19
- 適用市場：NBA 賽前雙向獨贏盤，預設包含延長賽
- 狀態：研究規格，尚未證明具有可持續獲利能力
- 正式投注額：0

> 這份是給網站下載的完整統整版。可執行門檻仍以各版本 `config.json` 為準；本檔把 active V、G 與協調層的決策邏輯放在同一份文件，避免只下載 V 或 G 時誤解最終結論。

## Active Registry

| 層級 | 版本 | 修訂識別碼 | 原始規格 |
|---|---|---|---|
| V engine | V3.1.1 | V3.1.1-20260719 | `models/v3/3.1.1/spec.md` |
| G engine | G1.1.1 | G1.1.1-20260719 | `models/g1/1.1.1/spec.md` |
| Coordination | 1.2.0 | V3.1.1_X_G1.1.1-20260719 | `models/coordination/v3.1.1-g1.1.1/spec.md` |

同一筆研究紀錄必須同時保存 V grade、G grade 與 coordination grade。協調層只負責合併顯示與候選分類，不建立、不平均、不加權任何勝率。

## 目前可以做與不能做

可以做：

- 使用手動輸入或合規來源建立同莊家、同市場、同時間的主客雙邊盤口快照。
- 用 V 與 G 分開計算價格層、break-even、EV、門檻距離與研究分級。
- 在 T-60m 鎖定研究預測，在 T-5m 只複核價格與突發資訊。
- Closing 後追加 CLV 與結果驗證，不覆寫賽前預測。

不能做：

- 不自動登入或繞過博彩網站限制抓取完整盤口。
- 不在未驗證前輸出正式下注建議、下注金額或保證獲利結論。
- 不用目標莊家價格回頭改模型勝率。
- 不為了湊主要場次降低 Gate。

## 共用數學

機率在資料與程式中使用 0 到 1；畫面顯示百分比與 pp。

| 名稱 | 公式 |
|---|---|
| 損益平衡機率 `P_BE` | `1 / target_odds` |
| 雙向比例去水 | `(1 / target_odds) / ((1 / target_odds) + (1 / opponent_odds))` |
| 情境 EV | `probability * target_odds - 1` |
| 保守優勢 `EdgePP` | `(P_C - P_BE) * 100` |
| 距離門檻 `ThresholdDistancePP` | `EdgePP - RequiredMarginPP` |
| 最低接受賠率 | `1 / (P_C - RequiredMarginPP / 100)` |

最低接受賠率只有在分母大於 0 時定義。更換去水方法、EV 公式或門檻距離公式，必須建立新版本並重新驗證。

## 基礎分級表

V 與 G 都使用相同的基礎價格數學，再由各自價格層、資料 Gate 與協調層向下降級或封頂。

| 條件 | 基礎分級 |
|---|---|
| 關鍵資料不足、信心為資料不足或新聞風險 3 | 資料不足 |
| `EdgePP < 0` | 不支持 |
| `RequiredMarginPP` 不適用 | ㄆ級，再套用價格層封頂 |
| `ThresholdDistancePP >= 0` | ㄅ級 |
| `-3 <= ThresholdDistancePP < 0` | ㄆ級・條件觀察 |
| `ThresholdDistancePP < -3` 且 `EdgePP >= 0` | ㄇ級・價格合理 |

低信心、Coverage 不足、新聞風險 2、價格延伸區或協調衝突都只能降級或封頂，不能把原本較低的結論升級。

## V Engine V3.1.1

V 負責已鎖定勝率與目標莊家價格的比較。`prediction` 與 `price_evaluation` 必須分離：價格變動只新增 price evaluation，不改 prediction id，也不改 `P_C/P_N/P_O`。

### V 價格層

| 程式邊界 | 定位 | 未獨立驗證前最高結論 |
|---|---|---|
| `[1.20, 1.30)` | 極低價格區 | 排除・極低價格 |
| `[1.30, 1.40)` | 低價延伸研究區 | ㄆ級・延伸研究 |
| `[1.40, 1.60]` | 核心決策區 | 可依完整規則列 ㄅ級・研究候選 |
| `(1.60, 1.75]` | 高價延伸研究區 | ㄆ級・延伸研究 |
| `(1.75, 2.00)` | 另行校準區 | 另行校準 |
| 其他，包括 `2.00` | 超出目前策略 | 範圍外 |

`core_odds_scope = [1.40, 1.60]` 只代表 V 可取得 ㄅ級的核心區，不代表全部可分類範圍。

## G Engine G1.1.1

G 負責資料 Gate、雙向一致性、價格分層、主要場次 Gate 與排序。G 不把目標莊家價格放入勝率特徵，也不與 V 混合勝率。

### G 價格層

| 程式邊界 | 定位 | Stage 0-2 門檻 | ㄅ級資格 |
|---|---|---:|---|
| `[1.01, 1.20)` | 極低價層 | 不開放 | 只記錄 |
| `[1.20, 1.35)` | 低價研究層 | 7pp | 最高 ㄆ級・延伸研究 |
| `[1.35, 1.60]` | 偏熱門核心層 | 5pp | 可依完整規則判定 |
| `(1.60, 2.20]` | 接近盤／小冷核心層 | 6pp | 可依完整規則判定 |
| `(2.20, 3.50]` | 中高價研究層 | 8pp | 最高 ㄆ級・延伸研究 |
| `(3.50, +∞)` | 高波動研究層 | 不開放 | 只記錄 |

### G 資料 Gate

任一關鍵條件失敗即停止或降級：

- 比賽身分、隊伍、市場、延長賽規則可確認。
- 同莊家、同市場、同時間的主客雙邊價格存在。
- 獨立基本面基準存在，且目標莊家價格未進入勝率特徵。
- 核心傷病與輪替情境可判定。
- 來源衝突已處理，schema 與來源血緣完整。
- OOD、stale 或未建模反向路徑不得列為主要場次。

### Coverage 權重

八項證據權重為 25 / 12 / 10 / 18 / 15 / 10 / 5 / 5，缺失權重不得重分配。

| 覆蓋狀態 | 條件 |
|---|---|
| 高 | 至少 85%，且無關鍵缺口 |
| 中 | 65% 到 84.9% |
| 低 | 50% 到 64.9%，最高 ㄆ級 |
| 資料不足 | 低於 50% 或關鍵欄位失敗 |

## 雙邊一致性

同一場必須同時建立主客兩個候選邊：

- `P_N(home) + P_N(away) = 1`
- `P_C(home) + P_O(away) = 1`
- `P_C(away) + P_O(home) = 1`

若同場兩邊同時符合 G ㄅ級數學條件，標記雙邊價值衝突，coordination grade 固定為 ㄆ，並阻止主要場次。

## 協調層 1.2.0

協調層前置條件：

- V 與 G 必須使用相同 `analysis_cutoff` 與 `data_version`。
- 兩套引擎必須保留獨立輸出。
- 不得平均、加權或人工折衷兩套勝率。
- 任一引擎資料不足時，協調層以資料不足為優先。

### 合併規則

1. 雙邊價值衝突時，協調結論固定 ㄆ級並阻止主要場次。
2. V 位於核心區，且 V 與 G 都為 ㄅ級時，才可顯示「V3.1.1 x G1.1.1 雙引擎候選」。
3. 只有 G 為 ㄅ級時，保留 G 單引擎研究資格，但 coordination grade 最高 ㄆ級。
4. V 位於延伸區時，即使 G 為 ㄅ級，coordination grade 仍最高 ㄆ級。
5. 只有 V 為 ㄅ級時，coordination grade 最高 ㄆ級，標記 G Gate 未通過。
6. 其他情況取兩套引擎中較低結論，不得向上升級。

## 主要場次政策

- 一般目標：每批 2 場。
- 硬上限：每批 3 場。
- 允許 0 或 1 場，不為湊數降低 Gate。
- 網站優先候選最多 2 場，且不是正式 G1 grade。
- 最高 EV 或最高中性勝率不能單獨決定主要場次。

第三場必須額外滿足：Coverage 至少 90%、區間不超過 5pp、至少 4 個比較來源、主要緩衝至少 2pp、新聞風險 0、高信心，且通過所有基本 Gate。

## 時點流程

| 時點 | 功能 | 限制 |
|---|---|---|
| T-24h | 研究預覽 | 最高 ㄆ級 |
| T-60m | 鎖定預測、建立待確認主要場次 | 不可回頭改勝率 |
| T-5m | 最終複核價格、傷病與突發資訊 | 價格變動不得改 prediction |
| Closing | 追加 CLV 與結果驗證 | 不覆寫賽前紀錄 |

## 研究紀錄必備欄位

每筆紀錄至少保存：

- `prediction_id`
- `price_evaluation_id`
- `model_v`
- `model_g`
- `coordination_id`
- `v_grade`
- `g_grade`
- `coordination_grade`
- `target_odds`
- `opponent_odds`
- `P_C`
- `P_N`
- `P_O`
- `break_even_probability`
- `no_vig_probability`
- `edge_pp`
- `threshold_distance_pp`
- `minimum_acceptable_odds`
- `analysis_cutoff`
- `data_version`
- `source_lineage`
- `formal_stake_fraction = 0`

## 驗證要求

- 禁止 random split。
- 必須使用 nested walk-forward。
- final holdout 只能解封一次。
- 必須分開報告 V、G、coordination、主要場次與優先候選結果。
- CLV、Brier Score、Log Loss、ROI 只能在 point-in-time 紀錄足夠後作為驗證輸出。
- 未完成 Stage 2 與前瞻紙上測試前，不宣稱模型有效或具有獲利能力。

## 完整性

本完整統整版由 `models/manifest.json` 註冊，並指向 active V、G 與 coordination 規格。發布前必須通過 `scripts/validate_model_registry.py`，確認 active config、spec hash、協調政策與 prediction schema 相容。
