# NBA Value Lab V5.2 UI P2

## 目標

V5.2 在不修改 V3.1 × G1.1 模型與研究資料格式的前提下，加入靜態網站可用的頁面路由與精簡趨勢圖。

## 路由

網站使用 Hash Router，不依賴伺服器 rewrite：

- `#/dashboard`：今日分析
- `#/picks`：主要場次
- `#/validation`：模型驗證
- `#/sources`：資料來源
- `#/research`：研究紀錄

重新整理會保留目前頁面；瀏覽器上一頁與下一頁可切換分頁。手機底部導覽與桌面導覽使用同一套路由狀態。

## 趨勢圖

### 歷史績效趨勢

只使用已有賽果的正式主要場次：

- 紙上淨值曲線
- 累積命中率
- CLV 序列

缺少有效市場賠率的紀錄不會加入淨值曲線。

### 單場市場賠率與勝率軌跡

同一場、同一選擇方至少累積兩個正式快照後顯示：

- 中性勝率變化
- 目標市場賠率變化
- T−60m、T−5m、Closing 等階段順序

只有市場賠率更新時應維持同一組比賽勝率；圖表用於快速發現錯誤改動。

## 模組拆分

```text
js/v5/
├─ core/router.js
├─ utils/history.js
├─ utils/sparkline.js
└─ pages/
   ├─ performance-trends.js
   └─ market-trends.js

css/
├─ v5-routing-p2.css
└─ v5-trends-p2.css
```

所有 Sparkline 使用內建 SVG，不加入外部圖表套件，也不增加大型資料檔。

## 資料安全

- 不使用示範 slate 製造趨勢。
- 不保存 Box Score 或 Play-by-play。
- 歷史紀錄仍為 append-only。
- 同場同選擇方績效只保留較新的最終版本。
- 所有歷史文字在新增 V5.2 卡片時先做 HTML escaping。
