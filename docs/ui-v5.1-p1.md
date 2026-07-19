# NBA Value Lab V5.1 UI P1

## Research Timeline

研究紀錄以時間軸呈現 T−60m 鎖定、T−5m 複核、市場賠率變動、基本面更新、Closing 與賽果。原始表格保留為 V4.10 fallback；V5.1 正常載入時隱藏表格。

示範 slate 不得進入正式 Timeline。

## Performance Dashboard

績效只使用：

- `main_candidate = true`
- `won` 已有布林結果
- 同一 `game_id + selection_team_id` 只保留時間較新的版本

指標：

- 命中率：正式主要場次勝場／有效賽果樣本。
- 紙上 ROI：固定每場 1 單位，只使用有效十進位市場賠率。
- 平均 CLV：只使用已有 Closing 的紀錄。
- Brier Score：以中性勝率及二元結果計算。
- 最大回撤：依時間排序的固定 1 單位紙上序列。

所有績效都屬紙上研究，不代表正式投注結果。

## Mobile First

- 720px 以下使用固定底部五分頁導覽。
- 支援 iPhone safe area。
- 所有主要互動元素至少 44px。
- 時點流程與篩選器可橫向滑動。
- Drawer 在手機改為底部 Sheet。

## Light Theme

淺色模式採暖灰背景、米白卡片、深墨文字與低飽和綠色重點。目標是降低長時間閱讀疲勞，同時保持資料密度。

## Dark Theme

深色模式採深藍黑背景、分層藍灰卡片與較柔和的高亮色，避免純黑與過度明亮的霓虹對比。

## Fallback

任何 V5.1 UI 模組載入失敗時，仍使用 V4.10 UI；模型、T−60m、T−5m、歷史資料與 G1.1 選擇邏輯不受影響。
