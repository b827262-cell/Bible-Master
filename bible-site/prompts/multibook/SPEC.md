# 四福音版網站規格（給各模型照著改）

資料已就緒：`data/mat.json`、`mrk.json`、`luk.json`、`jhn.json`（馬太、馬可、路加、約翰），格式：
`{key, book, version, chapters:[{ch, verses:[{v, text, end?}], notes:[...]}]}`。
`end` 只在原文把兩節印成一節時出現：路加 1:1–2（`v:1, end:2`）、路加 2:34–35、（約翰 7:53 已併入 8:1，沒有獨立的一節）。
**經文只能用 fetch 從 `../data/<key>.json` 讀，程式裡不准寫死任何經文。不載入外部資源。全繁體中文。手機 375px 不橫向捲動。**

## 網址規則
| 頁面 | 網址 | 沒帶或不合法時 |
|---|---|---|
| 目錄 | `index.html?book=KEY` | `book` 預設 `mat` |
| 逐章 | `chapter.html?book=KEY&ch=N` | `book` 預設 `mat`，`ch` 預設 1 |
| 搜尋 | `search.html?q=字&book=KEY` | `book` 沒帶或 `all` ＝搜全部四卷 |
| 卡片 | `card.html?book=KEY&ch=N&v=M` | `book` 預設 `mat`，`ch`、`v` 預設 1 |

KEY 只能是 `mat`、`mrk`、`luk`、`jhn`；其他值一律當成預設值，不可報錯。

## app.js 提供的 `Bible` 物件
| 函式 | 說明 |
|---|---|
| `Bible.BOOKS` | `[{key:"mat",name:"馬太福音"},{key:"mrk",name:"馬可福音"},{key:"luk",name:"路加福音"},{key:"jhn",name:"約翰福音"}]` |
| `Bible.bookKey(raw)` | `raw` 是 BOOKS 裡的 key 就回傳它，否則回傳 `"mat"` |
| `Bible.bookName(key)` | 書名 |
| `Bible.load(key)` | fetch `../data/<key>.json`，每卷各自快取，回傳 Promise（資料物件） |
| `Bible.loadAll()` | 回傳 Promise，依 BOOKS 順序的四個資料物件陣列 |
| `Bible.param(name)` | 網址參數，沒有回傳 `""` |
| `Bible.verseLabel(verse)` | verse 物件 → `"5"`，有 `end` 時 `"1-2"` |
| `Bible.ref(key, ch, verse)` | → `"馬太福音 5:3"`，合併節 → `"路加福音 1:1-2"`（verse 是節物件） |
| `Bible.chapterOf(data, ch)` | 找出第 ch 章，找不到回傳 null |
| `Bible.escape(s)` | HTML 跳脫 |
| `Bible.nav(active)` | 在 `<nav id="nav">` 畫導覽（目錄／搜尋／經文卡片），`active` 傳 `"index.html"` 這種檔名 |
| `Bible.bookTabs(hostId, activeKey, page)` | 在 id 為 hostId 的元素畫四個書卷連結（`page?book=key`），目前這卷加 `aria-current="page"` 與 `.active` |
| `Bible.fail(host, err)` | 顯示錯誤訊息（`.error`） |

## 各頁需求
- **index.html**：標題「四福音（和合本）」；`Bible.bookTabs("book-tabs", key, "index.html")`；目前這卷的章格線（每格連到 `chapter.html?book=KEY&ch=N`，顯示「第 N 章・M 節」，M 用 `verses.length`）；搜尋表單 GET 到 `search.html`：輸入框 `name="q"`，下拉 `name="book"`（選項：全部四卷 value=all，另外四卷），預設選項是目前這卷。
- **chapter.html**：標題「書名 第 N 章」；書卷連結 `Bible.bookTabs`；該章每節一列，節號用 `Bible.verseLabel`，節的 `id="v"+v`；有 `end` 時另外放一個空的 `<span id="v"+end>` 錨點（讓 `#v2` 也能到路加 1:1–2）；notes 顯示在「參照」區；上一章／下一章／回目錄（連回 `index.html?book=KEY`）；畫完後讀 `location.hash`，有對應元素就 `scrollIntoView()`。
- **search.html**：輸入框＋下拉（all＋四卷）＋送出鈕；`?q=` 自動搜尋；每筆顯示 `Bible.ref(...)`（例如「馬太福音 5:3」），連到 `chapter.html?book=KEY&ch=N#vV`，後接經文，關鍵字用 `<mark>`（先跳脫再標）；顯示「共 N 筆」；全部列出、不分頁；`book=all` 依書卷順序、章節順序。
- **card.html**：三個下拉（書卷、章、節）；換書卷→章回到 1、節回到 1；換章→節回到 1；出處「書名 章:節（和合本）」，合併節用 `Bible.ref`；其餘同前（canvas 畫圖、`<a download>`，檔名 `KEY-章-節.png`，例如 `mat-5-3.png`）。

## 驗收（`python3 bible-site/tools/check_all.py` 會自動測）
- 四卷首章與末章全部節都顯示；沒帶 book 時是馬太。
- 路加 1 章有「1-2」標示。
- 搜尋「耶穌」：馬太 274、馬可 274、路加 326、約翰 309、全部 1183 筆。
- `#v40`（馬可 1）、`#v2`（路加 1）、`#v25`（約翰 21）開啟後該節要在畫面內。
