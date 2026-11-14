# 禱讀狀態看板驗收證據

2026-11-14，PM獨立驗收。未commit/push/部署或修改正式資料與排程。

- regression.json：check_all 3/3、visual、homeadmin/admin、deploy全部exit0，使用隔離副本及.verify。
- ui-browser-results.json：29/29，fixture對照來源、動態截止日、四尺寸、錯誤/逾時/重試/文字注入、亮暗四情境文字對比。
- weekly-browser-results.json：21/21，既有週封面草稿與寫入回歸，僅寫臨時副本。
- live-browser-results.json：7/7，隔離後台讀取真實正式站與systemd；API及UI一致、靜態模組保護、POST權杖。
- api-observed.json：當次真實唯讀API摘要（正式9篇、本機8篇、截止11/25），為觀測快照，不代替之後即時狀態。
- progress-results.json：6個額外獨立案例，完整與錯誤情境。
- mutation-results.json：3次臨時突變都被測試抓到。
- ops-dashboard-checks.log：repo獨立unittest 22項通過，含參數案例；既有pm_status未使用with的檔案讀寫會出現ResourceWarning，並非測試失敗。
- regression-source-hashes.json：回歸副本的五份admin來源雜湊；除其後看板CSS對比修正外，四份admin執行程式與交付一致；最終版本見final-source-hashes.json。
- browser.mjs、fixture.json、run-ui.py：PM瀏覽器fixture驗收程式。從專案根目錄可執行 python3 -B output/ops-dashboard-20261114/run-ui.py /tmp/ops-dashboard-ui-recheck；需要現有Chrome及Node22。

獨立離線測試：python3 -B bible-site/tests/ops_dashboard_checks.py。截圖與最終報告見bible-site/REVIEW-ops-dashboard.md。
