# 管理後台與服務腳本複審報告

- 複審時間：2026-11-02 21:35–22:05（Asia/Taipei）
- 對象：`bible-site/admin/server.py`、`bible-site/admin/admin.js`、`bible-site/admin/index.html`、專案根目錄 `start.sh`
- 依據：`bible-site/tasks/50-admin-server.md`、`51-admin-ui.md`、`52-start-sh.md`
- 複審者：Front-end Engineer（本會話）。**未修改任何程式碼**；本報告是本次唯一新增檔案。
- 受測方式：讀原始碼逐條對照 ＋ 獨立啟動暫存後台（隨機自由埠、127.0.0.1）與 `FRONTEND_PORT=18190 BACKEND_PORT=18191` 實測。

## 紅線遵守情形

| 項目 | 結果 |
|---|---|
| 不動／不重啟線上 8090、8091 | 遵守。複審前後 PID 皆為 1277554（8090）／1277567（8091），未變 |
| 不以預設埠執行 start.sh | 遵守。所有 start/stop 皆用 `FRONTEND_PORT=18190 BACKEND_PORT=18191` |
| 不刪改 `logs/frontend.pid`、`logs/backend.pid` | 遵守。前後 md5 相同（`4760e168…`、`51a14d0c…`） |
| 不修改任何程式碼 | 遵守。僅新增本報告 |

## 執行 `python3 bible-site/tests/service_checks.py`

**結果：全部通過（30 項，exit 0）**

```
通過：後台檔案沒有簡體字
通過：server.py 的 --host 預設是 127.0.0.1（127.0.0.1）
通過：admin.js、index.html 沒有寫死 127.0.0.1:8090
通過：index.html 沒有過時的「47 項」
通過：admin.js 送出 POST 時帶 X-Bible-Admin 標頭
通過：GET /api/status 回 200 且 total_verses 為 3776
通過：任何回應都沒有 Access-Control-* 標頭
通過：GET /api/unknown 回 404 並有內容
通過：GET /nonexistent.png 回 404
通過：靜態檔只提供 index.html、admin.js、admin.css（server.py 回 404）
通過：/api/report/ 只讀白名單報告（CLAUDE.md、HANDOFF.md 等回 404）
通過：POST /api/action/smoke_test 沒帶 X-Bible-Admin 回 403
通過：POST 帶 X-Bible-Admin 但 Origin 是外站回 403
通過：POST 帶 X-Bible-Admin 與同源 Origin 可執行 smoke_test
通過：POST /api/action/build_data 已移除（回 404）
通過：後台處理請求時沒有 Traceback
通過：start.sh 沒有用 pkill／killall 依名稱殺行程
通過：start.sh start（18190/18191）成功且兩個埠都在監聽
通過：後台預設只綁 127.0.0.1（18191）
通過：前台 /site/index.html 與後台 /api/ping 都回 200
通過：PID 檔名帶埠號
通過：start.sh stop 後兩個埠都釋放
通過：埠被外來行程佔用時 start 回報錯誤並以非 0 結束（不沿用）
通過：stop 不會殺掉外來行程
通過：線上 8090/8091 服務的 PID 沒有變
通過：線上服務的 logs/frontend.pid、backend.pid 沒有被改或刪
結果：全部通過
```

**但腳本通過不代表程式正確。** 下列逐條對照發現 3 個腳本沒涵蓋的實質問題。

---

## 一、任務 50（`server.py`）逐條對照

