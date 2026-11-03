---
role: fe
files: [bible-site/admin/index.html, bible-site/admin/admin.js]
depends: [99-zone-admin-ui, 103-art-admin-api]
checks:
  - python3 bible-site/tests/service_checks.py blessartadmin --grep "blessartadmin：(後台|admin\.js)"
  - python3 bible-site/tests/service_checks.py zoneadmin
  - python3 bible-site/tests/service_checks.py homeadmin
  - python3 bible-site/tests/service_checks.py admin
---
後台（`bible-site/admin/`）在「前台音樂」下面新增「收藏卡圖片」區塊：「抽經文卡」四個主題（work 天父賜福你的工作、peace 天父賜你平安、rest 天父給你安息、faith 在神凡事都能）各有一張預先生成的收藏卡圖，**每月換一次新圖**。只改 `index.html` 與 `admin.js`；後端 API 已完成（讀 `admin/server.py` 的 `/api/blessing-art`、`/api/blessing-art/reset`、`/api/upload`、`/api/token`）。**照抄現有「主頁設定」圖片那一段與「前台音樂」那一段的做法**（`uploadFile("image", file)`、`assetUrl()`、token 取得與 `X-Bible-Admin`／`X-Bible-Token` 標頭、狀態文字）。介面全部繁體中文，不載入外部資源，不要簡體字，不要寫死經文，**不要有任何寫 `blessing.json` 的請求**，不要動既有區塊的 id 與行為。

## index.html
加一個 `<section id="blessing-art-settings">`，標題「收藏卡圖片」，說明文字：「每個主題一張圖，該主題所有經文卡共用；經典小卡片：直式 5:7、1000×1400 JPG、3 MB 以內為主（上限 5 MB；先用 tools/art_convert.py 轉檔），圖內不要放文字。每月更換：上傳新圖 → 改版次 → 儲存 → 執行『發佈』。沒有圖的主題維持純文字卡。」另寫：「上傳新素材後，請在 ASSETS-LICENSE.md 補一行（工具、生成日期）。」
四個主題（順序 work、peace、rest、faith），每個主題一格（`<fieldset>` 或 `<div>`），格內有：主題標題與張數、該主題所有卡的出處清單（用 `<details>` 收合）、以及這些 id（驗收腳本會檢查，**完全一樣**，`<t>` 是主題 id）：
`art-<t>-file`（`<input type="file" accept="image/jpeg,image/png,image/webp">`，附 `<label>`）、`art-<t>-alt`（`<input type="text" maxlength="120">`）、`art-<t>-edition`（`<input type="text" maxlength="20">`，placeholder 例如「2026 年 11 月版」）、`art-<t>-preview`（`<img>`，沒有圖時隱藏）、`art-<t>-save`（儲存）、`art-<t>-clear`（清除）。
整個區塊另有一個 `art-status`（`role="status"`）。總共 26 個 id（含 `blessing-art-settings`）。四格用靜態 HTML 寫好，不要用 JS 產生 id。

## admin.js
- 載入時 `GET /api/blessing-art`：把各主題張數與出處（`book` 代號用現有的書名對照，格式如「馬太福音 25:21」；沒有對照表就自己寫四卷名稱的小物件）填進清單；把現行設定填進 alt／版次／預覽。
- 選檔後用 `uploadFile("image", file)` 上傳（上限 5 MB，沿用主題頁的錯誤訊息），成功後預覽換成新圖（`assetUrl()` 走 `/site-assets/`）並記下新路徑，狀態寫「已上傳，尚未儲存」；alt 若空白，預設填「<主題標題>收藏卡」；版次若空白，預設填當月「YYYY 年 M 月版」。
- 該主題「儲存」：把**整份**目前設定（四個主題各自的最新值，沒有圖的主題不要放進去）`POST /api/blessing-art`，帶 token 標頭；成功顯示「已儲存。記得執行發佈。」，失敗顯示後端回的錯誤。
- 該主題「清除」：從整份設定拿掉這個主題後 `POST /api/blessing-art`，預覽隱藏。
- 不要用 `innerHTML` 插入來自伺服器的字串（用 `textContent`／`createElement`）。

結果以驗收腳本為準，不要改測試。
