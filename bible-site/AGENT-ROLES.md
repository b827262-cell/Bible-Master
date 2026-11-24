# Herdr 團隊角色與派工規則

核對日期：2026-11-14。以目前畫面標籤 tab1～tab5 為準；Herdr 的 tab ID、number 及畫面標籤不一定相同。

| 畫面標籤 | 實際 pane | Agent／目前模型 | 固定角色 | 任務範圍 |
| --- | --- | --- | --- | --- |
| tab1 | w2:p1 | Codex | PM／架構／最終驗收 | 拆任務、指定檔案與驗收條件、協調相依、獨立驗收、依使用者授權管理發布 |
| tab2 | w2:p2 | CodeBuddy／DeepSeek V4.1 Flash，high | 後端與資料工程 | Python、API、資料驗證、安全檢查、資料庫流程、排程；跨檔變更先由 PM 指定範圍 |
| tab3 | w2:p5 | CodeBuddy／DeepSeek V4.1 Flash，high | 主力實作與前端整合 | HTML/CSS/JS、後台表單、互動與響應式版面、功能整合；後端相依交由 tab2 協作 |
| tab4 | w2:pC | DeepSeek Harness／inclusionAI Ling 3.2 Flash（free） | 測試與獨立 QA | 隔離執行測試、重現問題、檢查回歸與邊界、整理缺陷證據；測試程式僅在任務指定時可改 |
| tab5 | w2:pD | DeepSeek Harness／e500-ollama/nemotron-3.5-bolt-e4b:ud-q8 | 地端工程助理 | 唯讀盤點、文件與交接、檔案清單、簡單單檔腳本；先以小範圍任務驗證能力，再擴大責任 |

以上為初始分工，不把模型名稱視為能力驗證；依後續實際交付與 PM 驗收調整。tab3 為既有完成週封面與禱讀排程任務的主實作 pane；視窗重整後目前標籤為3，不再稱它tab4。

目前可用性：tab2、tab3、tab5已回覆確認並待命。使用者回報tab4恢復後，PM重新下達角色；tab4已實際回覆「tab4 QA 已就緒」，確認目前模型與協作規則，恢復承接獨立QA任務。本次未派發新測試或功能修改。

## Freebuff（互動式 CLI，2026-11-24 實測）

| 項目 | 內容 |
| --- | --- |
| 終端 | 預設預期 `t7`；實際由 `foreground.argv` 的檔名 `freebuff` 動態解析（不另開第二實例，維持單一 `t7`），tab id 與 pane id 亦每次動態取得 |
| 模型 | Solar Pro 4（廣告贊助免費額度，時間制，用完即停）；使用者可自行 `/model` 切換 |
| 能力（已驗證） | 唯讀程式審查、短文問答；能自行讀檔後給出條列意見 |
| 能力邊界 | 行號與事實精確度不穩定：實測 3 條審查意見中 1 條為誤判、1 條行號錯誤。不可當最終驗收來源 |
| 派工工具 | `bible-site/tools/freebuff_dispatch.py`（`roles.yml` 的 `freebuff.dispatch` 同步登錄） |
| 派工流程 | 動態解析 terminal/tab → `herdr-app do tab.select` → `pane.focus` → `herdr-core send`（send 自帶 Enter，不再補按） |
| 完成判定 | 以終端 cwd 對應 `~/.config/manicode/projects/<cwd 名>/chats/*`，要求本次 prompt 的 user 訊息＋其後 `isComplete` 的 assistant 訊息，且時間晚於派工；**不可**用 `hc wait`／`turn`／`status`（hc 未註冊 freebuff，turn 恆 0、status 恆 null） |
| 防護 | 併發鎖（`dispatch.lock`）＋相同 prompt 短時間重送封鎖；多個 freebuff 終端或無法唯一識別 session 一律拒絕，不猜測；逾時不自動重試 |
| 驗收 | 一律人工／PM／CodeBuddy 核對回覆內容；工具只輸出原文，不宣告通過 |
| 限制 | 無 headless、無 ACP；每次派工消耗免費額度，不適合高頻自動化 |

## 協作約定

1. 每份實作任務由 PM 指定目標、唯一負責人、可改檔案、檢查指令與交付物。先回報現況與衝突，再修改授權檔案。
2. tab2、tab3 不同時修改同一檔案；需要共用修改時，由 PM 指定其中一人寫入，另一人提出建議。
3. tab4 獨立驗收，不能只重述實作者的通過聲明；測試使用隔離副本，包含必要的 `data/devotional.json` 與 `.verify/`，避免覆寫真實報告或資料。
4. tab5 的地端小任務保持輸入與範圍精簡；不承擔人工神學審核，不憑模型記憶填寫經文。經文一律取專案JSON。
5. 所有agent保留工作樹已有變更，不清理未追蹤檔、不自行commit／push／部署、不改模型或機器設定。正式資料庫寫入、排程安裝與發布由PM依使用者授權另行下達。
6. 完成回報：修改檔案、實際執行檢查與exit code、失敗原因、未完成事項。不得自行宣稱整體驗收通過。
7. 角色確認本身不授權擴充工作；後續依PM任務檔逐項實作，不因角色描述自行修改其他檔案。

## 路由注意

`tools/herdr_team.py` 已在任務139同步至目前編制，送出前檢查live inventory，保留pane ID大小寫。unknown、blocked或查無agent不會自動派發／宣告完成，仍由PM以明確pane ID人工派發及核對。每次派工前重新讀取Herdr inventory；pane重建後ID會改變。

## 本輪實作交付（139～143）

tab2完成路由與狀態API，tab3完成看板與亮／暗對比修正。tab5完成單檔進度工具，經PM回饋修正；其自測工具被拒絕，測試由PM補齊。tab4本輪未交付測試檔，且模型請求顯示TIMEOUT重試，PM已撤回其寫入責任、改為唯讀覆核；本輪獨立測試與最終驗收由PM完成，不把尚未交付的覆核當成通過證據。
