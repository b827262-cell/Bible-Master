# 每日禱讀後台新增、修訂、審核與上架驗收

狀態：**PASS**。驗收日期：2026-11-16（Asia/Taipei）。

新版入口：<http://127.0.0.1:8093/#devotional-editor>。內容編輯、設定與上架均集中於「每日禱讀內容管理」；操作說明見 [DEVOTIONAL-EDITOR.md](admin/DEVOTIONAL-EDITOR.md)。

## 完成內容

- 新增／修改日期、主題、經文出處、來源、默想、反思及禱告，預覽四福音唯讀經文；跨章與合併節對照原資料。
- 獨立資料庫草稿及樂觀版本檢查，保存修訂不改原文章或已核准公開版本；日期與並行衝突拒絕覆蓋。來源／神學人工雙重確認，核准以單一交易套用，保留審核軌跡；範圍變更撤銷不適用的媒體核准。
- 可調整啟用、開始／截止日期及每日台灣時間；私人備份、原子寫入與失敗還原。排程與文章日期分開說明，超出上架期間的核准文章會提示先調整設定。
- 手動上架使用固定既有服務；檢查設定版本、日期、執行中工作、新 InvocationID 與實際啟動時間，避免將舊成功或條件略過誤報成功。逾時明示服務可能仍在執行。
- 新 API 的 GET/POST 均驗證 Host、同來源、後台標頭及權杖；限制 JSON 大小，私有 Python/SQL/權杖檔案不提供下載。失敗保留輸入，輸出使用純文字避免 XSS。

## 驗收結果

| 檢查 | 結果 |
| --- | --- |
| `python3 -B bible-site/tests/devotional_editor_checks.py` | **32/32 PASS**，唯一命名隔離 PostgreSQL + 真實 HTTP；並行日期、原文保留、衝突後明確重核、真正 CLI export 排除未來／未核准資料 |
| 後端承辦獨立資料庫／HTTP | **49/49 + 15/15 PASS**，含媒體失效、範例／範本／範圍外目標拒絕、核准軌跡、原子失敗與權限 |
| `python3 -B bible-site/tests/devotional_operations_checks.py` | **23/23 PASS**，模擬服務／暫存設定；跨月、版本、原子寫入、每階段還原及還原失敗、重複／略過／失敗／逾時 |
| `python3 -B bible-site/tests/ops_dashboard_checks.py` | **25/25 PASS**，既有唯讀看板／派工回歸 |
| Chromium 前端契約與互動測試 | **139/139 PASS**，亮暗色、375/1440、對比、dirty、409、XSS、失敗、逾時、期間外核准訊息及既有功能 |
| 實際 8093 Chromium 唯讀驗收 | **9/9 PASS**，31 篇文章與實際設定、今日文章開啟、唯讀經文、兩種寬度與無 JS 例外；全程 GET |
| `python3 bible-site/tools/check_all.py` | **3/3 PASS** |
| `python3 bible-site/tests/visual_checks.py` | **PASS** |
| `python3 bible-site/tests/deploy_checks.py` | **PASS** |
| `python3 -B bible-site/tests/service_checks.py homeadmin admin` | **PASS**，最後版本再次以隔離目錄執行 |
| JS 語法、Python 語法、使用者服務 unit verify、`git diff --check` | **PASS** |

整體檢查在完整隔離副本執行，包含 devotional.json 與 .verify/，不覆寫原報告。PostgreSQL 測試只建立及刪除本次唯一命名的資料庫；正式上架與真實排程設定寫入使用隔離模擬，沒有以驗收名義啟動正式發布服務。

## 實際啟用與資料保全

- 已正式安裝新增的 `005_admin_editor.sql`。安裝前拒絕名稱碰撞，未重建或覆寫既有核心表／觸發器／匯出 view。
- 安裝前後原資料一致：**380** 篇，entries hash `d1cc902d19ccfd7faf86ee25cf8c5dfb`；ranges hash `25fe2d64f7da334e718cfb83187bd20d`；audit **760** 筆。新增草稿表為空；未代替使用者編輯或核准正式文章。
- 已啟用 `bible-site-admin-editor.service`，127.0.0.1:8093、獨立私人 token，啟用使用者服務自動啟動。既有 8091 adapter、8092 後台及舊 token 保留，未中斷使用中的舊服務。
- 真實 HTTP 可列出 2026-11-16 至 2026-12-16 共 **31** 篇已核准文章。實際排程維持 **2026-11-16 至 2026-12-16 含當日，每日 06:00 台灣時間**；下一次為 2026-11-17 06:00。設定與發布服務指紋於驗收前後一致。
- 本次沒有 commit、push 或部署公開網站，沒有執行正式手動上架。Cloudflare 最終更新仍以實際正式站公開資料查驗，服務成功不等同網站已完成部署。

完整證據與亮暗色截圖在 [output/devotional-admin-editor-20261116](../output/devotional-admin-editor-20261116/)。`source-sha256.json` 對應驗收原始碼，`schema-install.json` 記錄資料指紋，`database-http-results.json`／`fixture-browser-results.json`／`live-browser-results.json` 與回歸記錄保留分項結果；不含權杖或未來文章正文。

未通過項目：無。
