# Bible-Master

靜態網站（純 HTML/CSS/JS）：和合本馬可福音，16 章 678 節。章節目錄、逐章閱讀、全文搜尋、經文卡片。
背景與三台地端模型設定見 `HANDOFF.md`，流程與角色分工見 `bible-site/PLAN.md`。

## 鐵則
- 經文只能來自 `bible-site/data/mark.json`，它由 `bible-site/tools/build_data.py` 從 `.verify/mark.txt` 產生。任何模型（包含我）都不憑記憶寫經文，網頁只用 fetch 讀 JSON，原始碼不可寫死經文。
- `.verify/` 必須在 `bible-site/` 的上一層（`build_data.py` 用相對路徑讀 `bible-site/../.verify/mark.txt`）。
- 不載入外部資源；介面全部繁體中文。
- 模型自稱「測試全過」不可信，一律以外部腳本為準。

## 完成標準
`python3 bible-site/tools/check_all.py` 結束碼 0（3/3：經文比對、節數與檔案、網站檢查）。
它會追加 `bible-site/TEST-REPORT.md` 並重寫 `bible-site/FAILS.md`。需要 node 與 `/usr/bin/google-chrome`（headless）。

## 建站任務
給 E500 的 5 份小任務提示在 `bible-site/prompts/01..05-*.md`，一次只做一份，每份做完就跑 `check_all.py`。

## 語言
過程敘述用英文，結案報告用繁體中文；不用日文與簡體中文。程式碼、路徑、指令保持英文。
