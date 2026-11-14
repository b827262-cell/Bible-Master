---
pane: w2:p5
role: deepseek
files:
  - bible-site/admin/server.py
  - bible-site/admin/index.html
  - bible-site/admin/admin.css
  - bible-site/admin/admin.js
timeout_min: 25
checks:
  - node --check bible-site/admin/admin.js
  - python3 -c 'import ast; ast.parse(open("bible-site/admin/server.py",encoding="utf-8").read())'
---
# 後台逐日封面編輯：主實作

使用者已核准：七天草稿一次儲存、包含光色及裁切、沿用圖片上傳規格並提供封面建議提示。只准修改上列四個檔案；不可修改 data、測試、報告或其他人變更，不 commit/push/部署。Codex PM 另寫測試並隔離驗收。

1. 把既有 #home-week-days 唯讀列表改成七張 details 編輯卡，星期一預設展開，其餘收合；星期固定1–7，不可刪除或排序。卡片 summary 顯示星期、主題及未儲存標記。
2. 每天欄位：theme(1–40)、book/ch/v 連動下拉、經文唯讀預覽(沿用 /api/book/ 讀 JSON)、image 素材下拉及上傳、alt(1–120)、light 六位色碼及色票、focus x/y 0–100 整數滑桿。focus 原本省略時顯示 35/50（依前台有效預設值修正），未動過滑桿則保存省略。
3. 草稿只放記憶體，連 enabled 開關都不立即 POST。新增 #home-week-save「儲存整週」；沿用 GET/POST /api/home-week，不增新端點、不改 payload {enabled,days}。儲存成功後用伺服器回值更新乾淨基準；失敗保留所有輸入並播報中文錯誤。載入/上傳/儲存中禁重複操作；無完整七天資料或載入失敗時禁止儲存，避免舊草稿覆蓋。
4. #home-week-reload 有草稿時先 confirm 放棄；beforeunload 有草稿或上傳中需提示。重新載入失敗保留草稿。細部編輯不重建整個表單以免丟焦點，連動載入需防止舊請求覆蓋新選擇。
5. 上傳沿用 /api/upload?kind=image，預覽 /site-assets/。只接受能解碼圖片及現有格式/5MiB 上限；選圖或上傳後預覽構圖與光色，若不是約16:9、低於1600×900或大於600KiB顯示建議但不拒絕。週封面上傳不可沿用「大於1600建議縮小」的舊訊息；其他上傳流程維持原行為。上傳成功僅改草稿，其餘六天保留，不刪除未使用檔。
6. 伺服器 validate_home_week_config 補強 light：相對亮度>=0.72，對 #06140f 對比>=7（sRGB標準公式）；focus 兩數皆0–100整數%，超出回400。UI也驗證並提供中文提示及 aria-invalid/aria-describedby。既有登入/Token/Origin/64KiB/原子寫入維持，任何一筆錯誤整週不寫入；home.json 六欄位不動。
7. 預覽包含圖片 object-fit:cover/object-position 與深底上所選經文光色。樣式沿用後台，鍵盤可用、輸入至少44px、320/375/768/1440無水平溢出。不可手打經文、不可將 verse text 寫到設定。

完成只回報改動檔案、檢查結果、限制。不要在真實工作樹跑 check_all 或會覆寫報告的檢查，PM會在隔離副本跑。不要清理未追蹤檔。
