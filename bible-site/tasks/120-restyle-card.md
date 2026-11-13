---
pane: w2:p5
role: qwen
files:
  - bible-site/site/card.html
depends:
  - 119-restyle-search
timeout_min: 20
checks:
  - python3 bible-site/tests/site_checks.py card
  - python3 bible-site/tests/site_checks.py restyle --grep "restyle card\.html|改版素材"
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "card\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/card.html`。

請參照 `bible-site/design/sample-2026-11.html` 與 `bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`，將經文卡片頁 `bible-site/site/card.html` 改版為 2026-11 新外觀，同時保留既有功能與檢查契約：

1. **版面、金色飛鷹 B 卡面裝飾與畫布契約**：
   - 使用 `.wrap`／`.panel` 版面，明體主標題 `<h1>經文卡片</h1>`（≥ 20px）。
   - 三個選單 `#book-select`、`#ch-select`、`#v-select` 皆有 `<label>`、觸控高度 ≥ 44px、文字對比 ≥ 4.5:1。
   - **金色飛鷹 B（水彩風）卡面裝飾**：
     - 依交辦單規定：「B 用在『經文卡片』頁（`card.html`）的卡面裝飾與入口方塊外側那張；圖檔路徑由設定檔或固定檔名提供，頁面不寫死在多處」。
     - **重要**：請透過 `Bible.CARD_ART.face`（在 `app.js` 定義）或 `style.css` 的 `.card-face-art` class 取得 `eagle-B` 圖片，**切勿在 `card.html` 原始碼內直接寫死 `eagle-B.jpg` 字串**（否則會違反 `restyle_assets` 的「前台頁面不重複寫死檔名」檢查！）。
     - 可在卡片預覽區顯示 `.card-face-art` 裝飾，或將 `Bible.CARD_ART.face` 載入後繪入 `#card-canvas` 並搭配高對比文字底板，務必確保 `#card-canvas` 寬度 `canvas.width >= 600`、在 320/375/768/1440px 下顯示寬度 `0 < shownW <= width` 不水平溢出，且 `canvas.setAttribute("data-ref", refText)` 始終等於 `Bible.ref(book, ch, verse) + "（和合本）"`（例如 `card.html?book=luk&ch=1&v=1` 的 `data-ref` 為 `路加福音 1:1-2（和合本）`，且圖片載入完成前後都會立即設好 `data-ref` 與畫出文字，不因非同步讀圖而延遲 `data-ref`）。
2. **微互動三種狀態（`role="status"`）**：
   - 加入狀態回饋列 `<p class="status" id="card-status" role="status" aria-live="polite"></p>` 與膠囊下載按鈕 `<button type="button" class="pill solid" id="download-btn">下載圖片</button>`（觸控高度 ≥ 44px）。
   - 載入書卷或切換章節時設 `data-state="busy"`（`正在產生經文卡片…`），繪製完成後設 `data-state="ok"`（`已產生：路加福音 1:1-2`），點擊 `#download-btn` 下載完成後設 `data-state="ok"`（`圖片已下載`），發生錯誤時設 `data-state="fix"`（`載入失敗，請稍後再試`）。
3. **導覽列與背景音樂**：
   - 保留 `<nav id="nav"></nav>`（`Bible.nav("card.html")`，對應底部導覽列「抽卡」為目前頁）、`<script src="app.js"></script>`、`<script src="music.js"></script>`。
   - **重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 或 `mkdir /tmp/...` 的複合 bash 指令（會觸發 Qwen CLI 審批確認視窗而導致 pane 進入 blocked 狀態），只執行 front matter `checks:` 列出的單行 `python3` 指令即可。**
