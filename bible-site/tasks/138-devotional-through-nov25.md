# 每日禱讀逐日公開至 2026-11-25（含當日）

使用者已決定「逐日到11/25」。沿用 Asia/Taipei 每日06:00，11/25為最後公開日，11/26起不得自動發布；其餘365篇保持原狀。tab4主實作，PM驗收與安裝本機user systemd設定。

只准新增以下檔案（若存在先回報，不覆蓋）：
- `bible-site/devotional/systemd/release-through-20261125.timer.conf`
- `bible-site/devotional/systemd/release-through-20261125.service.conf`
- `bible-site/devotional/systemd/RELEASE-through-20261125.md`

其他工作樹、資料庫及正式站唯讀；不要commit/push/部署，不自行安裝設定或觸發服務。不要碰既有host.conf、主unit或365篇資料。

實作：
1. timer drop-in：先空白 `OnCalendar=` 清掉無限每日排程，再設 `OnCalendar=2026-11-14..25 06:00:00 Asia/Taipei`，保留既有Persistent=true行為。
2. service drop-in：新增ExecCondition，在Asia/Taipei的實際日期超過2026-11-25時回1、截止日含當天回0。Python3標準庫datetime/zoneinfo即可；必須在既有ExecStart（git fetch/checkout及publish）前執行，防止Persistent補跑到11/26時公開越界日期。不重寫原ExecStart、不變更SSH主機。不要提供測試用環境變數繞過正式日期判斷。
3. 具體測試：systemd-analyze calendar，證明11/25 06:00仍有執行、11/26無下一次；對ExecCondition實際程式碼以隔離方式模擬台灣11/25與11/26（含UTC日期不同的界線），驗證0/1。驗證systemd語法，保留完整測試紀錄於/tmp。
4. 說明文件寫清安裝位置為對應user unit的 `release-through-20261125.conf` drop-in，PM負責安全新增（不覆蓋既有檔案）、daemon-reload、重啟timer、確認下一次及最後一次。不要執行正式服務測試，因其會推送。
5. 截止後未來內容仍留在DB，已公開內容不刪除。11/25預期累計20篇（11/06～11/25，含原15篇及365計畫前5篇），不可把20篇聲稱365篇已全公開。

完成後只回報檔案、測試結果與證據位置，然後待命。
