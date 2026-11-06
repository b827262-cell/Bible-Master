# 四福音靈修索引

資料庫 `bible_devotional` 使用 debian-toshiba 上 PostgreSQL 18（5433）。SSH 必須能免互動連線，遠端帳號須能以 `sudo -n -u postgres` 執行 psql。命令開始時切換為 NOLOGIN 的最小權限角色；此方式仍依賴遠端管理員的 sudo 權限，不是獨立資料庫帳號。

使用 `DEVOTIONAL_SSH_HOST` 及 `DEVOTIONAL_DATABASE` 可指定 SSH 主機與資料庫；預設為 `debian-toshiba` 和 `bible_devotional`。不在檔案中保存密碼。不要在任意來源 CSV 填入受著作權保護的正文或媒體。

```bash
python3 -B bible-site/devotional/cli.py dry-run --devotional-csv 清單.csv --media-csv 影音.csv --output-report /tmp/preview.json
python3 -B bible-site/devotional/cli.py show --date 2026-11-06
python3 -B bible-site/devotional/cli.py today
python3 -B bible-site/devotional/cli.py import --devotional-csv 清單.csv --media-csv 影音.csv
python3 -B bible-site/devotional/cli.py review 1 --type source --reviewer 審核者
python3 -B bible-site/devotional/cli.py draft 1 --summary 原創摘要 --reflection 原創反思
python3 -B bible-site/devotional/cli.py review 1 --type theology --reviewer 神學審核者
python3 -B bible-site/devotional/cli.py media-link 1 1
python3 -B bible-site/devotional/cli.py media-review 1 --reviewer 審核者
python3 -B bible-site/devotional/cli.py export --output /tmp/devotional.json
```

`show` 供審核者查看指定日期的經文、默想、反思、禱告和審核狀態，經文即時取自專案四福音 JSON。這個命令會顯示待審草稿，不代表已核准公開。

使用 AGY 的 Gemini 4 Argon Medium 產生下一篇原創草稿，會將所選專案經文送往該模型服務，並消耗其額度。預設只輸出草稿，加入 `--save` 才寫入 PostgreSQL 的待審狀態。該日期已有紀錄時不呼叫模型，也不覆蓋。

```bash
python3 -B bible-site/devotional/generate_draft.py --date 2026-11-20 --reference '路加福音 19:1–10'
python3 -B bible-site/devotional/generate_draft.py --date 2026-11-20 --reference '路加福音 19:1–10' --save
```

產生草稿不代表神學審核通過。請先確認內容、來源與日期，再由人員完成既有雙重審核；工具沒有自動排程或自動發佈。

兩項審核完成後，可執行 `python3 -B bible-site/devotional/cli.py export --output bible-site/data/devotional.json`，將核准內容匯出供 `site/devotional.html` 閱讀。執行網站公開建置前，請先檢查匯出內容。沒有資料或當日沒有核准內容時，頁面會顯示提示。

審核前請人工確認來源日期、經文、版權、連結及影音是否對應。兩項審核可由不同人執行；本程式不驗證審核者身份。`sample_` / `template_` 批次與測試網址不可核准。相同網址和日期重新匯入不覆寫資料，待修正紀錄需人工處理。影音連結須人工檢驗並手動關聯至正確經文。若一支影音對應多段經文，暫列待審核，尚不提供多段影音核准。

爬蟲預設停用：`python3 -B bible-site/devotional/crawler.py --fixture /path/to/test.html` 僅測試本機文件。`--live` 須先由管理員人工確認規則及使用依據，將資料庫 source_policy 設為 APPROVED 並填寫相關證據；每次即時再確認 robots.txt。它僅輸出索引候選，無自動匯入或排程，缺少明確日期時不會猜測，頁面正文不會保存。不要把 robots.txt 視為版權授權。

測試請只使用隔離資料庫，SQL 測試本身會 rollback。範本 CSV 是假資料，不代表真實發布日期或影音來源。原創與神學正確性須人員審核，程式無法保證。

新建隔離測試庫時，依序執行 `schema.sql`、`grants.sql`、`002_policy.sql`、`003_scripture_bounds.sql`、`004_title.sql` 與 `integration_test.sql`。章節上限依專案四福音 JSON 的 89 章建立，經文來源版本更新時須同步檢查上限。撰寫草稿時可加上 `--title` 和 `--prayer`，修改主題會撤銷神學核准。
