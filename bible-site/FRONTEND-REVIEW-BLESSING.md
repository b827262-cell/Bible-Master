# 「抽經文卡」功能複審報告

- 複審時間：2026-11-03（Asia/Taipei）
- 範圍：`bible-site/site/blessing.html`、`bible-site/data/blessing.json`、`bible-site/site/app.js` 的導覽項、`bible-site/site/index.html` 的入口連結
- 依據：`bible-site/tasks/61-blessing-page.md`、`62-nav-blessing.md`、`63-index-blessing-entry.md`、`64-blessing-tab-logic.md`；元素契約見 `bible-site/tests/blessing_probe.html` 頁首註解
- 複審者：Front-end Engineer（本會話）。**未修改任何程式碼或資料**，未執行 `build_data`；本報告是本次唯一新增檔案。
- 受測方式：讀原始碼逐條對照 ＋ Chrome（CDP）實測 `http://127.0.0.1:8090/site/blessing.html`（唯讀）＋ 執行專案既有兩支檢查腳本。
- 紅線：線上 8090／8091 前後 PID 相同（1439868／1439888），兩者仍回 200；`blessing.html`、`blessing.json`、`app.js`、`index.html` 的 mtime 未變。

## 自動檢查結果

### `python3 bible-site/tools/check_all.py` — **通過（3/3，exit 0）**

與本功能相關的項目全部通過：

```
通過：index.html / chapter.html / search.html / card.html 的導覽列有「抽經文卡」連結（指向 blessing.html）
通過：index.html 的 <main> 內有指向 blessing.html 的入口連結
通過：blessing.html 一開始顯示封面與「點選領受祝福」按鈕、尚未出現卡片、預設主題是 work、主題標籤與 blessing.json 一致
通過：blessing.html 載入時沒有 JavaScript 錯誤
通過：blessing.html 按「點選領受祝福」後出現 work 主題的卡：標題、經文原文、出處、短文、署名「愛你的天父」都對
通過：blessing.html?card=work-01 不用按鍵就直接顯示 work-01 那張卡
通過：blessing.html?theme=peace 抽到的是 peace 主題的卡
通過：blessing.html 先點主題標籤「rest」再抽，抽到 rest 主題的卡
通過：blessing.html 還在封面時點主題標籤，只切換主題、不抽卡、封面仍在
通過：blessing.html 已抽出卡片後點主題標籤「peace」，立刻換成 peace 主題的新卡
通過：blessing.html「再抽一次」連按 6 次，每次都是同主題而且不會連續抽到同一張
總結：3/3 項檢查通過
```

### `python3 bible-site/tests/visual_checks.py` — **通過（全部，exit 0）**

`blessing.html` 相關 15 項全通過：淺／深色焦點外框 ≥2px、文字對比 ≥4.5:1、可存取名稱、375px 觸控 ≥44px、目前頁面不只靠顏色、標題字級、320/375/768/1440px 無水平溢出、320–1440px 畫布實際像素 ≥600 且顯示不超出。

---

## 一、任務 61：功能與限制逐條對照

