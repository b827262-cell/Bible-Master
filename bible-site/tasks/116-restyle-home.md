---
pane: w2:p5
role: qwen
files:
  - bible-site/site/home.html
depends:
  - 115-restyle-core-css-js
timeout_min: 25
checks:
  - python3 bible-site/tests/site_checks.py home
  - python3 bible-site/tests/site_checks.py restyle --grep "restyle home\.html"
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "home\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/home.html`。

請參照 `bible-site/design/sample-2026-11.html`、`bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`、`bible-site/logs/herdr-dispatch/change-20261113-hero.md`，將 `bible-site/site/home.html` 改版為 2026-11 新外觀，同時保留所有既有功能契約：

### 1. 主視覺（`.hero` / `.home-hero`）：照片與經文分離、經文與光同色
- **照片與經文分開放，經文不可蓋住照片裡的人物**：
  - 外層 `<section class="hero home-hero" aria-labelledby="hero-ref">`，寬螢幕左圖右文（`grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr)`），`≤820px` 上圖下文（`grid-template-columns: 1fr`）。
  - 左／上側照片區 `<div class="hero-pic"><img src="assets/jordan.jpg" alt="一位男子站在約但河水中，仰望從雲層灑下的光"></div>`（在 320／375／768／1440px 四種寬度下，照片高度皆 ≥ 200px，且 `.hero-pic img` 與 `.hero-body`／`.home-verse` 的矩形**完全不重疊**）。
  - 右／下側經文區 `<div class="hero-body home-card">`，背景帶從照片方向照過來的暖光 `radial-gradient(120% 90% at 0% 22%, rgba(253, 228, 170, .30), rgba(253, 228, 170, .08) 45%, transparent 70%)`。
  - 內含：
    - `<h1 class="sr-only">四福音</h1>`（或頂列 `.brand` 中的 `<h1>四福音 <small>和合本</small></h1>`，需確保 `text(d, "h1")` 包含 `"四福音"` 且明體 ≥ 20px）。
    - `<p class="eyebrow home-ref" id="hero-ref">今日經文</p>`（載入後填入 `Bible.ref(cfg.book, cfg.ch, verse) + "（和合本）"`，符合 `home_render` 對 `.home-ref` 的檢查）。
    - `<blockquote class="home-verse" id="hero-verse"></blockquote>`（載入後填入 `verse.text`，**原始碼不可寫死任何經文字句**；顏色必須是 `var(--sunlight)` 即 `#fdf2da` / `rgb(253, 242, 218)`，帶金色柔光 `text-shadow: 0 0 22px rgba(253, 222, 150, .55), 0 0 2px rgba(253, 242, 218, .35)`，使用 `var(--display)` 明體，與深色底對比 ≥ 4.5:1）。
    - `<div class="hero-actions home-ref-row">`：
      - `<a class="pill solid" id="read-link" href="chapter.html?book=luk&ch=4#v27">閱讀本章 →</a>`
      - `<button type="button" class="pill" id="music-btn" aria-pressed="false">♪ 播放音樂</button>`
      - 音樂狀態回饋元素 `<span class="status" id="music-status" role="status" aria-live="polite"></span>`（或共用狀態列）。

### 2. 便當格入口（`.bento`）與扇形紙卡 B、A、B
- 在 `<main class="wrap home">` 內放置 `<section class="bento" aria-label="入口">`：
  1. **四卷色塊入口（`.tile.book` × 4）**：
     - 對應 `mat`（太）、`mrk`（可）、`luk`（路）、`jhn`（約），連結指向 `index.html?book=<key>`，以 `--hue: var(--<key>)` 設定漸層背景，右上大字 `.glyph`（`aria-hidden="true"`），透過 `Bible.loadAll()` 動態填入章數與節數（如 `28 章 · 1071 節`），並確保有連結文字包含「進入四福音」（例如在第一個書卷方塊或快捷列保留 `<a class="pill" href="index.html">進入四福音 →</a>`，讓 `home_render` 檢查 `get("進入四福音") == "index.html"` 通過）。
  2. **每日禱讀入口（`a.tile.daily`）**：
     - `href="devotional.html"`，讀取 `../data/devotional.json` 顯示最新一篇（或今日）的日期數字 `.day`、年月、標題與經文出處（失敗時優雅顯示預設標題「每日禱讀」）。
  3. **抽經文卡入口（`a.tile.draw`）**：
     - `href="blessing.html"`，內含文字「抽一張經文卡，領受今天的祝福」（讓 `get("抽一張經文卡") == "blessing.html"` 通過）。
     - 內含 `<div class="fan" aria-hidden="true"><i></i><i></i><i></i></div>`：三張扇形卡片的 `background-image` 由共用 `style.css` 提供（**不可在 `home.html` 內寫死 `eagle-A.jpg` 或 `eagle-B.jpg` 檔名**），依序為 `eagle-B.jpg`、`eagle-A.jpg`、`eagle-B.jpg`（B、A、B，最上層是 B）。
  4. **搜尋四福音表單（`div.tile.find`）**：
     - `<form id="find-form" class="search-form" action="search.html" method="get" role="search">`
     - `<label for="find-q" class="eyebrow">搜尋四福音</label>`
     - `<input id="find-q" name="q" type="search" placeholder="輸入想找的字句，例如：重生" aria-describedby="find-status">`
     - `<button class="pill solid" id="find-go" type="submit">搜尋</button>`
     - `<p class="status" id="find-status" role="status" aria-live="polite"></p>`
     - **微互動處理**：當使用者空白送出時，攔截 `submit`（`e.preventDefault()`），設定 `input.setAttribute("aria-invalid", "true")`、`findStatus.dataset.state = "fix"`、`findStatus.textContent = "請先輸入要找的字句"` 並 `input.focus()`；當有輸入關鍵字時，設定按鈕 `aria-busy="true"` 與 `findStatus.dataset.state = "busy"`（`正在搜尋…`）並導向 `search.html?q=...`。

### 3. 保留既有 `home_static` 與 `home_render` 要求
- 頁面內所有 `<style>` 裡的 `animation` 與 `transition` 必須全部包在 `@media (prefers-reduced-motion: no-preference)` 內，且至少有 3 個 `@keyframes`。注意：`site_checks.py` 用 `animation\s*:\s*(?!none)` 掃描原始碼（含註解），因此若寫 `@media (prefers-reduced-motion: reduce)` 或註解，冒號後不可留空格（必須寫 `animation:none !important; transition:none !important;`，或直接交給 `style.css` 處理，不在 `home.html` 的 `@media (prefers-reduced-motion: no-preference)` 之外寫任何 `animation:`／`transition:`）。
- 保留 `<audio id="home-music" src="assets/home-music.mp3" loop preload="none"></audio>`、第一次觸碰播放（`GESTURES = ["click", "pointerup", "touchend", "keydown"]`）、`tryPlay()` 失敗重掛 `armFirstGesture()`、點擊 `#music-btn` 呼叫 `disarmFirstGesture()` 等完整邏輯。
- 呼叫 `Bible.nav("home.html")`（或 `Bible.nav(null)`），底部顯示 5 項膠囊導覽列且「首頁」為目前頁。
- **重要：請勿呼叫 `AskUserQuestion`（互動詢問會導致 pane 進入 blocked 狀態），遇到細節請直接依樣本與檢查腳本自行決定並完成。**
