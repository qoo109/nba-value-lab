# NBA Value Lab — G1 EV-Primary Shadow Specification v1

- 文件日期：2026-07-23
- 文件狀態：**Shadow Only／Inactive／No Production Effect**
- 對應正式基準：`G1.1.1-20260719`
- 正式 Stake：`0`
- 目的：在不改動現行 G1.1.1、網站正式分級、主要場次與資金規則的前提下，平行比較「EV 主導」與現行「PP／ThresholdDistancePP 主導」的決策品質。

> 本文件只建立影子研究規則，不啟用新模型、不改寫勝率、不產生正式下注建議，也不代表 EV 已證明優於現行 G1.1.1。

## 1. 不可覆蓋的正式基準

現行 active Registry 仍為：

- V：`V3.1.1`
- G：`G1.1.1`
- Coordination：`V3.1.1 × G1.1.1`

G1.1.1 的正式基礎分級仍使用：

- `EdgePP`
- `RequiredMarginPP`
- `ThresholdDistancePP`
- Coverage、傷病、新聞、價格時間、雙邊一致性與主要場次 Gate

本 Shadow 不得：

1. 修改 `models/g1/1.1.1/` 內任何既有規格或設定。
2. 修改 active Registry 指向。
3. 改變正式 `ㄅ／ㄆ／ㄇ／資料不足` 結論。
4. 改變正式主要場次數量或排序。
5. 改變正式 Stake；Stake 固定為 `0`。
6. 使用 Closing-only 資料冒充較早可執行價格。

## 2. 研究問題

本 Shadow 要回答的問題是：

> 在所有資料、模型、時間與風險 Gate 相同的條件下，使用「保守 EV」作為主要排序與價值判斷，並保留 PP Edge 作為最低安全門檻，是否能在真正 point-in-time、可執行的市場回測中，穩定優於現行 PP／ThresholdDistancePP 主導規則？

## 3. 共用輸入與數學

Shadow 必須沿用 V3.1.1 已鎖定的機率與價格物件，不得用目標莊家價格回寫模型勝率。

```text
P_C = 保守勝率
O   = 同一莊家、同一市場、同一 observed_at 的十進位賠率
P_BE = 1 / O
EdgePP = (P_C - P_BE) × 100
ConservativeEV = P_C × O - 1
```

基本原則：

- `ConservativeEV`：影子規則的主要價值指標與排序鍵。
- `EdgePP`：最低安全門檻與模型誤差緩衝，不取消。
- Coverage、傷病完整度、新聞風險、雙邊衝突、OOD、stale price 與來源血緣：仍是先行硬 Gate。
- EV 很高但資料 Gate 失敗時，結論仍為 `資料不足／跳過`。

## 4. Shadow 執行順序

```text
Step 1 — 共用資料與模型 Gate
  ↓
Step 2 — 鎖定 P_C 與 point-in-time price
  ↓
Step 3 — 計算 ConservativeEV
  ↓
Step 4 — 檢查 PP Edge 最低安全門檻
  ↓
Step 5 — 套用 Coverage／傷病／新聞／時間／雙邊一致性降級
  ↓
Step 6 — 產生 Shadow 分級與 Shadow 排序
  ↓
Step 7 — 與正式 G1.1.1 結果平行保存，不影響正式輸出
```

## 5. Shadow 分級原則

目前不預先捏造尚未經市場回測驗證的 EV 百分比門檻。第一個可執行 Shadow run 前，必須另行建立並凍結門檻設定；門檻不得在看過結果後調整。

在門檻凍結前，只允許輸出研究欄位：

- `shadow_conservative_ev`
- `shadow_edge_pp`
- `shadow_pp_guard_pass`
- `shadow_ev_rank`
- `shadow_data_gate_pass`
- `shadow_grade_candidate`
- `shadow_main_candidate`
- `shadow_no_selection_reason`

暫定語義：

| 狀態 | Shadow 結論 |
|---|---|
| 任一正式硬 Gate 失敗 | 資料不足／跳過 |
| `ConservativeEV <= 0` | 不支持 |
| EV 為正，但 PP 最低安全門檻未通過 | 觀察，不得列主要場次 |
| EV 與 PP 安全門檻均通過 | Shadow 候選，仍需所有風險 Gate |
| 來源不具真實 `observed_at` | 不得納入可執行 Shadow 績效 |

