---
role: de1050
files: [bible-site/site/index.html]
checks:
  - python3 bible-site/tests/visual_checks.py p0 --grep 'index.*可存取名稱'
  - python3 bible-site/tests/site_checks.py index
---
只改 bible-site/site/index.html 的兩行（視覺優化 P0：表單可存取名稱）：
1. 把 `<input type="search" name="q" placeholder="搜尋經文內容">` 改成 `<input type="search" name="q" placeholder="搜尋經文內容" aria-label="搜尋關鍵字">`
2. 把 `<select name="book" id="search-book">` 改成 `<select name="book" id="search-book" aria-label="搜尋範圍">`
其他內容一律不動。改完只回報改了哪裡。
