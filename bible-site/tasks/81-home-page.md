---
role: e500
files: [bible-site/site/home.html, bible-site/index.html, bible-site/site/index.html]
checks:
  - python3 bible-site/tests/site_checks.py home
  - python3 bible-site/tests/visual_checks.py p2 --grep home
  - python3 bible-site/tests/visual_checks.py p0 p1 --grep home
---
新增入口首頁 `bible-site/site/home.html`，並改兩個入口。素材已放好：`site/assets/jordan.jpg`（約但河中的人仰望天光）、`site/assets/home-music.mp3`。
頁面要顯示路加福音 4:27，但**經文只能用 `Bible.load("luk")` 從 JSON 讀**，原始碼裡不可以出現經文文字。不載入外部資源，介面全部繁體中文。
請先看 `site/blessing.html` 與 `site/style.css`，沿用它們的 `<head>`、`<nav id="nav">`、`Bible.nav()`、`Bible.fail()`、CSS 變數（`--card-bg`、`--accent`、`--accent-soft`…）和 `.btn-secondary`。

## 一、其他兩個檔案
- `bible-site/index.html`（根目錄轉址）：三處（`<meta http-equiv="refresh">`、`location.replace`、備援 `<a>`）都改成 `site/home.html`，標題文字改成「…前往入口首頁」。不可再出現 `site/index.html`。
- `bible-site/site/index.html`：`<main>` 裡，`<h1>` 上方加一行 `<p><a href="home.html">← 回首頁</a></p>`。其餘不動。

## 二、`site/home.html` 結構（class 與 id 要照寫，檢查靠它們）
```
<nav id="nav"></nav>
<main class="container home">
  <section class="home-hero">
    <img src="assets/jordan.jpg" alt="（繁體中文描述：一位男子站在約但河水中，仰望從雲層灑下的光）">
    <div class="hero-kicker" aria-hidden="true">四福音（和合本）</div>
    <button type="button" id="music-btn" aria-pressed="false">…</button>
  </section>
  <section class="home-card">
    <h1>四福音</h1>
    <blockquote class="home-verse"></blockquote>
    <div class="home-ref-row"><p class="home-ref"></p><a href="chapter.html?book=luk&ch=4#v27">閱讀本章 →</a></div>
  </section>
  <div class="home-actions">
    <a class="btn …" href="index.html">進入四福音 →</a>
    <a class="btn-secondary …" href="blessing.html">抽一張經文卡 →</a>
  </div>
  <audio id="home-music" src="assets/home-music.mp3" loop preload="none"></audio>
</main>
```
`.home-ref` 的文字是 `路加福音 4:27（和合本）`（用 `Bible.ref` 或 `Bible.bookName`，不要手打書名以外的經文）。`<h1>` 在卡片裡，字級沿用 style.css 對 h1 的規則，不要另外覆蓋。
兩顆入口連結要像按鈕：實心主色那顆比照現有 `button` 的外觀（背景 `--accent`、字 `--accent-fg`），都至少 48px 高、全寬、間距 10px；寬度 ≥ 768px 時並排。

## 三、視覺（全部寫在 home.html 的 `<style>`）
1. **英雄圖**：`.home-hero { position: relative; overflow: hidden; }`，圖 `width:100%; height: 68vw; min-height: 240px; max-height: 520px; object-fit: cover; object-position: 50% 35%; display:block`。圖上蓋由下往上的漸層（`::after`，透明 → `rgba(20,19,17,.55)`），`pointer-events:none`。深色模式再加一層 `rgba(0,0,0,.12)`。
2. **小標 `.hero-kicker`**：絕對定位在圖左下，白色字、`text-shadow: 0 1px 6px rgba(0,0,0,.6)`、字距 .12em、不要用 `<p>` 或 `<h*>`。
3. **音樂按鈕 `#music-btn`**：絕對定位在圖右下，圓角 9999px、背景 `rgba(20,19,17,.55)`、白字、`1px solid rgba(255,255,255,.5)`、最小高度 44px，不要套 `button` 預設的實心金色。
   - 暫停狀態（aria-pressed=false）文字：`♪ 播放音樂`。
   - 播放狀態（aria-pressed=true）文字：`<span class="bars" aria-hidden="true"><i></i><i></i><i></i></span> 暫停音樂`（可以用 JS 設 innerHTML，文字要含「暫停音樂」）。
   - `.bars i` 三根小直條（寬 3px、高 12px、圓角、白色），只在播放時動（`@keyframes` 縮放 `scaleY`，三根延遲不同）。
4. **卡片 `.home-card`**：`margin-top: -40px; position: relative;`（壓在圖的底緣），`background: var(--card-bg); border: 1px solid var(--border); border-top: 4px solid var(--accent); border-radius: 14px; padding: 24px 20px;`，淺色陰影 `0 6px 20px rgba(122,74,31,.12)`，深色（`prefers-color-scheme: dark`）改 `0 6px 20px rgba(0,0,0,.35)`；桌面 `padding: 32px 28px`、最大寬度 720px、置中。
   - `.home-verse`：`font-family: "Songti TC","PMingLiU","MingLiU",serif; font-size:1.1875rem; line-height:1.9; border-left:3px solid var(--accent); padding-left:14px; margin:.8em 0;`，`::before` 放一個大的「❝」（金色、`opacity:.5`、字級 2rem，`aria-hidden` 用 `content` 即可）。
   - `.home-ref-row`：flex、兩端對齊、可換行，下方 `1px dashed var(--border)`；`.home-ref` 用 `--muted`、14px。
5. **動態效果**：`@keyframes` 至少三個（圖片緩慢放大 scale 1→1.06、淡入上移 12px、音量條），**所有 `animation`／`transition` 宣告都必須寫在 `@media (prefers-reduced-motion: no-preference) { … }` 裡**，`@keyframes` 可以放在裡面或外面。圖片 20 秒、`ease-out`、`forwards`；卡片與兩顆按鈕淡入 0.5 秒，依序延遲 0.12 秒。
6. 手機 320px 到桌面 1440px 都不可以水平溢出。

## 四、JavaScript
- 載入：`Bible.nav(null)`；`Bible.load("luk")` 取第 4 章第 27 節填進 `.home-verse`，書名用資料或 `Bible.bookName("luk")`；失敗呼叫 `Bible.fail(...)`。
- **音樂**，`audio.volume = 0.6`：
  - 載入後嘗試 `audio.play()`。成功 → 按鈕設成播放狀態；被擋下（promise reject）→ 維持暫停狀態，並在 `document` 掛一次性的 `pointerdown` 與 `keydown` 監聽，第一次觸碰／按鍵就 `play()`（成功才設成播放狀態），之後移除監聽。
  - 按鈕點擊：播放中就暫停，暫停中就播放。按鈕自己的 pointerdown 不可以讓一次性監聽播放（否則點「暫停」會先被播放再被暫停）：一次性監聽要忽略來自 `#music-btn` 的事件。
  - `aria-pressed` 要永遠和 `audio.paused` 一致（用 `play`／`pause` 事件來同步最穩）。
- 不要把音樂路徑、經文寫在別處；不要加 `autoplay` 屬性。
