# PM 進度（聖經網站）

流程與角色分工見 `PLAN.md`。這份檔案由 PM 維護：上方狀態表由 `tools/pm_status.py` 依實際檔案與檢查結果自動產生，下方的紀錄由 PM 手寫。
環境檢查與基準線：`bash bible-site/tools/pm_setup.sh`；更新狀態：`python3 bible-site/tools/pm_status.py`。

<!-- pm:auto:start -->
更新時間：2026-11-24 16:54（由 `python3 bible-site/tools/pm_status.py` 產生，請勿手改此區塊）

| 步驟 | 狀態 |
|---|---|
| 0 資料產生（四福音 3776 節驗證） | 完成 |
| 1 建站（site/ 11 個檔案） | 完成 |
| 2 自動檢查 check_all.py 全過 | 完成 |
| 3 審核（REVIEW.md） | 完成 |
| 4 修正與 CHANGELOG.md | 完成 |
| 5 TODO.md 清空或不存在 | 完成 |

- site 檔案：11/11（缺：無）
- check_all.py：沿用上次 check_all.py 的結果（FAILS.md）：全部通過
- 四福音JSON驗證：四福音皆驗證成功
- 審核：通過 6 項，不通過 0 項（粗略計數，請人工看 REVIEW.md）
- TODO.md 未完成項目：沒有 TODO.md
<!-- pm:auto:end -->

## 計劃步驟（對應 PLAN.md）

| 步驟 | 負責 | 做法 | 驗收 |
|---|---|---|---|
| 0 資料產生 | 腳本 | `tools/build_data.py` | `verify_text.py` 678/678 |
| 1 建站 | E500（主編） | `prompts/01..05-*.md` 一次一份 | `check_all.py` 每份做完跑一次 |
| 2 審核 | A16 | 6 項檢查表，寫 `REVIEW.md` | 每項標通過／不通過 |
| 3 測試 | De1050（新會話） | 只跑 `check_all.py` | 回報最後一行 |
| 4 修正 | E500 | 依 `FAILS.md`、`REVIEW.md`，最多 3 輪 | `check_all.py` 結束碼 0 |
| 5 收尾 | 貓聽 | 處理 `TODO.md` | `TODO.md` 清空 |

## 紀錄

