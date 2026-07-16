# Model Registry

## 更新模型的正確方式

1. 建立新的版本資料夾，例如 `models/v3/3.1/`。
2. 放入 `spec.md` 與 `config.json`。
3. 更新 `models/manifest.json` 的 active 版本與路徑。
4. 推送到 `main`。
5. GitHub Actions 驗證成功後，GitHub Pages 自動發布。

## 重要原則

- `spec.md` 給人閱讀，不直接驅動運算。
- `config.json` 給網站執行。
- 舊版本不可覆寫，歷史預測必須保存當時的 V、G 版本。
- 若只是改門檻、價格層或 Gate，可只改設定。
- 若新增全新資料欄位、公式或模型結構，仍需要同步更新程式。
