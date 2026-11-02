---
role: de1050
files: [bible-site/site/card.html]
checks:
  - python3 bible-site/tests/site_checks.py card
  - "! grep -n '<footer>.*馬可福音' bible-site/site/card.html"
---
只改 bible-site/site/card.html 的一行：頁尾 <footer>和合本 · 馬可福音</footer> 寫死了書名，這個網站有四卷，請改成 <footer>四福音 · 和合本</footer>（其他頁面的頁尾就是這樣寫）。其他地方都不要動。改完只回報有改哪裡。