| # | 要求 | 判定 | 證據（行號） |
|---|---|---|---|
| 50-1 | 移除所有 CORS（三行 `Access-Control-*`、整個 `do_OPTIONS`） | **通過** | 全檔無 `Access-Control`、無 `do_OPTIONS`；實測 GET/POST/OPTIONS 回應皆無 CORS 標頭 |
| 50-2 | `log_message` 改用 `sys.stderr.write(... format % args)`，且不准簡體字 | **通過** | L99–101 完全符合；`send_error` 兩參數路徑不再當掉（PUT/DELETE/PATCH 回 501 且 body 完整，非空回應）。簡體字掃描：無 |
| 50-3 | 靜態檔白名單 `/`、`/index.html`、`/admin.js`、`/admin.css`，其他 404 | **不通過** | L130–135 的 `do_GET` 白名單正確，**但未覆寫 `do_HEAD`**（見下方「問題 1」） |
| 50-4 | `/api/report/<name>` 白名單 5 檔、只從 SITE_ROOT 讀、其他 404 | **通過** | L72 白名單、L278–291 用 `os.path.basename` 後比對、L283 只在 SITE_ROOT。實測 5 檔全 200；CLAUDE.md、HANDOFF.md、SERVICE-REPORT.md、PLAN.md 回 404；`..%2f`、`%2e%2e%2f`、`%00` 皆 404 |
| 50-5 | 刪除 `build_data` 動作 | **通過** | 全檔無 `build_data`；POST 該路徑回 404 |
| 50-6 | `do_POST` 先檢查 `X-Bible-Admin: 1`，再檢查 Origin（有才檢查、須等於 `http://`＋Host） | **通過** | L137–149。實測：無標頭 403、值 0/true/yes/2/空 皆 403、外站 Origin 403、`https://` 403、`Origin: null` 403、無 Origin 200、同源 200 |
| 50-7 | `ACTION_LOCK` 模組層級、`acquire(blocking=False)`、拿不到回 409、finally 釋放 | **通過** | L73 定義、L295 acquire、L296 回 409、L325–326 finally release。實測 4 個併發請求：1 個 200、3 個 409，鎖有效 |
| 50-8 | `--host` 預設 `127.0.0.1`、說明文字、`run_server` 預設值 | **通過** | L334 `def run_server(host="127.0.0.1"…)`、L352 預設與說明文字皆符合 |

### 問題 1（實質漏洞）：`HEAD` 方法完全繞過靜態檔白名單

- **位置**：`bible-site/admin/server.py` L112–135（`do_GET` 有白名單）、L95–97（只覆寫 `__init__`，**未定義 `do_HEAD`**）
- **原因**：`SimpleHTTPRequestHandler` 內建 `do_HEAD`，其行為等於 `do_GET` 但不送 body。因為子類別沒有覆寫 `do_HEAD`，`HEAD` 請求會直接落到父類別的實作，**不經過 L130–135 的白名單判斷**。
- **實測**：

  | 請求 | 結果 |
  |---|---|
  | `GET /server.py` | **404**（正確） |
  | `HEAD /server.py` | **200**，`Content-Length: 14354`（= server.py 實際大小） |
  | `GET /__pycache__/` | 404（正確） |
  | `HEAD /__pycache__/` | **200**，`Content-Length: 280` |

  以 `HEAD` 逐檔探測可確認原始碼檔名、存在與大小，洩漏了 L130–135 想阻擋的資訊。
- **判定**：**不通過**（任務 50 第 3 點「其他非 /api/ 路徑一律回 404」未被 `HEAD` 遵守）
- **修法建議**：在 `AdminRequestHandler` 加
  ```python
  def do_HEAD(self):
      self.do_GET()   # do_GET 已含白名單判斷；send_json 會寫 body，需改為只送標頭
  ```
  更穩妥是抽一個 `route(path, send_body)` 給 GET/HEAD 共用，HEAD 時不寫 body。

---

## 二、任務 51（`admin.js`、`index.html`）逐條對照

| # | 要求 | 判定 | 證據（行號） |
|---|---|---|---|
| 51-1 | POST 帶 `X-Bible-Admin: 1`；409 顯示「已有動作執行中，請稍候」 | **通過** | `admin.js` L127 帶標頭；L129–133 處理 409 並顯示指定文字 |
| 51-2 | 前台網址不可寫死 127.0.0.1；用 `location.hostname` 組；兩檔不得出現 `127.0.0.1:8090` | **通過** | `admin.js` L76 用 `${location.protocol}//${location.hostname}:8090/…`；L179–201 `setLinks()` 組前台/後台網址；`index.html` L21、L145 皆為 `href="#"` 加 id。grep 兩檔：無 `127.0.0.1:8090` |
| 51-3 | 「visual_checks.py 47 項」改成「visual_checks.py」 | **通過** | `index.html` L115 為 `🎨 視覺與無障礙檢驗 (visual_checks.py)`，無「47 項」 |
| 51-4 | 刪掉 build_data 按鈕與對應處理 | **通過** | 兩檔皆無 `build_data` |
| 51-5 | 全繁體、不載外部資源 | **通過** | 簡體字掃描：`admin.js`／`index.html`／`admin.css` 皆無。外部資源：三檔皆無 `http(s)://` 載入、無 `@import`、無外部 `<link>`／`<script src>`（只有 `data:` icon 與本地 `admin.css`／`admin.js`） |

