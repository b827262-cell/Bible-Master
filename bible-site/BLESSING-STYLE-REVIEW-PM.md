# 抽經文卡：視覺美化審查（Gemini PM）

- 審稿者：Gemini「PM」會話（https://gemini.google.com/u/1/app/837d46a9d47b0984）。
- 送審內容：使用者手機實機截圖（深色模式，`blessing.html` 安息主題 馬太 11:28），以及目前的配色變數、canvas 配色與四條限制（不載外部資源、繁體中文、WCAG AA 與 44px、經文不可改）。
- 狀態：**只是建議，尚未修改任何程式**。

## (A) 前 5 項問題（依影響排序）

| # | 現況問題 | 建議做法 |
|---|---|---|
| 1 | 上方文字卡與下方 canvas 圖卡內容完全重複；深色模式下米白 canvas 是突兀的亮塊，按鈕被擠到畫面底部 | 頁面只留 HTML 卡；canvas 隱藏，按「下載圖片」時才在背景繪製 |
| 2 | 導覽、4 顆主題、3 顆動作，共 8 顆實心 accent 按鈕，沒有主次 | 只留 1–2 處實心：選中的主題、「再抽一次」；其餘改外框或透明 |
| 3 | 經文與短文字型、字級、顏色相同，沒有層次 | 經文改系統明體、19px、左側 3px accent 豎線；出處下加虛線分隔；短文維持黑體 |
| 4 | 主題選中狀態是「粗體＋底線＋外框」，像舊式連結或 focus 殘留，寬度參差 | 2×2 等寬 grid；未選中為 surface＋細框；選中為實心 accent，前加「✦ 」，去底線 |
| 5 | 導覽「抽經文卡」與 `<h1>抽經文卡</h1>` 重複；「閱讀這一章」不明顯 | 出處本身做成連結並加「閱讀本章 →」；`<h1>` 縮小或改成較溫馨的副標 |

## (B) 建議配色（對比值由我用 WCAG 公式重算，全部 ≥ 4.5:1）

| 變數 | 淺色 | 深色 | 用途 |
|---|---|---|---|
| `--bg` | #f7f5ef | #161513 | 頁面底 |
| `--surface` | #ffffff | #22201c | 未選中按鈕、次要區塊 |
| `--card-bg`（新） | #fffcf5 | #28251f | 經文卡底 |
| `--fg` | #2c2b28（對 card 13.82） | #ede9df（對 card 12.60） | 主文字 |
| `--muted` | #635f56（對 card 6.21） | #aba69b（對 card 6.30） | 出處、輔助字 |
| `--border` | #ded8cc | #3d3932 | 外框、分隔線 |
| `--accent` | #7a4a1f（對 card 7.25） | #deb068（對 card 7.65） | 標題、主按鈕、選中 |
| `--accent-fg` | #ffffff（對 accent 7.43） | #171614（對 accent 9.06） | 主按鈕文字 |
| `--accent-soft`（新） | #f3ead8 | #352c1e | 次要按鈕 hover |

canvas 匯出圖卡（不跟深色模式變黑）：底 #fbf7ee、內框 2px #e2d5be（內縮 20px）、標題 #7a4a1f（6.95）、經文 #1f1e1b 明體、出處 #6e6659（5.30）、短文 #33312e、署名 #7a4a1f。

## (C) 按鈕層級
- **導覽列**：取消實心方塊；目前頁為 accent 文字＋粗體＋3px 底線，其他為 muted。
- **主題四顆**：2×2 grid、gap 10px；未選中 surface＋1px border；選中 accent 實心＋「✦ 」，去掉底線與雙框。
- **動作列**：「再抽一次」為主要（實心 accent、粗體、可加「↻」、flex 1.3）；「下載圖片」「分享」為次要（surface＋border，flex 1，hover 時用 accent-soft）。
- 全部維持 `min-height: 44px`，圓角 8px（膠囊可 9999px）。

## (D) 經文卡版面
- 卡片：`--card-bg`、1px border、圓角 14px、`border-top: 4px solid var(--accent)`；手機 padding 24px 20px，桌面 32px 28px；陰影深色 `0 8px 24px rgba(0,0,0,.35)`、淺色 `0 6px 20px rgba(122,74,31,.07)`。
- ① 主題小標：15px、600、accent、letter-spacing .08em、下距 16px。
- ② 經文：系統明體（`"Songti TC", "PMingLiU", serif`，只引用系統字型名稱，不下載）、19px、行高 1.85、左側 3px accent 豎線、padding-left 14px。
- ③ 出處：14px、muted、靠右；下方 1px dashed border 分隔，可兼作「閱讀本章 →」連結。
- ④ 短文：黑體 16.5px、行高 1.8；署名「—— 愛你的天父」靠右、15px、600、accent。

## 我的備註（實作前要處理）
1. **隱藏 canvas 會撞到現有檢查**：`tests/visual_checks.py`（第 123 行附近）和 `site_checks.py` 目前會在四種寬度檢查 `canvas#card-canvas` 的尺寸與 `data-ref`。若採用建議 1，要先把檢查改成「canvas 不顯示，但下載時產生的圖片 data-ref 正確」。
2. 建議 5 提到「閱讀這一章」看不到：其實 `#read-link` 存在，只是在截圖範圍外（動作按鈕下方）。
3. 「Noto Serif TC」是 Gemini 列的字型名稱；我會只列系統內建明體，不依賴使用者有沒有裝該字型。
4. 這些改動屬於樣式，深色／淺色兩套都要再跑 `visual_checks.py` 的對比與 44px 檢查。

## 實作結果（任務 70–72）
- 任務 70（我）：先寫客觀檢查。
  - `site_checks.py` 新增 `blessstyle` 群組（9 項）；
  - `visual_checks.py` 新增「導覽列目前頁不是實心色塊」，blessing 畫布改成「不顯示但畫好」；
  - `blessing_probe.html`、`visual_probe.html` 多輸出樣式量測；
  - `site_checks.py` 加上 `--grep`。
  - 先跑一次，確認新檢查不通過、舊檢查通過。
- 任務 71（A16，`style.css`）：配色變數、導覽列目前頁、`.btn-secondary`。檢查通過，但縮排被改亂，由我整理回 2 格縮排（內容不變）。
- 任務 72（E500，`blessing.html`）：卡片版面、主題 2×2、按鈕層級、canvas 隱藏與匯出配色。約 6 分鐘，一次通過。
- 我的微調：375px 截圖發現兩個問題，各自修正如下。
  - 「天父賜福你的工作」換行：主題按鈕縮小左右內距、改 15px、不換行。
  - 「分享」被擠到第二列：動作列改成 grid，「再抽一次」獨佔一列，下載與分享並排。
  - 320px 也確認不溢出。
- 驗證：`check_all.py` 3/3；`visual_checks.py` 全部通過（四種寬度、深淺色對比、44px、焦點外框）；`site_checks.py` 全部通過。

## 複審（完成後）
- 送審內容：375px 深色截圖、375px 淺色截圖、下載的 PNG，以及採用與未採用清單。
- Gemini 這次的會話模型顯示為 Flash-Lite（第一次審查時是 Argon）。
- 逐項結果：canvas 隱藏、按鈕收斂、經文卡排版、主題 2×2、配色對比、我加的按鈕排列，**六項全部「達成」**。
- 必修問題：無。
- 簽核：**通過可上線**。
