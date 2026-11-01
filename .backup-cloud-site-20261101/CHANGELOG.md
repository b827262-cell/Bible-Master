# 主編修改紀錄

## 2026-11-01 16:52（貓聽補做，E500 未交出檔案）

E500 在 15:32 之後沒有寫出任何檔案，`site/` 是空的、`check_all.py` 只有 1/3。
這一輪直接依 `tools/verify_text.py`、`tests/smoke.js`、`tests/site_checks.py` 的實際判定條件補齊 6 個檔案。

新增檔案（都在 `bible-site/site/`）：

| 檔案 | 內容 |
|---|---|
| `app.js` | 全域 `Bible`：`load()` 以 fetch 讀 `../data/mark.json` 並快取、`param()`、`ref()`、`escape()`、`chapterOf()`、`nav()`、`fail()` |
| `style.css` | 手機優先、`prefers-color-scheme` 深淺色、最大寬度 40em、導覽列、章節格線、經文清單、搜尋結果、按鈕 |
| `index.html` | 16 章格線目錄（含每章節數）、GET 搜尋表單 |
| `chapter.html` | `?ch=N` 顯示該章全部經文（每節 `id="vN"`）、`notes` 參照區、上一章／下一章／目錄 |
| `search.html` | 支援 `?q=`（自動帶入搜尋）、全部符合節逐筆列出、出處連到 `chapter.html?ch=…#vM`、關鍵字以 `<mark>` 標示、顯示「共 N 筆」 |
| `card.html` | 章／節下拉（支援 `?ch=N&v=M`）、文字卡片預覽、`<canvas>` 產生 PNG 並以 `<a download>` 下載 `mark-章-節.png` |

驗證結果（`python3 bible-site/tools/check_all.py`，結束碼 0）：

- 經文比對：678/678 節相符；`site/` 沒有寫死的經文。
- 節數與檔案：16 章、678 節，6 個檔案齊全。
- 網站檢查：連結全部存在、無外部資源、`chapter.html?ch=1` 45 節、`?ch=16` 20 節、`search.html?q=耶穌` 274 筆。

另外自行補測（`check_all.py` 沒涵蓋的部分）：

- 375px 寬下開 5 個頁面，`scrollWidth` 都等於 `clientWidth`，無橫向捲動。
- `card.html?ch=3&v=5` 顯示的經文與 `mark.json` 第 3 章第 5 節相符，出處為「馬可福音 3:5（和合本）」。
- 介面文字掃描無簡體字。
