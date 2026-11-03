---
role: e500
files: [bible-site/site/music.js, bible-site/site/style.css]
depends: [95-zone-data-build]
checks:
  - python3 bible-site/tests/site_checks.py zonemusic --grep "zonemusic：(site/music\.js|music\.js|style\.css)"
  - python3 bible-site/tests/site_checks.py chapter --grep "連結|外部"
---
前台四區（`index.html`、`search.html`、`card.html`、`blessing.html`）要有共用的背景音樂。這個任務只做兩個檔案：新檔 `bible-site/site/music.js`（整個功能），和在 `bible-site/site/style.css` **檔尾追加**按鈕樣式（不要改既有規則）。四個頁面加 `<script>` 是下一個任務，不要動它們。測試已經寫好：`bible-site/tests/site_checks.py` 的 `zone_static()`、`zone_render()` 與探測頁 `bible-site/tests/zone_probe.html`，請先讀，行為以它們為準。可以參考首頁 `site/home.html` 的音樂寫法（`tryPlay`、`armFirstGesture`、`disarmFirstGesture`、`GESTURES`）——手勢事件的選擇有原因（手機瀏覽器不認 pointerdown／touchstart），照抄它的思路。

介面全部繁體中文；不載入外部資源；不寫死經文；不要用 `autoplay` 屬性；整個檔案是一個 IIFE（`(function () { "use strict"; … }());`），不要外露全域變數。

## music.js 要做的事
1. 自己建立元素並接到 `document.body` 尾端（頁面 HTML 不放這些）：
   - `<button type="button" id="zone-music-btn" aria-pressed="false">`
   - `<audio id="zone-music">`：`loop = true`、`preload = "none"`、`volume = 0.6`。
2. 按鈕文字：暫停中是 `♪ 播放音樂`；播放中是 `<span class="bars" aria-hidden="true"><i></i><i></i><i></i></span> 暫停音樂`（用 innerHTML 設）。`aria-pressed` 永遠等於「audio 正在播放」，用 audio 的 `play`／`pause` 事件同步（和首頁一樣），載入時先 render 一次。
3. 讀設定：`fetch("../data/zone-music.json")`，取 `music`；只接受符合 `/^assets\/[A-Za-z0-9._-]+\.mp3$/i` 的值，其他情況（404、壞 JSON、不合格）一律退回 `"assets/home-music.mp3"`。拿到路徑之後才設 `audio.src`（探測頁會等 src 出現才量測）。
4. 跨頁記憶，全部用 `sessionStorage`，**每一次讀寫都包 try/catch**（隱私模式可能丟例外）：
   - `bm.zone.on`：`"1"` 或 `"0"`，是使用者最後一次的選擇（按按鈕、或第一次觸碰成功開始播放時寫 `"1"`；按暫停寫 `"0"`）。沒有值代表還沒選過。
   - `bm.zone.t`：目前播放秒數（字串）。在 `timeupdate`（最多每秒存一次）、`seeked`、和 `window` 的 `pagehide` 事件存。
   - `bm.zone.src`：目前這首的路徑。
5. 載入流程（拿到路徑之後）：
   - 設 `audio.src = 路徑`。若 `bm.zone.src` 等於這個路徑且 `bm.zone.t` 是正數，就把 `audio.currentTime` 設成那個秒數——**設 src 之後立刻設一次**（try/catch），並且再掛一個一次性的 `loadedmetadata` 監聽，在 `audio.currentTime < 秒數 - 1` 時再設一次。路徑不同（後台換過曲）就從頭播，不套用舊秒數。最後把目前路徑寫進 `bm.zone.src`。
   - 若 `bm.zone.on === "0"`：到此為止，**不播放、也不掛第一次觸碰的監聽**。
   - 否則呼叫 `tryPlay()`（回傳 Promise<boolean>，包 try/catch，`audio.play()` 被拒絕就是 false）。成功就結束；被拒絕就 `armFirstGesture()`。
6. 第一次觸碰：`var GESTURES = ["click", "pointerup", "touchend", "keydown"];`，`armFirstGesture()` 用 `GESTURES.forEach(function (name) { document.addEventListener(name, onFirstGesture); })` 掛上（已掛過就不重複掛）；`disarmFirstGesture()` 全部移除。`onFirstGesture(ev)` 要忽略來自 `#zone-music-btn` 的事件（用 `btn.contains(ev.target)`），其他情況呼叫 `tryPlay()`：成功就寫 `bm.zone.on = "1"` 並 disarm；失敗（例如那次觸碰只是捲動）就保持掛著，等下一次。**絕對不要**掛 `pointerdown`、`touchstart`、`mousedown`。
7. 按鈕 `click`：先 `disarmFirstGesture()`；若 audio 暫停中 → 寫 `bm.zone.on = "1"` 並 `tryPlay()`；否則寫 `"0"` 並 `audio.pause()`。

## style.css 檔尾追加
- `#zone-music-btn`：`position: fixed; right: 12px; bottom: 12px; z-index: 20; min-height: 44px; min-width: 44px; padding: 0 16px; border-radius: 9999px; border: 1px solid rgba(255,255,255,.5); background: rgba(20,19,17,.72); color: #fff; font-size: 14px; cursor: pointer;`（要有 `position: fixed` 與 `min-height: 44px` 這兩個字串）。深色／淺色背景都看得到，所以固定用深底白字。加上 `:focus-visible` 外框（沿用 style.css 既有的 focus 樣式變數／寫法）。
- `.bars` 三根小直條（`#zone-music-btn .bars`、`.bars i`：寬 3px、高 12px、圓角、白色，flex 對齊底部）。
- 動畫只能放在 `@media (prefers-reduced-motion: no-preference) { … }` 裡（`@keyframes` 也放裡面）：三根直條用 `scaleY` 上下跳，`transform-origin: bottom`，延遲 0 / .2s / .4s。這個區塊以外不可以出現任何 `animation:` 宣告。
- 手機 320px 不可以造成水平捲動；按鈕不要擋住頁尾文字太多（固定在右下角就好）。

完成後自己跑 `node --check bible-site/site/music.js`。結果以驗收腳本為準，不要改測試。
