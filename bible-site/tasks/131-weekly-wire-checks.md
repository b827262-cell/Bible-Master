---
pane: w2:p5
role: qwen
files:
  - bible-site/tests/site_checks.py
  - bible-site/tests/home_probe.html
  - bible-site/tests/visual_checks.py
  - bible-site/tests/deploy_checks.py
  - bible-site/tests/service_checks.py
timeout_min: 20
checks:
  - python3 -m py_compile bible-site/tests/site_checks.py bible-site/tests/visual_checks.py bible-site/tests/deploy_checks.py bible-site/tests/service_checks.py
  - python3 bible-site/tests/site_checks.py home
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的 5 個測試檔案，不可先改網站程式或資料檔。
**重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 的 bash 指令，只執行單行指令即可。**

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-weekly-wire.md` 的「1–5」節，先寫客觀檢查（在實作前應為紅燈）：

1. **`bible-site/tests/site_checks.py` 與 `bible-site/tests/home_probe.html`（新增 `homeweek` 群組並加入預設 `groups`）**：
   - `homeweek_assets()`：
     - 檢查 `bible-site/site/assets/cover-1-mon.jpg` … `cover-7-sun.jpg` 共 7 個檔案皆存在、非空、`<= 600 KB`、16:9（寬 `>= 1600`、`abs(w/h - 16/9) < 0.03`），且皆登記於 `bible-site/ASSETS-LICENSE.md`（1–3 含 `AGY`／`Imagen 3`，4–7 含 `Codex`／`image_gen`）。
     - 檢查 `bible-site/data/home-week.json` 存在、為合法 JSON、`enabled` 為布林、`days` 為 7 筆陣列（`day` 1..7 齊全），每筆含 `theme`、`book`、`ch`、`v`、`image`、`alt`、`light`，**不含** `text` 欄位且整份檔案不含任何與四福音和合本連續 8 字相同的經文；每筆 `light` 為 `#rrggbb` 且相對亮度 `>= 0.72`、在 `.hero-body` 深底上的對比 `>= 7.0`。
   - `homeweek_render(port)`（透過 `home_probe.html` 支援 `?wk=1` 或單獨測 `?day=1..7` 與退回情境）：
     - 7 個 `?day=1` … `?day=7` 各自渲染對應的 `cover-X-xxx.jpg`、`alt`、`#hero-ref` 含 `星期X`＋主題＋書卷章節、`--sunlight` 為該天 `light`、經文 `#hero-verse` 與 `data/{book}.json` 該節逐字一致、`#read-link` 指向 `chapter.html?book=...&ch=...#v...`、圖片與經文不重疊、對比 `>= 7:1`、無 JS 錯誤、320/375/768/1440px 無水平溢出。
     - 不帶 `?day` 時：在探測頁模擬／覆寫 `Asia/Taipei` 時間或測試預設台灣時間星期幾能對應顯示正確那一天的封面與經文。
     - 退回情境（使用臨時複製或 route mock，絕不改動真實 `data/`）：`home-week.json` 404、壞 JSON、`enabled: false`、缺當天、無效節數（如 `v: 999`）、圖片 404 時，皆安靜退回 `home.json` 預設封面（路加福音 4:27 / `jordan.jpg`），無 JS 錯誤、不顯示錯誤字樣。
2. **`bible-site/tests/visual_checks.py`**：
   - 在 `p2` 加入對 `home.html?day=1` … `home.html?day=7`（可抽測或全測）檢查：圖片載入完成（`naturalWidth > 0`）、無水平溢出、圖片與文字不重疊。
3. **`bible-site/tests/deploy_checks.py`**：
   - 檢查 `dist/data/home-week.json` 存在，且其中列出的 7 張 `cover-*.jpg` 皆存在於 `dist/site/assets/`。
   - 在臨時副本刪除 `data/home-week.json` 後執行 `build_public.py`，仍須成功退出（exit 0）。
4. **`bible-site/tests/service_checks.py`（`homeadmin` 群組）**：
   - 測試 `GET /api/home-week` 與 `POST /api/home-week`（切換 `enabled` true/false；無 token 回 403；壞 JSON／缺欄位／不存在的經文座標／不存在的圖檔／非法 `light` HEX 回 400；原子寫入且不影響既有 `home.json` 6 欄位與真實檔案）。
   - 檢查後台頁面 `admin/index.html` 含有 `#home-week-settings`（「一週封面」區塊與啟用開關）。
5. **驗證**：執行 `py_compile` 與 `python3 bible-site/tests/site_checks.py home` 確認既有 `home` 檢查仍全數通過。
