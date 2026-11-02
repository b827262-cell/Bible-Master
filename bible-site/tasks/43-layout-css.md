---
role: e500
files: [bible-site/site/style.css]
depends: [40-focus-css]
checks:
  - python3 bible-site/tests/visual_checks.py
  - python3 bible-site/tests/site_checks.py
---
只改 bible-site/site/style.css（視覺優化 P1／P2：觸控區域、目前位置、字級、經文對齊、留白）。規劃書是 bible-site/FRONTEND-VISUAL-OPTIMIZATION-PLAN.md，先讀它與目前的 style.css，再做下面這份修改清單。只用 CSS，不改 HTML／JS，不改顏色變數的名稱，不刪檔案最後的 :focus-visible 規則。

1. 導覽連結 `.nav-list a`：加 `min-height: 44px; display: flex; align-items: center;`。另外新增 `#chapter-links a { min-height: 48px; }`（逐章頁的上一章／下一章／回目錄）。
2. 書卷標籤 `.book-tabs a`：加 `min-height: 44px; display: flex; align-items: center;`。
3. 目前頁面與目前書卷不能只靠顏色：`.nav-list a.active` 與 `.book-tabs a.active` 都加 `font-weight: 700; text-decoration: underline; text-underline-offset: 0.2em;`。
4. 按鈕 `button, .btn, input[type="submit"]` 與搜尋框 `input[type="text"], input[type="search"]` 都加 `min-height: 44px;`。新增一條 `select { font: inherit; min-height: 44px; padding: 0.4em 0.6em; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--fg); }`。
5. 字級：`h1` 改為 `font-size: 1.375rem; line-height: 1.35; font-weight: 700;`，`h2` 改為 `font-size: 1.25rem; line-height: 1.4; font-weight: 600;`。新增 `@media (min-width: 48em) { h1 { font-size: 1.625rem; } .verse-text { font-size: 1.0625rem; } .container { padding-left: 2rem; padding-right: 2rem; } }`。
6. 經文對齊：`.verse-num` 改成固定寬度欄，`flex: 0 0 3rem; width: 3rem; min-width: 0; white-space: nowrap; font-size: 0.8125rem;`（其餘屬性保留）。合併節「34-35」也必須在這一欄內，讓每一節經文的左緣對齊。
7. 章節卡片 `.chapter-card` 加 `min-height: 48px;`。

驗收（腳本自動跑）：`python3 bible-site/tests/visual_checks.py` 全部通過、`python3 bible-site/tests/site_checks.py` 全部通過。你可以自己先跑 `python3 bible-site/tests/visual_checks.py p1` 看哪一項還不通過。改完只回報改了哪些規則。
