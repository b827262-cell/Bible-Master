---
role: de1050
files: [bible-site/site/search.html]
depends: [41-index-labels]
checks:
  - python3 bible-site/tests/visual_checks.py p0 --grep 'search.*可存取名稱'
  - python3 bible-site/tests/site_checks.py search
---
只改 bible-site/site/search.html 的兩行（視覺優化 P0：表單可存取名稱）：
1. 把 `<input type="search" name="q" id="search-q" placeholder="輸入關鍵字">` 改成 `<input type="search" name="q" id="search-q" placeholder="輸入關鍵字" aria-label="搜尋關鍵字">`
2. 把 `<select name="book" id="search-book">` 改成 `<select name="book" id="search-book" aria-label="搜尋範圍">`
其他內容一律不動。改完只回報改了哪裡。
