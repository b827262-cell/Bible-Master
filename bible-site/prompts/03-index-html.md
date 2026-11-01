# 任務 3/5：目錄頁

請建立 `bible-site/site/index.html`（只這一個檔案）。引用已存在的 `style.css` 和 `app.js`（先讀 app.js，不要改它）。

行為：
- 標題「馬可福音（和合本）」，簡短說明。
- 用 `Bible.load()` 讀資料，顯示 16 章的格線，每格是連到 `chapter.html?ch=N` 的連結，並標示該章節數（例如「第 1 章・45 節」）。
- 一個搜尋框，送出後前往 `search.html?q=關鍵字`（用 GET 表單即可）。
- 頁首有導覽列（`Bible.nav('index')`）。

## 共同規則（務必遵守）
- 工作區是 Bible-Master，網站檔案放在 `bible-site/site/`。
- 經文只能用 fetch 從 `../data/mark.json` 讀取。格式：`{book, version, chapters:[{ch, verses:[{v, text}], notes:[...]}]}`。程式裡不准寫任何經文。
- 不載入任何外部資源（不用 CDN、外部字型、外部圖片），字型用系統字型。
- 介面文字全部用繁體中文，要能在手機（375px 寬不橫向捲動）和桌面使用。
- 這個任務只寫下面列出的檔案，不要動其他檔案，也不要一次寫更多檔案。
- 寫完後執行 `python3 bible-site/tools/check_all.py`，只回報最後一行總結和你改了哪些檔案。尚未建立的其他頁面造成的失敗是正常的，不用處理。
