# 禱讀（Devotional）最終審查報告

**狀態：PASS**

## 一、審查方式

本任務為唯讀審查，只新增本報告檔案。所有結論都來自本輪實際執行的指令與工作樹內的既有紀錄，沒有引用未驗證的說法：

| 指令 | 結果 |
| --- | --- |
| `python3 bible-site/tests/site_checks.py devotional` | 41 條 devotional 檢查全通過，0 條不通過，exit 0 |
| `python3 bible-site/tools/check_all.py` | `[通過] 經文比對`、`[通過] 節數與檔案`、`[通過] 網站檢查`，總結 **3/3**，exit 0；`FAILS.md` 為「全部通過，沒有要修的項目」 |
| `python3 bible-site/tools/herdr_team.py status` | 8 個 pane 正常顯示，exit 0（明細見第五節） |
| 獨立算術覆核（見第三節） | 以 `data/{mat,luk,jhn}.json` 重跑 `devotional.js` 的過濾邏輯，復現紀錄中的 945／1842 兩個數字 |
| 獨立寫死經文掃描（見第四節） | 用 10／9／8 字連續共同段比對四福音全文，四個審查對象皆無命中 |
| `git status`／`find .verify`／`stat` | 受保護檔案與 `.verify/` 未被改動 |

## 二、`site_checks.py devotional` 的覆蓋度與真實性

### 1. 可單獨執行、也已納入全套檢查

- 單獨執行：`groups = {"devotional"}`，`python3 bible-site/tests/site_checks.py devotional` 可獨立跑通（本輪實測 41 條全綠）。
- 納入全套：`__main__` 的預設 `groups` 集合已含 `devotional`，因此 `check_all.py` 第三項（網站檢查）會一併執行；本輪在 `check_all.py` 的輸出中同樣數到 **41 條** devotional 檢查，兩邊一致，不是只在單跑時才生效。

### 2. 假資料只在 /tmp 副本、且完全沒有寫死經文

- 檢查用 `tempfile.TemporaryDirectory()` 複製 `site/` 與 `data/{mat,mrk,luk,jhn,zone-music,home,blessing,blessing-art}.json`，探測頁與假 `devotional.json` 都寫在這棵暫存樹裡；另有專條檢查「正式 data/devotional.json 沒有被檢查改動（假資料只存在 /tmp 副本）」守住這條界線。
- 假資料只含 `id`、`devotional_date`、`title`、`scripture_reference`、`ranges` 與佔位內文（`測試默想段落…`、`測試反思問題…`、`測試禱告內容…`），沒有經文字句。
- 預期經文由 `devotional_expected()` 在測試當下依 `ranges` 從四福音 JSON 算出，再與渲染結果**逐節**比對（`got == want`），合併節以 `章:節–末節 文字` 呈現，並有另條斷言確認「測試範圍真的涵蓋合併節」，避免合併節驗證被無聲移除。
- 檢查檔也自我要求：`site_checks.py` 的 devotional 段落本身不得與和合本經文有連續 8 字相同（本輪另有獨立掃描佐證，見第四節）。

### 3. 任務要求的驗證項目對照

| 要求 | 對應檢查（實測通過） |
| --- | --- |
| 有資料的日期渲染 | h2 標題＝`title`、`scripture_reference` 段落、「經文」小標、經文節數與內容逐節相等、「默想／反思／禱告」三段標題與內容、成功時 `#reading-status` 是空字串 |
| 日期預設與切換 | `#reading-date` 的 `value` 與 `max` 都等於台灣時間今天（Python 端以 `UTC+8` 獨立算出，今日實測 `2026-11-13`）；換到另一個有資料的日期會重新渲染該日內容與標題；換到沒資料的日期會清空 `#reading` 並顯示提示 |
| 無資料與錯誤情境 | `[]`、檔案 404、非法 JSON、非陣列 `{}`、不支援書卷（ACT）、範圍找不到經文（MAT 99）六種，每種都斷言訊息正確、`#reading` 為空，且**沒有未捕捉的 JS 錯誤** |
| 四種寬度不溢出 | 320／375／768／1440 四種視窗寬度下實測 `scrollWidth == clientWidth`（依序 305、360、753、1425），每個寬度各一條溢出檢查與一條 JS 錯誤檢查，共 8 條全過 |
| 導覽列與回首頁 | `#nav .nav-list a` 恰為 目錄／搜尋／經文卡片／抽經文卡（href 為 `index/search/card/blessing.html`）且有 `home.html` 回首頁連結 |
| 無外部資源 | 源碼層（只載入站內 `app.js`、`devotional.js`）＋執行層（`performance` 資源條目沒有非同來源 URL）雙重檢查 |
| 無未捕捉 JS 錯誤 | 探測頁在頁面腳本執行前安裝 `error`／`unhandledrejection`／`console.error` 轉發，覆蓋載入、切日期、四種寬度與全部錯誤情境 |

