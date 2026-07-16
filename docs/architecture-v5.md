# NBA Value Lab V5 UI Architecture

## 目標

V5 將 UI 與模型邏輯分離。V3.1、G1.1、T−60m、T−5m、研究紀錄與 Registry 不因畫面重構而改變。

## 新增結構

```text
css/
├─ v5-tokens.css
├─ v5-layout.css
└─ v5-components.css

js/v5/
├─ core/
│  └─ namespace.js
├─ utils/
│  └─ format.js
├─ components/
│  ├─ cards.js
│  └─ drawer.js
├─ pages/
│  └─ dashboard.js
└─ bootstrap.js
```

## 模組責任

- `namespace.js`：建立唯一的 `window.NBAVL.v5` 命名空間。
- `format.js`：研究強度、顏色語意、勝率與理由格式化。
- `cards.js`：首頁主要場次卡與候選卡。
- `drawer.js`：右側分析 Drawer、鍵盤 Escape 與焦點回復。
- `dashboard.js`：首頁資訊層級、進階區塊收合與導覽文字。
- `bootstrap.js`：協調 UI 初始化，不負責模型運算。

## 相容策略

`js/v4-init.js` 先載入既有模型與研究流程，再嘗試載入 V5 UI。若任一 V5 UI 檔案載入失敗，網站會回到 V4.10 介面，模型與資料流程仍可使用。

## 檔案大小政策

- 新增 JavaScript 模組建議不超過 300 行，硬上限 500 行。
- 新增 CSS 模組建議不超過 350 行，硬上限 500 行。
- 舊版大型檔案暫時保留為相容層，後續逐頁搬移後再刪除。
- 不在同一次重構中同時改模型、資料格式與 UI，以降低回歸風險。

## 下一批拆分

1. 將 `v4-render.js` 的表格、試算器與詳情函式搬入獨立模組。
2. 將研究紀錄改為 Timeline 元件。
3. 將 `styles.css` 依 legacy layout、table、form、theme 分割。
4. 等所有頁面完成搬移後，移除舊 Modal 與不再使用的 CSS。
