# 聖經網站計劃（和合本馬可福音）

## 目標
- 做一個靜態網站：章節目錄、逐章閱讀、全文搜尋、經文卡片。
- 只用 HTML、CSS、JavaScript，不需要伺服器或建置工具。
- 第一版收錄馬可福音全卷：16 章、678 節。
- 之後可以用同一套流程加入其他書卷。

## 鐵則：經文只能來自驗證過的資料
- 經文一律由腳本從 `.verify/mark.txt`（已驗證的和合本）轉成 `data/mark.json`。
- 任何模型都不准憑記憶寫經文。之前的測試證明，小模型會捏造經文。
- 網頁只讀 `data/mark.json` 來顯示經文。
- 審核和測試時，都用腳本逐字比對原始資料，不靠模型判斷。

## 分工

| 角色 | 機器與模型（已調好的設定） | 負責 | 交出的檔案 |
|---|---|---|---|
| **主編** | E500 Bonsai 27B 160K（medium、溫度 0.4） | 規劃頁面、寫全部程式和樣式、修正審核和測試發現的問題 | `site/`、`CHANGELOG.md` |
| **審核** | TUF A16 Bonsai 9B 128K（思考、溫度 0.4） | 對照檢查表審程式碼和頁面，執行經文比對腳本 | `REVIEW.md`（每項標「通過」或「不通過」，並寫出原因） |
| **測試** | De1050 Qwen3.5 4B 48K（不思考、top_k 1） | 執行測試腳本，回報結果 | `TEST-REPORT.md` |
| **收尾** | Harness「DS Bot」裡的貓聽（直接在對話欄下指令，雲端模型 DeepSeek-V41-Flash-1017 High） | 處理 `TODO.md` 裡還沒完成的項目 | 更新 `TODO.md`，並在對話欄回報 |

### 為什麼這樣分工
- **E500 當主編：** 它是唯一在三道程式題都穩定拿 100 分的模型，所以寫程式和修錯都交給它。
- **A16 當審核：** 它約 2 分鐘可以審一輪，成績中等，適合照著檢查表逐項打勾，不適合自己從頭寫程式。
- **De1050 當測試：** Harness 光是系統提示就佔掉約 3 萬 token。48K 的視窗只剩約 1.8 萬可用，所以每個任務都要很小，例如「執行 X，把結果寫進 Y」。
- **貓聽收尾：** 它用雲端模型，能力最強，但會用到外部額度，所以只處理三台本地機器做不完的項目。

## 流程

### 第 0 步：準備資料（由腳本完成，不經過模型）
- `tools/build_data.py`：把 `mark.txt` 轉成 `data/mark.json`，格式是 `[{ch, v, text}]`。
- `tools/verify_text.py`：把 `site/` 裡顯示的經文和 `mark.txt` 逐字比對。

### 第 1 輪：主編建立網站（E500，預估 30 到 60 分鐘）
- `index.html`：16 章的目錄。
- `chapter.html?ch=N`：逐章閱讀頁，內容從 JSON 載入。
- `search.html`：搜尋經文，結果附上出處。要支援 `search.html?q=關鍵字` 直接帶入搜尋，每筆結果顯示「馬可福音 章:節」。
- `card.html`：選一節經文產生卡片，可以下載成圖片。
- 共用的 `style.css` 和 `app.js`，手機和桌面都能用。

### 第 2 輪：審核（A16，每輪預估 10 到 20 分鐘）
檢查表：
1. 所有頁面都只從 JSON 讀經文，沒有寫死的經文。
2. 執行 `verify_text.py`，結果是 678/678 全部相符。
3. 頁面之間的連結都正確，沒有失效的連結（由 `tests/site_checks.py` 自動判定）。
4. 沒有載入外部資源，字型可以用系統字型（由 `tests/site_checks.py` 自動判定）。
5. 手機寬度（375px）下沒有橫向捲動。
6. 簡繁一致，全部是繁體中文。

### 第 3 輪：測試（De1050，每次約 5 到 10 分鐘）
只做一件事：執行一支整合腳本。
- `python3 bible-site/tools/check_all.py` 會一次跑完三項檢查：
  - `tools/verify_text.py`：678 節逐字比對，並檢查沒有寫死的經文。
  - `tests/smoke.js`：每章節數和 6 個必要檔案。
  - `tests/site_checks.py`：連結、外部資源，並用 headless Chrome 實際開頁面檢查經文和搜尋結果。
- 結果會加到 `TEST-REPORT.md`，並把每個不通過的項目原文寫進 `FAILS.md`。
- 結束代碼 0 代表全部通過。

### 第 4 步：回到主編修正
- 主編讀 `FAILS.md`（腳本產生的錯誤原文）和 `REVIEW.md`，只修正不通過的項目；修完自己跑一次 `check_all.py`。
- 修正後重跑第 2 和第 3 輪。
- 最多 3 個循環。還不通過的項目寫進 `TODO.md`。

### 第 5 步：貓聽處理剩下的項目
- 在 Harness 左側欄點「DS Bot」，開啟「貓聽」的對話，在對話欄貼上下面的「收尾」指令。不經過 Slack。
- 貓聽用的是 Harness 側欄 `Bible-Master` 工作區底下釘選的「貓聽」會話，工作區就是專案根目錄；指令裡仍寫絕對路徑，貼指令前先請它 `ls` 確認讀得到。
- 貓聽處理完會把 `TODO.md` 的項目打勾，並在對話欄回報結果。

