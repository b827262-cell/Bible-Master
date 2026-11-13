---
pane: w2:p5
role: qwen
files:
  - bible-site/tests/site_checks.py
  - bible-site/tests/visual_checks.py
  - bible-site/tests/blessing_probe.html
  - bible-site/tests/home_probe.html
timeout_min: 25
checks:
  - python3 -m py_compile bible-site/tests/site_checks.py bible-site/tests/visual_checks.py
  - python3 bible-site/tests/site_checks.py --grep "連結都指向存在的檔案"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/tests/site_checks.py`、`bible-site/tests/visual_checks.py`、`bible-site/tests/blessing_probe.html`、`bible-site/tests/home_probe.html`。
**重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 的 bash 指令（會觸發 Qwen CLI 審批確認視窗而導致 pane 進入 blocked 狀態），只執行單行指令即可。**

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-round3.md` 的「每項先寫 `tests/site_checks.py`／`visual_checks.py` 的客觀檢查再實作」，為第三輪的 B、C、D 三個項目先寫好客觀檢查（在頁面尚未實作 B、C、D 前，這些新檢查預期會紅燈；但檔案語法與既有連結檢查須通過）：

### 1. 更新 `bible-site/tests/blessing_probe.html` 與 `site_checks.py`（B. 愛心與背景底紋接線、卡背標題不壓老鷹）
1. **調整 `blessing_probe.html` 等待時間與探測欄位**：
   - 因點擊 `#draw-btn` 或 `#heart-btn` 會先播放約 1.6 秒的小驚喜動圖再翻出經文卡，請把 `blessing_probe.html` 內點擊後的等待迴圈從 `for (let i = 0; i < 20; i++)` 放寬為 `for (let i = 0; i < 35; i++)`（最長 3.5 秒），並把 `site_checks.py` 的 `blessing_state()` 中 `--virtual-time-budget=8000` 調高為 `--virtual-time-budget=18000`。
   - 在 `blessing_probe.html`（及／或 `home_probe.html`）量測並回傳 `heart` 物件：
     - `heartBtn`: 是否有 `#heart-btn`（或 `.heart`）按鈕、是否可見。
     - `heartImg`: `#heart-img` 的 `src` 檔名、`alt`。
     - `stageBg`: 愛心所在區塊（`.heart-stage` 或 `#heart-btn` 父容器）的 `backgroundColor`。
     - `pagePattern`: `body` 或 `.bless-stage`／`main` 的 `backgroundImage` 檔名與 `backgroundSize`。
     - `statusIdle`: 初始狀態列（`#heart-status` 或 `#share-msg`，具 `role="status"`）的文字。
     - `eagleOverlap`: 量測卡背圖容器（`.cover-card`）與卡背標題（`.cover-title`）、抽卡按鈕（`#draw-btn`）的矩形：確認 `.cover-title` 與 `#draw-btn` 不壓在 `.cover-card` 中央老鷹區域（例如位於 `.cover-card` 外部，或位於 `.cover-card` 下半部 `top >= cardRect.top + cardRect.height * 0.65`）。
2. **在 `site_checks.py`（`restyle` 或新增 `heart` 檢查函式並納入預設 `groups`）與 `visual_checks.py` 加入 B 的檢查**：
   - `site/assets/` 內存在 `heart-idle-light.gif`、`heart-idle-dark.gif`、`heart-surprise-light.gif`、`heart-surprise-dark.gif`、`heart-still.png`、`pattern-light.png`、`pattern-dark.png` 共 7 個檔案，皆非空且 `< 600 KB`，並在 `bible-site/ASSETS-LICENSE.md` 登記（含 Codex／OpenAI `image_gen` 與 Pillow 說明）。
   - `blessing.html` 抽卡前顯示待機愛心（淺色 `heart-idle-light.gif`、深色 `heart-idle-dark.gif`、`prefers-reduced-motion: reduce` 時為 `heart-still.png`），愛心區塊底色在淺色為 `rgb(243, 246, 242)`（`#f3f6f2`）、深色為 `rgb(10, 20, 18)`（`#0a1412`）。
   - `blessing.html` 頁面背景鋪設 `pattern-light.png`（淺色）與 `pattern-dark.png`（深色），平鋪尺寸約 `360px`。
   - 狀態列（`role="status"`）待機文字含「點愛心領受今天的祝福」，點擊愛心期間狀態列設 `data-state="busy"` 且文字含「正在為你抽一張卡…」、按鈕設 `aria-busy="true"` 防止重複觸發，完成後抽出經文卡並顯示完成文字。
   - 卡背上的標題（`.cover-title`「天父關心你」）與按鈕（`#draw-btn`）移到卡片下半部深色留白區或卡片外，不遮住老鷹（`eagleOverlap === false`）。

