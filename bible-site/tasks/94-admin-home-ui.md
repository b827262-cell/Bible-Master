---
role: a16
files: [bible-site/admin/index.html, bible-site/admin/admin.js, bible-site/admin/admin.css]
depends: [93-admin-home-api]
checks:
  - python3 bible-site/tests/service_checks.py admin
  - python3 bible-site/tests/service_checks.py homeadmin --grep "admin.js|index.html|主頁設定"
---
後台（`bible-site/admin/`）新增「主頁設定」區塊。只改 `index.html`、`admin.js`、`admin.css`；後端 API 已由上一個任務完成（讀 `server.py` 的 `/api/token`、`/api/home`、`/api/home/reset`、`/api/upload` 就知道格式）。介面全部繁體中文，不載入任何外部資源，不要簡體字，不要寫死經文。

## index.html
在既有版面裡加一個 `<section id="home-settings">`，標題「主頁設定」，需要這些元素（id 必須完全一樣，驗收腳本會檢查）：
- `home-book`（`<select>`：馬太福音 mat／馬可福音 mrk／路加福音 luk／約翰福音 jhn）、`home-ch`（`<select>` 章）、`home-v`（`<select>` 節），各有 `<label>`；
- `home-verse-preview`：顯示所選那一節的經文（本節經文只能由 JS 讀 `../data/<book>.json` 取得，絕不寫在 HTML 或 JS 裡）；
- `home-image-file`（`<input type="file" accept="image/jpeg,image/png,image/webp">`）、`home-image-select`（`<select>`：目前 `assets/` 可選的圖片）、`home-image-preview`（`<img>`，要有 `alt`）、`home-alt`（`<input type="text" maxlength="120">`，圖片說明）；
- `home-music-file`（`<input type="file" accept="audio/mpeg,.mp3">`）、`home-music-select`（`<select>`）、`home-music-preview`（`<audio controls>`）；
- 按鈕 `home-save`「儲存」、`home-reset`「還原預設」、`home-open`「開啟主頁預覽」；
- `home-status`：`<p role="status" aria-live="polite">`，顯示結果訊息。
- 區塊上方一行說明：「這裡的設定只存在本機；改完請執行發佈，才會更新到線上網站。」

## admin.js
- 頁面載入時：`fetch("/api/token")` 取得 token（只放在記憶體變數，不存 localStorage）、`fetch("/api/home")` 取得目前設定與清單，填入各欄位。
- 書卷／章／節三個下拉：章與節的選項、經文預覽都從同源的 `fetch("/api/book/<book>")` 取得（後台伺服器會回該卷的 JSON，格式 `{chapters:[{ch, verses:[{v,text}]}]}`；不要跨埠去讀前台）。經文預覽顯示 `book ch:v` 與該節文字。
- 選了檔案就立刻 `POST /api/upload?kind=image|music&name=<檔名>`（body 直接放 File），成功後把回傳的 `path` 加進下拉並選取、更新預覽；失敗顯示伺服器回的繁中錯誤。前端先檢查大小（圖 5 MB、音樂 8 MB），上傳圖片後如果寬度超過 1600px，在狀態列加一句「圖片寬度超過 1600px，建議先縮小再上傳」（只提示）。
- 「儲存」：`POST /api/home`，JSON 為 `{book, ch, v, image, alt, music}`（`ch`、`v` 要轉成數字）；成功顯示「已儲存到本機。要更新線上網站，請記得執行發佈。」。「還原預設」先 `confirm("確定要還原成預設的主頁設定嗎？")`，再 `POST /api/home/reset` 並重新填入欄位。「開啟主頁預覽」用 `window.open` 開前台根目錄（沿用 `admin.js` 現有用 `location.hostname` 組前台網址的做法，不可寫死 `127.0.0.1:8090`）。
- 所有 POST 要帶標頭：`X-Bible-Admin: 1`、`X-Bible-Token: <token>`（寫入端點）。沿用檔案裡現有的 fetch 輔助函式與錯誤處理風格。

## admin.css
沿用現有變數與卡片樣式；表單控制項高度至少 44px；深色模式不能壞；`home-image-preview` 最大寬度 100%、最大高度 200px。

不要啟動或停止任何服務。驗收以腳本為準。