## 各角色的指令範本（直接貼進 Harness）

開會話前先在 Harness 選對模型，工作區選 `Bible-Master`。

**主編（E500「Bonsai 2 27B PQ2_0 160K medium t0.4」）**
> 你是主編。請讀 `bible-site/PLAN.md` 和 `bible-site/data/mark.json`，在 `bible-site/site/` 建立 index.html、chapter.html、search.html、card.html、style.css、app.js。經文只能用 fetch 從 `../data/mark.json` 讀取，不准在程式裡寫任何經文。不要載入外部資源，全部用繁體中文，要能在手機和桌面上使用。完成後在 `bible-site/CHANGELOG.md` 記下這輪的修改，只回報改了哪些檔案。

**主編修正（E500，第 4 步）**
> 請讀 `bible-site/FAILS.md` 和 `bible-site/REVIEW.md`，只修正不通過的項目，不改其他地方。修完執行 `python3 bible-site/tools/check_all.py`，直到全部通過或已盡力。修完更新 CHANGELOG.md。這輪修不好的項目，寫進 `bible-site/TODO.md`，格式是 `- [ ] 問題｜檔案｜原因`。

**審核（A16「A16 - Bonsai 2 9B Q2_0 - 128K think t0.4」）**
> 你是審核員，只檢查、不修改程式。請執行 `python3 bible-site/tools/verify_text.py`，並照 PLAN.md 的 6 項檢查表檢查 `bible-site/site/`。把結果寫進 `bible-site/REVIEW.md`：每項標「通過」或「不通過」，不通過的要寫出檔案和原因。

**測試（De1050「48K no-think greedy」，開一個新會話）**
> 執行 `python3 bible-site/tools/check_all.py`，然後只回報最後一行的總結。不要修改任何檔案。

**收尾（Harness → DS Bot → 貓聽，貼在對話欄）**
> 請處理 `/home/b827262/project/AI/Bible-Master/bible-site/TODO.md` 裡所有沒打勾的項目，網站檔案在同一個資料夾的 `site/` 裡。每修好一項就打勾，最後執行 `python3 /home/b827262/project/AI/Bible-Master/bible-site/tools/verify_text.py`，回報修好幾項、還剩幾項，以及比對結果。經文只能用 `data/mark.json`，不准自己寫經文。

## 預估時間（依今天實測的速度）

| 步驟 | 由誰做 | 預估時間 |
|---|---|---|
| 第 0 步：產生資料 | 腳本 | 1 分鐘內 |
| 第 1 輪：建站 | E500 | 30 到 60 分鐘 |
| 第 2 輪：審核 | A16 | 每輪 10 到 20 分鐘 |
| 第 3 輪：測試 | De1050 | 每個任務 5 到 10 分鐘，其中光讀系統提示就要約 2.5 分鐘 |
| 第 4 步：修正（最多 3 輪） | E500 | 每輪 15 到 30 分鐘 |
| 第 5 步：收尾 | 貓聽 | 視剩下的項目而定 |

整體約 2 到 4 小時。

## 完成標準
- `python3 tools/check_all.py` 結束代碼為 0，三項檢查全部通過（包含 678/678 節相符）。
- 審核檢查表 6 項全部「通過」。
- `TODO.md` 沒有未完成的項目，或剩下的都由貓聽處理並回報了。

## 交接用的檔案（都放在 `Bible-Master/bible-site/`，原文在上一層 `.verify/mark.txt`）
```
PLAN.md          本計劃
data/mark.json   由腳本產生的經文資料
site/            網站（主編）
tools/           build_data.py、verify_text.py、check_all.py（一次跑完所有檢查）
tests/           smoke.js、site_checks.py
REVIEW.md        審核結果（A16）
TEST-REPORT.md   測試結果（check_all.py 每次執行都會加一段）
FAILS.md         最近一次不通過的項目原文（check_all.py 產生，給主編修正用）
TODO.md          未完成的項目（交給貓聽）
CHANGELOG.md     主編每輪修改紀錄
```

## 風險和對策

| 風險 | 對策 |
|---|---|
| 模型捏造經文 | 經文只由腳本產生，並逐字比對 |
| De1050 的上下文不夠用 | 每個任務都很小，一個任務一個新會話 |
| De1050 寫大檔案時，Harness 顯示「stream idle timeout」 | Ollama 在模型寫完整段工具呼叫之前不會傳任何內容，而 De1050 寫 4,000 token 約要 5 分鐘。已把這個 provider 的 `streamIdleTimeoutMs` 調成 30 分鐘。原則上仍只交代 De1050 小任務，不要叫它寫大檔案 |
| A16 審核時看錯 | 檢查表第 2 項用腳本判定，不靠模型判斷 |
| 貓聽讀不到專案資料夾 | 貓聽會話已在 `Bible-Master` 工作區內；仍先請它 `ls` 確認上述絕對路徑讀得到 |
| 貓聽會用到雲端額度 | 只把三台本地機器做不完的項目交給它 |