## 6. 與正式 G1.1.1 的公平比較

Baseline 與 Shadow 必須使用完全相同的：

- independent games
- Walk-forward OOF predictions
- 分析時間點
- bookmaker
- market type
- observed_at
- 可下注價格
- 傷病快照
- 缺失處理
- 結算規則
- 無效／取消盤處理

禁止：

- 讓 Shadow 使用較晚價格或 Closing，而 Baseline 使用較早價格。
- 使用不同 bookmaker 拼接價格。
- 只保留 Shadow 命中的比賽。
- 將同一場的多個 snapshots 當成獨立比賽。
- 事後挑選表現最好的 EV 門檻、賠率區間、賽季或 bookmaker。

## 7. 必須比較的正式指標

至少保存：

1. Bet count／eligible count
2. Realized ROI
3. Average EV at selection
4. CLV
5. Hit rate
6. Average odds
7. Maximum drawdown
8. Longest losing streak
9. Season／fold stability
10. Bookmaker stability
11. Odds-band stability
12. Calibration／reliability by selected subset
13. Baseline 與 Shadow 選場重疊率
14. Shadow 新增選場與移除選場的獨立表現

命中率不得單獨作為取代依據。

## 8. 可取代現行 G1 的必要條件

只有以下條件全部成立，才可以提醒使用者評估「正式取代」：

1. 已取得真實 bookmaker-level、帶 `observed_at` 的 Opening／盤中／Closing 資料。
2. Point-in-time Odds Join 已完成並通過 QA。
3. Executable Market Backtest 已完成，不是 Closing-only forecast benchmark。
4. Baseline G1.1.1 與 EV-primary Shadow 已在相同 OOF／價格／時間條件下平行運行。
5. Shadow 的改善不是由單一賽季、單一 bookmaker、單一賠率區間或少數極端場次造成。
6. Shadow 的 ROI／CLV／drawdown／穩定性整體證據優於 Baseline，且沒有以明顯惡化風險換取表面 ROI。
7. 樣本量與獨立場次達到預先凍結的 promotion gate。
8. 所有門檻與比較方法在結果揭露前已預先宣告。
9. Artifact QA 與正式結果檔明確給出：

```text
G1_EV_PRIMARY_REPLACEMENT_READY = true
```

10. 使用者再次明確批准建立新的正式 G 版本；不得直接覆寫 G1.1.1。

若任一條件未成立：

```text
G1_EV_PRIMARY_REPLACEMENT_READY = false
```

## 9. 提醒規則

當 Repository、PR、Workflow 或 Artifact 首次出現可稽核證據，確認第 8 節全部條件成立時，應主動提醒使用者：

> EV-primary Shadow 已達到正式取代評估門檻；是否建立新的 G 版本並更新 active Registry？

提醒只代表可以進入版本升級審查，不代表自動取代、不代表可下注，也不改變 Stake `0`。

## 10. 失敗或無法取代時的處理

可能結果固定為：

- `SHADOW_NOT_EXECUTABLE`：缺真實 timestamped odds。
- `SHADOW_STRUCTURAL_BLOCKED`：資料／樣本／join／來源 Gate 未通過。
- `SHADOW_VALID_NEGATIVE_RESULT`：已公平執行，但 EV-primary 未優於 Baseline。
- `SHADOW_CONTINUE_RESEARCH`：結果混合或不穩定，繼續累積預先定義樣本。
- `SHADOW_REPLACEMENT_REVIEW_READY`：全部 promotion 條件通過，可提醒使用者審查新版本。

負結果必須保存，不得為了讓 EV 成為主指標而降低 Gate 或重複調門檻。

## 11. 目前正式狀態

```text
G1 EV-primary shadow specification: DOCUMENTED
shadow implementation: NOT STARTED
real timestamped odds: NOT ACQUIRED
executable shadow backtest: NOT RUN
replacement review: NOT AUTHORIZED
G1.1.1 active status: UNCHANGED
formal Stake: 0
```

目前唯一允許的結論：

> 保留 G1.1.1 為正式基準；EV-primary 僅作平行 Shadow。等真正可執行的市場資料與公平回測完成後，再依預先宣告的 promotion gate 決定是否提醒並建立新版本。