## 三、突變測試紀錄的獨立覆核

紀錄位置：`bible-site/logs/herdr-dispatch/111-devotional-site-checks-1-w2_p1.log` 與 `…-2-w2_p1.log`。其中轉錄的宣稱是：移除 `devotional.js` 的章節結尾範圍判斷後，檢查抓到兩項失敗——「MAT 預期 12 節、實際 945 節」「日期切換預期 6 節、實際 1842 節」。

本審查**不只引用該轉錄**，而是用工作樹的經文 JSON 重跑 `devotional.js` 的兩個過濾條件（起點 `(verse.end || verse.v) < start_verse`、終點 `verse.v > end_verse`），以「渲染出的段落數」為單位（合併節只算一段）獨立計算：

| 情境 | MAT 5:1–12（今天那筆） | LUK 1:1–4＋JHN 3:1–3（換日期那筆） |
| --- | --- | --- |
| 正常（預期值） | **12** 段 | **6** 段 |
| 去掉章上界 `chapter.ch > end_chapter` | **945** 段 | **1842** 段 |
| 去掉節上界 `verse.v > end_verse` | 48 段 | 115 段 |

結論：紀錄中的 12／945 與 6／1842 **逐字復現**，因此該突變測試屬實，不是口頭宣稱；48／115 則與 111 執行者（w2:p5）自報的另一種突變數值相同，兩條路徑互不衝突。突變一律在 `/tmp` 副本進行，未污染正式工作樹（本輪 `git status` 亦無 `devotional.js` 變動）。

一處需要澄清的紀錄細節：該兩份 w2:p1 日誌的 header 判定是 `verdict=改到範圍外的檔案`（`out_of_scope` 為 `bible-site/design/sample-2026-11.html`、`bible-site/tools/herdr_team.py`），w2:p5 那份則是 `verdict=pane 卡在審批`。這些是**派工流程**的狀態（該 pane 在同一時間窗内還動了別的任務的檔案，或卡在人工審批），不是本交付物的品質判定；`state.json` 現在仍記著 `111-devotional-site-checks → 失敗`，讀 `herdr_team.py status` 時請以此為據理解，實際交付物經本輪直接執行檢查已確認全綠。

## 四、鐵則與受保護檔案

### 1. 寫死經文檢查（獨立方法，不用被評檢查檔自己的邏輯）

以四福音全部經文建立 10／9／8 字連續字串集合，再與審查對象取「最長連續共同段」：

| 對象 | 結果 |
| --- | --- |
| `bible-site/site/devotional.html` | 無 ≥8 字共同段 |
| `bible-site/site/devotional.js` | 無 ≥8 字共同段 |
| `bible-site/tests/site_checks.py` 的 devotional 段落 | 無 ≥8 字共同段 |
| `bible-site/data/devotional.json`（默想／反思／禱告正文） | 無 ≥8 字共同段（順帶確認正式默想文字沒有抄整節聖經） |

### 2. 受保護檔案未被改動

