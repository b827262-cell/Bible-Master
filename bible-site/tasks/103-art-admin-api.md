---
role: pm
files: [bible-site/admin/server.py]
depends: [98-zone-admin-api, 100-art-data-build]
checks:
  - python3 bible-site/tests/service_checks.py blessartadmin --grep "blessartadmin：(GET|POST|DELETE|先用|可以同時|驗證失敗|所有|出處|沒有任何|沒有留下|測試沒有|處理請求)"
  - python3 bible-site/tests/service_checks.py zoneadmin
  - python3 bible-site/tests/service_checks.py homeadmin
  - python3 bible-site/tests/service_checks.py admin
---
只改 `bible-site/admin/server.py`（純 Python 標準庫）。後台要能設定「抽經文卡四個主題各自的收藏卡圖」，存在 `<SITE_ROOT>/data/blessing-art.json`。測試 `python3 bible-site/tests/service_checks.py blessartadmin`（函式 `blessartadmin()`）已經寫好，請先讀，行為以它為準。**照抄現有 `zone-music`（`load_zone_config`／`validate_zone_config`／`handle_api_zone_music_*`）與 `home` 那兩組的寫法**，共用 `check_write_auth`、`read_body`／`reject_too_large`、`atomic_write_json`、`list_assets`。不要改既有端點的行為。**絕對不能寫入或修改 `data/blessing.json`**（37 張經文卡固定）：它只能被唯讀讀取。

## 新增
- 常數：`ART_FIELDS = ("image", "alt", "edition")`；`art_config_path()` 指向 `<SITE_ROOT>/data/blessing-art.json`；`load_blessing_themes()`：唯讀讀 `<SITE_ROOT>/data/blessing.json`，回傳 `(themes, cards)`（讀不到或壞掉回 `([], [])`）；`load_art_config()`（檔案不存在、壞掉、不是物件 → `{}`）；`validate_art_config(obj)`：必須是物件；每個鍵必須是 `blessing.json` 的主題 id；每個值必須是物件且欄位剛好是 `image`、`alt`、`edition`；`image` 符合 `^assets/[A-Za-z0-9._-]+$`、不含 `..`、副檔名限 `.jpg .jpeg .png .webp`（轉小寫）、`<SITE_ROOT>/site/<image>` 檔案已存在；`alt` 是字串，去頭尾空白後 1–120 字；`edition` 是字串，0–20 字（可為空字串）。回傳錯誤訊息字串或 `None`（照 `validate_home_config` 的慣例）。空物件 `{}` 是合法的。
- `GET /api/blessing-art`（唯讀，不需 token）：200 `{"themes": [...], "config": {...}, "images": [...]}`。`themes` 依 `blessing.json` 的順序，每項 `{"id", "title", "count", "refs"}`，`refs` 是該主題每張卡的 `{"book", "ch", "v"}` 清單（**只有出處，不含經文文字或短文**），`count` 等於 `refs` 的長度。`images` 是 `list_assets()` 的圖片清單。
- `POST /api/blessing-art`：寫入端點共同規則（`check_write_auth`，不過回 403 且不讀內容）→ 內容超過 65536 回 413 → 不是 JSON 回 400 → 驗證不過回 400（**不得改動檔案**）→ 通過才用 `atomic_write_json` 寫入整份設定，回 200 `{"ok": true, "config": {...}}`。
- `POST /api/blessing-art/reset`：同樣的授權規則，把檔案寫成 `{}`，回 200 `{"ok": true, "config": {}}`，不刪任何 assets 檔。
- 沒有 DELETE；沒有任何寫 `blessing.json` 的端點。路由放在 `startswith("/api/")` 的 404 分支之前。錯誤訊息用繁體中文，不外洩 Traceback 或路徑。
- 不要碰 `data/` 底下其他檔案；不要啟動或停止服務。

完成後自己跑 `python3 -m py_compile bible-site/admin/server.py`。結果以驗收腳本為準。
