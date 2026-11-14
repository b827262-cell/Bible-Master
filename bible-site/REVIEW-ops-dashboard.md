# 禱讀狀態看板與派工工具驗收

**狀態：PASS**

驗收日期：2026-11-14。使用者「execute」授權依NEXT-TARGETS執行；已完成139～143的功能、工具修正及獨立測試。本輪未commit、push、部署、重啟既有長駐後台或改動每日發布排程。

本機後台新增唯讀禱讀狀態看板與GET `/api/devotional-status`：正式站／本機篇數及日期分列，顯示台灣時區觀測時間、timer下一次與截止日、最後執行結果，並正確處理部分來源不可用、整體失敗及逾時。正常截止不當成故障，未來日期不會被說成已發布。

後端只讀固定正式HTTPS來源與固定systemd unit。HTTP有3秒timeout與2MiB讀取上限，不跟隨重導；systemctl有2秒timeout、輸出上限及固定屬性。原token／Origin與靜態白名單保留，新Python模組無法下載。沒有新增資料庫或發布寫入操作。

Herdr工具已對齊tab2後端、tab3前端、tab4 QA、tab5助理；opaque pane ID大小寫保留。失效、unknown、blocked、agent_not_found拒絕自動派發；working轉unknown不會因checks或檔案變動而被判成功。

進度工具改查四福音JSON與3776節、目前11份必要前台檔案；缺檔、壞型別／JSON、非物件經文元素或章節／節數不符皆失敗。`--no-checks`明示沿用舊FAILS結果，不執行check_all；自動區塊外的手寫紀錄完整保留。既有正式PROGRESS沒有為此次測試重寫。

## 修改與交付

| 負責 | 檔案與結果 |
| --- | --- |
| tab2 | `tools/herdr_team.py`、`admin/server.py`、新增`admin/devotional_status.py` |
| tab3 | `admin/index.html`、`admin/admin.js`、`admin/admin.css` |
| tab5 | `tools/pm_status.py`；經PM回饋修正後交付。其自身測試工具被拒絕，未宣稱自行通過 |
| PM | 獨立驗收、`tests/ops_dashboard_checks.py`、操作說明、任務／驗收文件；pm_status僅清除行尾空白並補最後換行，另澄清CSS註解 |
| tab4 | 本輪長時間未交付測試檔，後續明確顯示模型請求TIMEOUT重試；PM撤回寫入責任並接手，tab4的待回覆唯讀覆核不作為本報告通過證據 |

## 實際驗證

| 檢查 | 結果與覆蓋 |
| --- | --- |
| `python3 -B bible-site/tests/ops_dashboard_checks.py` | PASS，22項unittest，含多組參數案例；全程離線mock，臨時目錄寫入 |
| PM看板Chrome驗收 | PASS，29/29：來源分列、動態截止日、320/375/768/1440無溢出、partial failure、空資料、無systemd、失敗／正常截止、XSS、HTTP／JSON失敗、12秒逾時、鎖重複操作、恢復、僅GET、可存取回饋、無JS例外；另含亮／暗兩模式×正常／警告／錯誤／截止四情境，共8組實際合成背景的文字對比皆≥4.5 |
| PM真實資料整合 | PASS，7/7：隔離admin API＋Chrome；實際正式站9篇至11/14、本機8篇至11/13、實際timer下次11/15且截止11/25；靜態隱私、POST權杖及畫面一致性 |
| 既有週封面Chrome回歸 | PASS，21/21；含草稿、失敗保留、上傳、鎖定、整週持久化、其餘六日不變 |
| 進度工具獨立案例 | PASS，6/6：正常、缺卷、壞JSON、null經文、少一節、缺前台檔；手寫紀錄保留 |
| `python3 -B bible-site/tools/check_all.py` | PASS，3/3，隔離副本 |
| `python3 -B bible-site/tests/visual_checks.py` | PASS，隔離副本 |
| `python3 -B bible-site/tests/service_checks.py homeadmin admin` | PASS，隔離副本 |
| `python3 -B bible-site/tests/deploy_checks.py` | PASS，隔離副本；僅檢查，沒有部署 |
| `git diff --check` | PASS |

完整回歸副本包含`data/devotional.json`與根目錄`.verify/`。回歸後僅調整新看板範圍的CSS語意色與註解，已另行完成上述29項瀏覽器及7項真實資料整合複驗；其餘四份admin執行程式與回歸快照SHA256一致。真實資料、FAILS／TEST-REPORT／PROGRESS、原先已修改的`tools/dispatch/roles.yml`與開始前雜湊一致，沒有覆寫他人變更。

測試效力另以三次隔離突變證明：把沿用快取狀態改成永遠失敗、把截止日改成固定11/25、讓working轉unknown仍可通過；對應獨立測試三次均確實判失敗。突變只在臨時副本，正式程式沒有保留。

## 證據與使用

- 完整紀錄與雜湊：`../output/ops-dashboard-20261114/`
- 真實資料畫面：[375px](screenshots-ops/live-dashboard-375.png)、[1440px](screenshots-ops/live-dashboard-1440.png)
- fixture不同篇數／動態截止日畫面：[375px](screenshots-ops/fixture-dashboard-375.png)、[1440px](screenshots-ops/fixture-dashboard-1440.png)
- [操作說明](admin/DEVOTIONAL-STATUS.md)

現有長駐後台沒有重啟，以免打斷使用中的操作；下次啟動／重啟會載入新版。看板本身不會變更已核准內容、已公開內容或11/25截止設定。
