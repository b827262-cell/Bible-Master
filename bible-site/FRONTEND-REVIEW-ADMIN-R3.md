# 管理後台與服務腳本複審報告（第三輪）

- 複審時間：2026-11-02 22:43–23:00（Asia/Taipei）
- 對象：專案根目錄 `start.sh`（`SCRIPT_DIR` 改用 `pwd -P`）
- 依據：`bible-site/tasks/54-start-sh-realpath.md`；前一輪報告 `FRONTEND-REVIEW-ADMIN-R2.md` 的「新問題 1」
- 複審者：Front-end Engineer（本會話）。**未修改任何程式碼**；本報告是本次唯一新增檔案。

## 紅線遵守情形

| 項目 | 結果 |
|---|---|
| 不動／不重啟線上 8090、8091 | 遵守。前後 PID 皆 1277554（8090）／1277567（8091），兩者仍回 200 |
| 只用 18190/18191 | 遵守。全部 start/stop 皆 `FRONTEND_PORT=18190 BACKEND_PORT=18191` |
| 不動 `logs/frontend.pid`、`logs/backend.pid` | 遵守。前後 md5 相同（`4760e168…`、`51a14d0c…`） |
| 不改程式碼 | 遵守。`start.sh` mtime 仍為 22:39，未變 |
| 測完清掉殘留行程與暫存軟連結 | 遵守。18190/18191 皆空、`/tmp/symtest`、`/tmp/symx`、`/tmp/symtest2` 已刪除、`logs/` 只剩四個正式檔 |

## 修正內容確認

`start.sh` L22：

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
```

與任務 54 要求一字不差（只改這一行，其餘未動）。`grep pwd` 顯示另一處 L27 `PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"` 未加 `-P`，但經實測無影響（見 N2）。

---

## 一、重測「新問題 1」：軟連結路徑 start→stop

**方法沿用上一輪**：建立 `/tmp/symtest/proj -> <ROOT>`，從軟連結路徑執行 start 與 stop，使用 18190/18191。

### 1-1 軟連結啟動 → 同路徑 stop — **通過**

```
軟連結: /tmp/symtest/proj -> /home/b827262/project/AI/Bible-Master
shell pwd（未解）: /tmp/symtest/proj
shell pwd -P     : /home/b827262/project/AI/Bible-Master
start rc=0
  18190 PID=1427567 cwd=/home/b827262/project/AI/Bible-Master/bible-site
  18191 PID=1427578 cwd=/home/b827262/project/AI/Bible-Master
--- 同路徑 stop ---
stop rc=0
[INFO] 正在停止 Bible-Master 前台與後台服務...
[INFO] 停止前台服務 (PID: 1427567, Port: 18190)...
[SUCCESS] 前台服務已停止。
[INFO] 停止後台服務 (PID: 1427578, Port: 18191)...
[SUCCESS] 後台服務已停止。
--- stop 後埠狀態 ---
  ✓ 兩個埠皆已釋放
```

**對照上輪**：上輪同情境下前台顯示「Port 18190 由其他程式佔用，不處理」且 18190 殘留（PID 1382741）。

### 1-2 交叉情境（額外驗證，確認不只是同路徑巧合）

| 情境 | 結果 | 判定 |
|---|---|---|
| 軟連結啟動 → **實體路徑** stop | stop rc=0，兩埠釋放 | **通過** |
| 實體路徑啟動 → **軟連結** stop | stop rc=0，兩埠釋放 | **通過** |
| 軟連結 A 啟動 → **另一個軟連結 B** stop（`proj` / `proj2` 指向同一專案） | stop rc=0，兩埠釋放 | **通過** |

三種交叉情境都通過，代表 `pwd -P` 讓 `SITE_ROOT` 不論從哪條路徑呼叫都統一成實體路徑，`is_our_service` 的 `cwd` 比對才真正成立。

---

## 二、三種啟動方式一致性與線上服務認定

### 2-1 `SITE_ROOT` 在六種組合下是否一致 — **通過**

| 呼叫路徑 | 實體路徑呼叫 | 軟連結路徑呼叫 |
|---|---|---|
| `<ROOT>/start.sh`（A 分支） | `<ROOT>/bible-site` | `<ROOT>/bible-site` |
| `<ROOT>/service.sh`（A 分支，軟連結） | `<ROOT>/bible-site` | `<ROOT>/bible-site` |
| `<ROOT>/bible-site/start.sh`（B 分支，軟連結） | `<ROOT>/bible-site` | `<ROOT>/bible-site` |

六種組合全部解析為同一個 `SITE_ROOT`：`/home/b827262/project/AI/Bible-Master/bible-site`。

### 2-2 `PROJECT_ROOT` 是否也一致（檢查 L27 未加 `-P` 的影響） — **通過**

因 `SCRIPT_DIR` 已是實體路徑，L27 的 `cd "${SCRIPT_DIR}/.." && pwd` 必然也得到實體路徑。實測：

| 呼叫路徑 | 分支 | `PROJECT_ROOT` | `SITE_ROOT` |
|---|---|---|---|
| `<ROOT>/start.sh` | A | `<ROOT>` | `<ROOT>/bible-site` |
| `<LINK>/start.sh` | A | `<ROOT>` | `<ROOT>/bible-site` |
| `<LINK>/bible-site/start.sh` | B | `<ROOT>` | `<ROOT>/bible-site` |

