# 後台一週封面編輯驗收

**狀態：PASS**

驗收日期：2026-11-14（Asia/Taipei）。主實作：tab4 DeepSeek 4.1 Flash；驗收：Codex PM。

已完成七天逐日編輯，整週草稿一次儲存。可設定主題、書卷章節、圖片、替代文字、光色與裁切位置；經文預覽來自既有 JSON。開關變更亦留在草稿，儲存沿用 GET／POST `/api/home-week`。

光色前後端皆驗證相對亮度至少 0.72、對深底色 `#06140f` 對比至少 7；裁切接受 0–100 整數百分比。既有省略 focus 的資料維持省略，畫面使用前台有效預設 35% 50%。圖片沿用既有格式及 5 MiB 上限，對比例、尺寸及檔案大小提供建議。

修改範圍：`admin/server.py`、`admin/index.html`、`admin/admin.js`；API 回歸補於 `tests/service_checks.py`。另修正 `tests/visual_checks.py`、`tests/visual_probe.html` 的日期設定，從實際已上架禱讀選取最近日期量測，保留 h2 大於 h3 且使用明體的斷言。本次量測日期為 2026-11-13，沒有修改真實禱讀內容。

驗收使用臨時副本及隨機本機埠；完整回歸副本包含 `data/devotional.json` 與 `.verify/`。瀏覽器以獨立 Chrome profile 測試，故障注入只作用於測試頁面。

| 檢查 | 結果 |
| --- | --- |
| `node --check bible-site/admin/admin.js` | PASS |
| Python AST 解析 `admin/server.py` | PASS |
| 後台瀏覽器操作 | PASS，21/21 |
| `python3 bible-site/tools/check_all.py` | PASS，3/3 |
| `python3 bible-site/tests/visual_checks.py` | PASS |
| `python3 bible-site/tests/deploy_checks.py` | PASS |
| `python3 bible-site/tests/service_checks.py homeadmin admin` | PASS |

瀏覽器操作涵蓋：七張編輯卡、星期一預設展開、缺省裁切、320／375／768／1440 無水平溢出、開關與欄位只改草稿、離頁提示、取消重載、偏暗光色錯誤、儲存失敗保留草稿、重載失敗保留草稿並禁止儲存、成功重載清除草稿、經文原文一致、實際上傳與尺寸提示、光色與構圖預覽、儲存鎖定及防重複送出、單日更新保留其餘六天、重新整理後持久化、無 JavaScript 例外。

截圖已人工檢視桌面預覽與手機版排版；以下各圖為 1000px 高的畫面截圖：

- [星期一 375px](screenshots-weekly-editor/admin-mon-375.png)、[1440px](screenshots-weekly-editor/admin-mon-1440.png)
- [星期日 375px](screenshots-weekly-editor/admin-sun-375.png)、[1440px](screenshots-weekly-editor/admin-sun-1440.png)
- [欄位錯誤 375px](screenshots-weekly-editor/admin-error-375.png)
- [未儲存草稿 375px](screenshots-weekly-editor/admin-dirty-375.png)

瀏覽器逐項結果與隔離執行紀錄位於本機 `/tmp/weekly-editor-acceptance/final2/`、`/tmp/weekly-editor-acceptance/regression-final.json`，屬暫存證據。

使用限制：整週儲存採既有最後寫入結果，未新增多人同時編輯的版本衝突處理；上傳後未選用的圖片保留，不自動刪除。此次未更改真實 `data/*.json`，未 commit、push 或部署；工作樹原有變更及素材保留。