**附註（非不通過，僅記錄）**：`index.html` L34 標題寫死「前台網站 (Port 8090)」、L112「check_all.py 3/3」。前者在改用非 8090 埠時會與實際不符，後者為固定文案；任務 51 未要求修改，故不列為缺陷。

---

## 三、任務 52（`start.sh`）逐條對照

| # | 要求 | 判定 | 證據（行號） |
|---|---|---|---|
| 52-1 | PID 檔名帶埠號 | **通過** | L46–47 `frontend-${FRONTEND_PORT}.pid`、`backend-${BACKEND_PORT}.pid`；實測產生 `frontend-18190.pid`、`backend-18191.pid` |
| 52-2 | 新增 `is_our_service <pid> <kind>`，用 `ps -o args=` 比對 | **部分通過，見問題 2** | L99–120 已實作，但 frontend 條件比規格多要求 `--bind ${BIND_HOST}`（見問題 2） |
| 52-3 | 埠被佔用：`is_our_service` 成立才沿用並寫 PID；否則報錯 exit 1、**不寫 PID 檔** | **通過** | L231–243、L270–281。實測：外來行程（非 lookalike）佔 18190 時 `rc=1`、錯誤訊息含 PID 與指令列、**未寫 PID 檔**、外來行程存活 |
| 52-4 | `stop_services` 只有 `is_our_service` 成立才 kill；不成立 `print_warn`；PID 檔只刪本埠 | **通過** | L192–208、L211–227。實測外來行程不會被殺 |
| 52-5 | `BACKEND_BIND` 預設 `127.0.0.1`、`start_backend` 用 `--host`、status/啟動訊息依 bind 顯示 | **通過** | L40 預設、L284 `--host "${BACKEND_BIND}"`、L154–160 與 L326–332 條件顯示。實測後台綁 `127.0.0.1`，前台仍 `0.0.0.0` |
| 52-6 | 啟動確認改成最多 5 秒、每 0.5 秒檢查、PID 須等於剛啟動的 PID、逾時 exit 1 | **通過** | L251–266、L288–303（`attempts < 10`、`sleep 0.5`） |
| 52-7 | 不准 `pkill`／`killall`／依名稱殺 | **通過** | 全檔無 `pkill`／`killall`；kill 都針對 `get_port_pid` 取得的 PID |

### 問題 2（實質 bug）：`is_our_service` 的 frontend 判斷多要求 `--bind`，導致「自己啟動的服務停不掉」

- **位置**：`start.sh` L105
  ```bash
  if [[ "${cmdline}" == *"http.server ${FRONTEND_PORT}"* && "${cmdline}" == *"--bind ${BIND_HOST}"* ]]; then
  ```
- **規格要求**（任務 52 第 2 點）：kind=frontend 時**只需**包含 `"http.server ${FRONTEND_PORT}"`。實作**多加**了 `--bind ${BIND_HOST}` 條件。
- **觸發情境**：`BIND_HOST` 是「執行當下」的環境變數，不是服務啟動時的記錄。若使用者以 `BIND_HOST=127.0.0.1` 啟動，之後再以預設值執行 `./start.sh stop`（`BIND_HOST=0.0.0.0`），字串比對失敗。
- **實測（以測試埠 18190/18191）**：
  ```
  啟動：BIND_HOST=127.0.0.1  → 程序為 python3 -u -m http.server 18190 --bind 127.0.0.1
  停止：不帶 BIND_HOST（預設 0.0.0.0）
  結果：[WARN] Port 18190 由其他程式佔用，不處理   ← 自己的服務被當成外來程式
        [SUCCESS] 後台服務已停止。
  停止後 18190 仍在監聽（前台殘留）
  ```
