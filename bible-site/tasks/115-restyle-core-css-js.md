---
pane: w2:p5
role: qwen
files:
  - bible-site/site/style.css
  - bible-site/site/app.js
timeout_min: 25
checks:
  - python3 bible-site/tests/site_checks.py restyle --grep "eagle-A\.jpg|改版素材|style\.css|app\.js"
  - python3 bible-site/tests/site_checks.py restyle --grep "restyle .*：(導覽列|目前頁|背景音樂按鈕|頁面底部留白)"
  - python3 bible-site/tests/site_checks.py zonemusic blessnav
  - python3 bible-site/tests/visual_checks.py p0 p1 --grep "style\.css 每條規則|底部導覽列|導覽列每項觸控區|導覽列目前頁|導覽列不遮住|捲到底時導覽列"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/style.css` 與 `bible-site/site/app.js`。

請參照 `bible-site/design/sample-2026-11.html`、`bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`、`bible-site/logs/herdr-dispatch/change-20261113-hero.md`，完成改版第一階段（共用樣式與共用腳本）：

### 1. 更新 `bible-site/site/app.js`
1. **五項底部膠囊導覽列 `Bible.nav(active)`**：
   - 導覽列固定五項（順序不可變）：
     `{ href: "home.html", label: "首頁" }`、
     `{ href: "index.html", label: "目錄" }`、
     `{ href: "devotional.html", label: "禱讀" }`、
     `{ href: "blessing.html", label: "抽卡" }`、
     `{ href: "search.html", label: "搜尋" }`。
   - **每個前台頁面都必須恰有一項標成目前頁**：請在 `Bible.nav(active)` 內將傳入的 `active` 正規化映射：
     - `null`、`""`、`"home.html"` → `"home.html"`
     - `"index.html"`、`"chapter.html"` → `"index.html"`
     - `"devotional.html"` → `"devotional.html"`
     - `"blessing.html"`、`"card.html"` → `"blessing.html"`
     - `"search.html"` → `"search.html"`
   - 對目前頁的 `<a>` 同時設定 `a.className = "active"` 與 `a.setAttribute("aria-current", "page")`；並在 `#nav` 元素設定 `navEl.classList.add("dock")` 與 `navEl.setAttribute("aria-label", "主要導覽")`。
2. **共用飛鷹卡面設定與微互動輔助函式**：
   - 在 `window.Bible` 提供共用常數 `CARD_ART: { back: "assets/eagle-A.jpg", face: "assets/eagle-B.jpg" }`（讓頁面不必寫死 `eagle-A.jpg`／`eagle-B.jpg` 檔名）。
   - 在 `window.Bible` 提供微互動輔助函式（例如 `Bible.busy(btn, label)`、`Bible.settle(btn, label)`、`Bible.say(statusEl, state, text)`、`Bible.toast(text)`），方便後續各頁面統一實現 `busy`／`ok`／`fix` 三種狀態與 `aria-busy="true"`。
   - 保留既有 `BOOKS`、`load`、`loadAll`、`bookKey`、`bookName`、`verseLabel`、`ref`、`param`、`escape`、`chapterOf`、`bookTabs`、`fail`（其中 `fail` 也可同步設定 `role="status"` 與 `data-state="fix"`）。

### 2. 更新 `bible-site/site/style.css`
1. **完整沿用 `sample-2026-11.html` 的 `:root`、深色模式與共用變數**：
   - 淺色 `:root`：`--paper: #f3f6f2`、`--surface: #ffffff`、`--ink: #10231f`、`--muted: #586a64`、`--river: #0e6b5b`、`--river-soft: #dcefe9`、`--lamp: #c98a1b`、`--sunlight: #fdf2da`、`--line: rgba(16, 35, 31, .12)`、`--glass: rgba(255, 255, 255, .72)`、`--shadow: ...`、`--mat: #c98a1b`、`--mrk: #d9583b`、`--luk: #0e6b5b`、`--jhn: #3d55c4`、`--display: "Noto Serif TC", "Noto Serif CJK TC", "Source Han Serif TC", "Songti TC", "PMingLiU", serif`、`--body: system-ui, -apple-system, "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", sans-serif`、`--r-lg: 28px`、`--r-md: 18px`。
   - 深色 `@media (prefers-color-scheme: dark)` 與 `:root[data-theme="dark"]`：`--paper: #0a1412`、`--surface: #121f1c`、`--ink: #e9f1ee`、`--muted: #94a8a1`、`--river: #55d3b7`、`--river-soft: #16302a`、`--lamp: #f0bf5c`、`--line: rgba(233, 241, 238, .14)`、`--glass: rgba(18, 31, 28, .72)`、`--mat: #f0bf5c`、`--mrk: #ff8a6b`、`--luk: #55d3b7`、`--jhn: #8fa2ff`。
   - 同時保留舊變數別名對映（如 `--bg: var(--paper)`、`--fg: var(--ink)`、`--card-bg: var(--surface)`、`--border: var(--line)`、`--accent: var(--river)`、`--accent-fg: var(--paper)`、`--accent-soft: var(--river-soft)`、`--focus: var(--lamp)`），確保所有深淺色文字對比皆 ≥ 4.5:1（注意：深色模式下若按鈕背景為 `--river: #55d3b7` 或 `--accent`，文字顏色應為深色 `#0a1412`／`var(--paper)` 以維持對比 ≥ 4.5:1）。
   - 將飛鷹圖背景定義在 `style.css`（如 `.fan i { background-image: url("assets/eagle-B.jpg"); }`、`.fan i:nth-child(2) { background-image: url("assets/eagle-A.jpg"); }`，以及 `.card-back-art` / `#cover .cover-card` 使用 `url("assets/eagle-A.jpg")`、`.card-face-art` 使用 `url("assets/eagle-B.jpg")`）。
