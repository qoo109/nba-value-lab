# Market Residual Analysis v1

更新日期：2026-07-17

## 目的

Closing Market 已明顯優於目前的非市場模型，因此下一步不是直接尋找「下注門檻」，而是檢查模型相對收盤市場是否仍提供可重現的增量資訊。

本層只回答兩個問題：

1. 模型與市場在什麼機率區間、分歧幅度與方向下表現不同？
2. 使用過去賽季選出的少量模型殘差權重，能否在下一個賽季改善 Closing Market 的 Log Loss 與 Brier Score？

## 分析內容

### 殘差分群

報告按以下維度輸出聚合指標：

- 賽季
- Closing 去水主隊勝率區間
- 模型減市場的有號分歧區間
- 模型與市場的絕對分歧區間
- 模型、市場是否站在同一勝負方向

每個群組包含：

- 場次
- 模型與市場 Log Loss
- 模型與市場 Brier Score
- 每場 log score 中模型優於市場的比例
- 模型減市場的平均差值
- bootstrap 95% 區間

這些群組結果都是探索性診斷，不能單獨轉成投注規則。

### 時間留存混合測試

目前可配對資料只有兩個賽季，因此採用：

```text
2021-22：選擇模型殘差權重
2022-23：完全留存測試
```

混合公式：

```text
p_blend = p_market + w × (p_model - p_market)
```

其中 `w` 只能從 0.00 至 1.00、每 0.05 一格的固定網格中選擇。

候選混合只有在以下條件同時成立時才會被標記為有增量訊號：

1. 訓練季選出的 `w > 0`。
2. 留存季的 Log Loss 優於純 Closing Market。
3. 留存季的 Brier Score 優於純 Closing Market。
4. 兩項改善的 bootstrap 95% 上界都小於 0。

即使通過，仍只代表研究訊號，不會直接啟用正式市場混合模型。

## 安全邊界

Christopher Treasure 資料只有 Closing 標籤，沒有精確 observation timestamp，因此固定禁止：

- ROI 回測
- CLV 計算
- 進場價模擬
- 投注優勢宣稱
- 將逐場模型／市場配對資料上傳為 Artifact

Artifact 僅保存：

- 匯入與對齊 QA
- 聚合分群 CSV
- 殘差與時間留存 JSON 報告

## Workflow

```text
Actions
→ Build Market Residual Analysis v1
→ Run workflow
```

輸入：

```text
source_run_id: 29551715399
dataset_handle: christophertreasure/nba-odds-data
```

輸出 Artifact：

```text
market-residual-analysis-v1
```

## 升級條件

要考慮正式 Market Blend，至少還需要：

- 三個以上完整留存賽季
- 來源與 Closing 定義交叉驗證
- 多賽季一致改善
- 獨立於權重選擇的最終 holdout
- 未來 point-in-time 盤口資料