| # | 要求 | 判定 | 證據（行號） |
|---|---|---|---|
| 61-1 | 建立 `site/blessing.html` | **通過** | 檔案存在（14550 bytes） |
| 61-2 | 用 fetch 讀 `../data/blessing.json`（`{themes,cards}`） | **通過** | L361–365 |
| 61-3 | 經文一律用 `Bible.load(card.book)` ＋ `chapterOf`＋`Number()` 比對 | **通過** | L95–106（`Bible.chapterOf`、`Number(chapter.verses[i].v)===Number(v)`） |
| 61-4 | 頁面原始碼不寫任何經文／短文／出處字串 | **通過** | 掃描：37 張卡的短文片段 0 段出現在頁面；頁面無「書名 章:節」樣式字串；`愛你的天父` 為契約指定的固定署名（允許） |
| 61-5 | `<nav id="nav">` ＋ `Bible.nav("blessing.html")` | **通過** | L33、L70 |
| 61-6 | `<h1>抽經文卡</h1>` | **通過** | L36 |
| 61-7 | `#theme-tabs`：每主題一個 `<button type="button" data-theme aria-pressed>`，名稱用 theme.title，順序同 JSON，預設 work | **通過** | L38、L200–211；實測 4 個主題、預設 work、`aria-pressed` 只有一個 true |
| 61-8 | 封面 `#cover`：大標「天父關心你」、`♥` aria-hidden 且 `var(--accent)`、`#draw-btn` | **通過** | L40–44、L14；實測 `aria-hidden="true"` |
| 61-9 | `article#blessing-card[hidden]`，抽到才移除 hidden | **通過** | L46、L257 |
| 61-10 | 卡片內依序 h2.card-title / p.card-verse（textContent=verse.text）/ p.card-ref（`Bible.ref`＋「（和合本）」）/ p.card-message / p.card-sign「愛你的天父」 | **通過** | L47–51、L243–246、L241；實測文字與 `data/*.json` 逐字相符 |
| 61-11 | 卡片有 `data-id`／`data-theme`／`data-draws`（從 1 開始），且**在內容與 canvas 都完成後最後才設定** | **通過** | L252–255；MutationObserver 實測 `data-draws` 變動的同一 tick 內，`.card-title`、`.card-verse`、`.card-ref`、`.card-message`、canvas `data-ref`、`read-link href` 都已就緒（不是空字串） |
| 61-12 | `#again-btn`／`#download-btn`／`#share-btn`／`a#read-link`（href `chapter.html?book=&ch=#v`）／`#share-msg role="status"` | **通過** | L54–59、L250；實測 `readHref=chapter.html?book=luk&ch=10#v7` 格式正確 |
| 61-13 | `#card-canvas`：每次重畫並設 `data-ref` = `.card-ref` 文字；寬 600、pad 40；背景 `#fff7ec`；標題 bold 24px `#7a4a1f`、經文 26px `#1a1a1a`、出處 20px `#666666`、短文 22px `#333333`、署名靠右 20px `#7a4a1f`；高度依內容 | **通過** | L124–198；實測 `cw=600`、`chh=416`、`canvasRef` 與 `.card-ref` 完全相同 |
| 61-14 | canvas 加 `aria-hidden="true"` 避免重複朗讀 | **通過** | L52 |
| 61-15 | `?theme=` 有效才套用、否則預設 | **通過** | L385–389；實測 `?theme=zzz`、`?theme=`（空）都退回 work |
| 61-16 | `?card=` 有效就直接顯示（隱藏封面、改主題）、無效當沒有 | **通過** | L391–400；實測 `?card=zzz`、`?card=`、`?card=work-01x` 都留在封面；`?card=peace-01` 直接顯示且主題切到 peace |
| 61-17 | `?card=` 與 `?theme=` 同時存在時以 card 為準 | **通過** | L394–400 在 theme 之後執行並覆寫；實測 `?card=peace-01&theme=work` → 顯示 peace-01、active=peace |
| 61-18 | 按 `#draw-btn`：隱藏封面、從目前主題隨機抽 | **通過** | L330–334 |
| 61-19 | `#again-btn`：同主題再抽，**不得連續同卡**（該主題僅一張才例外） | **通過** | L336–339、L223–237（`excludeId` 且 `pool.length>1` 才過濾）；實測連按 20 次，連續同卡 0 次 |
| 61-20 | 點主題標籤：只切換 aria-pressed；卡片已顯示就立刻抽新卡；還在封面只切換不抽 | **通過** | L341–356、L352 `if (cover.hidden)`（任務 64 已修正寫反）；實測封面狀態點 faith → 封面仍在、`data-draws=null`、active=faith |
| 61-21 | 下載：`toDataURL("image/png")`，檔名 `blessing-<card id>.png` | **通過** | L314–328；**實測下載成功**：檔名 `blessing-peace-01.png`、70,545 bytes、600×416、PNG 檔頭正確、與 `toDataURL` **逐位元組相同** |
| 61-22 | 分享：先 `navigator.share`（title「抽經文卡」、url 去掉查詢後加 `?card=<id>`）；失敗／不存在 → `clipboard.writeText` 並顯示「已複製連結」；都不可用 → 「請手動複製：<網址>」；全程 try/catch | **通過** | L269–312；**四種路徑實測**見下節 |
| 61-23 | 讀取失敗用 `Bible.fail`，不空白 | **通過** | L264–266（經文）、L402–404（JSON） |
| 61-24 | 翻牌動畫只放在 `@media (prefers-reduced-motion: no-preference)` | **通過** | L26–29；實測 `prefers-reduced-motion: reduce` 下 `animationName=none`、`animationDuration=0s` |
| 61-25 | 不載入任何外部資源（不寫 http:// 或 https://） | **通過** | 全檔掃描：無 `http://`、`https://`、`@import`、外部 `<script src>`／`<link href>` |
| 61-26 | 介面全繁體、頁尾 `<footer>四福音 · 和合本</footer>` 不寫單一卷名 | **通過** | L63；簡體字掃描 `blessing.html` 無 |
| 61-27 | 按鈕與標籤觸控 ≥44px；320px 無水平捲軸；主題標籤 flex-wrap | **通過** | L10（`flex-wrap: wrap`）；320px 實測：`documentElement.scrollWidth=320=innerWidth`、溢出元素 0、draw-btn/again/download/share/read-link 皆 44px、4 個主題標籤皆 44px |
| 61-28 | 所有 button 有可讀文字；不用 `outline:none` | **通過** | 8 個 button 全部有文字（含 4 個主題標籤）；檔案無 `outline` 字樣 |

## 二、任務 62／63／64

