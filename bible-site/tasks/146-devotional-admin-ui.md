# 146 每日禱讀管理UI（tab3主辦）

完整讀145 API契約，實作使用者要求的後台「設定＋新增/修改＋審核＋上架」。只准修改 `bible-site/admin/index.html`、`bible-site/admin/admin.css`，新增 `bible-site/admin/devotional_editor.js`。不改admin.js/server/資料/DB/排程，不commit/push。先用fixture開發，不等145完成；PM做獨立瀏覽器驗收。

在現有唯讀禱讀卡片之後新增section `#devotional-editor`，獨立JS載入並註冊DOMContentLoaded。所有私有新API需自行GET /api/token，token僅存在記憶體，GET/POST都帶X-Bible-Admin:1及X-Bible-Token。不能因取token失敗而無限重試或影響其他後台功能。

API參照145；147設定契約：`get_settings→{version,enabled,start_date,end_date,time,timezone:"Asia/Taipei",today,busy,service:{active,result},warning:null|string}`；save_settings回同格式，publish→`{ok:true,message,outcome:"service_completed",settings:...}`。錯誤為{error}與HTTP狀態碼；publish服務完成不等於Cloudflare網站已更新。

介面須有：
1. 每日上架設定：啟用開關、開始日期、截止日期（含當日）、每天HH:MM（台灣時區），「儲存設定」。載入實際值（目前12/16但不可寫死）。暫停僅停止之後自動排程，與手動上架分別說明。排程執行期間與文章日期不同，標示清楚。
2. 內容列表：日期範圍from/through、重新讀取，已核准與待審草稿分列；日期、標題、出處、審核狀態與「編輯」。不可把單憑日期判為已發布；真正公開狀態看原卡片。
3. 新增/修改表單：日期、主題、經文出處、來源網址（可空採本站）、默想、反思、禱告；原文經文預覽唯讀，按「預覽經文」呼叫preview，textContent渲染，不憑模型或手填經文。保留原多段/cross-chapter/merged verse，不限縮只一節。
4. 「儲存草稿」：新增draft_id=null/version0，編輯原entry帶base_version，繼續編輯draft帶version；成功更新draft metadata、失敗保留全部輸入；409明確提示重新讀取，不自動覆蓋。草稿保存不等於核准或公開。
5. 審核區：審核者姓名、兩個未預勾的確認「已核對來源與經文」「已審閱默想、反思與禱告」，按「確認審核並排入上架」；僅已save且無dirty draft可按。修改任何欄位後清除確認、禁止批准未儲存內容。成功後以entry新version為基準，之後再改另存新修訂；未來日期只說排入逐日上架。
6. 「立即上架已核准內容」：呼叫publish、送confirm:true與最新settings.version；spinner/鎖重複操作，HTTPtimeout至少100秒；逾時不能說失敗已取消，提示服務可能仍在執行，重新讀取狀態。只在服務idle與今天位於設定開始/截止內可按（server仍重驗），暫停自動timer不必阻擋合法手動上架。完成說「上架服務完成，正式站更新請重新整理確認」，可觸發舊卡片的refresh.click()查真實正式站；不宣稱未來或未部署的版本已公開。

多份表單草稿各自追蹤dirty：刷新或切換文章/新增前，確有未儲存資料才confirm；beforeunload保留原週封面handler並加入此區。讀列表/操作結果不得默默覆寫正在修改的設定或另一篇內容。載入/寫入/審核/上架中鎖相關欄位避免in-flight輸入丟失；generation防舊請求覆蓋。不要把token或內容存localStorage。

樣式只限本section，亮/暗小字對比>=4.5、375/1440無橫向溢出、表單有label與role=status/aria-live，textarea保留段落、錯誤繁中且用textContent。不要將SQL/Git/SSH內部細節放進一般編輯流程。保留週封面、音樂、收藏圖與舊看板。

在/tmp fixture測正常新增與修訂、save/approve/publish/settings各種失敗保留資料、stale409、XSS、busy/dirty、source原文、兩種寬度；不觸碰真實write API。完成node --check新JS並回報。
