---
pane: w2:p5
role: qwen
files:
  - bible-site/site/search.html
depends:
  - 118-restyle-chapter
timeout_min: 20
checks:
  - python3 bible-site/tests/site_checks.py search
  - python3 bible-site/tests/site_checks.py restyle --grep "restyle search\.html"
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "search\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/search.html`。

請參照 `bible-site/design/sample-2026-11.html` 與 `bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`，將搜尋頁 `bible-site/site/search.html` 改版為 2026-11 新外觀與微互動三種狀態，同時保留既有搜尋功能與檢查契約：

1. **版面與表單結構**：
   - 使用 `.wrap`／`.panel` 版面，明體主標題 `<h1>經文搜尋</h1>`（≥ 20px）。
   - 搜尋表單 `<form method="get" action="search.html" class="search-form" id="search-form" role="search">`：
     - `<input type="search" name="q" id="search-q" placeholder="輸入想找的字句，例如：重生" aria-label="搜尋關鍵字" aria-describedby="result-info">`
     - `<select name="book" id="search-book" aria-label="搜尋範圍"></select>`
     - `<button type="submit" class="pill solid" id="search-btn">搜尋</button>`
   - 狀態回饋列 `<p class="status" id="result-info" role="status" aria-live="polite"></p>` 與結果列表 `<ul class="search-results" id="results"></ul>`。
2. **微互動三種狀態（`busy`／`ok`／`fix`）**：
   - 表單支援直接在頁面上攔截 `submit`（`e.preventDefault()`，並用 `history.replaceState` 更新網址 `?q=...&book=...`）以及頁面初次帶 `?q=...` 載入：
   - **待修正（空白關鍵字）**：當 `q.trim() === ""`（無論是初次不帶 `q` 之後按送出，或清空後按送出），設定 `input.setAttribute("aria-invalid", "true")`、`infoEl.setAttribute("data-state", "fix")`、`infoEl.textContent = "請先輸入要找的字句"`、`resultsEl.innerHTML = ""`（初次載入若網址完全沒帶 `?q=`，可先顯示一般提示或當使用者按送出時觸發 `fix`；若網址帶 `?q=` 空值或送出空白表單則必設 `aria-invalid="true"` 與 `data-state="fix"`）。
   - **處理中（`busy`）**：開始搜尋時，移除 `aria-invalid`，設定 `searchBtn.setAttribute("aria-busy", "true")`、`infoEl.setAttribute("data-state", "busy")`、`infoEl.textContent = "搜尋中…"`。
   - **已完成（`ok`）**：找到符合經文時，移除 `searchBtn` 的 `aria-busy`，設定 `infoEl.setAttribute("data-state", "ok")`、`infoEl.textContent = "找到 " + matches.length + " 節（共 " + matches.length + " 筆）"`，並渲染 `#results li`（每筆含 `.search-ref` 連結與 `<mark>` 標示，對比 ≥ 4.5:1）。
   - **待修正（查無結果 `fix`）**：`matches.length === 0` 時，移除 `searchBtn` 的 `aria-busy`，設定 `input.setAttribute("aria-invalid", "true")`、`infoEl.setAttribute("data-state", "fix")`、`infoEl.textContent = "找不到「" + q + "」，請換個字句再試一次"`。
   - 當使用者修改輸入框內容（`input` 事件）時，自動清除 `aria-invalid`。
3. **導覽列與背景音樂**：
   - 保留 `<nav id="nav"></nav>`（`Bible.nav("search.html")`）、`<script src="app.js"></script>`、`<script src="music.js"></script>`。
   - **重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 或 `mkdir /tmp/...` 的複合 bash 指令（會觸發 Qwen CLI 審批確認視窗而導致 pane 進入 blocked 狀態），只執行 front matter `checks:` 列出的單行 `python3` 指令即可。**
