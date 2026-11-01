# 任務 1/5：共用腳本與樣式

請建立 `bible-site/site/app.js` 和 `bible-site/site/style.css`（只這兩個檔案）。

app.js 要提供（掛在全域物件 `Bible` 上）：
- `Bible.load()`：用 fetch 讀 `../data/mark.json`，快取結果，回傳 Promise。
- `Bible.param(name)`：讀取網址的查詢參數。
- `Bible.ref(ch, v)`：回傳字串「馬可福音 {ch}:{v}」。
- `Bible.escape(s)`：HTML 跳脫，所有插入頁面的文字都要經過它或用 textContent。
- `Bible.nav(active)`：在 `<nav id="nav">` 內產生導覽列，連結：index.html（目錄）、search.html（搜尋）、card.html（經文卡片）。

style.css：手機優先、深淺色皆可讀（用 `prefers-color-scheme`）、字級舒適的閱讀版面（最大寬度約 40em 置中）、導覽列、章節格線、經文清單、搜尋結果、按鈕樣式；`body` 不可有橫向捲動。

## 共同規則（務必遵守）
- 工作區是 Bible-Master，網站檔案放在 `bible-site/site/`。
- 經文只能用 fetch 從 `../data/mark.json` 讀取。格式：`{book, version, chapters:[{ch, verses:[{v, text}], notes:[...]}]}`。程式裡不准寫任何經文。
- 不載入任何外部資源（不用 CDN、外部字型、外部圖片），字型用系統字型。
- 介面文字全部用繁體中文，要能在手機（375px 寬不橫向捲動）和桌面使用。
- 這個任務只寫下面列出的檔案，不要動其他檔案，也不要一次寫更多檔案。
- 寫完後執行 `python3 bible-site/tools/check_all.py`，只回報最後一行總結和你改了哪些檔案。尚未建立的其他頁面造成的失敗是正常的，不用處理。