- **判定**：**不通過**（任務 52 第 4 點「自己啟動的服務要能停掉」在此情境失效；也是第 2 點未照規格實作）
- **修法建議**：frontend 條件只比對 `"http.server ${FRONTEND_PORT}"`；若要連 bind 一起驗，應把實際 bind 記在 PID 檔旁（如 `frontend-<port>.bind`），不要依賴執行當下的 `BIND_HOST`。

### 問題 3（設計弱點）：只靠指令列字串比對，外來行程可被「沿用」並被殺

- **位置**：`start.sh` L99–120（`is_our_service`）＋ L234–237、L273–276（沿用並寫 PID 檔）
- **原因**：`is_our_service` 只比對 `ps -o args=` 的字串。任何人在該埠跑一個指令列剛好包含 `http.server 18190 --bind 0.0.0.0`（或 `admin/server.py … --port 18191`）的行程，就會被認定是「本服務」。
- **實測**：在 `/tmp` 另起 `python3 -u -m http.server 18190 --bind 0.0.0.0`（與本專案無關的行程），於專案目錄執行 `start.sh start`：
  ```
  [WARN] Port 18190 已被本服務佔用（PID 1351149），沿用既有服務。
  ```
  接著執行 `stop`：
  ```
  [INFO] 停止前台服務 (PID: 1351149, Port: 18190)...
  [SUCCESS] 前台服務已停止。
  外來行程仍存活? 否——已被殺
  ```
- **判定**：**不通過**（任務 52 的核心訴求「外來行程不沿用也不殺」未完全達成；`service_checks.py` 的外來行程用的是純 `http.server <port> --bind 127.0.0.1`，恰好不含 `--bind 0.0.0.0` 以外差異，所以沒抓到）
- **說明**：這是規格本身的設計限制（規格就是指定用字串比對），若要根治需改用 `ss -ltnp` 取得的 inode／cwd／`/proc/<pid>/cwd` 或 PID 檔＋啟動時間戳交叉驗證。**建議在報告層級標為「需人工決策」而非單純程式 bug**，但就「任務要求的行為」而言實測失敗，故仍列不通過。

---

## 四、介面語言與外部資源

| 項目 | 判定 | 證據 |
|---|---|---|
| 後台全繁體中文 | **通過** | `server.py`、`admin.js`、`index.html`、`admin.css` 逐字掃描：無簡體字 |
| 不載入外部資源 | **通過** | 四檔皆無 `http(s)://` 外部載入；`index.html` 僅 `data:` icon ＋本地 `admin.css`／`admin.js`；`admin.css` 無 `@import`／外部 `url()` |
| `start.sh` 全繁體 | **通過** | 掃描無簡體字 |

---

## 五、結論

| 分類 | 數量 |
|---|---|
| 通過 | 17（任務 50 七項、任務 51 五項、任務 52 五項，另含介面語言與外部資源） |
| 不通過 | 3（問題 1／2／3） |
| 需人工 | 0 |

**需修正的優先順序**：
1. **問題 2**（`is_our_service` 多比對 `--bind`）— 會讓使用者「停不掉自己啟動的前台」，最直接影響日常操作。
2. **問題 1**（`HEAD` 繞過靜態白名單）— 可探測 `server.py`、`__pycache__` 的存在與大小，屬資訊洩漏。
3. **問題 3**（字串比對可被冒用）— 規格本身的設計限制，建議 PM 決定是否改為更強的識別方式。

**附註**：`service_checks.py` 30 項全過，但上述 3 個問題都不在它的涵蓋範圍（未測 `HEAD`、未測 `BIND_HOST` 變動後 stop、外來行程用了不會被誤認的指令列）。建議後續把它們補進 `service_checks.py`。

總計：通過 17 項、不通過 3 項、需人工 0 項（共 20 項）。
