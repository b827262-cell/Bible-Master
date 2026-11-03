---
role: pm
files: [bible-site/admin/server.py]
depends: [95-zone-data-build]
checks:
  - python3 bible-site/tests/service_checks.py zoneadmin --grep "zoneadmin：(GET|POST|DELETE|先用|驗證失敗|所有|前台音樂的設定|沒有留下|測試沒有|處理請求)"
  - python3 bible-site/tests/service_checks.py homeadmin
  - python3 bible-site/tests/service_checks.py admin
---
只改 `bible-site/admin/server.py`（純 Python 標準庫）。後台要能設定「前台四區共用的背景音樂」，存在 `<SITE_ROOT>/data/zone-music.json`。測試 `python3 bible-site/tests/service_checks.py zoneadmin`（函式 `zoneadmin()`）已經寫好，請先讀，行為以它為準。**照抄現有「主頁設定」那一組的寫法**：`HOME_*` 常數、`load_home_config`、`validate_home_config`、`handle_api_home_get`／`handle_api_home_post`／`handle_api_home_reset`、`atomic_write_json`、`check_write_auth`、`read_body`／`reject_too_large`、`list_assets`，以及 `do_GET`／`do_POST` 的路由。不要改它們的行為，`home.json` 的六欄規則不可動。

## 新增
- 常數：`ZONE_FIELDS = ("music",)`、`ZONE_DEFAULTS = {"music": "assets/home-music.mp3"}`；`zone_config_path()` 指向 `<SITE_ROOT>/data/zone-music.json`；`load_zone_config()`（檔案不存在或壞掉或不合格 → 預設值，和 `load_home_config` 一樣的容錯）；`validate_zone_config(obj)`：必須是物件、欄位剛好是 `music`、值是字串、符合 `^assets/[A-Za-z0-9._-]+$`、不含 `..`、副檔名 `.mp3`（轉小寫比較）、`<SITE_ROOT>/site/<music>` 檔案已存在；回傳錯誤訊息字串或 `None`（照 `validate_home_config` 的回傳慣例）。
- `GET /api/zone-music`（唯讀，不需 token）：200 `{"config": {...}, "default": {...}, "music": [...]}`，`music` 是 `list_assets()` 的 mp3 清單（同 `/api/home` 的 `music`）。
- `POST /api/zone-music`：寫入端點共同規則（`check_write_auth`，不過回 403 且不讀內容）→ 內容超過 65536 回 413 → 不是 JSON 物件回 400 → 驗證不過回 400（**不得改動檔案**）→ 通過才用 `atomic_write_json` 寫入，回 200 `{"ok": true, "config": {...}}`。
- `POST /api/zone-music/reset`：同樣的授權規則，把檔案寫成預設值，回 200 `{"ok": true, "config": {...}}`，不刪任何 assets 檔。
- 沒有 DELETE。路由要放在 `startswith("/api/")` 的 404 分支之前。錯誤訊息用繁體中文，不外洩 Traceback 或路徑。
- 不要碰 `data/` 底下任何檔案（`zone-music.json` 只能經由端點寫）；不要啟動或停止服務。

完成後自己跑 `python3 -m py_compile bible-site/admin/server.py`。結果以驗收腳本為準。