### 2. 更新 `site_checks.py` 與 `visual_checks.py`（C. 每日禱讀頁標題層級）
- 在 `site_checks.py` 的 `devotional` 檢查（以及 `visual_checks.py` 的 `devotional.html` 檢查）中，量測 `#reading h2`（當天標題，如「到主面前得安息」）與 `#reading h3`（段落標題「經文／默想／反思／禱告」）的計算後 `fontSize` 與 `fontFamily`：
  - 新增檢查：`devotional：當天標題（h2）字級大於段落標題（h3）字級，且當天標題使用明體`（斷言 `h2Px > h3Px` 且 `"serif" in h2Font`）。

### 3. 更新 `site_checks.py` 與 `visual_checks.py`（D. 收藏經節 `bookmarks`）
- 在 `site_checks.py` 新增 `"bookmarks"` 檢查群組（並加入 `__main__` 的預設 `groups` 集合，使 `check_all.py` 自動執行）：
  1. **靜態與鐵則檢查**：`chapter.html`、`index.html`、`app.js` 原始碼不含寫死經文，且使用 `localStorage` 鍵 `bible.bookmarks.v1`。
  2. **動態渲染與互動檢查**（可在暫存無頭 Chrome profile 或現有 probe 頁面／內嵌腳本執行）：
     - 在 `chapter.html?book=jhn&ch=3` 點選 `#v16`：操作列 `.chips` 出現收藏按鈕（`aria-pressed="false"`，文字含 `收藏這一節`）。
     - 點擊收藏按鈕：`aria-pressed` 變為 `"true"`，按鈕文字變為 `"✓ 已收藏"`，狀態列（`#reading-status`，`role="status"`）播報含 `"已收藏"`、`"約翰福音 3:16"`、`"本機儲存"`。
     - 檢查 `localStorage.getItem("bible.bookmarks.v1")`：解析後為陣列，元素只含座標欄位（`book`、`ch`、`v`、`at`），**絕不含任何經文文字**（無連續中文字句）。
     - 重新整理 `chapter.html?book=jhn&ch=3` 後再點 `#v16`：按鈕仍維持 `aria-pressed="true"` 與 `"✓ 已收藏"`。
     - 再次點擊取消收藏：`aria-pressed` 變回 `"false"`，狀態列播報含 `"已取消收藏"` 與 `"約翰福音 3:16"`。
     - 收藏 `jhn 3:16` 後打開 `index.html`：存在「我的收藏（1 節）」摺疊區（如 `#bookmarks-box`），展開後顯示出處 `約翰福音 3:16` 與由 `Bible.load` 動態載入的經文（與 `data/jhn.json` 第 3 章第 16 節一致），並提供「前往閱讀」（連往 `chapter.html?book=jhn&ch=3#v16`）、「做成經文卡片」（連往 `card.html?book=jhn&ch=3&v=16`）與「移除」按鈕；點擊「移除」後變成 0 節並顯示無收藏說明文字；底部導覽列仍維持 5 項。
     - **損壞資料容錯檢查**：當 `localStorage.setItem("bible.bookmarks.v1", "{bad json")` 時，載入 `index.html` 與 `chapter.html` 不發生 JS 錯誤、不壞頁，並顯示繁體中文提示。
     - **無水平溢出檢查**：在 320／375／768／1440px 下，`chapter.html`（展開 `.chips`）與 `index.html`（展開收藏區）皆無水平溢出（`scrollWidth <= clientWidth`）。
