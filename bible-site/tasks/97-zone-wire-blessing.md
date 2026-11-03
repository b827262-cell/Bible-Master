---
role: de1050
files: [bible-site/site/blessing.html]
depends: [96-zone-music-js]
checks:
  - python3 bible-site/tests/site_checks.py zonemusic --grep "zonemusic：blessing.html"
  - python3 bible-site/tests/site_checks.py chapter --grep "連結|外部"
---
只改 `bible-site/site/blessing.html`，只加一行：找到 `<script src="app.js"></script>` 那一行，在它的**下一行**加上同樣縮排的
```
<script src="music.js"></script>
```
其他一個字都不要動。不要在頁面裡放 `<audio>` 或按鈕（music.js 會自己建立）。
