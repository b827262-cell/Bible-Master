---
role: a16
files: [bible-site/data/zone-music.json, bible-site/tools/build_public.py]
checks:
  - python3 bible-site/tests/site_checks.py zonemusic --grep "zone-music.json (只有|的 music 是)"
  - python3 bible-site/tests/deploy_checks.py --grep "build_public|zone-music.json 指定的音樂|沒被使用的上傳音樂"
---
前台四區（目錄、搜尋、經文卡片、抽經文卡）要共用一首背景音樂，設定存在新檔 `bible-site/data/zone-music.json`。只改兩個檔案。測試（`tests/site_checks.py` 的 `zone_data()`、`tests/deploy_checks.py`）已經寫好，請先讀，行為以它們為準。

## 1. 新增 `bible-site/data/zone-music.json`
內容剛好是一個欄位（UTF-8，結尾換行）：
```
{"music": "assets/home-music.mp3"}
```
不要加其他欄位，不要動 `data/home.json`，不要新增任何音樂檔。

## 2. 改 `bible-site/tools/build_public.py`
- `DATA_FILES` 清單加上 `"zone-music.json"`（放在 `"home.json"` 後面）。
- `referenced_assets()`：除了現有讀 `data/home.json` 的 `image`／`music`，也要讀 `data/zone-music.json`，把它的 `music`（字串）加進 `used`。檔案不存在時略過（和 home.json 的寫法一樣）；JSON 壞掉不要讓整個發佈崩潰以外的事發生——沿用 home.json 那段的處理方式即可，不要自創新行為。
- 其他邏輯一律不動；不要碰 `HEADERS`、`ALWAYS_ASSETS`、`NOT_FOUND`。

完成後自己跑 `python3 -m py_compile bible-site/tools/build_public.py`。結果以驗收腳本為準。
