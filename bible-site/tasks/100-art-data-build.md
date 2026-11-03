---
role: a16
files: [bible-site/data/blessing-art.json, bible-site/tools/build_public.py]
depends: [95-zone-data-build]
checks:
  - python3 bible-site/tests/site_checks.py blessart --grep "blessart：(data/blessing-art.json 存在|blessing-art.json)"
  - python3 bible-site/tests/deploy_checks.py --grep "blessing-art|收藏卡圖"
---
「抽經文卡」每個主題會有一張預先生成的收藏卡圖，設定存在新檔 `bible-site/data/blessing-art.json`。只改兩個檔案。測試（`tests/site_checks.py` 的 `blessart_data()`、`tests/deploy_checks.py`）已經寫好，請先讀，行為以它們為準。

## 1. 新增 `bible-site/data/blessing-art.json`
目前還沒有圖，內容就是一個空物件（UTF-8，結尾換行）：
```
{}
```
將來每個主題的格式是 `{"work": {"image": "assets/…", "alt": "…", "edition": "2026 年 11 月版"}}`，由後台寫入；你不要自己編任何項目、不要新增圖檔。**不要動 `data/blessing.json`**（37 張經文卡固定不動）。

## 2. 改 `bible-site/tools/build_public.py`
- `DATA_FILES` 清單加上 `"blessing-art.json"`（放在 `"zone-music.json"` 後面）。
- `referenced_assets()`：像讀 `home.json`、`zone-music.json` 那樣，讀 `data/blessing-art.json`，把每個主題設定裡的 `image`（字串）加進 `used`。檔案不存在時略過；內容不是物件、或某個主題的設定不是物件時要略過那一項，不可以丟例外。
- 其他邏輯一律不動；不要碰 `HEADERS`、`ALWAYS_ASSETS`、`NOT_FOUND`。

完成後自己跑 `python3 -m py_compile bible-site/tools/build_public.py`。結果以驗收腳本為準。
