---
role: de1050
files: [bible-site/site/index.html]
depends: [62-nav-blessing]
checks:
  - python3 bible-site/tests/site_checks.py blessindex
  - python3 bible-site/tests/site_checks.py index
---
只改 bible-site/site/index.html 一處：在 `<p>四福音全文，共四卷。點選章節閱讀全文，或搜尋經文內容。</p>` 這一行的下一行，新增一行：
`<p><a href="blessing.html">抽一張經文卡，領受今天的祝福 →</a></p>`
其他內容一律不動。改完只回報改了哪裡。