| # | 要求 | 判定 | 證據（行號） |
|---|---|---|---|
| 62 | `app.js` 的 `nav()` links 在「經文卡片」後加「抽經文卡」 | **通過** | `app.js` L119 `{ href: "blessing.html", label: "抽經文卡" }`；四頁導覽實測都有此連結 |
| 63 | `index.html` 在說明段下一行加入口連結 | **通過** | `index.html` L16 `<p><a href="blessing.html">抽一張經文卡，領受今天的祝福 →</a></p>` |
| 64 | `themeTabs` 條件由 `if (!cover.hidden)` 改為 `if (cover.hidden)` | **通過** | `blessing.html` L352 已是 `if (cover.hidden)`；行為實測符合（見 61-20） |

---

## 三、自動檢查沒涵蓋、本次補測的項目

### 3-1 分享四種路徑 — **通過**

以覆寫 `navigator.share`／`navigator.clipboard` 模擬四種環境（L297–312）：

| 情境 | 期望 | 實測 | 判定 |
|---|---|---|---|
| 有 `navigator.share` | 呼叫 share，title「抽經文卡」、url 帶 `?card=` | 收到 `{title:"抽經文卡", url:"…/blessing.html?card=peace-01"}` | 通過 |
| share 失敗 | 退回 clipboard 並顯示「已複製連結」 | `clipText` 為同一網址、`#share-msg` = 「已複製連結」 | 通過 |
| share 與 clipboard 都不存在 | 顯示「請手動複製：<網址>」 | 「請手動複製：http://…/blessing.html?card=peace-01」 | 通過 |
| clipboard 也失敗（權限被拒） | 顯示「請手動複製：<網址>」 | 同左 | 通過 |

**分享網址會去掉既有查詢字串**：以 `?card=peace-01&junk=1#frag` 進站後按分享，得到 `…/blessing.html?card=peace-01`（`junk` 與 `#frag` 都被移除），符合 L269–279。

### 3-2 非同步競爭與連續快速點擊 — **通過**

| 情境 | 實測 | 判定 |
|---|---|---|
| 連按 `#draw-btn` 10 次（同一 tick 內） | `data-draws=10`，最終卡內容完整、canvas `data-ref` 與 `.card-ref` 一致、無 JS 錯誤 | 通過 |
| 連按 `#again-btn` 15 次 | `draws` 由 10→25（每次遞增），最終內容一致 | 通過 |
| 快速切換主題 6 次 | 最終 `theme=rest`、卡為 `rest-05`、內容與 ref／canvas 一致 | 通過 |
| `?card=` 載入後立刻 again＋切主題＋again | 最終 `theme=faith`、`id=faith-05`、`refMatchesCanvas=true`、`#theme-tabs` active 只有 faith | 通過 |

四種情境全程 **0 個 `Runtime.exceptionThrown`、0 個 console error**。

### 3-3 深色模式可讀性 — **通過（客觀量測）**

深色下（`body` 背景 `rgb(23,22,20)`）：標題 7.08:1、經文 13.05:1、出處 6.17:1、短文 13.05:1、署名 7.08:1、`#share-msg` 6.17:1 —— 全部 ≥4.5:1。頁面所有顏色都用 `style.css` 的變數（L14–25 皆為 `var(--…)`），`visual_checks.py` 的深色項目也通過。

### 3-4 無障礙 — **通過**

`canvas` `aria-hidden="true"`、`♥` `aria-hidden="true"`、`#share-msg role="status"`、卡片標題為 `<h2>`、8 個按鈕都有可讀文字、頁面無 `outline:none`；`visual_checks.py` 的「可聚焦元件焦點外框 solid ≥2px」與「文字對比 ≥4.5:1」在深淺色皆通過。

---

## 四、需人工

| # | 項目 | 原因 |
|---|---|---|
| 4-1 | 實際手機的 `navigator.share` 原生分享面板、系統剪貼簿提示外觀 | headless Chrome 只能模擬 API 行為，無法確認真機 UI。已用覆寫方式驗證四條分支的邏輯與訊息文字皆正確 |
| 4-2 | 卡片視覺美感（字體、留白、♥ 裝飾比例） | 主觀判斷；已確認規格要求的顏色、字級、寬度、對齊與靠右署名都符合 |

---

## 五、結論

| 分類 | 數量 |
|---|---|
| 通過 | 36 |
| 不通過 | 0 |
| 需人工 | 2 |

**未發現未做到、做錯或新引入的功能問題。**自動檢查（`check_all.py` 3/3、`visual_checks.py` 全過）之外，本次另外補測了它沒涵蓋的：分享四條分支與網址清理、四種非同步競爭／連續快速點擊、`?card=`×`?theme=` 六種非法與衝突組合、`data-draws` 設定時序（MutationObserver）、下載 PNG 逐位元組比對、320px 溢出與觸控尺寸、reduced-motion、深色對比、無障礙屬性，結果全部符合契約。

**可留意（非缺陷）**：`blessing.json` 有三個字（`窗`、`黑`、`翻`）出現在我的簡體字清單中，但這三字繁簡同形（Big5 可編碼、`s2t` 不改），屬正常繁體用字，不列為問題。

總計：通過 36 項、不通過 0 項、需人工 2 項（共 38 項）。
