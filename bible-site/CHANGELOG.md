# 主編修改紀錄

## 2026-11-01 17:14–18:31（E500 建站，依 prompts/01..05）

由 E500（Bonsai 2 27B PQ2_0 160K medium t0.4）在 Harness 寫出全部 6 個檔案；PM 每做完一份就跑 `check_all.py` 核對。

| 時間 | 檔案 | 備註 |
|---|---|---|
| 17:14 | `app.js`、`style.css` | 全域 `Bible`：load、param、ref、escape、chapterOf、nav、fail |
| 17:47 | `chapter.html` | 第一版直接呼叫 `param()` 等未定義的全域函式，經文完全沒顯示 |
| 17:48 | `chapter.html` 修正 | 改成 `Bible.xxx`、`Bible.nav()` 直接畫導覽；`#v40` 捲動通過 |
| 17:54 | `index.html` | 16 章格線、GET 搜尋表單 |
| 18:02 | `search.html` | `?q=` 自動搜尋，「耶穌」274 筆 |
| 18:31 | `card.html` | 章／節下拉、canvas 繪製、下載 `mark-章-節.png` |

先前由貓聽（雲端）補做的版本已移到 `../.backup-cloud-site-20261101/`，不再使用。

## 2026-11-01 21:00（前台測試第一輪修正）

依 `FRONTEND-TEST-REPORT.md` 修正；簡易項目交 De1050／A16，較難項目交 E500。

| 項目 | 負責 | 檔案 | 內容 |
|---|---|---|---|
| E6 favicon 404 | De1050 | 4 個 HTML | `<head>` 加 `<link rel="icon" href="data:,">`，不再請求 `/favicon.ico` |
| E4 焦點看不清 | TUF A16 | `style.css` | 刪除導覽列與章節卡片的 `outline: none`，新增 `:focus-visible` 外框（`--focus`，深淺色皆有） |
| E7 簡體字形 | E500 | `tools/build_data.py`、`data/mark.json` | 新增 `NORMALIZE`（脚→腳、叙→敘），重新產生資料；`.verify/mark.txt` 原文未改，`verify_text.py` 同樣經 `parse()` 比對 |

PM 另外只做了排版整理：補上 4 行 icon 的縮排、還原 A16 誤加在 `style.css` 第 2 行註解的空格。
