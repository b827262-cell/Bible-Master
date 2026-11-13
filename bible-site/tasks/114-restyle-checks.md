---
pane: w2:p5
role: qwen
files:
  - bible-site/ASSETS-LICENSE.md
  - bible-site/tests/site_checks.py
  - bible-site/tests/visual_checks.py
  - bible-site/tests/visual_probe.html
  - bible-site/tests/home_probe.html
  - bible-site/tests/zone_probe.html
  - bible-site/tests/blessing_probe.html
timeout_min: 30
checks:
  - python3 -m py_compile bible-site/tests/site_checks.py bible-site/tests/visual_checks.py
  - grep -q "site/assets/eagle-A.jpg" bible-site/ASSETS-LICENSE.md
  - grep -q "site/assets/eagle-B.jpg" bible-site/ASSETS-LICENSE.md
  - python3 bible-site/tests/site_checks.py --grep "eagle-A\.jpg"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案（`bible-site/ASSETS-LICENSE.md` 與 `bible-site/tests/` 下的檢查與探測檔）。**本任務是改版第一步「先寫客觀檢查」，請勿修改 `bible-site/site/` 下的任何頁面**（因此寫完後針對舊頁面的新外觀檢查會失敗是預期的，但 `py_compile` 與下方 `checks` 必須通過）。

請先完整讀取：
- `bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`
- `bible-site/logs/herdr-dispatch/change-20261113-hero.md`
- `bible-site/design/sample-2026-11.html`（唯一的視覺依據）

並完成以下工作：

### 1. 在 `bible-site/ASSETS-LICENSE.md` 登記兩張金色飛鷹高解析度正式圖
目前 `bible-site/site/assets/eagle-A.jpg`（1792×2400，卡背徽章風）與 `bible-site/site/assets/eagle-B.jpg`（1792×2400，水彩風）已由 AGY（Google Imagen 3）產出並放入 `site/assets/`。請在 `bible-site/ASSETS-LICENSE.md` 表格補上這兩行（註明用途：A 為抽經文卡卡背與首頁入口方塊中間卡；B 為經文卡片頁卡面裝飾與首頁入口方塊外側及最上層卡；來源：由 AGY 使用 Google Imagen 3 生成，2026-11-13；備註：1792×2400，圖內已有金框）。

### 2. 更新 `bible-site/tests/site_checks.py` 與探測檔（`home_probe.html`、`zone_probe.html`、`blessing_probe.html`）
請在保留既有功能檢查（四卷切換、`#v` 錨點捲動、搜尋筆數、`card.html` 三下拉與 `data-ref`、`blessing.html` 37 張卡與 `blessart`、`zonemusic` 跨頁續播、`devotional` 41 條檢查）的前提下，同步更新舊版外觀假設並加入 2026-11 改版檢查：

1. **金色飛鷹圖檔靜態檢查**（檢查名稱請包含 `eagle-A.jpg` 以便 `checks` 單獨驗證）：
   - 檢查 `site/assets/eagle-A.jpg` 與 `site/assets/eagle-B.jpg` 存在、尺寸為 `1792×2400`（或長邊 ≥ 1700 且比例 3:4）、檔案大小 ≤ 3 MB，且已在 `ASSETS-LICENSE.md` 登記。
   - 檢查圖檔路徑由共用設定（如 `app.js` 或 `style.css` 變數）提供，不在多個頁面重複寫死；注意：`blessart_static` 原本檢查 `blessing.html` 原始碼不出現 `assets/*.jpg`，請確保抽卡前卡背圖透過 `style.css` 或 `app.js` 提供，或者調整該檢查使收藏卡主題圖仍只來自 `blessing-art.json`。
2. **配色變數與 `blessstyle` 更新**：
   - 將 `PALETTE` 更新為 `sample-2026-11.html` 的 `:root` 與深色變數：
     - 淺色：`--paper: #f3f6f2`、`--surface: #ffffff`、`--ink: #10231f`、`--muted: #586a64`、`--river: #0e6b5b`、`--river-soft: #dcefe9`、`--lamp: #c98a1b`、`--mat: #c98a1b`、`--mrk: #d9583b`、`--luk: #0e6b5b`、`--jhn: #3d55c4`。
     - 深色（`@media (prefers-color-scheme: dark)` 與 `:root[data-theme="dark"]`）：`--paper: #0a1412`、`--surface: #121f1c`、`--ink: #e9f1ee`、`--muted: #94a8a1`、`--river: #55d3b7`、`--river-soft: #16302a`、`--lamp: #f0bf5c`、`--mat: #f0bf5c`、`--mrk: #ff8a6b`、`--luk: #55d3b7`、`--jhn: #8fa2ff`。
   - `blessstyle` 中原本針對舊版棕色樣式（例如左側 3px 豎線或舊版按鈕背景）的檢查，請對齊新樣本風格（明體經文、膠囊按鈕、`#cover` 顯示 `eagle-A.jpg` 卡背圖、2×2 主題按鈕、署名 `愛你的天父` 等）。
3. **底部浮動膠囊導覽列（五項）**：
   - 將 `home_render`、`zone_render`、`devotional_render`、`home_probe.html`、`zone_probe.html`、`DEVOTIONAL_PROBE` 中原本檢查「導覽列有四項（目錄、搜尋、經文卡片、抽經文卡）」全部更新為**五項**：`["首頁", "目錄", "禱讀", "抽卡", "搜尋"]`（對應 `["home.html", "index.html", "devotional.html", "blessing.html", "search.html"]`），且**每個前台頁面（含 `home.html`、`chapter.html`、`card.html`）的 `navCount == 5`、`navActive == 1`**（恰有一項標成目前頁，具 `.active` 或 `aria-current="page"`）。
   - `blessnav` 改為檢查導覽列有指向 `blessing.html` 的「抽卡」（或含「抽」字）連結。
