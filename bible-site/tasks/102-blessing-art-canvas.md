---
role: fe
files: [bible-site/site/blessing.html]
depends: [101-blessing-art-view]
checks:
  - python3 bible-site/tests/site_checks.py blessart --grep "blessart"
  - python3 bible-site/tests/site_checks.py blessing blessnav blessindex blessstyle
---
只改 `bible-site/site/blessing.html`。上一個任務已經讓 `drawCanvas(title, verseText, refText, message, artImg)` 收到載入成功的主題圖（`artImg` 是 `Image` 物件，沒有圖時是 `null`）。這個任務讓「下載圖片」的 canvas 圖卡把主題圖合成進去。測試是 `tests/site_checks.py` 的 `blessart_render()`（含 canvas 紅／藍像素、`canvasH` 的檢查），請先讀。

## 要做的事
- `artImg` 為 `null`：**完全維持現在的畫法**（既有的 `blessstyle` 檢查要求：寬 600、底色 `#fbf7ee`、真的畫了字）。
- `artImg` 有值：在卡片最上方（`pad` 之下、標題之上）畫主題圖，寬度＝`maxWidth`（即 `W - pad * 2`），高度依圖片原比例（`maxWidth * naturalHeight / naturalWidth`，四捨五入），圖與標題之間留 `gap`。計算總高 `H` 時要加上這一塊（圖高 + `gap`），其餘文字的位置整體往下移。圖片用 `ctx.drawImage(artImg, pad, y, maxWidth, 圖高)`；圖片是同源檔案，不會污染 canvas，所以 `toDataURL` 照常能用。
- `canvas.setAttribute("data-ref", …)` 等既有行為不變；不要新增全域變數；不要改「下載圖片」`handleDownload` 的檔名規則（`blessing-<卡id>.png`）。
- 圖框的圓角／邊框在 canvas 裡不必做。

完成後跑 `node --check`（把 `<script>` 抽出來）。結果以驗收腳本為準，不要改測試。
