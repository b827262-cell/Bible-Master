---
role: a16
files: [bible-site/site/style.css]
checks:
  - grep -q "book-tabs a:focus-visible" bible-site/site/style.css
  - python3 bible-site/tests/site_checks.py index
---
只改 bible-site/site/style.css：檔案最後面有一條規則，選擇器是「.nav-list a:focus-visible,\n.chapter-card:focus-visible {」（內容是 outline: 2px solid var(--focus); outline-offset: 2px;）。請在這條規則的選擇器清單裡加上第三個選擇器 .book-tabs a:focus-visible（用逗號接在 .chapter-card:focus-visible 後面），讓書卷切換標籤的鍵盤焦點也有同樣的外框。規則內容不要改，也不要新增別的規則，其他地方都不要動。改完只回報改了哪裡。
