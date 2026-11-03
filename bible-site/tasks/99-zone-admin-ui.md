---
role: fe
files: [bible-site/admin/index.html, bible-site/admin/admin.js]
depends: [98-zone-admin-api]
checks:
  - python3 bible-site/tests/service_checks.py zoneadmin --grep "zoneadmin：(後台|admin\.js)"
  - python3 bible-site/tests/service_checks.py homeadmin
  - python3 bible-site/tests/service_checks.py admin
---
後台（`bible-site/admin/`）在「主頁設定」下面新增「前台音樂」區塊，讓人上傳／選擇／試聽／儲存／還原「前台四區（目錄、搜尋、經文卡片、抽經文卡）共用的背景音樂」。只改 `index.html` 與 `admin.js`；後端 API 已完成（讀 `admin/server.py` 的 `/api/zone-music`、`/api/zone-music/reset`、`/api/upload`、`/api/token`）。**照抄現有「主頁設定」音樂那一段的做法**（`home-music-file`／`home-music-select`／`home-music-preview`、`uploadFile(kind, file)`、`assetUrl()`、`updateMusicPreview`、`saveHomeSettings`、token 取得與 `X-Bible-Admin`／`X-Bible-Token` 標頭、狀態文字）。介面全部繁體中文，不載入外部資源，不要簡體字，不要動「主頁設定」的任何行為與 id。

## index.html
加一個 `<section id="zone-music-settings">`，標題「前台音樂」，一句說明「目錄、搜尋、經文卡片、抽經文卡四個頁面共用這一首；首頁音樂在上面的『主頁設定』另外設定」。需要這些 id（驗收腳本會檢查，完全一樣）：
`zone-music-file`（`<input type="file" accept=".mp3,audio/mpeg">`，附 `<label>`）、`zone-music-select`（`<select>`，列出 assets 的 mp3）、`zone-music-preview`（`<audio controls preload="none">`）、`zone-music-save`（儲存）、`zone-music-reset`（還原預設）、`zone-music-status`（`role="status"` 的狀態文字）。
提醒文字要含「發佈」：「儲存後要執行『發佈』，公開網站才會換歌。」另寫一行：「上傳新素材後，請在 ASSETS-LICENSE.md 補一行來源與授權。」

## admin.js
- 頁面載入時（`GET /api/zone-music`）填入下拉選單並選中目前設定，預覽 `<audio>` 的 src 用 `assetUrl()`（走同源 `/site-assets/`）。
- 選檔上傳：用既有的 `uploadFile("music", file)`（上限 8 MB，與主頁相同的錯誤訊息），成功後把新檔加進下拉並選中、更新預覽、狀態寫「已上傳，尚未儲存」。
- 儲存：`POST /api/zone-music`，內容 `{"music": 下拉選中的值}`，帶 token 標頭；成功顯示「已儲存。記得執行發佈。」，失敗顯示後端回的錯誤。
- 還原預設：`POST /api/zone-music/reset`，成功後下拉回到 `assets/home-music.mp3`。
- 不要用 `innerHTML` 插入來自伺服器的字串（用 `textContent`／`createElement`），不要寫死經文。

結果以驗收腳本為準，不要改測試。
