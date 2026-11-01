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
