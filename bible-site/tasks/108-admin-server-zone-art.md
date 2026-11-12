---
role: e500
files: [bible-site/admin/server.py]
depends: [105-build-zone-art-assets, 107-site-blessing-single-art]
checks:
  - python3 -m py_compile bible-site/admin/server.py
  - python3 bible-site/tests/service_checks.py zoneadmin blessartadmin homeadmin admin
---
所有操作都在 E500 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、home.json、chapter.html、不下載或引入外部資源。只能更改 front matter 允許的檔案。

只改 admin/server.py。驗收以 service_checks.py zoneadmin、blessartadmin、homeadmin、admin 為準。
zone-music.json 必填 music 舊規則不變；新增選填 zones object，鍵只允許 index/search/card/blessing，值同 music：assets/ 檔名、不可含 ..、副檔名 mp3、檔案存在。POST 合法後 atomic_write_json 保留 zones，不存在時沿用 music；GET 回 config/default/music 並加 zones array [{id,title}] 四區中文名稱（目錄、搜尋、經文卡片、抽經文卡）。reset 清除 zones 回預設，保留所有 assets。

blessing-art.json 保留 work/peace/rest/faith，新增選填 cards object，key 必須是 data/blessing.json 已存在的 37 個 ID，value 嚴格和主題 entry 一樣恰有 image/alt/edition 並套相同白名單、長度、檔案存在驗證。GET /api/blessing-art 原有 themes / refs / config / images 不變，額外回 cards 列表共 37 筆，每筆 id/theme/book/ch/v，不可有經文正文或 message，供 UI 依主題顯示。
POST 全量物件，含 cards 可省略；clear 一張由前端發一份刪 key 的完整設定，原子寫檔，不做新的 DELETE 端點。
所有寫入端點沿用 check_write_auth；64KB 限制、400/403/413、POST 輸入先完整驗證後寫、路徑不得逃逸。home.json 6 欄驗證零修改，不新增寫 blessing.json 的路由，四福音 JSON 不碰。
