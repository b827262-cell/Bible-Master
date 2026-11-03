---
role: e500
files: [bible-site/site/blessing.html]
checks:
  - python3 bible-site/tests/site_checks.py blessing
  - python3 bible-site/tests/visual_checks.py --grep blessing
---
新增一個頁面 bible-site/site/blessing.html（「抽經文卡」）。只建立這一個檔案，不改其他檔案。先讀 bible-site/site/card.html（抽卡頁的寫法、canvas 畫卡與下載）、bible-site/site/app.js（Bible.load、Bible.ref、Bible.nav、Bible.fail、Bible.param）、bible-site/site/style.css（用既有 CSS 變數 --bg --surface --fg --muted --border --accent --accent-fg --focus，淺色與深色都要可讀）、bible-site/data/blessing.json（資料格式）、bible-site/tests/blessing_probe.html（測試會用到的元素契約）。

## 功能
網站參考教會的「抽卡」：先看到封面，按一下就抽出一張卡；卡上有主題標題、一節經文、出處、一段祝福短文與署名。

資料：頁面用 fetch 讀 "../data/blessing.json"（{themes:[{id,title,default}], cards:[{id,theme,book,ch,v,message}]}）。每張卡的經文一律用 Bible.load(card.book) 讀 ../data/<book>.json 後，依 ch、v 找到那一節（章用 Number(chapter.ch)===Number(card.ch)，節用 Number(verse.v)===Number(card.v)）。**頁面原始碼裡不可寫任何經文、短文或出處字串**，全部來自 JSON；自動檢查會掃描。

## 元素契約（測試依此找元素，ID 與屬性必須完全一致）
- `<nav id="nav"></nav>`，script 結尾呼叫 `Bible.nav("blessing.html")`。
- `<h1>抽經文卡</h1>`。
- `<div id="theme-tabs">`：每個主題一個 `<button type="button" data-theme="<id>" aria-pressed="true|false">主題名稱</button>`，主題名稱用 blessing.json 的 theme.title；目前主題 aria-pressed="true"，其餘 "false"。順序同 blessing.json。預設主題是 default:true 的那個（work）。
- 封面 `<section id="cover">`：一個大標「天父關心你」、一個裝飾用的 ♥（aria-hidden="true"，顏色 var(--accent)）、按鈕 `<button type="button" id="draw-btn">點選領受祝福</button>`。
- 卡片 `<article id="blessing-card" hidden>`，抽到卡才顯示（移除 hidden）。裡面依序：
  `<h2 class="card-title">`（theme.title）、`<p class="card-verse">`（經文原文，textContent = verse.text，不改字）、`<p class="card-ref">`（Bible.ref(card.book, card.ch, verse) + "（和合本）"）、`<p class="card-message">`（card.message）、`<p class="card-sign">愛你的天父</p>`。
  卡片元素上要有屬性 data-id（卡片 id）、data-theme（theme id）、data-draws（整數，每顯示一張卡就加 1，從 1 開始）。**這三個屬性要在經文、出處、短文、canvas 都畫好之後最後才設定**（測試看到 data-draws 變了就會立刻讀內容）。
- 按鈕（卡片出現後顯示）：`<button type="button" id="again-btn">再抽一次</button>`、`<button type="button" id="download-btn">下載圖片</button>`、`<button type="button" id="share-btn">分享</button>`，以及連結 `<a id="read-link">`（文字「閱讀這一章」，href 是 chapter.html?book=<book>&ch=<ch>#v<v>）。`<p id="share-msg" role="status">` 顯示分享結果。
- `<canvas id="card-canvas">`：每次顯示卡時重畫，並設定屬性 data-ref 等於 .card-ref 的文字。畫法沿用 card.html 的 wrapText：寬 600px、pad 40；背景用淺暖色 #fff7ec；依序畫標題（粗體 24px、顏色 #7a4a1f）、經文（26px、#1a1a1a）、出處（20px、#666666）、短文（22px、#333333）、署名「愛你的天父」靠右（20px、#7a4a1f）；高度依內容計算；canvas 的 width/height 屬性是實際像素，CSS 只設 max-width:100%; height:auto（和 card.html 一樣）。canvas 預覽可放在卡片下方，並用 aria-label 或隱藏方式避免與卡片內容重複朗讀（canvas 加 aria-hidden="true"）。

## 行為
1. 載入：讀 blessing.json；網址參數 `?theme=<id>` 若是有效主題就設為目前主題，否則用預設主題；`?card=<id>` 若是有效卡片 id，就**不用按鍵直接顯示那張卡**（隱藏封面，目前主題改成那張卡的主題）；無效就當作沒有。
2. 按 #draw-btn：隱藏封面，從目前主題的卡片隨機抽一張顯示。
3. 按 #again-btn：從目前主題再抽一張，**不得連續抽到與目前顯示相同的那一張**（該主題只有一張時才例外）。
4. 按主題標籤：只切換目前主題（更新 aria-pressed）；若卡片已顯示，就立刻在新主題抽一張新卡；若還在封面，只切換主題、不抽卡。
5. 下載：沿用 card.html 的 canvas.toDataURL("image/png") 做法，檔名 "blessing-<card id>.png"。
6. 分享：先試 navigator.share（標題「抽經文卡」、url 為目前頁面網址去掉查詢字串後加 `?card=<id>`）；沒有 navigator.share 或失敗，就用 navigator.clipboard.writeText 複製同一個網址並在 #share-msg 顯示「已複製連結」；連 clipboard 都不能用，就在 #share-msg 顯示「請手動複製：<網址>」。所有 async 呼叫都要 try/catch，不可丟出未處理錯誤。
7. 讀取失敗（fetch 失敗、找不到經文）用 Bible.fail 顯示錯誤，不要讓畫面空白。
8. 翻牌動畫：卡片出現時加 CSS class 做淡入加輕微位移即可，**動畫只放在 `@media (prefers-reduced-motion: no-preference)` 裡**；不能因動畫延遲而讓 data-draws 或內容晚於畫面更新。

## 其他限制
- 純 HTML/CSS/JavaScript，不載入任何外部資源（不寫 http:// 或 https:// 字串，不用外部字型或圖片）。
- 介面全部繁體中文；頁尾 `<footer>四福音 · 和合本</footer>`，不可寫單一書卷名。
- 所有按鈕與標籤沿用 style.css 的樣式，觸控高度至少 44px；手機寬度 320px 不可出現水平捲軸；主題標籤可換行（flex-wrap）。
- 所有 button 都要有可讀文字；焦點外框沿用 style.css（不要寫 outline:none）。
- 為避免與其他頁共用 id 衝突，其他頁的 id 不必理會；本頁 id 以上列為準。

驗收（腳本自動跑，不信你自己的說法）：site_checks.py blessing 與 visual_checks.py --grep blessing 全部通過。改完只回報建立了哪個檔案。
