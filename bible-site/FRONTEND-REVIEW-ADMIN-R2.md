# 管理後台與服務腳本複審報告（第二輪）

- 複審時間：2026-11-02 22:11–22:40（Asia/Taipei）
- 對象：`bible-site/admin/server.py`（新增 `do_HEAD`）、專案根目錄 `start.sh`（`is_our_service` 改寫）
- 依據：`bible-site/tasks/53-admin-review-fixes.md`；前一輪報告 `FRONTEND-REVIEW-ADMIN.md` 的問題 1、2、3
- 複審者：Front-end Engineer（本會話）。**未修改任何程式碼**；本報告是本次唯一新增檔案。
- 受測方式：讀原始碼逐條對照 ＋ 獨立啟動暫存後台（隨機自由埠、127.0.0.1）＋ `FRONTEND_PORT=18190 BACKEND_PORT=18191` 實際啟停 ＋ 仿冒行程實測。

## 紅線遵守情形

| 項目 | 結果 |
|---|---|
| 不動／不重啟線上 8090、8091 | 遵守。前後 PID 皆 1277554（8090）／1277567（8091），兩者 `curl` 仍回 200 |
| 不用預設埠執行 start.sh | 遵守。全部用 `FRONTEND_PORT=18190 BACKEND_PORT=18191` |
| 不刪改 `logs/frontend.pid`、`logs/backend.pid` | 遵守。前後 md5 相同（`4760e168…`、`51a14d0c…`） |
| 不修改任何程式碼 | 遵守。`start.sh`、`server.py` mtime 仍為 22:07，未變 |
| 測試後 18190/18191 無殘留 | 遵守。最終檢查兩埠皆空，`logs/` 也無 `*-18190.pid`／`*-18191.pid` |

## 執行 `python3 bible-site/tests/service_checks.py`

**結果：全部通過（35 項，exit 0）**

相較上一輪（30 項）新增 5 項且全數通過：

```
通過：HEAD 也套用同一份白名單（HEAD /server.py、/__pycache__/ 回 404）
      （{"/": 200, "/admin.js": 200, "/server.py": 404, "/__pycache__/": 404, "/api/unknown": 404}）
通過：以 BIND_HOST=127.0.0.1 啟動、預設環境 stop 後兩個埠都釋放（rc=0）
通過：外來行程的指令列與前台相同（/tmp 下的 http.server 18190 --bind 0.0.0.0）：start 不沿用並以非 0 結束（rc=1）
通過：外來行程的指令列與前台相同（…）：stop 不會殺掉它
通過：外來行程的指令列含 admin/server.py --port 18191（不是本專案的 server.py）：start 不沿用並以非 0 結束（rc=1）
通過：外來行程的指令列含 admin/server.py --port 18191（…）：stop 不會殺掉它
通過：線上 8090/8091 服務的 PID 沒有變
通過：線上服務的 logs/frontend.pid、backend.pid 沒有被改或刪
結果：全部通過
```

`py_compile`、`bash -n`、`node --check` 皆通過。

---

## 一、前一輪三個問題的重新實測

### 問題 1：`HEAD` 繞過靜態檔白名單 — **通過（已修好）**

- **位置**：`server.py` L137–148（新增 `do_HEAD`），L141 白名單與 L143 `super().do_HEAD()`
- **獨立實測**（自起暫存後台，非專案腳本）：

| 請求 | 修正前（上輪） | 修正後（本輪） |
|---|---|---|
| `HEAD /server.py` | **200**，CL=14354 | **404**，CL=0，body 0B |
| `HEAD /__pycache__/` | **200**，CL=280 | **404**，CL=0 |
| `HEAD /admin.css` | 200 | 200，CL=6816（= 實際大小），body 0B |
| `HEAD /index.html` | 200 | 200，CL=5516（= 實際大小），body 0B |
| `HEAD /` | 200 | 200，CL=5516，body 0B |

- 額外驗證：`HEAD /server.py.bak`、`/admin/server.py`、`/CLAUDE.md`、`/nonexistent.png` 皆 404；帶查詢字串 `HEAD /server.py?x=1` 仍 404；`HEAD /admin.js?cache=1` 正確 200。
- **判定：通過**。`server.py` 的大小（14933B）不再從 `HEAD` 洩漏。

### 問題 2：`is_our_service` 多比對 `--bind`，自己啟動的服務停不掉 — **通過（已修好）**

- **位置**：`start.sh` L105——frontend 條件只剩 `*"http.server ${FRONTEND_PORT}"*`，`--bind` 比對已刪除
- **實測**（18190/18191）：

```
啟動：BIND_HOST=127.0.0.1 bash start.sh start   → rc=0，18190 PID 1380280、18191 PID 1380291
停止：bash start.sh stop（不帶 BIND_HOST，預設 0.0.0.0）
結果：[INFO] 停止前台服務 (PID: 1380280, Port: 18190)... [SUCCESS] 前台服務已停止。
      [INFO] 停止後台服務 (PID: 1380291, Port: 18191)... [SUCCESS] 後台服務已停止。
停止後：18190/18191 皆已釋放；無殘留 PID 檔
```