2. **底部浮動膠囊導覽列（`#nav` / `.dock`）與背景音樂按鈕位置**：
   - `#nav, .dock` 設為 `position: fixed; left: 50%; bottom: max(14px, env(safe-area-inset-bottom)); transform: translateX(-50%); z-index: 10; display: flex; gap: 4px; padding: 6px; border-radius: 999px; border: 1px solid var(--line); background: var(--glass); -webkit-backdrop-filter: blur(18px) saturate(1.6); backdrop-filter: blur(18px) saturate(1.6); box-shadow: var(--shadow); max-width: calc(100vw - 16px);`
   - `#nav .nav-list` 為 `list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: nowrap; gap: 4px;`，`#nav a, .dock a` 在一般寬度 `min-width: 56px; min-height: 48px; padding: 0 14px; display: grid; place-items: center; border-radius: 999px; text-decoration: none; font-size: .92rem; white-space: nowrap; color: var(--ink); border: 0;`，在 `@media (max-width: 380px)` 下 `min-width: 48px; min-height: 44px; padding: 0 9px; font-size: .86rem;`（確保 320px 寬時 5 個項目全部 ≥ 44×44 且總寬度 ≤ 304px 不水平溢出！）。
   - 目前頁 `#nav a.active, #nav a[aria-current="page"], .dock a.active, .dock a[aria-current="page"]`：`background: var(--ink); color: var(--paper); font-weight: 700; border: 0; text-decoration: none;`。
   - `body` 設定 `padding-bottom: 130px;`（或 `.container` / `.wrap` `padding-bottom: 130px;`），確保捲到底部時導覽列絕不遮住頁面最後一段內容。
   - `#zone-music-btn` 改為 `bottom: 86px; right: 16px;`（避開底部導覽列，確保在 320/375/768/1440px 下兩者矩形完全不重疊）。
3. **共用新外觀元件、微互動三態與無障礙焦點／動態關閉**：
   - 納入樣本的 `.wrap`、`.top`、`.brand`、`.pill`（含 `.pill.solid`）、`.hero`、`.hero-pic`、`.hero-body`、`.bento`、`.tile`、`.book`、`.daily`、`.draw`、`.fan`、`.find`、`.panel`、`.reader`、`.chap`、`.verses`、`.dev`、`.pray`、`.status[data-state="busy|ok|fix"]`（含 `::before` 轉圈、`✓`、`!` 圖示）、`[aria-invalid="true"]` 虛線粗框（`border: 2px dashed var(--ink)`）、`.toast`。
   - 確保 `h1, h2, h3` 使用 `font-family: var(--display)` 且 `h1` 在 375px 與 1440px 皆 `>= 20px`。
   - 確保所有可聚焦元素（`a[href], button, input, select, [tabindex]`）在 `:focus` 與 `:focus-visible` 皆有 `outline: 3px solid var(--lamp); outline-offset: 2px;`（實線且 ≥ 2px）。
   - 確保所有動畫都放在 `@media (prefers-reduced-motion: no-preference)` 內，且另有 `@media (prefers-reduced-motion: reduce)` 將 `animation: none !important; transition: none !important; scroll-behavior: auto;` 明確關閉，讓新舊兩個 reduced-motion 檢查都能通過。
   - 注意：`visual_checks.py p0` 會檢查 `style.css` 頂層規則數與瀏覽器 `sheet.cssRules.length` 完全相等，因此請勿使用瀏覽器會整條丟棄的不合法 CSS 選擇器。
