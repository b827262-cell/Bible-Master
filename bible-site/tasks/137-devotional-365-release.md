# 365 日禱讀上架：主辦核對與交付

使用者交辦「每日禱讀 請派工並完成365日上架」。tab4 DeepSeek 4.1 Flash 主辦，Codex PM 驗收。先完成可驗證的內容與發布準備；PM 正詢問維持每日公開或一次公開全部，未收到答覆前不可改日期或公開策略。

唯一可新增／修改：`bible-site/REVIEW-devotional-365-release.md`。其他檔案、資料庫、systemd、正式站全部唯讀。測試與匯出只能用 `/tmp` 隔離資料夾；不得 commit/push/部署，不觸發 publish_daily.py 正式模式、不替任何人填寫人工審核。

請實際執行並記錄：

1. 使用 cli.sql 唯讀查資料庫，核對 2026-11-21～2027-11-20 恰有365唯一連續日期，每天一篇且 title/summary/reflection/prayer/ranges 完整，所有 source/theology 審核狀態、審核者、時間及 audit 記錄一致。既有15篇（11/06～11/20）須完整保留。不得假設 Markdown 待審字樣代表目前DB狀態。
2. 對照 batch-365 的365份 drafts（46批）、reading_plan()、四福音JSON，以及DB的日期、經文範圍與正文。列出任何差異，分辨 fix_365.py 修訂造成的合理差異；以目前DB內容為準逐一檢查原37項疑點是否已解決。可使用現有備份，禁止覆寫。全365篇讀取核對來源經文，找空白、簡體字、重複／模板內容或無法由經文支持的敘述；標記需人工確認的具體day/date/field/原因。
3. cli.py export --through 2027-11-20 匯出至 `/tmp`，驗證全部380篇、365目標日期齊全、原15篇不變。預設截至今天匯出亦驗證無未來日期，絕不可直接改正式data/devotional.json。
4. 唯讀核對 systemd timer/service、獨立發布checkout及最近journal、origin/main上的publish_daily腳本與正式站JSON。核對正式站當前公開篇數與日期、排程下一次執行、建置是否納入devotional.json，列出上架缺口。不要更改發布checkout或git狀態。
5. 在隔離副本執行 devotional/test_publish.py、tests/site_checks.py devotional；包含data/devotional.json及.verify，避免真實工作樹報告或資料被改。
6. 交付報告寫清：已完成、未完成、證據、檢查指令與結果、發布方式需要PM決策之處。狀態如實：不能以資料庫APPROVED直接宣告正式站365篇已公開，不把機器檢核描述為人工神學審核。

開始後直接執行，完成回覆檔案、檢查結果與需要PM處理的缺口。