- 2026-11-01 15:32　專案由 `tools/Harness-model/` 複製到 Bible-Master；基準線 678/678、`check_all.py` 1/3。寫好 5 份建站提示。
- 2026-11-01 16:47　任務 1 送給 E500（Harness 新會話，Bible-Master 工作區）。
- 2026-11-01 16:52　貓聽（雲端模型）另行補齊 6 個站檔（`CHANGELOG.md` 有記錄），`check_all.py` 3/3。E500 當時仍在讀檔、沒有寫出檔案，已由 PM 在 16:5x 手動停止，避免覆蓋貓聽的檔案。
- 待辦：獨立核對貓聽交出的檔案（鐵則：不憑模型自述）→ 步驟 2 審核 → 步驟 3 測試 → 視需要修正。
- 2026-11-01 16:55　依使用者指示改用三台地端模型：A16（Bonsai 9B 128K think）做審核寫 `REVIEW.md`；De1050（Qwen3.5 4B 48K no-think greedy）新會話只跑 `check_all.py`；修正交給 E500。貓聽與 PM 只在地端出問題時才介入。新增 `tools/pm_setup.sh`（環境檢查與基準線）與 `tools/pm_status.py`（更新本檔的狀態表）。
- 2026-11-01 16:58　A16 交出 `REVIEW.md`（6 項全通過）；PM 獨立核對：375px 下 6 個頁面都無橫向捲動、簡體字掃描無問題。A16 對第 5 項的說明有誤（把 40em 寫成約 64px），結論仍成立。
- 2026-11-01 16:58　De1050 第一次回報 2/3：原因是多個 `check_all.py` 同時跑，共用 Chrome 預設 profile 而讀到空頁面（非網站問題；De1050 的文字說明也有誤，以腳本輸出為準）。已在 `tests/site_checks.py` 改成每次呼叫用獨立 `--user-data-dir`，三個同時執行都 3/3。
- 2026-11-01 16:59　De1050 重跑：「總結：3/3 項檢查通過」。步驟 0–4 完成；無 `TODO.md`，不需貓聽收尾。
- 2026-11-01 17:03　Stop hook 指出建站沒有照計劃由 E500 做：貓聽版本已備份到 `.backup-cloud-site-20261101/`，`site/` 清空，重新由 E500 依 prompts/01..05 建站。PM（貓聽開的會話）獨立審查時發現真缺陷：`chapter.html?ch=1#v40` 不會捲動到該節（經文 fetch 後才畫出）。已加入 `tests/anchor_probe.html` 與 site_checks.py 的第 6 項檢查，並寫進 prompts/02。
- 2026-11-01 18:31　E500 依 prompts/01..05 寫完 6 個檔案（chapter.html 一輪修正）。`check_all.py` 3/3（含 #v40 捲動），PM 另測 375px 6 頁都無橫向捲動。
- 2026-11-01 18:34　A16 審核 E500 版本，`REVIEW.md` 6 項全通過（第 3 項說 card.html 連到 chapter.html，實際沒有，不影響結論）。
- 2026-11-01 18:36　De1050 新會話執行 `check_all.py`：「總結：3/3 項檢查通過」。無 `TODO.md`，不需貓聽收尾。E500 會話寫完後停在壓縮上下文，已由 PM 停止。計劃完成。
- 2026-11-01 20:30　前台測試第一階段（本機 127.0.0.1:8090，Front-end Engineer／deepseek-4.1-flash）：31 案，通過 27、不通過 2（E6 favicon 404、E7 經文含「脚」×8「叙」×1，來源 `.verify/mark.txt` 即如此）、需人工 2（E2 深色外觀、E4 導覽列與章節卡片 `outline: none`）。PM 已複驗 E6、E7、E4。報告：`FRONTEND-TEST-REPORT.md`。
- 2026-11-01 20:4x　第二階段 Tailscale（100.76.46.86:8090）由使用者親自測試，結果 OK；伺服器已由使用者停止。待決：E6／E4 是否交 E500 修、E7 是否修正原文、E2 由誰目視。
- 2026-11-01 21:00　前台修正第一輪完成。E6（De1050）、E4（A16）、E7（E500）都一次完成，無需貓聽。PM 複驗：4 頁 0 個 favicon 請求、0 筆 Console 錯誤；Tab 焦點 2px `--focus` 外框；`mark.json` 0 個「脚／叙」，8 個「腳」1 個「敘」；`.verify/mark.txt` 未改；`check_all.py` 3/3。下一步：Front-end Engineer 複審。
- 2026-11-01 21:25　Front-end Engineer 複審（`FRONTEND-REVIEW-ROUND2.md`）：31 案，通過 30、不通過 0、需人工 1（E2 深色外觀）。E6、E7 由不通過轉通過，E4 由需人工轉通過，其餘 27 案無回歸。待：E2 真人目視、commit。
- 2026-11-01 22:18　dispatch：20-chapter-html 通過（e500）。
- 2026-11-01 22:32　dispatch：21-search-html 通過（e500）。
- 2026-11-01 22:33　dispatch：30-review 通過（a16）。
- 2026-11-01 22:34　dispatch：31-test 通過（de1050 → de1050）。
- 2026-11-01 22:55　dispatch：12-card-html 通過（e500）。
- 2026-11-01 22:58　dispatch：11-index-html 通過（a16 → a16 → e500）。
- 2026-11-01 23:00　dispatch：30-review 通過（a16）。
- 2026-11-01 23:00　dispatch：31-test 通過（de1050）。
- 2026-11-01 23:00　四大福音全部加入：原文自維基文庫轉出並與 ebible.org 交叉比對，`build_data.py`／`verify_text.py`／`smoke.js`／`site_checks.py` 改為四卷；網站改為 `?book=` 書卷切換。新增派工腳本 `tools/dispatch.py`（headless、範圍檢查、重試與升級，skill `bible-dispatch`）。E500 寫 chapter／search／card，A16 改 index（失敗後升級 E500），A16 審核、De1050 測試。`check_all.py` 3/3（含 index、card 檢查），375px 6 頁無橫向捲動。待：前端工程師複審、commit。
- 2026-11-01 23:15　dispatch：14-booktabs-focus 通過（a16 → a16）。
- 2026-11-01 23:15　dispatch：13-card-footer 通過（de1050）。
- 2026-11-01 23:15　Front-end Engineer 四福音複審（`FRONTEND-REVIEW-4G.md`）：37 案，通過 35、不通過 1（A7 卡片頁尾寫死「馬可福音」）、需人工 1（深色外觀）。PM 複驗屬實，加上 `site_checks.py` 的「頁尾沒有寫死單一書卷名稱」檢查，經 dispatch 修正：De1050 改 card.html 頁尾，A16 補 `.book-tabs a:focus-visible`，都一次通過。`check_all.py` 3/3。待：深色外觀真人目視、commit。
- 2026-11-02 11:07　dispatch：40-focus-css 通過（a16）。
- 2026-11-02 11:08　dispatch：41-index-labels 通過（de1050）。
- 2026-11-02 11:08　dispatch：42-search-labels 通過（de1050）。
- 2026-11-02 11:23　dispatch：43-layout-css 通過（e500）。
- 2026-11-02 11:25 視覺優化（FRONTEND-VISUAL-OPTIMIZATION-PLAN.md）：新增 tests/visual_checks.py（淺深色、320/375/768/1440px）；派工 40 A16 焦點外框、41/42 De1050 表單 aria-label、43 E500 觸控區域／目前位置／字級／經文對齊，四項一次通過；visual_checks 全過、check_all 3/3。待：Front-end Engineer 複審、深色目視、commit。
- 2026-11-02 12:40　PM 獨立複驗（不憑模型自述，全部以腳本與實測為準）：`check_all.py` 3/3（四卷 3776/3776）、`visual_checks.py` 47/47。R2 的兩項不通過已確認修好：E8 的 `306:` 行號污染已不存在（`style.css` 無行號殘留），CSSOM 50 條規則中 `:focus-visible` 有 2 條且生效；E6 六類元素 computed outline 皆 `solid 2px`（淺色 `rgb(179,84,0)`、深色 `rgb(224,164,92)`）。E5 深色外觀以客觀量測替代目視：深色變數確實生效（背景 `#171614`／`#21201d`），本文 13.05–14.48:1、次要文字 6.17–6.85:1、焦點 7.47–8.30:1，全部 ≥4.5:1。另測：搜尋 XSS 四種 payload 皆無節點注入、無 `__xss` 觸發；16 種不合法 `book`／`ch`／`v` 都退回預設且 0 個 Console 錯誤；合併節錨點 `#v2`／`#v35`／`#v25` 齊備且 `id` 無重複。待辦只剩 commit。
- 2026-11-02 20:37　dispatch：50-admin-server 通過（e500）。
- 2026-11-02 21:06　dispatch：51-admin-ui 通過（e500）。
- 2026-11-02 21:34　dispatch：52-start-sh 通過（e500）。
- 2026-11-02 22:10　dispatch：53-admin-review-fixes 通過（e500）。
- 2026-11-02 22:42　dispatch：54-start-sh-realpath 通過（e500）。
- 2026-11-03 00:36　dispatch：61-blessing-page 通過（e500）。
- 2026-11-03 00:37　dispatch：62-nav-blessing 通過（a16）。
- 2026-11-03 00:38　dispatch：63-index-blessing-entry 通過（de1050）。
- 2026-11-03 00:40　dispatch：64-blessing-tab-logic 通過（de1050）。
- 2026-11-03 09:18　dispatch：71-style-palette-nav 通過（a16 → a16 → e500）。
- 2026-11-03 09:25　dispatch：72-blessing-restyle 通過（e500）。
- 2026-11-03 12:57　dispatch：91-launcher-entry-url 通過（a16）。
- 2026-11-03 13:00　dispatch：92-launcher-data-check 通過（e500）。
- 2026-11-03 21:39　dispatch：95-zone-data-build 需要雲端（貓聽）（a16 → a16 → e500 → e500）。
- 2026-11-03 21:42　dispatch：100-art-data-build 通過（a16）。
- 2026-11-03 21:53　dispatch：96-zone-music-js 通過（e500）。
- 2026-11-03 21:54　dispatch：97-zone-wire-blessing 通過（de1050）。
- 2026-11-03 21:55　dispatch：97-zone-wire-card 通過（de1050）。
- 2026-11-03 21:56　dispatch：97-zone-wire-index 通過（de1050）。
- 2026-11-03 21:57　dispatch：97-zone-wire-search 通過（de1050）。
- 2026-11-03 22:06　dispatch：98-zone-admin-api 需要雲端（貓聽）（pm → pm）。
- 2026-11-03 22:06　dispatch：101-blessing-art-view 通過（fe）。
- 2026-11-03 22:07　dispatch：102-blessing-art-canvas 通過（fe）。
- 2026-11-03 22:09　dispatch：103-art-admin-api 通過（pm）。
- 2026-11-03 22:10　dispatch：99-zone-admin-ui 通過（fe）。
- 2026-11-03 22:13　dispatch：104-art-admin-ui 通過（fe）。
- 2026-11-03 22:50　前台四區背景音樂（`site/music.js`、`data/zone-music.json`、後台 `/api/zone-music`）與抽經文卡主題收藏卡圖（`data/blessing-art.json`、5:7 小卡片、燙金框畫進圖檔、`tools/art_convert.py`、後台 `/api/blessing-art`）完成。派工 13 個任務（地端 7、fe 4、pm 2），新增雲端角色 fe／pm／cb／cmd／agy／qoder。`check_all.py` 3/3，visual 通過。使用者回報 iPad 實機測試 OK（首次點擊開始播、換頁後再點接續）。背景音樂候選曲 Ballade pour Adeline 的來源（Audio.com 免費下載）已記在 `ASSETS-LICENSE.md`，檔案不放進 repo。
- 2026-11-05 09:03　dispatch：106-site-music-zones 通過（e500）。
- 2026-11-05 09:09　dispatch：109-admin-html-zone-cards 需要雲端（貓聽）（de1050 → de1050 → e500）。
- 2026-11-05 09:12　dispatch：107-site-blessing-single-art 通過（e500 → e500）。
- 2026-11-05 09:19　dispatch：105-build-zone-art-assets 通過（a16 → a16）。
- 2026-11-12 23:30　PM 盤點區域音樂／單卡收藏圖（任務 105–110）：105／106／107 已由 dispatch 通過；108（server.py）、109（index.html）、109b（admin.js）的改動已在工作樹（11-12 18:00 前後，不是經 dispatch.py 完成，沒有派工紀錄），PM 重跑三份任務檔的 checks 全過。110 最終審查原本卡在「跨頁續播探測 2/3」：原因是測試伺服器不支援 HTTP Range，headless Chrome 對未整檔下載的 mp3 無法 seek（不是 `music.js` 缺陷）。PM 改測試：`site_checks.py` 加 `RangeHandler`、`zone_probe.html` 第三頁同曲時最多等 6 秒、四區改用不同曲目並加「兩區同曲」與 blessing 獨立曲案例；zonemusic 平行 8 次全過（改前 6 次有 1 次失敗），四個突變（永不續播、忽略分區鍵、search 誤用 index 鍵、忽略 blessing 鍵）都被抓到。地端 `dsh` 與三台 Ollama 端點當時無回應，110b 複審改用 `tools/herdr_team.py` 派給 w2:p1（Codex）：`REVIEW-zone-art.md` 狀態 PASS、無中度以上問題。PM 複驗：`check_all.py` 3/3、`service_checks.py zoneadmin blessartadmin homeadmin admin`、`deploy_checks.py`、`visual_checks.py` 全過；四福音 JSON、`blessing.json`、`home.json` 無 diff。待：使用者決定 commit／發佈；`devotional`（禱讀）尚無任務檔與驗收檢查。
- 2026-11-13 00:30　禱讀：本地提交分區音樂／單卡圖、herdr 派工工具與紀錄後，合併 origin/main（PR #1 的每日禱讀頁、審核修正、06:00 上架程式；禱讀檔案以遠端較新版本為準）。合併後 `check_all.py` 3/3、`deploy_checks.py`、`service_checks.py`、`devotional/test_publish.py`（隔離測試庫）全過。資料庫 `bible_devotional`（本機 DT 10.0.3.69，PostgreSQL 18，port 5433）共 380 篇（2026-11-06～2027-11-20，日期連續；後 365 篇涵蓋四福音 3776 節），PM 機器稽核：經文範圍與標示一致、無空欄、無簡體／日文。5 篇引號內經文與四福音 JSON 字句不同（id 192、306、328、342、362），已由程式從 JSON 複製原文取代。使用者 2026-11-12 決定全部核准：380 篇來源與神學審核均登記為核准（審核者欄註明由使用者授權、Claude 代為登記）。注意：`cli.py` 預設主機名 `debian-toshiba` 不在 known_hosts，需設 `DEVOTIONAL_SSH_HOST=10.0.3.69`。
- 2026-11-13 00:45　禱讀上架排程：在 DT 安裝並啟用 `bible-devotional-publish.timer`（user timer，每日 06:00，Linger=yes；發佈用 checkout 在 `~/.local/share/bible-devotional/main`，drop-in 設 `DEVOTIONAL_SSH_HOST=10.0.3.69`）。`publish_daily.py --dry-run`：已核准且到期 8 篇（11-06～11-13）；暫存副本以 headless Chrome 開 `devotional.html`，當日標題、經文、默想／反思／禱告都有顯示。**未完成**：DT 沒有 GitHub 寫入憑證（無 gh、無 HTTPS 憑證、SSH 金鑰被 GitHub 拒絕），本地 main 領先 origin/main 的 commit 尚未 push，06:00 排程的 push 也會失敗，待使用者設定憑證。
- 2026-11-24 16:45　任務 144～147 程式碼鐵則審查與測試驗證（t5 審核官）：
  - **審查範圍**：`admin/devotional_editor.py`（443 行）、`admin/devotional_editor.js`（1261 行）、`admin/devotional_operations.py`（444 行）、`devotional/005_admin_editor.sql`（428 行）、`admin/systemd/bible-site-admin-editor.service`（19 行）、`devotional/systemd/bible-devotional-publish.service`（9 行）。
  - **(a) 無寫死聖經經文**：通過。devotional_editor.py 的 `_scripture()` 方法從 `data/*.json` 讀取經文，不內建任何經文內容；devotional_editor.js 的經文顯示來自 API 回應的 `verse.text` 欄位；其餘檔案不涉及經文。
  - **(b) 介面文字全為繁體中文**：通過。所有使用者可見文字（錯誤訊息、UI 標籤、註解）均為繁體中文，無簡體或日文。
  - **(c) 無載入外部 CDN/字型資源**：通過。devotional_editor.js 為純前端腳本，不引用任何外部 CDN 或字型；systemd 設定檔僅含路徑與環境變數。
  - **(d) 無洩漏私人 token 或未核准草稿正文**：通過。devotional_editor.js 的 token 僅從 `/api/token` 端點動態取得，存於 closure 記憶體中，不寫入 localStorage；systemd 設定檔中的 `BIBLE_ADMIN_TOKEN_FILE` 僅為路徑，不含實際 token 值；SQL 與 Python 檔案無 token 或草稿內容。
  - **測試結果**：
    - `tests/ops_dashboard_checks.py`：25 項測試全部通過（exit code 0）。
    - `tests/devotional_operations_checks.py`：23 項測試全部通過（exit code 0）。
    - `tests/deploy_checks.py`：全部檢查通過（結果：全部通過，exit code 0）。
  - **待收斂之版控狀態**：本地 main 落後 origin/main 10 個每日禱讀發布 commit，待總工程師驗收後整理提交。
- 2026-11-28 08:18　福音藝廊建置（子任務 B 文件同步）：新增 7 幅 16:9 油畫與 7 首專屬器樂，前台 `gallery.html`／`gallery.js` 以 `data/gospel-gallery.json` 呈現一週七日主題，首頁 `home.html` 新增「七日藝廊・音樂與經文圖」入口卡；`tools/build_public.py` 與相關驗證（`check_all.py`、`visual_checks.py` 等）一併更新。本次僅同步 `README.md` 前台功能表與本紀錄，未改動 `pm:auto` 自動區塊。
