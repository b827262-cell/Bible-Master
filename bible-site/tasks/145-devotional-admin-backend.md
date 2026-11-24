# 145 每日禱讀內容管理後端（tab2主辦）

使用者要求：「以上設定在後台區，讓我可以新增、修訂/修改內容和上架」。完整實作，不只做唯讀卡片。沿用既有365篇與12/16截止設定，不替人自動核准或改既有文章。

只准修改 `bible-site/admin/server.py`，新增 `bible-site/admin/devotional_editor.py`、`bible-site/devotional/005_admin_editor.sql`。不安裝schema/排程、不碰真實DB寫入、不啟動正式發布、不commit/push。PM在隔離DB驗收後負責正式schema安裝。保留144已完成的跨月修正與所有既有功能。

## 資料設計與完整性

新增獨立`admin_devotional_drafts`資料表存草稿（UUID文字id、整數version、entry_id可空、base_version、payload JSONB、status DRAFT/APPLIED、updated_at、reviewer/applied_at）。不要把儲存草稿直接寫進entries：既有已核准文章修改後若立即撤銷核准，隔天export會把舊文章移除，所以必須保留舊版直到人員核准修訂。

migration只新增此表與必要的固定SQL函式，不改既有entries/trigger/view的定義、不更新舊資料。最小GRANT給bible_devotional_operator，函式SECURITY INVOKER、固定search_path，REVOKE PUBLIC EXECUTE；UUID由Python產生免額外extension。SQL函式參數處理payload，禁止把使用者字串插入DO $body$等外層dollar-quoted程式（會產生注入風險）。一般SELECT函式呼叫參數以安全SQL literal或JSON quoting。

entry version為資料庫計算的穩定digest，包含日期/來源/出處/四文字欄/審核狀態/ranges。draft save及approve皆檢查version，舊分頁回409，不默默覆蓋。新日期衝突要409，不能覆蓋該日內容。

核准在單一DB transaction內鎖定draft/entry，重新核對base_version，再更新/新增entries及ranges，最後依序寫入來源核准與神學核准，沿用既有觸發器及audit（必須實際人工勾選兩項且reviewer非空才可呼叫）。draft標APPLIED；任何錯誤整筆rollback。可使用approval內短暫LOCK TABLE entries IN SHARE ROW EXCLUSIVE MODE避免其他寫入的同日競態，設定lock_timeout及statement_timeout，不能長時間持鎖。變更經文範圍時既有媒體標UNVERIFIED，避免錯誤沿用媒體核准。儲存與核准須冪等/可辨識衝突，不產生重複文章或假成功。

DB連線沿用DEVOTIONAL_SSH_HOST/DEVOTIONAL_DATABASE、sudo postgres psql5433、SET ROLE bible_devotional_operator；SSH有ConnectTimeout、子程序timeout<=15秒、statement_timeout<=8秒，無shell=True，不在檔案放密碼。DB名/host嚴格驗證，錯誤回安全繁中摘要，不能回傳SQL/正文/憑證/原始stderr。schema缺失回503可辨識，不可GET自動migration。

## API契約（與146/147共用，不任意改名）

所有`/api/devotional-editor/*` GET/POST都需既有`check_write_auth()`四項保護（X-Bible-Admin、X-Bible-Token、Origin、Host）；不能落入舊的僅X-Bible-Admin操作分支。JSON body最多64KiB。

模型欄位：`content={date,reference,title,source_url,summary,reflection,prayer}`，其中source_url可空，自動產生本站對應經文來源。date嚴格ISO，reference經既有parser解析，僅接受專案四福音有效範圍，逐節對照site_root/data/*.json，包含merged verse。不要接受client傳入經文正文或ranges。所有文字拒NUL；title<=80、reference<=240、source_url<=2048、summary/prayer各<=6000、reflection<=2000，必要欄位非空。來源不自動抓網頁。

- GET `/api/devotional-editor/list?from=YYYY-MM-DD&through=YYYY-MM-DD` → `{entries:[{id,date,title,reference,source_status,theology_status,version}],drafts:[{id,entry_id,date,title,version,updated_at}]}`。範圍<=366日，最多500筆，不靜默截斷。不要開放sample/template/out-of-scope舊紀錄核准。
- GET `/api/devotional-editor/entry?id=<int>` → `{entry:{id,version,content,source_status,theology_status},scripture:[{book,chapter,verse,end,text}]}`。
- GET `/api/devotional-editor/draft?id=<uuid>` → `{draft:{id,version,entry_id,base_version,content,status},scripture:[...]}`。
- POST `/api/devotional-editor/preview` body `{reference}` → `{ranges:[...],scripture:[...]}`。純讀不寫DB。
- POST `/api/devotional-editor/save` body `{draft_id:null|uuid,version:0|int,entry_id:null|int,base_version:null|string,content}` → `{draft:{id,version,entry_id,base_version,content,status},scripture:[...]}`。Save只寫新草稿表，不改已核准entries。
- POST `/api/devotional-editor/approve` body `{draft_id,version,reviewer,source_confirmed:true,theology_confirmed:true}` → `{entry:{id,version,content,source_status,theology_status},draft:{id,version,status:"APPLIED"},message}`。兩項確認不得用truthy字串替代true。修改後要重新save才能approve。
- GET `/api/devotional-editor/settings` → 呼叫獨立模組`devotional_operations.get_settings()`（147實作）。
- POST `/api/devotional-editor/settings` body `{version,enabled,start_date,end_date,time}` → 呼叫`save_settings(payload)`。
- POST `/api/devotional-editor/publish` body `{confirm:true,schedule_version}` → 呼叫`publish_now(payload)`。

147函式失敗以`OperationError(message,status)`回傳；內容模組同樣提供安全錯誤類別。server只回 `{error:message}`及對應400/403/404/409/503；未知exception回通用500不曝stack。147未完成時先保留lazy import/503，不因模組不存在讓整個server無法啟動。

新增前端JS白名單 `/devotional_editor.js`（GET/HEAD），其他新Python/SQL/MD仍404。146不修改admin.js，會自行取得token，使用新JS。

## 驗證

建立唯一命名的隔離PostgreSQL DB（不能覆蓋既有test DB），依序schema/grants/002/003/004/005，測新草稿保存、更新、舊version409、同日衝突、approve與audit、原核准版本在草稿階段保留、改範圍媒體失效、注入字串只是文字、rollback。可加/tmp測試，不新增repo測試；PM另寫獨立整合驗收。測完只清理自己建立的隔離DB。HTTP在隨機port/臨時root/tokenfile驗證所有auth，原資料/真實unit不動。

請先確認契約並開工；必要調整立刻告知PM。完成回報檔案、實際測試、限制，待命。