- **對照上輪**：上輪同樣情境下前台顯示「Port 18190 由其他程式佔用，不處理」且 18190 殘留。本輪已能正常停止。
- **判定：通過**。

### 問題 3：只靠指令列字串比對，外來行程被沿用並被殺 — **通過（已修好）**

- **位置**：`start.sh` L105–114（frontend 加上 `/proc/<pid>/cwd` 比對）、L116–122（backend 改比對完整絕對路徑）
- **實測 A（前台仿冒）**：在 `/tmp/fake` 啟動指令列**完全相同**的 `python3 -u -m http.server 18190 --bind 0.0.0.0`

```
仿冒 cwd=/tmp/fake（≠ SITE_ROOT）
start  → rc=1  [ERROR] Port 18190 被其他程式（PID 1380554：python3 -u -m http.server 18190 --bind 0.0.0.0）佔用，未啟動
PID 檔 → 未寫（正確）
stop   → 仿冒行程仍存活（正確）
```

- **實測 B（後台仿冒）**：在 `/tmp/fake` 用複製出來的 `server.py` 啟動 `--port 18191`（指令列含 `admin/server.py`，但非本專案絕對路徑）

```
仿冒 cmd=python3 -u ./server.py --host 127.0.0.1 --port 18191
start  → rc=1  [ERROR] Port 18191 被其他程式（PID 1380624：…）佔用，未啟動
PID 檔 → 未寫（正確）
stop   → 仿冒行程仍存活（正確）
```

- **對照上輪**：上輪同樣的仿冒 A 會被「沿用」並在 stop 時被殺。本輪兩個情境都正確拒絕且不殺。
- **判定：通過**。

---

## 二、修正是否引入新問題

| # | 檢查項 | 判定 | 證據 |
|---|---|---|---|
| N1 | `do_HEAD` 對 `/api/...` 的行為 | **通過** | `HEAD /api/ping`、`/api/status`、`/api/models`、`/api/tasks`、`/api/unknown`、`/api/report/TEST-REPORT.md` 全回 **404**、CL=0、body 0B（符合任務 53 指定：`/api/` 開頭也走 404 標頭） |
| N2 | `do_HEAD` 是否影響其他 HTTP 方法 | **通過** | `OPTIONS/PUT/DELETE` 仍回 501（父類行為）、`GET /api/status` 200、`POST smoke_test` 200，皆與修正前一致；無 CORS 標頭 |
| N3 | `do_HEAD` 404 回應是否只送標頭 | **通過** | 實測標頭為 `Content-Type: application/json; charset=utf-8`、`Content-Length: 0`，body 0B（完全符合任務 53 指定的三行） |
| N4 | 靜態檔 `HEAD` 的 `Content-Type`／`Last-Modified` | **通過** | `HEAD /admin.css` 與 `GET /admin.css` 標頭完全一致（`Content-type: text/css`、`Content-Length`、`Last-Modified` 皆同）；`super().do_HEAD()` 正確沿用 |
| N5 | `SITE_ROOT` 在三種啟動方式是否一致 | **通過** | 見下表，三者皆解析為 `<ROOT>/bible-site` |
| N6 | 線上 8090/8091 是否仍被認定為本服務 | **通過** | 直接呼叫 `is_our_service`：8090 frontend → 0、8091 backend → 0；反向測試 PID 1／自身 → 1（正確排除） |
| N7 | `bible-site/start.sh`（B 分支）實際啟停 | **通過** | 啟動後 18190 cwd=`<ROOT>/bible-site`、18191 正常；stop 後兩埠皆釋放 |
| N8 | `service.sh`（軟連結）實際啟停 | **通過** | start rc=0、stop rc=0，兩埠皆釋放 |
| N9 | 是否使用 `pkill`／`killall` | **通過** | `grep` 全檔無 |
| N10 | 簡體字 | **通過** | `start.sh`、`server.py` 掃描皆無 |
| N11 | 透過符號連結路徑啟動時的 cwd 比對 | **不通過** | 見下方「新問題 1」 |

### N5 詳細：三種啟動方式的 `SITE_ROOT`

| 呼叫方式 | 走哪個分支 | `SITE_ROOT` | `realpath` |
|---|---|---|---|
| `<ROOT>/start.sh` | A（`-d $SCRIPT_DIR/bible-site`） | `<ROOT>/bible-site` | `<ROOT>/bible-site` |
| `<ROOT>/service.sh`（軟連結） | A | `<ROOT>/bible-site` | `<ROOT>/bible-site` |
| `<ROOT>/bible-site/start.sh`（軟連結） | B（`-f $SCRIPT_DIR/site/index.html`） | `<ROOT>/bible-site` | `<ROOT>/bible-site` |

三者相同 → `is_our_service` 的 `cwd = SITE_ROOT` 比對在正常路徑下一致。

---

## 三、新問題

### 新問題 1（實質）：透過符號連結路徑啟動時，`cwd` 字串比對失準，服務停不掉