- `git status --short` 對 `data/{mat,mrk,luk,jhn,blessing,home,devotional}.json` 各自回報 **0** 筆變動。
- `data/devotional.json` 的 mtime 是 `2026-11-13 00:19`，對應已提交的發佈（`a16d9b5 Publish daily devotional 2026-11-13`），且與 HEAD 無差異；不是檢查程式所為（檢查另有專條自我約束，且本輪實測通過）。
- `.verify/`（位於專案根，79 個檔案）近 10 小時內被改動的檔案數為 **0**。
- `bible-site/site/devotional.html`、`bible-site/site/devotional.js` 為追蹤中檔案，相對 HEAD **無 diff**。
- 本輪唯一有變動的檔案是 `bible-site/tests/site_checks.py`（+418/−2），即任務 111 的交付物本身；`REVIEW-devotional.md` 依本任務規定新增。

## 五、`herdr_team.py` 團隊編制檢查

`python3 bible-site/tools/herdr_team.py status` 實測輸出顯示：

- `w2:p6  agent=agy  status=done  角色=agy、image  職務=PM 調度／前端與生圖` → `agy` 已在唯一的 `TEAM` 表內（檔頭無重複 `TEAM`／import 區塊，關鍵定義各只出現一次）。
- `w2:p4 … 角色=-  最後=（本腳本尚未派工過）｜CodeBuddy（Herdr 未識別 agent，手動派發）`、`w2:p8 …｜Claude（總PM，負責統籌與發佈）` → 兩個非派工 pane 已有清楚標示，不再只顯示「不在團隊映射」。
- `112-herdr-team-roster` 在 `state.json` 已是 `通過（2026-11-13 01:13）`，本任務 front matter 的 `depends` 條件成立。

## 六、觀察事項（不影響本次 PASS，留給後續決策）

1. **合併節終點邊界的語意**：`devotional.js` 的下界用 `(verse.end || verse.v) < start_verse`（會連同跨起點的合併節整段取用），上界只比對 `verse.v > end_verse`，所以範圍終點若落在合併節**中間**，會把整個合併節都渲染出來（多出後半節）。本輪逐一計算 8 筆正式資料的 16 個邊界，全部落在單獨節上，因此現況碰不到；測試 fixture 也沒有覆蓋這個邊界（`LUK 1:1–4` 的合併節在範圍內而非終點）。屬潛在議題，若要收緊需先定調「整段保留或裁切」，並同時改 `devotional.js` 與新增邊界 fixture。
2. **`media_urls` 與 `source_url` 完全未被頁面使用**：資料欄位存在、頁面不渲染也不顯示來源，檢查也沒有假設它。若後續打算讓這些欄位上線，需另開任務補渲染與檢查。
3. **經文段落萃取方式**：檢查以 `#reading` 的葉節點序列在「經文」小標與下一個小標之間取 `p`，能容忍一層容器；若日後改成更深或分段的結構，需要同步調整 `devotional_scripture()`，否則會誤判。
4. **派工紀錄的語意**：`logs/herdr-dispatch/state.json` 記的是流程結果（越界、卡在審批、逾時），不等於交付物好壞；審查時應像本輪一樣直接重跑檢查，再回頭解讀日誌。
5. **執行成本**：devotional 群組一輪會啟動約 12 次 headless Chrome（41 條檢查），`check_all.py` 的網站檢查項目因此變長；後續若再加寬度或情境，建議在同一個探測頁回合內批次收集，避免 Chrome 呼叫線性增加。

## 七、結論

**狀態：PASS。**

- 任務 111 交付的 devotional 自動化檢查可單獨執行、已納入 `check_all.py`，41 條覆蓋了渲染、日期、六種異常情境、四種寬度、導覽列、外部資源與 JS 錯誤，且以 /tmp 假資料＋動態逐節比對達成「零寫死經文」的鐵則（檢查檔自己也不例外）。
- 突變測試經本審查獨立算術覆核，12／945 與 6／1842 完全復現，屬實且未污染工作樹。
- `python3 bible-site/tests/site_checks.py devotional` 與 `python3 bible-site/tools/check_all.py`（3/3）本輪實測全綠，`FAILS.md` 為空；受保護的經文 JSON、`.verify/`、`devotional.html`、`devotional.js` 皆未被改動。
- `herdr_team.py` 編制已補 `w2:p6（agy、image）`，`w2:p4`／`w2:p8` 有明確標示，並維持「CodeBuddy 不補自動派工分支」的評估結論。

未通過原因：無。第六節五項為後續建議，不構成退回。
