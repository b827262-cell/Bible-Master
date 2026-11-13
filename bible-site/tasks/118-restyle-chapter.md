---
pane: w2:p5
role: qwen
files:
  - bible-site/site/chapter.html
depends:
  - 117-restyle-index
timeout_min: 20
checks:
  - python3 bible-site/tests/site_checks.py chapter
  - python3 bible-site/tests/site_checks.py restyle --grep "restyle chapter\.html"
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "chapter\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/chapter.html`。

請參照 `bible-site/design/sample-2026-11.html`（樣本二：閱讀頁）與 `bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`，將閱讀頁 `bible-site/site/chapter.html` 改版為 2026-11 新外觀，同時保留既有功能與檢查契約：

1. **版面與樣本二「閱讀頁」視覺**：
   - 使用 `.panel`／`.reader` 版面：
     - 章節標頭 `.chap`：超大章號 `<span class="num" id="chap-num"></span>`（`clamp(4.5rem, 3rem + 8vw, 7.5rem)`，`color: var(--river)`，`font-family: var(--display)`）、總節數 `<p class="eyebrow">共 <span id="chap-count">–</span> 節</p>`、明體主標題 `<h1 id="title"></h1>`（顯示「書名 第 N 章」，字級 ≥ 20px）。
     - 書卷切換 `#book-tabs`（4 卷標籤，觸控區 ≥ 44×44）。
     - 經文列表 `<ul id="verses" class="verse-list verses"></ul>`：每節 `<li id="vN">` 包含節號 `<span class="verse-num">`（主色 `var(--river)` 小字、`tabular-nums`）與經文 `<span class="verse-text">`（明體 `var(--display)`、行距 2；**注意**：所有 `.verse-text` 的左緣必須對齊在同一欄 `len(verseLefts) == 1`，包括合併節如路加福音 1:1–2 / 2:34–35！合併節仍須保留 `<span id="vEnd"></span>` 隱藏錨點，且不可讓該錨點擠歪 `.verse-text` 的左緣對齊）。
     - 點選經文節時可顯示樣本二的 `.chips` 快捷列（「做成經文卡片」連往 `card.html?book=KEY&ch=CH&v=V`；注意：依交辦單規定，「收藏這一節」屬新功能建議，請勿在正式頁加入收藏按鈕）。
     - 保留參照區 `#notes-area` > `#notes-list`、章節導航 `#chapter-links`（上一章、回到目錄、下一章，每項觸控高 ≥ 48px）、以及 `#v` 錨點自動捲動（`el.scrollIntoView({ behavior: "auto", block: "center" })`）。
2. **微互動狀態區與導覽列**：
   - 頁面內提供 `<p class="status" id="reading-status" role="status" aria-live="polite"></p>`，載入中設 `data-state="busy"`（`正在載入經文…`），載入完成後清空或設 `data-state="ok"`，載入失敗設 `data-state="fix"`。
   - 保留 `<nav id="nav"></nav>`（呼叫 `Bible.nav("chapter.html")`，對應底部導覽列「目錄」為目前頁），且 `chapter.html` **不載入** `music.js`（維持閱讀頁安靜）。
   - `<footer id="footer"></footer>` 静态 HTML 保持空白（由 JS 動態填入，避免觸發「頁尾寫死單一書卷名稱」檢查）。
   - **重要：請勿呼叫 `AskUserQuestion`（互動詢問會導致 pane 進入 blocked 狀態），遇到細節請直接依樣本與檢查腳本自行決定並完成。**
