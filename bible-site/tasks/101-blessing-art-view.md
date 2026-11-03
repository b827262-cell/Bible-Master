---
role: fe
files: [bible-site/site/blessing.html]
depends: [97-zone-wire-blessing, 100-art-data-build]
checks:
  - python3 bible-site/tests/site_checks.py blessart --grep "blessart：blessing.html|blessart.*(card-art|版次徽章|data-art|下載經文圖|原圖位元組|純文字|圖真的載入|JavaScript|切換到有圖|320px)"
  - python3 bible-site/tests/site_checks.py blessing blessnav blessindex blessstyle
---
只改 `bible-site/site/blessing.html`（樣式寫在它自己的 `<style>` 裡，不要動 `style.css`，也不要動 `<script src="music.js">` 那一行）。「抽經文卡」要做成「球員收藏卡」：每個主題（work／peace／rest／faith）可以有一張預先生成的主題圖，該主題底下所有卡共用；沒有圖的主題維持現在的純文字卡。測試 `tests/site_checks.py` 的 `blessart_*`（以及 `tests/blessing_probe.html` 的 `art` 欄位）已經寫好，請先讀，行為以它們為準。**37 張卡的經文、短文不可改，`data/blessing.json` 不要動；頁面原始碼不可寫死任何圖檔路徑或經文**（圖片路徑只來自設定檔）。介面全部繁體中文，不載入外部資源。

## 設定檔
頁面載入時 `fetch("../data/blessing-art.json")`，格式 `{"<主題id>": {"image": "assets/…", "alt": "…", "edition": "2026 年 11 月版"}}`。失敗（404、壞 JSON、不是物件）一律當作 `{}`，頁面照常運作。這個 fetch 的 Promise 要在顯示卡片之前就緒（顯示卡片時等它）。

## HTML
- 在 `<article id="blessing-card">` 裡、`<h2 class="card-title">` 之前加：
  `<figure class="card-art" hidden><img alt=""><figcaption class="card-edition"></figcaption></figure>`
- 在 `.card-actions` 裡、`#download-btn` 之前加：
  `<a id="art-download" class="btn-secondary" hidden>下載經文圖</a>`（不是 `<button>`，樣式跟 `#download-btn` 一樣的次要按鈕；既有的「實心 accent 按鈕只有兩顆」檢查不能壞）。

## 顯示邏輯（改 `showCard`）
顯示一張卡時，同時等經文與設定檔，再看 `artMap[主題id]`：
- 有設定 → 用 `new Image()` 預載 `entry.image`；**載入成功**才算有圖。有圖：`.card-art` 取消 `hidden`，`<img>` 的 `src`＝`entry.image`、`alt`＝`entry.alt`；`.card-edition` 的文字＝`entry.edition`（空字串就把 figcaption 設成 `hidden`）；`#art-download` 取消 `hidden`，`href`＝`entry.image`，`download` 屬性＝`"blessing-" + 主題id + (版次去掉所有非英數字元後，非空才加 "-" + 它) + 圖檔副檔名（含點，例如 `.png`）`；`#blessing-card` 的 `data-art`＝`entry.image`。
- 沒有設定、或圖載入失敗 → `.card-art` 與 `#art-download` 設 `hidden`，`data-art` 設成空字串，完全回到現在的純文字卡。
- 換主題（點主題按鈕）會重新抽一張卡，所以會自動換圖，不需要另外處理。
- 把載入成功的 `Image` 物件傳給 `drawCanvas`（下一個任務會用它合成；這個任務先讓 `drawCanvas` 多收一個參數 `artImg` 但還不畫也可以，但**簽名要是 `drawCanvas(title, verseText, refText, message, artImg)`**）。

## CSS（寫在頁面的 `<style>`）
收藏卡畫框：`.card-art { margin: 0 0 14px; position: relative; }`，`.card-art img { display:block; width:100%; height:auto; border-radius:10px; }`（直式 5:7 的圖，寬度不可超出卡片；320px 不可水平溢出），`.card-edition` 是疊在圖左下角的小徽章（圓角 9999px、半透明深底 `rgba(20,19,17,.7)`、白字、13px、`position:absolute; left:8px; bottom:8px`）。圖框外加一圈與卡片一致的細邊框／陰影讓它有「收藏卡」質感，顏色用既有 CSS 變數（`--border`、`--accent`、`--card-bg`）。所有 `animation`／`transition` 只能寫在 `@media (prefers-reduced-motion: no-preference)` 裡。

完成後把頁面裡的 `<script>` 抽出來跑 `node --check` 確認沒有語法錯誤。結果以驗收腳本為準，不要改測試。
