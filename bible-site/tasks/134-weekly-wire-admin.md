---
pane: w2:p5
role: qwen
files:
  - bible-site/admin/server.py
  - bible-site/admin/index.html
  - bible-site/admin/admin.js
depends:
  - 133-weekly-wire-build
timeout_min: 25
checks:
  - python3 bible-site/tests/service_checks.py homeadmin admin
  - python3 bible-site/tools/check_all.py
  - python3 bible-site/tests/visual_checks.py
  - python3 bible-site/tests/deploy_checks.py
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不可改動 `home.json` 既有 6 欄位結構與驗證。
**重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 的 bash 指令，只執行單行指令即可。**

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-weekly-wire.md` 第 4 節實作後台最小版「一週封面」：
1. **`bible-site/admin/server.py`**：
   - 新增 `GET /api/home-week`：讀取 `data/home-week.json`（若不存在或損壞回預設 `{"enabled": false, "days": []}`）。
   - 新增 `POST /api/home-week`：沿用既有的登入（`X-Bible-Token`）、CSRF／Origin 檢查、64 KB 上限與原子寫入；驗證 `enabled` 為布林、`days` 為 7 筆、`day` 1..7、書卷與章節存在於 `data/{book}.json`、圖檔存在於 `site/assets/`、`light` 符合 `^#[0-9a-fA-F]{6}$`、不含 `text` 欄位，不合格回 400。
2. **`bible-site/admin/index.html` 與 `bible-site/admin/admin.js`**：
   - 在主頁設定區旁加入 `<section class="card" id="home-week-settings">`（「一週封面」）：顯示七天的星期、主題、經文出處與縮圖預覽，以及一個啟用／停用整組輪換的開關（寫入 `POST /api/home-week` 的 `enabled`）。
   - 逐日編輯主題／經文／換圖本輪不做。
3. 確認 `service_checks.py homeadmin admin`、`check_all.py`、`visual_checks.py`、`deploy_checks.py` 全部退出碼 0。
