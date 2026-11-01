# 任務 5/5：經文卡片頁

請建立 `bible-site/site/card.html`（只這一個檔案）。引用已存在的 `style.css` 和 `app.js`（先讀 app.js，不要改它）。

行為：
- 兩個下拉選單：章（1–16）與節（依所選章的節數更新），預設第 1 章第 1 節；也支援網址 `card.html?ch=N&v=M`。
- 用 `Bible.load()` 讀資料，預覽卡片：經文 + 出處「馬可福音 章:節（和合本）」。
- 「下載圖片」按鈕：用 `<canvas>` 把卡片畫成 PNG（自動換行、中文字型用系統字型、不使用外部資源），以 `<a download>` 下載，檔名如 `mark-1-1.png`。
- 經文只能來自 JSON，不可寫死。

## 共同規則（務必遵守）
- 工作區是 Bible-Master，網站檔案放在 `bible-site/site/`。
- 經文只能用 fetch 從 `../data/mark.json` 讀取。格式：`{book, version, chapters:[{ch, verses:[{v, text}], notes:[...]}]}`。程式裡不准寫任何經文。
- 不載入任何外部資源（不用 CDN、外部字型、外部圖片），字型用系統字型。
- 介面文字全部用繁體中文，要能在手機（375px 寬不橫向捲動）和桌面使用。
- 這個任務只寫下面列出的檔案，不要動其他檔案，也不要一次寫更多檔案。
- 寫完後執行 `python3 bible-site/tools/check_all.py`，只回報最後一行總結和你改了哪些檔案。尚未建立的其他頁面造成的失敗是正常的，不用處理。
