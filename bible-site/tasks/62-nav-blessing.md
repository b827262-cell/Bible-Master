---
role: a16
files: [bible-site/site/app.js]
depends: [61-blessing-page]
checks:
  - node --check bible-site/site/app.js
  - python3 bible-site/tests/site_checks.py blessnav
---
只改 bible-site/site/app.js 的 nav() 函式裡的 links 陣列：在 `{ href: "card.html", label: "經文卡片" }` 後面加一個項目 `{ href: "blessing.html", label: "抽經文卡" }`（記得上一個項目後面補逗號）。
其他內容一律不動，不要改縮排風格。改完只回報改了哪一行。