### 2-3 線上 8090/8091 是否仍被 `is_our_service` 認定 — **通過**

以兩種方式驗證（第二種避免把腳本複製到 `/tmp` 造成 `SCRIPT_DIR` 偏差）：

```
SITE_ROOT=/home/b827262/project/AI/Bible-Master/bible-site
8090 PID=1277554 cwd=/home/b827262/project/AI/Bible-Master/bible-site
→ 8090 frontend = 0（認定為本服務）
→ 8091 backend  = 0（認定為本服務）
--- 反向測試（應為 1）---
PID 1 frontend = 1（正確）
自身 backend   = 1（正確）
```

線上服務實況：8090／8091 皆 LISTEN，`/site/index.html` 與 `/api/ping` 都回 200。

### 2-4 軟連結啟動時，後台指令列是否為實體絕對路徑 — **通過**

```
後台 PID=1431083
cmd=python3 -u /home/b827262/project/AI/Bible-Master/bible-site/admin/server.py --host 127.0.0.1 --port 18191
含實體路徑 '<ROOT>/bible-site/admin/server.py'? 是
含軟連結路徑 '/tmp/symtest/proj'? 否（正確）
```

後台的 `is_our_service` 條件（完整絕對路徑）在軟連結啟動時仍成立，且不會把軟連結字串寫進指令列。

---

## 三、執行 `python3 bible-site/tests/service_checks.py`

**結果：全部通過（36 項，exit 0）**；`bash -n start.sh` 亦通過。

相較上一輪（35 項）新增 1 項並通過：

```
通過：經由軟連結路徑啟動、同路徑 stop 後兩個埠都釋放（rc=0）
```

其餘 35 項維持通過，包含：後台無簡體字、`--host` 預設 127.0.0.1、無寫死 127.0.0.1:8090、`X-Bible-Admin` 標頭、無 CORS、404 有內容、靜態白名單、**HEAD 白名單**、報告白名單、POST 各項 403／200、build_data 已移除、無 Traceback、無 pkill／killall、**BIND_HOST 不同時 stop**、**兩種仿冒行程不沿用也不殺**、線上 PID 與兩個 `.pid` 檔未變。

---

## 四、是否引入新問題

| # | 檢查項 | 判定 | 說明 |
|---|---|---|---|
| N1 | L27 的 `pwd` 未加 `-P` 是否造成不一致 | **通過** | `SCRIPT_DIR` 已是實體路徑，其父目錄必然也是；實測 `PROJECT_ROOT` 在實體／軟連結呼叫下皆相同 |
| N2 | `pwd -P` 是否影響 `bible-site/start.sh`（B 分支） | **通過** | B 分支 `SITE_ROOT="${SCRIPT_DIR}"` 直接沿用實體路徑，實測 start/stop 正常、兩埠釋放 |
| N3 | 是否影響 logs 目錄位置 | **通過** | `LOG_DIR="${PROJECT_ROOT}/logs"`，`PROJECT_ROOT` 為實體路徑 → 仍指向專案 `logs/`，未產生 `/tmp` 下的新 logs |
| N4 | 是否影響 `cd "${PROJECT_ROOT}"` 後的路徑 | **通過** | 所有 start/stop 皆正常，`logs/frontend-18190.pid`、`backend-18191.pid` 產生於正確位置 |
| N5 | 是否使用 `pkill`／`killall` | **通過** | `grep` 全檔無 |
| N6 | 是否引入簡體字 | **通過** | 掃描無 |
| N7 | 其他行為（restart/status/logs/-f/--systemd）是否被動到 | **通過** | 只改 L22 一行，`git` 無其他差異；未測項不在本次範圍 |

**未發現新問題。**

---

## 五、結論

| 分類 | 數量 |
|---|---|
| 通過 | 10 |
| 不通過 | 0 |
| 需人工 | 0 |

**逐項總覽**

| 項目 | 判定 | 依據 |
|---|---|---|
| 修正內容：L22 改為 `pwd -P` | 通過 | `start.sh` L22 |
| 新問題 1：軟連結同路徑 start→stop 兩埠釋放 | 通過 | 實測 18190/18191 |
| 交叉 A：軟連結啟動 → 實體 stop | 通過 | 實測 |
| 交叉 B：實體啟動 → 軟連結 stop | 通過 | 實測 |
| 交叉 C：軟連結 A 啟動 → 軟連結 B stop | 通過 | 實測 |
| `SITE_ROOT` 三種啟動方式 × 實體／軟連結共 6 種一致 | 通過 | `start.sh` L22–32 |
| `PROJECT_ROOT` 一致（L27 無落差） | 通過 | 實測 |
| 線上 8090/8091 仍被 `is_our_service` 認定（含反向測試） | 通過 | `start.sh` L99–125 |
| 軟連結啟動時後台指令列為實體絕對路徑 | 通過 | `start.sh` L290 |
| `service_checks.py` 36 項全過（含新增軟連結項） | 通過 | exit 0 |
| 是否引入新問題（N1–N7） | 通過 | 無 |

**建議**：`pwd -P` 這一行修得正確且最小。若日後想更保險，可把 L27 也改成 `pwd -P`（語意更明確，目前無實際差異）；另建議把本輪三種交叉情境（軟連結↔實體）補進 `service_checks.py`，目前只測了「同為軟連結路徑」。

總計：通過 10 項、不通過 0 項、需人工 0 項（共 10 項）。
