# 142 禱讀唯讀看板（tab3）

使用者要求execute NEXT-TARGETS。只准修改 `bible-site/admin/index.html`、`bible-site/admin/admin.js`、`bible-site/admin/admin.css`。先讀141任務JSON契約，依此以fixture開發，不等待後端完成；不修改server/data/DB/systemd/Git，不commit/push/部署。保留全部既有週封面編輯與其他後台功能。

新增獨立卡片section `#devotional-status`，標題「每日禱讀上架狀態」。自GET `/api/devotional-status` 讀資料，載入一次與手動「重新整理」；不要每15秒對正式站與systemd造成重複查詢。載入中鎖本卡刷新、避免重複/舊請求覆蓋，fetch使用AbortController timeout<=12秒；失敗要清楚標示資料未更新，不能殘留綠色成功狀態冒充即時結果。

顯示：正式站公開篇數與最新日期、本機匯出篇數與最新日期（明確分開）、觀測時間、台灣時區、timer啟用/active狀態、下一次、截止日、最後執行起訖/結果；null顯示未知或尚無資料而不是0/成功。局部失敗保留其他有效來源。release_state=cutoff顯示「已依設定截止」，不當故障。未到期排程只說已排程，不說未來已發布。不得硬編11/25/篇數/下一次時間。

所有來源文字用textContent，避免XSS；警告/錯誤用中文、安全不曝rawsecret。role=status/aria-live、按鈕可存取名稱、鍵盤可用，375/1440無橫向溢出。不可新增編輯、核准、發布、延長截止日等操作。

在/tmp副本測fixture正常、public unavailable但local/schedule有效、schedule缺失、lastfailed、cutoff、整體HTTP錯誤/timeout與惡意文字；node --check admin.js。只能對隔離UI測試，不覆寫真實資料/報告。QA會另做獨立瀏覽器測試。完成回報改動/檢查/限制後待命。
