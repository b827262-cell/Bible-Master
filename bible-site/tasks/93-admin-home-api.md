---
role: e500
files: [bible-site/admin/server.py]
checks:
  - python3 bible-site/tests/service_checks.py homeadmin --grep "token|Token|/api/|POST|GET|上傳|拒絕|還原|Traceback|暫存|預設|DELETE|home.json"
  - python3 bible-site/tests/service_checks.py admin
---
只改 `bible-site/admin/server.py`（純 Python 標準庫，不可 import 第三方套件）。目前它完全唯讀；請新增「主頁設定」的寫入端點。測試 `python3 bible-site/tests/service_checks.py homeadmin` 已經寫好（函式 `homeadmin()`），請先讀它，所有行為以它為準。

## 1. 可由環境變數覆蓋的路徑（測試用）
- `BIBLE_SITE_ROOT`：放 `data/` 與 `site/` 的目錄。預設就是現在的 `SITE_ROOT`（`bible-site/`）。`SITE_ROOT` 這個全域變數改成「環境變數有設就用它」，其餘讀 `data/*.json` 的地方都跟著用它。`HERE`（admin 目錄，提供靜態檔）不變。
- `BIBLE_ADMIN_TOKEN_FILE`：token 檔路徑，預設 `HERE/.token`。

## 2. Token
- 伺服器啟動時用 `secrets.token_urlsafe(32)` 產生 token，寫到 token 檔（先用 `os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600)`，權限必須是 600），每次啟動重新產生。
- `GET /api/token`：只有在「Host 標頭的主機名是 127.0.0.1、localhost 或 [::1]（可再加環境變數 `BIBLE_ADMIN_ALLOWED_HOSTS` 逗號分隔的額外主機名）」且「沒有 Origin，或 Origin 等於 `http://` + Host」時回 `{"token": "..."}`；否則回 403。這是為了擋 DNS rebinding 與跨站讀取。

## 3. 寫入端點共同規則
所有新的 POST 端點（`/api/home`、`/api/home/reset`、`/api/upload`）在做任何事之前，依序檢查，任何一項不過都回 403 JSON `{"error": "..."}`，而且**不讀取請求內容、不寫任何檔**：
1. `X-Bible-Admin` 標頭等於 `1`（現有規則）；
2. `X-Bible-Token` 標頭用 `hmac.compare_digest` 與 token 比對；
3. Origin 若存在必須等於 `http://` + Host（現有規則）；
4. Host 主機名在上面的允許清單內。
既有的 `/api/action/*` 規則不變（它們不需要 token）。不要加任何 `Access-Control-*` 標頭。沒有 DELETE 端點。

## 4. 端點
- `GET /api/home`（不需 token，唯讀）：回 `{"config": {...}, "defaults": {...}, "images": [...], "music": [...]}`。
  - `config`：讀 `<SITE_ROOT>/data/home.json`；檔案不存在或壞掉時回預設值。
  - 預設值：`{"book":"luk","ch":4,"v":27,"image":"assets/jordan.jpg","alt":"一位男子站在約但河水中，仰望從雲層灑下的光","music":"assets/home-music.mp3"}`。
  - `images`：`<SITE_ROOT>/site/assets/` 底下副檔名為 jpg／jpeg／png／webp 的檔案，格式 `assets/<檔名>`，排序；`music`：副檔名 mp3 的。
- `GET /api/book/<key>`（不需 token，唯讀）：`key` 必須是 `mat/mrk/luk/jhn` 之一，回 `<SITE_ROOT>/data/<key>.json` 的內容（JSON，原樣）；其他 key 回 404。這是給後台畫面預覽經文用的（後台在 8091、前台在 8090，瀏覽器不能跨來源直接讀）。
- `POST /api/home`：內容是 JSON。
  - 先看 `Content-Length`：超過 65536 回 413（不讀內容）；不是合法 JSON 物件回 400。
  - 欄位必須剛好是 `book, ch, v, image, alt, music`，多一個或少一個都回 400。
  - `book` 在 `mat/mrk/luk/jhn`；`ch`、`v` 是 int（不是字串、不是 bool），而且在 `<SITE_ROOT>/data/<book>.json` 的 `chapters[].ch` / `verses[].v` 裡真的存在。
  - `image`、`music` 必須符合 `^assets/[A-Za-z0-9._-]+$`，不含 `..`，對應檔案（`<SITE_ROOT>/site/<image>`）已存在；`image` 副檔名限 `.jpg .jpeg .png .webp`，`music` 限 `.mp3`（比較時轉小寫）。
  - `alt`：去頭尾空白後 1–120 字。
  - 驗證全部通過才寫入 `<SITE_ROOT>/data/home.json`：JSON（`ensure_ascii=False, indent=2`，結尾換行），先寫到同目錄的暫存檔（`tempfile.mkstemp`，dir 同目錄），`os.replace` 取代；任何錯誤都要刪掉暫存檔。成功回 200 `{"ok": true, "config": {...}}`。驗證不過回 400，**不得改動 home.json**。
- `POST /api/home/reset`：把 home.json 寫成預設值（同樣原子寫入），回 200 `{"ok": true, "config": {...}}`。不刪任何 assets 檔。
- `POST /api/upload?kind=image|music&name=<原檔名>`：請求內容是原始位元組。
  - `kind` 只能是 `image` 或 `music`，否則 400。
  - 先看 `Content-Length`：0 或缺少回 400；image 超過 5 MiB（5×1024×1024）、music 超過 8 MiB 回 413，不讀內容、不留檔。
  - 用檔頭 magic bytes 判斷真實格式：JPEG 以 `ff d8 ff` 開頭；PNG 以 `89 50 4e 47 0d 0a 1a 0a` 開頭；WebP 為 `RIFF` + 4 byte + `WEBP`；MP3 以 `ID3` 開頭，或前兩個位元組是 `ff` 加上 `(第二個 byte & 0xe0) == 0xe0`。`kind=image` 只收前三種，`kind=music` 只收 MP3；格式不符回 400，不留檔。
  - 存檔名完全由伺服器決定：`upload-<UTC 時間 YYYYMMDD-HHMMSS>-<4 位隨機 hex>.<由真實格式決定的副檔名 jpg/png/webp/mp3>`，存到 `<SITE_ROOT>/site/assets/`；`name` 參數只用來顯示，不可影響檔名與路徑（含 `../` 也無妨）。用 `O_EXCL` 建立避免覆蓋既有檔；寫入中失敗要刪掉殘檔。成功回 200 `{"ok": true, "path": "assets/<檔名>", "bytes": N}`。
- 上述端點的路由加在現有 `do_GET`／`do_POST` 裡；`/api/token`、`/api/home` 要放在 `startswith("/api/")` 的 404 分支之前。`do_HEAD` 規則不變。

## 5. 其他
- 所有新字串（錯誤訊息）用繁體中文，不要簡體字或日文；沒有任何 Traceback 外洩給使用者（例外用 try/except 轉成 500 JSON，且訊息不含路徑）。
- 不要執行 `build_data.py`，不要修改 `data/` 底下的任何檔案（`home.json` 只能經由上面的端點寫），不要啟動或停止任何服務。
- 完成後自己跑：`python3 -m py_compile bible-site/admin/server.py`。驗收腳本會跑 `service_checks.py homeadmin` 與 `admin`，結果以腳本為準。
