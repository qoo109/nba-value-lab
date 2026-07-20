# Model Registry

## 更新模型的正確方式

1. 建立新的版本資料夾，例如 `models/v3/3.1/`。
2. 放入自足的 `spec.md` 與 `config.json`；spec 必須包含公式、完整分級表、邊界與限制。
3. 更新 `models/manifest.json` 的 active 版本與路徑。
4. 若 active V/G/協調層改變，同步更新 `models/releases/*-complete/` 的完整統整規則。
5. 推送到 `main`。
6. GitHub Actions 驗證成功後，GitHub Pages 自動發布。

## 重要原則

- `spec.md` 給人閱讀，不直接驅動運算，但必須足以獨立重建設定語意。
- `config.json` 給網站執行。
- active config 必須以 `spec_integrity` 保存 spec 精確檔案位元組的 SHA-256；不得把摘要寫回被雜湊的 spec 本身。
- 舊版本不可覆寫，歷史預測必須保存當時的 V、G 版本。
- 協調層也必須同時提供 `spec.md` 與 `config.json`，並明確保存 V、G、coordination 三個分級。
- 網站下載區的「完整統整規則」必須由 manifest 註冊，並通過 validator 檢查 active components 與 spec hash。
- 若只是改門檻、價格層或 Gate，可只改設定。
- 若新增全新資料欄位、公式或模型結構，仍需要同步更新程式。
