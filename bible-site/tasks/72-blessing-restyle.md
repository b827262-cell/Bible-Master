---
role: e500
files: [bible-site/site/blessing.html]
depends: [71-style-palette-nav]
checks:
  - python3 bible-site/tests/site_checks.py blessing blessstyle
  - python3 bible-site/tests/visual_checks.py --grep blessing
---
只改 bible-site/site/blessing.html 的樣式與標記，讓抽經文卡頁面更好看。抽卡、主題切換、分享、下載的 JavaScript 邏輯不要動，以下列出的地方除外。
style.css 已經有變數 `--card-bg`、`--accent-soft`，也有 `.btn-secondary` 次要按鈕樣式，直接用。

## 一、`<style>` 區塊
**1. 主題按鈕 `#theme-tabs`**
- 排成 2×2 等寬：`display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 0.5em 0 1em;`
- `#theme-tabs button`（未選中）：`background: var(--surface); color: var(--fg); border: 1px solid var(--border); font-weight: 500; text-decoration: none; border-radius: 9999px;`
- `#theme-tabs button[aria-pressed="true"]`（選中）：`background: var(--accent); color: var(--accent-fg); border-color: var(--accent); font-weight: 700; text-decoration: none;`
- `#theme-tabs button[aria-pressed="true"]::before { content: "✦ "; }`
- 原本「選中＝粗體＋底線」那條規則刪掉。

**2. 卡片 `#blessing-card`**
- `background: var(--card-bg); border: 1px solid var(--border); border-top: 4px solid var(--accent); border-radius: 14px; padding: 24px 20px; margin-top: 1em; box-shadow: 0 6px 20px rgba(122, 74, 31, 0.07);`
- 深色模式改陰影：`@media (prefers-color-scheme: dark) { #blessing-card { box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35); } }`
- 桌面加大內距：`@media (min-width: 48em) { #blessing-card { padding: 32px 28px; } }`

**3. 卡片內各段**
- `.card-title`：`font-size: 0.9375rem; font-weight: 600; color: var(--accent); letter-spacing: 0.08em; margin: 0 0 16px;`
- `.card-verse`：`font-family: "Songti TC", "PMingLiU", "MingLiU", serif; font-size: 1.1875rem; line-height: 1.85; font-weight: 500; color: var(--fg); border-left: 3px solid var(--accent); padding-left: 14px; margin: 0 0 12px;`
- 新的出處列 `.card-ref-row`：`display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.25em 1em; padding-bottom: 18px; margin-bottom: 20px; border-bottom: 1px dashed var(--border);`
- `.card-ref`：`color: var(--muted); font-size: 0.875rem; margin: 0;`
- `.card-message`：`font-size: 1.03125rem; line-height: 1.8; letter-spacing: 0.02em; color: var(--fg); margin: 0 0 18px;`
- `.card-sign`：`text-align: right; font-size: 0.9375rem; font-weight: 600; color: var(--accent); letter-spacing: 0.05em; margin-bottom: 0.5em;`
- `.card-sign::before { content: "—— "; }`：破折號用 CSS 加，署名文字本身仍是「愛你的天父」，不要改 HTML 文字。

**4. `#read-link`**
- 保留 `min-height: 44px`、`display: inline-flex`、`align-items: center`、`color: var(--accent)`。
- 改成 `font-size: 0.875rem; padding: 0.25em 0.5em; text-decoration: underline; text-underline-offset: 0.2em;`。
- hover 改用 `background: var(--accent-soft)`。

**5. 動作按鈕**
- `.card-actions` 改成 `display: flex; gap: 0.5em; flex-wrap: wrap; margin-top: 1em;`。
- `#again-btn { flex: 1.3 1 auto; font-weight: 700; }`
- `#download-btn, #share-btn { flex: 1 1 auto; }`

**6. canvas**
- `#card-canvas` 的規則改成 `#card-canvas { display: none; }`。

## 二、HTML 標記（`<article id="blessing-card">` 裡）
- 把 `<p class="card-ref"></p>` 包進新的出處列，並把閱讀連結移到出處旁邊，文字改成「閱讀本章 →」：
```html
<div class="card-ref-row">
  <p class="card-ref"></p>
  <a id="read-link">閱讀本章 →</a>
</div>
```
- 原本 `.card-actions` 裡的 `<a id="read-link">閱讀這一章</a>` 刪掉，不要留兩個。
- `<canvas id="card-canvas" aria-hidden="true"></canvas>` 加上 `hidden` 屬性。
- 按鈕：
  - 「再抽一次」文字改成「↻ 再抽一次」；
  - `#download-btn`、`#share-btn` 加上 `class="btn-secondary"`。

## 三、`drawCanvas()`：只改顏色與字型，版面計算不動
- 底色：`#fff7ec` 改成 `#fbf7ee`。
- 填完底色後，加畫內框：`ctx.strokeStyle = "#e2d5be"; ctx.lineWidth = 2; ctx.strokeRect(20, 20, W - 40, H - 40);`。
- 經文：
  - 字型：兩處 `"26px sans-serif"` 都改成 `"26px 'Songti TC', 'PMingLiU', serif"`（量寬度的那處也要改，才會一致）；
  - 顏色：`#1a1a1a` 改成 `#1f1e1b`。
- 出處：`#666666` 改成 `#6e6659`。
- 短文：`#333333` 改成 `#33312e`。
- 署名文字改成 `"—— 愛你的天父"`。
- `canvas.setAttribute("data-ref", refText)` 保留。

改完只回報改了哪些地方。
