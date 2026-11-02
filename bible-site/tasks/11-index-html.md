---
role: a16
files: [bible-site/site/index.html]
checks:
  - python3 bible-site/tests/site_checks.py index
---
修正 bible-site/site/index.html（只改這一個檔案）。測試發現：搜尋表單的下拉 <select name="book" id="search-book"> 只有一個 value="all" 的選項，而且沒有預設選到目前這卷。請先讀 bible-site/site/index.html 和 bible-site/site/app.js 的 Bible.BOOKS，然後在腳本裡（取得 key = Bible.bookKey(Bible.param("book")) 之後）做：(1) 清空這個 select，先加一個 value="all"、文字「全部四卷」的 option；(2) 用 Bible.BOOKS.forEach 為四卷各加一個 option（value 是 book.key，文字是 book.name）；(3) 最後設 select.value = key。這樣 select 一共要有 5 個選項、目前選中的是目前這卷（例如 ?book=luk 就選路加福音）。其他部分都不要動，保留 <link rel="icon" href="data:,">。
