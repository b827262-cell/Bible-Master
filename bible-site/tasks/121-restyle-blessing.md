---
pane: w2:p5
role: qwen
files:
  - bible-site/site/blessing.html
depends:
  - 120-restyle-card
timeout_min: 25
checks:
  - python3 bible-site/tests/site_checks.py blessing blessstyle blessart
  - python3 bible-site/tests/site_checks.py restyle --grep "restyle blessing\.html|改版素材"
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "blessing\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/blessing.html`。

請參照 `bible-site/design/sample-2026-11.html` 與 `bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`，將抽經文卡頁 `bible-site/site/blessing.html` 改版為 2026-11 新外觀，同時嚴格保留既有 37 張卡、`blessstyle`、`blessart` 與 `visual_checks` 的全部檢查契約：

1. **抽卡前畫面（`#cover`）：顯示金色飛鷹 A 卡背**：
   - 依交辦單：「A 是抽經文卡的卡背（抽卡頁抽卡前的畫面）；抽卡頁抽卡前的畫面（目前是愛心加『點選領受祝福』）改成顯示這張卡背；心形 GIF 素材待總PM驗收並給使用者看過之後才可以用，在那之前 `blessing.html` 的這一段先不要接 `heart-*.gif`」。
   - **重要鐵則**：`blessart_static` 與 `restyle_assets` 都嚴格規定 `blessing.html` 原始碼內**不可出現任何 `assets/*.jpg` 或 `eagle-A.jpg` 字串**！因此 `#cover`（或其內部卡背容器 `.cover-card.card-back-art`）的 `eagle-A.jpg` 背景圖**必須完全由 `style.css` 的 class（如 `#cover .card-back-art` 或 `#cover` 本身的 `background-image`）或 `Bible.CARD_ART.back` 提供**，使 `blessing_probe.html` 與 `home_probe.html` 量測 `#cover` 時 `cov.hasA === true` 且 `cov.blankBlock === false`，同時 `blessing.html` 原始碼零寫死圖檔名！
   - 保留 `<button type="button" class="pill solid" id="draw-btn">點選領受祝福</button>`（在封面上未抽卡前顯示，抽卡後 `#cover` 隱藏）。
2. **主題按鈕（`#theme-tabs`）與卡片樣式（`#blessing-card`，對齊 `blessstyle` 新檢查）**：
   - `#theme-tabs` 四顆主題按鈕在 320px、375px、1000px 下皆排成 `2×2` 等寬等高格線、文字不裁切、觸控高 ≥ 44px。
   - 選中的主題按鈕（`aria-pressed="true"`）背景為 `var(--river)`（文字顏色在淺深色下皆滿足對比 ≥ 4.5:1，例如深色模式下用 `#0a1412`／`var(--paper)`）、`::before` 有 `"✦ "`、無底線；未選中的主題按鈕為 `var(--surface)` 底色＋邊框、無 `"✦"`。
   - 實心主色（`backgroundColor === var(--river)`）的按鈕在卡片顯示時**剛好只有兩顆**：選中的主題按鈕與 `#again-btn`（「↻ 再抽一次」）；因此請確保其他按鈕（如 `#download-btn`、`#share-btn`）使用 `var(--surface)` 底色＋邊框（次要樣式）。
   - 所有動作按鈕（`#draw-btn`、`#again-btn`、`#download-btn`、`#share-btn`、`#art-download`）皆為膠囊形（`border-radius: 9999px`，圓角 ≥ 高度的一半）且觸控高 ≥ 44px。
   - `.card-verse` 使用明體 `var(--display)`、字級 `>= 20px`（`1.25rem`），且**移除舊版左側 3px 豎線**（`border-left: 0`，因為新版 `blessstyle` 檢查 `v.left <= 1 and v.px >= 20`！）。
   - 保留 `.card-sign::before { content: "—— "; }`、署名 `愛你的天父`、`#read-link`（「閱讀本章 →」與 `.card-ref` 同一列且在 `.card-actions` 之前）、`.card-art`（`border: 0`、無漸層背景）、`.card-edition`、`a#art-download`、隱藏的背景 `<canvas id="card-canvas">`（底色 `#fbf7ee`、合成主題圖或純文字）。
3. **微互動狀態回饋（`#share-msg`）**：
   - `#share-msg` 設 `class="status" role="status" aria-live="polite"`：抽卡載入中設 `data-state="busy"`（`抽卡中…`），抽卡完成、下載或複製連結成功設 `data-state="ok"`（如 `已抽出祝福卡`、`圖片已下載`、`已複製連結`），失敗時設 `data-state="fix"`。
4. **導覽列與背景音樂**：
   - 保留 `<nav id="nav"></nav>`（`Bible.nav("blessing.html")`）、`<script src="app.js"></script>`、`<script src="music.js"></script>`。
   - **重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 或 `mkdir /tmp/...` 的複合 bash 指令（會觸發 Qwen CLI 審批確認視窗而導致 pane 進入 blocked 狀態），只執行 front matter `checks:` 列出的單行 `python3` 指令即可。**
