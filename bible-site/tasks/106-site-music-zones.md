---
role: e500
files: [bible-site/site/music.js]
checks:
  - node --check bible-site/site/music.js
  - python3 bible-site/tests/site_checks.py zonemusic
---
所有操作都在 E500 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、home.json、chapter.html、不下載或引入外部資源。只能更改 front matter 允許的檔案。

改 site/music.js：從 location.pathname 的檔名辨識 index.html/search.html/card.html/blessing.html 對應 index/search/card/blessing。讀取 ../data/zone-music.json，取符合 assets/…mp3 的 zones[目前頁面]，沒有則取 music，再沒有則回預設 assets/home-music.mp3。
不可影響 sessionStorage bm.zone.on / bm.zone.t / bm.zone.src；切不同 mp3 從 0 起播（避免舊秒數污染），同 mp3 跨頁續播；第一次手勢的 click/pointerup/touchend/keydown、暫停後禁止重自播、按鈕 44px、a11y 等既有行為全部保留。只有這一檔。
詳見 site_checks.py zonemusic、zone_probe.html，含同曲跨頁／換曲測試。