- **位置**：`start.sh` L108–111

  ```bash
  cwd="$(readlink "/proc/${pid}/cwd" 2>/dev/null || true)"
  if [ "${cwd}" = "${SITE_ROOT}" ]; then
  ```

- **原因**：`SITE_ROOT` 由 `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` 算出。`pwd` **不會解析符號連結**；而 Linux 的 `/proc/<pid>/cwd` 記錄的是**實體路徑**。當使用者透過符號連結進入專案時，兩者字串不相等。
- **實測**：建立 `/tmp/symtest/proj -> /home/b827262/project/AI/Bible-Master`，從 `/tmp/symtest/proj` 執行 `start.sh start`（18190/18191）：

  ```
  start rc=0
    前台 PID=1382741  /proc/1382741/cwd = /home/b827262/project/AI/Bible-Master/bible-site
    腳本算出的 SITE_ROOT（未解連結）= /tmp/symtest/proj/bible-site
    實體 SITE_ROOT                = /home/b827262/project/AI/Bible-Master/bible-site
  同一路徑執行 stop:
    [WARN] Port 18190 由其他程式佔用，不處理      ← 自己的服務被當成外來
    [INFO] 停止後台服務 (PID: 1382752, Port: 18191)... [SUCCESS]
    18190 殘留（PID 1382741）
  ```

- **判定**：**不通過**。這是修正 3 引入的**新**邊界問題（上輪用字串比對指令列時不會有這個落差）。日常從專案實體路徑操作不受影響，但透過軟連結（例如某些部署或 `~/proj` 連結）就會踩到。
- **修法建議**：把比對兩邊都正規化，例如
  ```bash
  local cwd_real site_real
  cwd_real="$(readlink -f "/proc/${pid}/cwd" 2>/dev/null || true)"
  site_real="$(readlink -f "${SITE_ROOT}" 2>/dev/null || true)"
  if [ -n "${cwd_real}" ] && [ "${cwd_real}" = "${site_real}" ]; then
  ```
  或在腳本開頭把 `SITE_ROOT` 改成 `$(cd "${SITE_ROOT}" && pwd -P)`。

### 附註（非缺陷，僅記錄）

- `start.sh` L105 的 frontend 比對用 `*"http.server ${FRONTEND_PORT}"*`，若埠號是 1819 而實際埠是 18190，字串 `http.server 1819` 會是 `http.server 18190` 的前綴，**理論上**可能誤配。實務上 `start.sh` 只用一個固定 `FRONTEND_PORT`，且 `get_port_pid` 已鎖定該埠的監聽者，風險極低；腳本測試的 18190/18191 也不受影響。不列為不通過，建議未來可加空格邊界（`*"http.server ${FRONTEND_PORT} "*`）。

---

## 四、結論

| 分類 | 數量 |
|---|---|
| 通過 | 14 |
| 不通過 | 1（新問題 1） |
| 需人工 | 0 |

**逐項總覽**

| 項目 | 判定 | 行號 |
|---|---|---|
| 問題 1：`HEAD` 套用靜態白名單 | 通過 | `server.py` L137–148 |
| 問題 1：`HEAD /server.py`、`/__pycache__/` 回 404 且 CL=0 | 通過 | L145–148 |
| 問題 1：`HEAD` 靜態檔標頭與 GET 一致 | 通過 | L143 |
| 問題 2：frontend 條件移除 `--bind` | 通過 | `start.sh` L105 |
| 問題 2：`BIND_HOST=127.0.0.1` 啟動、預設 stop 可停 | 通過 | L105 |
| 問題 3：frontend 加 `/proc/<pid>/cwd` 比對 | 通過 | L107–112 |
| 問題 3：backend 改比對完整絕對路徑 | 通過 | L117 |
| 問題 3：仿冒 A 不沿用、不殺 | 通過 | L105–114 |
| 問題 3：仿冒 B 不沿用、不殺 | 通過 | L117 |
| N1：`HEAD /api/...` 回 404 | 通過 | `server.py` L144–148 |
| N2：其他 HTTP 方法不受影響 | 通過 | `server.py` L150+ |
| N3：`HEAD` 404 只送標頭 | 通過 | L145–148 |
| N5／N6：`SITE_ROOT` 三種啟動一致、線上服務仍認得 | 通過 | `start.sh` L21–32、L105 |
| N7／N8：`bible-site/start.sh`、`service.sh` 實際啟停 | 通過 | `start.sh` L21–32 |
| N11：符號連結路徑下 cwd 比對 | **不通過** | `start.sh` L108–111 |
| 未使用 `pkill`／`killall`、無簡體字、`py_compile`／`bash -n`／`node --check` | 通過 | — |

**建議**：新問題 1 只需在 `start.sh` L108–111 對兩邊路徑做 `readlink -f` 正規化即可修好，屬低風險小改。修好後建議把「透過符號連結路徑啟動再 stop」補進 `service_checks.py`。

總計：通過 14 項、不通過 1 項、需人工 0 項（共 15 項）。
