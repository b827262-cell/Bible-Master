---
pane: w2:p1
role: codex
files: [bible-site/tests/site_checks.py]
timeout_min: 30
checks:
  - python3 -m py_compile bible-site/tests/site_checks.py
  - python3 bible-site/tests/site_checks.py devotional
  - python3 bible-site/tools/check_all.py
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、blessing.json、home.json、data/devotional.json、.verify/、資料庫。只能更改 front matter 允許的檔案 `bible-site/tests/site_checks.py`。

請在 `bible-site/tests/site_checks.py` 新增 `devotional` 檢查群組（可單獨執行 `python3 bible-site/tests/site_checks.py devotional`，並納入 `__main__` 預設 `groups` 集合使 `check_all.py` 一併執行）。

### 檢查設計要求
1. **鐵則：不可在測試檔寫死任何經文**：
   - 使用 `tempfile.TemporaryDirectory()` 建立暫存站點副本（複製 `site/` 與 `data/{mat,mrk,luk,jhn,zone-music,home,blessing,blessing-art}.json`），在暫存副本寫入測試用的假 `data/devotional.json`。
   - 假 `devotional.json` 只含 `id`、`devotional_date`、`title`、`scripture_reference`、`ranges`（如 `MAT` 5:1–12 及含合併節的 `LUK` 1:1–4）與佔位文字（`summary`、`reflection`、`prayer`，例如 `"測試默想段落"`、`"測試反思問題"`、`"測試禱告內容"`），**絕對不可寫死任何經文字句**。
   - 預期經文一律由 Python 在測試時從 `data/{mat,mrk,luk,jhn}.json` 依 `ranges` 動態讀出（包含合併節格式 `{ch}:{v}–{end} {text}` 或 `{ch}:{v} {text}`），再與 headless Chrome 渲染後的 `#reading` 內容逐節比對。
2. **必須涵蓋的驗證項目**：
   - **有資料的日期**：顯示 `h2` 標題、`scripture_reference`、「經文」標題、渲染出的經文節數與內容完全等於四福音 JSON 該範圍（測試一般節與合併節）、以及「默想」「反思」「禱告」三段標題與對應內容，`#reading-status` 為空字串。
   - **日期預設與切換**：`#reading-date` 預設值與 `max` 皆為台灣時間（`Asia/Taipei`）今天（`YYYY-MM-DD`）；將 `#reading-date` 切換到另一個有資料的日期（觸發 `change` 事件）會重新渲染該日內容；切換到無資料的日期會清空 `#reading` 並顯示對應提示。
   - **無資料與錯誤情境（皆須無未捕捉的 JavaScript 錯誤）**：
     - 沒有資料的日期 → `#reading-status` 顯示繁體中文提示（`此日期尚無已審核的禱讀內容。`），`#reading` 為空。
     - `devotional.json` 為 `[]` → `#reading-status` 顯示 `此日期尚無已審核的禱讀內容。`。
     - `devotional.json` 不存在（HTTP 404） → `#reading-status` 顯示 `此日期尚無已審核的禱讀內容。`。
     - `devotional.json` 格式錯誤（例如非合法 JSON 或非陣列 `{}`） → `#reading-status` 顯示 `禱讀資料載入失敗，請稍後再試。`。
     - 經文範圍不合法（例如不支援的書卷或找不到經文） → `#reading-status` 顯示 `經文載入失敗，請稍後再試。`。
   - **版面、導覽列與無外部資源**：
     - 在 `320`、`375`、`768`、`1440` 四種視窗寬度下（有渲染禱讀內容時），`scrollWidth <= clientWidth` 無水平溢出。
     - 導覽列 `#nav .nav-list a` 正常產生 4 個項目（目錄、搜尋、經文卡片、抽經文卡），且頁面有回首頁連結 `home.html`。
     - 沒有載入外部資源，沒有任何 Console / pageerror JavaScript 錯誤。
3. **突變測試（Mutation Test）**：
   - 在 `/tmp` 暫存副本中（**絕對不要留在工作樹**）故意把 `site/devotional.js` 的範圍過濾改壞（例如把 `chapter.ch > range.end_chapter` 拿掉，或把 `verse.v > range.end_verse` 改壞），對該副本跑一次檢查，證明新寫的 `devotional` 檢查確實會抓到錯誤並判不通過。
   - 在最終回覆中詳細列出：(a) 新增了哪些檢查項、(b) 突變測試怎麼改、抓到哪幾條不通過、(c) 現有 `site/devotional.html` 與 `site/devotional.js` 是否有被檢查揭露任何缺陷。
