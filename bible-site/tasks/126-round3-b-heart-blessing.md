---
pane: w2:p5
role: qwen
files:
  - bible-site/ASSETS-LICENSE.md
  - bible-site/site/assets/heart-idle-light.gif
  - bible-site/site/assets/heart-idle-dark.gif
  - bible-site/site/assets/heart-surprise-light.gif
  - bible-site/site/assets/heart-surprise-dark.gif
  - bible-site/site/assets/heart-still.png
  - bible-site/site/assets/pattern-light.png
  - bible-site/site/assets/pattern-dark.png
  - bible-site/site/app.js
  - bible-site/site/style.css
  - bible-site/site/blessing.html
depends:
  - 125-round3-checks
timeout_min: 25
checks:
  - python3 bible-site/tests/site_checks.py blessing blessstyle blessart heart
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "blessing\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案。
**重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 的 bash 指令（會觸發 Qwen CLI 審批確認視窗而導致 pane 進入 blocked 狀態），只執行單行指令即可。**

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-round3.md` 的「B. 愛心與背景圖案接到正式抽卡頁」與 `bible-site/design/sample-2026-11.html` 的「樣本六」，完成正式抽卡頁愛心與底紋接線：

1. **複製 v3 素材至 `bible-site/site/assets/` 並登記 `bible-site/ASSETS-LICENSE.md`**：
   - 將 `output/imagegen/heart-20261113/` 下的 `heart-idle-light.gif`、`heart-idle-dark.gif`、`heart-surprise-light.gif`、`heart-surprise-dark.gif`、`heart-still.png`、`pattern-light.png`、`pattern-dark.png` 共 7 個檔案複製到 `bible-site/site/assets/`。
   - 在 `bible-site/ASSETS-LICENSE.md` 登記這 7 個檔案（來源必須包含 `OpenAI image_gen` 與 `Pillow` 字樣：Codex 以 OpenAI `image_gen` 產生母圖＋Python Pillow 輸出 GIF／PNG）。
   - 在 `bible-site/site/app.js`（或 `style.css`）定義共用路徑常數（例如 `Bible.HEART_ART = { idle: { light: "assets/heart-idle-light.gif", dark: "assets/heart-idle-dark.gif" }, surprise: { light: "assets/heart-surprise-light.gif", dark: "assets/heart-surprise-dark.gif" }, still: "assets/heart-still.png", patternLight: "assets/pattern-light.png", patternDark: "assets/pattern-dark.png" }`），確保 `build_public.py` 的 `referenced_assets()` 能掃描到全部 7 個 `assets/...` 完整字串。
2. **`blessing.html` 與 `style.css` 實作愛心待機、1.6 秒小驚喜、底紋與卡背排版修正**：
   - **抽卡頁背景底紋（必設在 `body` 上）**：
     - 探測器 `blessing_probe.html` 與 `home_probe.html` 會依序檢查 `[d.body, d.querySelector(".bless-stage"), d.querySelector("main")]` 第一個 `backgroundImage !== "none"` 的元素（因為 `style.css` 的 `body` 原本有 `radial-gradient`，所以一定會抓到 `d.body`）。
     - 因此請在 `blessing.html` 的 `<body class="bless-page">`（或 `blessing.html` 內嵌 `<style>` 針對 `body`）設定：
       - 淺色：`background-image: url("assets/pattern-light.png"); background-repeat: repeat; background-size: 360px 360px;`
       - 深色（`@media (prefers-color-scheme: dark)` 與 `:root[data-theme="dark"]`）：`background-image: url("assets/pattern-dark.png"); background-repeat: repeat; background-size: 360px 360px;`
   - **愛心舞台與底色一致（`blessing.html` 原始碼必須直接出現 `#f3f6f2` 與 `#0a1412`）**：
     - `site_checks.py` 的 `heart_source()` 會直接檢查 `blessing.html` 原始碼內含 `#f3f6f2`、`#0a1412`、`點愛心領受今天的祝福`、`正在為你抽一張卡`、`aria-busy`。
     - 愛心所在區塊 `.heart-stage` 底色必須在淺色為 `#f3f6f2`（`rgb(243, 246, 242)`）、深色為 `#0a1412`（`rgb(10, 20, 18)`），且 `background-image: none`。
     - 內含 `<div class="heart-stage"><button type="button" class="heart-btn" id="heart-btn" aria-busy="false" aria-describedby="heart-status"><img id="heart-img" src="assets/heart-idle-light.gif" alt="金框綠色愛心，點一下領受祝福"></button><p class="status" id="heart-status" role="status" aria-live="polite" data-state="idle">點愛心領受今天的祝福</p></div>`。
     - 注意：`#heart-btn` 不要加 `.pill` class，且背景色透明或 `var(--paper)`（不可為 `var(--river)`，以免影響 `blessstyle` 對膠囊按鈕與實心主色按鈕數量的檢查）。
   - **微互動與 `prefers-reduced-motion: reduce`**：
     - 待機時：若 `matchMedia("(prefers-reduced-motion: reduce)").matches` 為真，將 `#heart-img` 的 `src` 設為 `assets/heart-still.png`；否則依當前深淺色設為 `assets/heart-idle-light.gif` 或 `assets/heart-idle-dark.gif`（並監聽 `prefers-color-scheme` 與 `prefers-reduced-motion` 變化）。
     - 點擊 `#heart-btn` 時：
       - 若 `#heart-btn.getAttribute("aria-busy") === "true"`，直接 return 不重複觸發。
       - **同步立即設定**：`heartBtn.setAttribute("aria-busy", "true")`、`heartStatus.setAttribute("data-state", "busy")`、`heartStatus.textContent = "正在為你抽一張卡…"`（探測器會在 `el.click()` 同步返回當下立即讀取 `aria-busy` 與 `#heart-status` 的 `data-state="busy"` 及文字！此時 `#blessing-card` 的 `data-draws` 還不能改變）。
       - 若未開啟 `prefers-reduced-motion: reduce`，將 `#heart-img` 的 `src` 換成對應淺／深色的 `assets/heart-surprise-light.gif` 或 `assets/heart-surprise-dark.gif`，用 `setTimeout` 等待 `1600ms`（若開啟 `prefers-reduced-motion: reduce` 則不播動圖，用 `setTimeout` 等待 `150ms`），時間到後才執行 `markDrawn(); showCard(pickCard(currentTheme));`，並將 `heartBtn.setAttribute("aria-busy", "false")`、`heartStatus.setAttribute("data-state", "ok")`、`heartStatus.textContent = "已為你抽出一張祝福卡"`。
       - 注意：原有的 `#draw-btn` 點擊仍保持立即抽卡（或同樣在 3.5 秒內完成抽卡並更新 `#blessing-card[data-draws]`），確保既有 `blessing`／`blessstyle`／`blessart` 檢查 100% 通過。
   - **卡背標題與按鈕不遮住老鷹**：
     - 探測器檢查 `.cover-title` 與 `#draw-btn` 的 `getBoundingClientRect().top` 必須 `>= cr.top + cr.height * 0.65`（在 `.cover-card` 下半部 65% 以下）或完全在 `.cover-card` 矩形外部。
     - 最乾淨的做法：把 `.cover-title`（「天父關心你」）與 `#draw-btn`（「點選領受祝福」）移到 `.cover-card` 元素外面的下方（仍在 `#cover` 容器內），讓 `.cover-card` 完整呈現 `eagle-A.jpg` 金色飛鷹，完全不被文字或按鈕壓住！
