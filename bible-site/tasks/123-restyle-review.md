---
pane: w2:p1
role: codex
files:
  - bible-site/REVIEW-restyle.md
  - bible-site/screenshots-restyle/home-375-light.png
  - bible-site/screenshots-restyle/home-375-dark.png
  - bible-site/screenshots-restyle/home-1440-light.png
  - bible-site/screenshots-restyle/home-1440-dark.png
  - bible-site/screenshots-restyle/index-375-light.png
  - bible-site/screenshots-restyle/index-375-dark.png
  - bible-site/screenshots-restyle/index-1440-light.png
  - bible-site/screenshots-restyle/index-1440-dark.png
  - bible-site/screenshots-restyle/chapter-375-light.png
  - bible-site/screenshots-restyle/chapter-375-dark.png
  - bible-site/screenshots-restyle/chapter-1440-light.png
  - bible-site/screenshots-restyle/chapter-1440-dark.png
  - bible-site/screenshots-restyle/search-375-light.png
  - bible-site/screenshots-restyle/search-375-dark.png
  - bible-site/screenshots-restyle/search-1440-light.png
  - bible-site/screenshots-restyle/search-1440-dark.png
  - bible-site/screenshots-restyle/card-375-light.png
  - bible-site/screenshots-restyle/card-375-dark.png
  - bible-site/screenshots-restyle/card-1440-light.png
  - bible-site/screenshots-restyle/card-1440-dark.png
  - bible-site/screenshots-restyle/blessing-375-light.png
  - bible-site/screenshots-restyle/blessing-375-dark.png
  - bible-site/screenshots-restyle/blessing-1440-light.png
  - bible-site/screenshots-restyle/blessing-1440-dark.png
  - bible-site/screenshots-restyle/devotional-375-light.png
  - bible-site/screenshots-restyle/devotional-375-dark.png
  - bible-site/screenshots-restyle/devotional-1440-light.png
  - bible-site/screenshots-restyle/devotional-1440-dark.png
depends:
  - 122-restyle-devotional
timeout_min: 25
checks:
  - test -s bible-site/REVIEW-restyle.md
  - sed -n '3p' bible-site/REVIEW-restyle.md | grep -Eq '^\*\*狀態：(PASS|FAIL)\*\*$'
  - grep -q "^\*\*狀態：PASS\*\*$" bible-site/REVIEW-restyle.md
  - test -d bible-site/screenshots-restyle
  - python3 bible-site/tools/check_all.py
  - python3 bible-site/tests/visual_checks.py
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不可修改任何網站原始碼、測試或設定檔，只能新增／更新 `bible-site/REVIEW-restyle.md` 以及輸出截圖至 `bible-site/screenshots-restyle/`。

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`、`bible-site/logs/herdr-dispatch/change-20261113-hero.md` 與 `bible-site/design/sample-2026-11.html`，對前台 2026-11 新外觀改版進行唯讀獨立審查並擷取截圖：

1. **執行自動檢查並驗證**：
   - `python3 bible-site/tools/check_all.py`
   - `python3 bible-site/tests/visual_checks.py`
   - `python3 bible-site/tests/site_checks.py restyle`
2. **擷取各頁面在 375px 與 1440px、淺色與深色模式下的截圖**：
   - 建立目錄 `bible-site/screenshots-restyle/`。
   - 以本機無頭 Chrome（`google-chrome` / `chromium`）針對前台各頁面（`home.html`、`index.html`、`chapter.html?book=luk&ch=4`、`search.html?q=耶穌`、`card.html?book=luk&ch=1&v=1`、`blessing.html?card=work-01`、`devotional.html`）在 `375px` 與 `1440px`、淺色（light）與深色（dark，`--force-dark-mode` 或 `--blink-settings=preferredColorScheme=0` / `data-theme="dark"`）下截圖，存為 `bible-site/screenshots-restyle/<page>-<375|1440>-<light|dark>.png`（共 28 張，涵蓋全部 7 個頁面 × 2 寬度 × 2 色系）。
3. **撰寫審查報告 `bible-site/REVIEW-restyle.md`**：
   - 第 1 行：`# 前台新外觀改版（2026-11）最終審查報告`
   - 第 2 行：空白
   - **第 3 行必須嚴格為 `**狀態：PASS**` 或 `**狀態：FAIL**`**（不加其他字元）。
   - 報告內容逐項核對：
     1. 配色變數（淺色與深色 `:root`）、字體變數（`--display` 明體、`--body` 黑體）、大圓角（`28px`／`18px`）與文字對比（≥ 4.5:1）。
     2. 底部浮動膠囊導覽列（5 項：首頁、目錄、禱讀、抽卡、搜尋；`aria-current="page"` 與粗體標示目前頁；觸控區 ≥ 44×44；不遮住音樂按鈕與頁面底部內容）。
     3. 首頁主視覺（照片與經文分開不重疊、320/375/768/1440px 下人物完整可見；經文文字顏色 `#fdf2da` 與照片灑落的光同色並有暖光照射；便當格入口與扇形卡片順序 B、A、B 且最上層為 B）。
     4. 金色飛鷹正式圖（`eagle-A.jpg`、`eagle-B.jpg` 1792×2400、≤ 3MB、`ASSETS-LICENSE.md` 登記、共用層提供路徑、頁面不重複寫死）。
     5. 微互動三種狀態（`busy`／`ok`／`fix` 各有不同圖示與中文訊息、`role="status"`／`aria-live="polite"`、空白與無結果搜尋設 `aria-invalid="true"` 與 `aria-describedby`）。
     6. 動態與無障礙（`prefers-reduced-motion: reduce` 關閉動畫、鍵盤焦點可見、320/375/768/1440 無水平溢出）。
     7. 截圖清單（列出 `bible-site/screenshots-restyle/` 內所有截圖檔名與檢查結果）。
