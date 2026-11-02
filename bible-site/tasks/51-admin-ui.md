---
role: e500
files: [bible-site/admin/admin.js, bible-site/admin/index.html]
depends: [50-admin-server]
checks:
  - node --check bible-site/admin/admin.js
  - python3 bible-site/tests/service_checks.py admin
---
只改 bible-site/admin/admin.js 與 bible-site/admin/index.html（管理後台頁面）。後端 server.py 已改成：POST 動作必須帶標頭 X-Bible-Admin: 1，build_data 動作已刪除。請先讀 server.py、admin.js、index.html，再修改：

1. admin.js 的 POST（目前是 fetch(endpoint, { method: "POST" })）改成 fetch(endpoint, { method: "POST", headers: { "X-Bible-Admin": "1" } })。收到 409 時在終端區顯示「已有動作執行中，請稍候」。
2. 前台網址不可寫死 127.0.0.1：
   - admin.js 第 76 行附近的「閱讀第 1 章」連結，改用 `${location.protocol}//${location.hostname}:8090/site/chapter.html?book=${b.key}&ch=1`。
   - index.html 裡所有 "http://127.0.0.1:8090/site/index.html" 與頁尾的「前台：http://127.0.0.1:8090/…｜後台：http://127.0.0.1:8091/」：連結的 href 先改成 "#"，加上 id（例如 id="frontend-link"），再在 admin.js 載入時用 location.hostname 組出實際網址設定 href 與顯示文字。整個 admin.js 和 index.html 都不准再出現字串 127.0.0.1:8090。
3. index.html 裡「visual_checks.py 47 項」改成「visual_checks.py」（不寫項數）。
4. 刪掉 index.html 裡觸發 build_data 的按鈕（以及 admin.js 裡對應的處理，若有）。
5. 兩個檔案都不准有簡體字，介面一律繁體中文；不載入外部資源。

驗收（腳本自動跑）：node --check 通過，且 python3 bible-site/tests/service_checks.py admin 全部通過。改完只回報改了哪些地方。