4. **首頁（`home.html`）新設計與「經文不擋人物、經文與光同色、扇形卡 B-A-B」檢查**（更新 `home_probe.html`、`home_static`、`home_render`）：
   - **主視覺照片與經文分離不重疊**：在 `320`、`375`、`768`、`1440` 四種寬度下，量測主視覺照片（`.hero-pic img` 或 `.home-hero img`）與經文內容區（`.hero-body` 或 `.home-verse`）的 `getBoundingClientRect()`，確認**兩個矩形完全不重疊**（寬螢幕左圖右文、窄螢幕上圖下文，沒有任何文字或按鈕蓋在照片人物上）。
   - **經文與光同色（`--sunlight: #fdf2da`）**：檢查首頁今日經文（`blockquote` / `.home-verse`）computed color 為 `rgb(253, 242, 218)`（`#fdf2da`）、有 `text-shadow`（非 `none`），且經文區塊（`.hero-body`）帶有暖光 `radial-gradient` 背景，文字對比 ≥ 4.5:1。
   - **便當格入口與扇形紙卡 B、A、B**：
     - 首頁有四卷入口方塊（`.book`）、每日禱讀入口（`.daily`，連往 `devotional.html`）、抽經文卡入口（`.draw`，連往 `blessing.html`）、搜尋表單（`.find`）。
     - 抽經文卡入口方塊內有三張扇形卡片（`.fan i`），三張的 computed `backgroundImage` 依序為 `eagle-B.jpg`、`eagle-A.jpg`、`eagle-B.jpg`（B、A、B，最上層第 3 張是 B），淺色與深色模式下皆有圖、不是空白色塊。
5. **微互動（Micro-interactions）檢查**（可在 `site_checks.py` 新增 `restyle` 或整合至各頁面群組）：
   - 檢查搜尋（`home.html`、`index.html`、`search.html`）：空白送出時輸入框設 `aria-invalid="true"`、有 `aria-describedby` 指到 `role="status"`（或 `aria-live="polite"`）的狀態元素，且狀態元素 `data-state="fix"` 並顯示「怎麼修」的中文提示；查無結果時同樣設 `aria-invalid="true"` 與 `data-state="fix"`；找到結果時 `data-state="ok"`；處理中時按鈕或狀態列有 `aria-busy="true"` 或 `data-state="busy"`。
   - 檢查三種狀態（`busy`、`ok`、`fix`）在 `style.css` 中具有不同圖示／形狀（如轉圈、打勾 `✓`、驚嘆號 `!`）且必有文字，不單靠顏色傳達（灰階下仍可分辨）。
   - 檢查音樂按鈕（`#music-btn`、`#zone-music-btn`）、經文卡片頁（`card.html`）、抽經文卡頁（`blessing.html`）、禱讀頁（`devotional.html`）皆有 `role="status"` 或 `aria-live` 的狀態回饋區。

### 3. 更新 `bible-site/tests/visual_checks.py` 與 `bible-site/tests/visual_probe.html`
- 將 `devotional.html` 加入 `PAGES` 清單，讓所有前台頁面都納入視覺與無障礙檢查。
- **p0（CSS 規則、焦點外框、深淺色對比 ≥ 4.5:1、表單可存取名稱）**：
  - 擴充 `TEXTS` 選擇器以涵蓋新樣本元件（`.hero blockquote`, `.tile`, `.book`, `.daily`, `.draw`, `.dock a`, `#nav a`, `.status`, `.dev p`, `.dev .pray`, `.verses li` 等），注意對漸層背景元素（如 `.hero`、`.book`、`.draw`）計算對比時，若 `backgroundColor` 為透明但有深色／淺色背景圖或漸層，請在 `visual_probe.html` 的 `background()` 妥善處理（例如 `.hero` 與 `.book` 的文字在深色漸層底上，可取其宣告底色或 fallback 底色計算，避免誤把透明 `backgroundColor` 當成白底導致假警報）。
- **p1（觸控目標 ≥ 44×44、底部導覽列五項與不遮擋、經文對齊）**：
  - 檢查每個頁面的底部導覽列（`#nav` / `.dock`）為 `position: fixed`，恰好 5 個連結，每項寬高 ≥ 44×44，恰有一項標為目前頁（`aria-current="page"` 或 `.active`，且 `fontWeight >= 600`、背景與一般項不同）。
  - 檢查底部導覽列不與 `#zone-music-btn` 重疊，且頁面 `body`（或主容器）底部留白充足（例如 `padding-bottom >= 100px` 或捲動到底時導覽列不遮住最後一段內容）。
  - 移除舊版死板的 `h1` 必須剛好 22px／26px 的限制（改為檢查 `h1` 使用明體 `--display` 且字級合理 `>= 20px`）。
- **p2（`card.html` 畫布與飛鷹卡面、四種寬度 320/375/768/1440 無水平溢出、首頁照片與經文不重疊、`prefers-reduced-motion`）**：
  - 檢查 `home.html` 在 320/375/768/1440px 下，主視覺照片（`.hero-pic img` / `.home-hero img`）與經文區（`.hero-body` / `.home-verse`）矩形不重疊、照片高 ≥ 200px、經文用明體且顏色為 `#fdf2da`。
  - 檢查 `@media (prefers-reduced-motion: reduce)` 規則存在並關閉動畫。
