---
pane: w2:p1
role: codex
files:
  - bible-site/REVIEW-round3.md
  - bible-site/screenshots-round3/home-375-light.png
  - bible-site/screenshots-round3/home-375-dark.png
  - bible-site/screenshots-round3/home-1440-light.png
  - bible-site/screenshots-round3/home-1440-dark.png
  - bible-site/screenshots-round3/index-375-light.png
  - bible-site/screenshots-round3/index-375-dark.png
  - bible-site/screenshots-round3/index-1440-light.png
  - bible-site/screenshots-round3/index-1440-dark.png
  - bible-site/screenshots-round3/chapter-375-light.png
  - bible-site/screenshots-round3/chapter-375-dark.png
  - bible-site/screenshots-round3/chapter-1440-light.png
  - bible-site/screenshots-round3/chapter-1440-dark.png
  - bible-site/screenshots-round3/search-375-light.png
  - bible-site/screenshots-round3/search-375-dark.png
  - bible-site/screenshots-round3/search-1440-light.png
  - bible-site/screenshots-round3/search-1440-dark.png
  - bible-site/screenshots-round3/card-375-light.png
  - bible-site/screenshots-round3/card-375-dark.png
  - bible-site/screenshots-round3/card-1440-light.png
  - bible-site/screenshots-round3/card-1440-dark.png
  - bible-site/screenshots-round3/blessing-375-light.png
  - bible-site/screenshots-round3/blessing-375-dark.png
  - bible-site/screenshots-round3/blessing-1440-light.png
  - bible-site/screenshots-round3/blessing-1440-dark.png
  - bible-site/screenshots-round3/devotional-375-light.png
  - bible-site/screenshots-round3/devotional-375-dark.png
  - bible-site/screenshots-round3/devotional-1440-light.png
  - bible-site/screenshots-round3/devotional-1440-dark.png
depends:
  - 128-round3-d-bookmarks
timeout_min: 25
checks:
  - test -s bible-site/REVIEW-round3.md
  - sed -n '3p' bible-site/REVIEW-round3.md | grep -Eq '^\*\*狀態：(PASS|FAIL)\*\*$'
  - grep -q "^\*\*狀態：PASS\*\*$" bible-site/REVIEW-round3.md
  - test -d bible-site/screenshots-round3
  - python3 bible-site/tools/check_all.py
  - python3 bible-site/tests/visual_checks.py
  - python3 bible-site/tests/deploy_checks.py
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不可修改任何網站原始碼、測試或設定檔，只能新增／更新 `bible-site/REVIEW-round3.md` 以及輸出截圖至 `bible-site/screenshots-round3/`。

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-round3.md` 與 `bible-site/design/sample-2026-11.html`，對第三輪改版（A 光束修正、B 愛心與底紋接線＋卡背標題不遮老鷹、C 禱讀標題層級、D 收藏經節）進行唯讀獨立審查並擷取截圖：

1. **執行自動檢查並驗證**：
   - `python3 bible-site/tools/check_all.py`
   - `python3 bible-site/tests/visual_checks.py`
   - `python3 bible-site/tests/deploy_checks.py`
2. **擷取各頁面在 375px 與 1440px、淺色與深色模式下的截圖**：
   - 建立目錄 `bible-site/screenshots-round3/`。
   - 以本機無頭 Chrome 擷取前台頁面（`home`、`index`、`chapter`、`search`、`card`、`blessing`、`devotional`）在 `375px` 與 `1440px`、淺色（light）與深色（dark）下的截圖至 `bible-site/screenshots-round3/<page>-<375|1440>-<light|dark>.png`（共 28 張），並親自檢視確認：
     - `blessing` 抽卡前愛心與底紋、卡背標題與按鈕不遮住老鷹。
     - `devotional` 當天標題字級大於「經文／默想／反思／禱告」段落標題。
     - `index` 與 `chapter` 收藏經節區塊與按鈕呈現正常。
3. **撰寫審查報告 `bible-site/REVIEW-round3.md`**：
   - 第 1 行：`# 第三輪改版（愛心接線、光束修正、禱讀標題、收藏經節）最終審查報告`
   - 第 2 行：空白
   - **第 3 行必須嚴格為 `**狀態：PASS**` 或 `**狀態：FAIL**`**（不加其他字元）。
   - 逐項列出 A、B、C、D 與三項自動檢查、截圖檢視結果。
