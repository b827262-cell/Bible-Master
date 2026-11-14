# 143 獨立QA（tab4）

> PM收尾調整：測試檔寫入已移交PM，tab4不再寫檔，改為唯讀覆核139～142並回報具體缺陷。下列為原測試範圍，仍由PM獨立測試覆蓋。原因：tab4長時間未交付測試檔，避免與PM並行寫入同檔。

你負責139～142的獨立驗證。現在即可讀任務建立測試，不等待實作完成；允許測試先紅。只准新增／修改 `bible-site/tests/ops_dashboard_checks.py`。其他檔案只讀，不跑真實check_all，不改報告/資料/DB/systemd，不commit/push/部署，不向真實agent發測試指令。

測試用unittest與標準庫；臨時目錄與mock必須隔離所有副作用，拒絕真實網路/SSH/systemctl/Herdr派工。測試不得與tab2/tab5的實作自述互相抄結論，斷言依139/140/141/142規格。可用現有資料JSON作唯讀fixture。

至少包含：
1. herdr_team角色mapping、含大寫opaqueID、live不存在拒送、unknown/blocked不可自動派發、不把working→unknown判成功。測試mock inventory與send，不能觸碰真實pane。
2. pm_status正常四卷0、缺檔/壞JSON/節數不符/必要前台檔缺失非0、--no-checks不跑check_all、手寫進度保留。全部用臨時root。
3. devotional_status正式站與local分開、日期/空資料/壞JSON/大小界線、publicfailure但schedule可用、無systemd、service失敗/never、截止日從calendar動態讀、UTC與台灣日期交界；安全摘要不含草稿正文或任意命令錯誤。契約與141一致。
4. API整合：隔離server隨機port，mock外部資料來源，GET回200含契約，Python模組靜態路徑仍404，無修改資料。若原函式簽名未定，先寫清楚預期並回報PM協調，不要求實作者為了過測試改出與需求無關的私有介面。

請勿在此腳本中新增Chrome/CDP複雜相依；PM另負責375/1440真實瀏覽器與週封面回歸。完成只跑本檔，回報實際通過/失敗與證據；實作未完成時直接列失敗、待PM通知後重跑，不反覆浪費模型額度。
