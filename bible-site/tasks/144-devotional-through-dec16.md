# 144 每日禱讀延長至2026-12-16（tab2實作，PM安裝驗收）

使用者交辦「請上架每日禱讀1個月到12/16日」。沿用已決定的逐日公開，台灣時間每天06:00，2026-12-16含當日，12/17起停止自動公開；不可一次公開未來內容。

只准修改 `bible-site/admin/devotional_status.py`，以及新增：
- `bible-site/devotional/systemd/release-through-20261216.timer.conf`
- `bible-site/devotional/systemd/release-through-20261216.service.conf`
- `bible-site/devotional/systemd/RELEASE-through-20261216.md`

不改其他檔案/資料/DB/已核准內容/正式站，不commit/push，不自行安裝systemd、不觸發服務。PM負責安裝、獨立測試及報告。舊11/25模板及安裝檔須保留。

1. timer新drop-in（名稱release-through-20261216.conf，排序在舊1125之後）清除舊OnCalendar，新增兩條有限規則：`2026-11-16..30 06:00:00 Asia/Taipei` 與 `2026-12-01..16 06:00:00 Asia/Taipei`。保留Persistent。
2. service新drop-in先清空舊ExecCondition（目前唯一條件是舊11/25日期護欄），再加台灣實際日期<=2026-12-16才回0的Python3條件；12/17起回1跳過。原ExecStart及host.conf不動，不新增能繞過日期的環境變數。若不重設舊條件，兩條條件AND會錯在11/25截止，務必避免。
3. 狀態看板目前_parse_cutoff遇到多個有限規則不同截止日回None。改為：每條規則都能完整辨識為有限日期時，取所有規則截止日的max（因此11/30+12/16=>12/16）；只要有無限/未知/逗號日期列表/不合法日期，仍回None。保持原單月、UTC時區與對外JSON契約，不把12/16寫死在程式。
4. 在/tmp mock測試：兩月合併截止12/16、順序互換、有限+無限仍None、12/16台灣23:59:59前不expired、12/17 00:00expired；service同時刻0/1；systemd-analyze calendar證明11/16～12/16共31次且最後12/16、12/17無排程。所有repo檢查避免pycache寫入（ast/ -B）。
5. 說明含安全新增的兩個user drop-in位置，明確保留舊檔靠排序覆蓋，PM daemon-reload/restart timer後要驗證有效ExecCondition只有新日期條件。不要觸發正式publish服務測試。

完成交付檔案、檢查/證據與限制，然後待命。PM會獨立核對內容截至12/16可匯出41篇，包含原15篇及365計畫前26篇。
