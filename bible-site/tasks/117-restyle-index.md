---
pane: w2:p5
role: qwen
files:
  - bible-site/site/index.html
depends:
  - 116-restyle-home
timeout_min: 20
checks:
  - python3 bible-site/tests/site_checks.py index blessindex
  - python3 bible-site/tests/site_checks.py restyle --grep "restyle index\.html"
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "index\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/index.html`。

請參照 `bible-site/design/sample-2026-11.html` 與 `bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`，將目錄頁 `bible-site/site/index.html` 改版為 2026-11 新外觀，同時保留既有功能與檢查契約：

1. **版面與視覺（對齊樣本）**：
   - 使用 `.wrap`／`.panel` 容器、明體主標題 `<h1>四福音（和合本）</h1>`（≥ 20px）。
   - `<main>` 內保留指向 `home.html` 的「← 回首頁」連結、指向 `blessing.html` 的「抽一張經文卡，領受今天的祝福 →」連結、指向 `devotional.html` 的「每日禱讀 →」連結（可用 `.pill` 膠囊按鈕美化）。
   - 書卷切換 `#book-tabs`（4 卷膠囊標籤，目前卷有 `.active` 與 `aria-current="page"`，觸控區 ≥ 44×44）與章節卡片 `.chapter-grid` > `.chapter-card`（觸控區 ≥ 48px，最後一張顯示 `第 N 章・M 節`，文字對比 ≥ 4.5:1）。
2. **搜尋表單與微互動三種狀態**：
   - 搜尋表單 `<form method="get" action="search.html" class="search-form" id="search-form" role="search">`：
     - `<input type="search" name="q" id="search-q" placeholder="搜尋經文內容" aria-label="搜尋關鍵字" aria-describedby="search-status">`
     - `<select name="book" id="search-book" aria-label="搜尋範圍">`（5 個選項：全部四卷＋四卷，預設值為當前 `key`）
     - `<button type="submit" class="pill solid" id="search-btn">搜尋</button>`
     - `<p class="status" id="search-status" role="status" aria-live="polite"></p>`
   - **微互動行為**：
     - 當使用者空白送出時：`e.preventDefault()`，設 `searchQ.setAttribute("aria-invalid", "true")`、`searchStatus.setAttribute("data-state", "fix")`、`searchStatus.textContent = "請先輸入要找的字句"`，並 `searchQ.focus()`。
     - 當使用者輸入文字時：移除 `aria-invalid` 與 `data-state="fix"`。
     - 當非空白送出時：設 `searchBtn.setAttribute("aria-busy", "true")`、`searchStatus.setAttribute("data-state", "busy")`、`searchStatus.textContent = "搜尋中…"`，再導向 `search.html`。
3. **導覽列與背景音樂**：
   - 保留 `<nav id="nav"></nav>`、`<script src="app.js"></script>`、`<script src="music.js"></script>`（`music.js` 在 `app.js` 之後載入，頁面不自行放 `<audio>` 或 `#zone-music-btn`）。
   - 頁尾 `<footer>四福音 · 和合本</footer>` 不寫死單一書卷名稱。
   - **重要：請勿呼叫 `AskUserQuestion`（互動詢問會導致 pane 進入 blocked 狀態），遇到細節請直接依樣本與檢查腳本自行決定並完成。**
