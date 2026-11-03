# Launcher（start.sh）改動驗收報告

- 驗收時間：2026-11-03 13:01–13:20（Asia/Taipei）
- 受測檔案：專案根目錄 `start.sh`（`service.sh` 為指向它的符號連結）
- 規格：`bible-site/tasks/91-launcher-entry-url.md`、`bible-site/tasks/92-launcher-data-check.md`
- 驗收者：獨立驗收者（本會話）。**只測試、未修改任何檔案**；本報告是唯一新增檔案。
- 限制遵守：未重啟／停止 8090／8091、未使用 `pkill`／`killall`、未 commit／push、**未執行 `build_data`**（含副本內；副本中的 `build_data.py` 已替換為「被呼叫就留下標記」的偵測用替身）。

## 一、兩支指定檢查（結束碼）

| 指令 | 結果 | 結束碼 |
|---|---|---|
| `python3 bible-site/tests/launcher_checks.py` | 全部通過（9 項） | **0** |
| `python3 bible-site/tests/service_checks.py service` | 全部通過（16 項） | **0** |

`launcher_checks.py` 輸出：

```
通過：start.sh 語法正確（bash -n）
通過：service.sh 仍然是指向 start.sh 的符號連結
通過：start.sh 至少印出 4 行前台網址（啟動與 status 各有本機與 Tailscale）（8 行）
通過：入口網址都指向根目錄 /（不再是 site/index.html）（4 行）
通過：目錄頁另外以「四福音目錄」標示並連到 /site/index.html（本機與 Tailscale 各一行以上）（4 行）
通過：沒有任何入口行還指向 site/index.html（行 ）
通過：經文資料檢查涵蓋 mat、mrk、luk、jhn 四個 json
通過：經文資料檢查條件沒有提到 blessing.json（缺它不應重建經文）
通過：缺少 blessing.json 時只印警告（有 print_warn 提到 blessing.json）
通過：blessing.json 的警告附近沒有呼叫 build_data.py
結果：全部通過
```

`service_checks.py service` 的 16 項包含：`start`（18190/18191）成功、後台只綁 127.0.0.1、兩個埠回應 200、PID 檔帶埠號、`stop` 後兩埠釋放、外來行程不沿用也不殺、`BIND_HOST` 不同時仍能 stop、軟連結路徑 start/stop，以及**線上 8090/8091 PID 與 `logs/*.pid` 未被改動**。

## 二、`git diff start.sh` 逐條對照

`git diff` 只有 3 個 hunk、共 +16／−6 行，全部落在兩個規格範圍內。

| # | 規格要求 | 判定 | 證據（行號） |
|---|---|---|---|
| 91-1 | 4 行前台網址由 `/site/index.html` 改為 `/` | **通過** | L146、L149（status 的本機／Tailscale）、L331、L334（啟動摘要）皆為 `http://…:${FRONTEND_PORT}/${NC}` |
| 91-2 | 每組入口下方加「四福音目錄」行，指向 `/site/index.html` | **通過** | L147、L150、L332、L335；Tailscale 那行仍在 `if [ -n "${TAILSCALE_IP}" ]` 內（L148–151、L333–336） |
| 91-2 | 保留顏色與 emoji、其餘文字不變 | **通過** | diff 顯示只改網址字串與新增 4 行，`${CYAN}`／`${BOLD}`／`🌐`／`👉` 皆原樣 |
| 91-3 | 不動 L26 的 `-f "${SCRIPT_DIR}/site/index.html"` | **通過** | `git diff -U0` 無此行；實際 L26 仍為 `elif [ -f "${SCRIPT_DIR}/site/index.html" ]; then` |
| 91-4 | 全繁體、無簡體與日文 | **通過** | 全檔掃描：簡體字 0、日文假名 0 |
| 92-1 | 資料檢查擴大到 mat／mrk／luk／jhn | **通過** | L78 為單行條件，四個 `data/<卷>.json` 都在其中 |
| 92-1 | 四個檔名都出現在條件裡 | **通過** | 同上（`launcher_checks.py` 亦驗證通過） |
| 92-2 | blessing.json 缺檔只 `print_warn` | **通過** | L83–85：`if [ ! -f "${SCRIPT_DIR…}/data/blessing.json" ]; then print_warn "缺少 blessing.json，抽經文卡功能將無法使用"; fi` |
| 92-2 | 該 warn 附近**不呼叫** build_data | **通過** | L83–85 區塊內只有 `print_warn`，無 `python3`／`build_data`；與 L78–82 的建置區塊彼此獨立 |
| 92-2 | 不讓腳本因此結束 | **通過** | 該 `if` 內無 `exit`；實測（見三-3）缺 blessing.json 仍正常啟動 |
| 92-3 | 其餘不動 | **通過** | diff 僅 3 個 hunk，無其他改動 |

## 三、獨立重現

### 3-1 `./start.sh start`（18190/18191）— **通過**

```
[SUCCESS] 前台網站已啟動 (PID: 1906844, Port: 18190)
[SUCCESS] 管理後台已啟動 (PID: 1906855, Port: 18191)
  🌐  前台網站 (聖經四福音閱讀器)
      👉 本機連結:   http://127.0.0.1:18190/
      👉 四福音目錄: http://127.0.0.1:18190/site/index.html
      👉 區網/VPN:   http://100.76.46.86:18190/
      👉 四福音目錄: http://100.76.46.86:18190/site/index.html
start rc=0
```

入口是 `http://127.0.0.1:18190/`，且另有「四福音目錄」連到 `/site/index.html` —— 符合要求。

### 3-2 `./start.sh status` — **通過**

```
 🌐 前台網站 (Port 18190): ● 運行中 (PID: 1906844)
    - 本機入口:   http://127.0.0.1:18190/
    - 四福音目錄: http://127.0.0.1:18190/site/index.html
    - Tailscale:  http://100.76.46.86:18190/
    - 四福音目錄: http://100.76.46.86:18190/site/index.html
```

`status` 與啟動摘要兩處都正確。

### 3-3 `curl` 驗證 — **通過**

| 網址 | 狀態碼 |
|---|---|
| `http://127.0.0.1:18190/` | **200** |
| `http://127.0.0.1:18190/site/index.html` | **200** |
| `http://127.0.0.1:18190/site/home.html` | **200** |
| `http://127.0.0.1:18191/api/ping` | **200** |

`/` 的內容確認是轉址頁（`<meta http-equiv="refresh" content="0; url=site/home.html">` 與 `location.replace("site/home.html")`），與「入口首頁改成 home.html」一致。

### 3-4 `./start.sh stop` 與殘留確認 — **通過**

```
[SUCCESS] 前台服務已停止。
[SUCCESS] 後台服務已停止。
stop rc=0
```

- `ss -ltn` 檢查 `18190`／`18191`：**監聽行數 0**
- `ps` 精確比對（排除自身指令字串）：**無殘留行程**
- `logs/*18190*`、`logs/*18191*`：**無殘留 PID 檔**

> 註：第一次用 `pgrep -af 'http.server 18190'` 時比對到我自己指令列裡的字串（假陽性），已改用 `ps -eo pid,args | grep -v grep | grep -v 'bash -c'` 重驗，確認無殘留。

## 四、離雜副本：缺少 `blessing.json` — **通過**

- 副本：`/tmp/launcher-test-copy`（`cp -a` 專案 `start.sh` 與 `bible-site/`，並建立 `service.sh -> start.sh` 連結）
- 防護措施：先把副本的 `bible-site/tools/build_data.py` 換成偵測用替身（被呼叫就寫出 `/tmp/launcher-test-copy/BUILD_DATA_CALLED` 並 `exit 1`），**確保真正專案的 `build_data` 絕不會被執行**
- 測試埠：`FRONTEND_PORT=18190 BACKEND_PORT=18191`

### 4-1 刪掉 `data/blessing.json`（四卷齊全）— **通過**

```
[INFO] 檢查環境依賴...
[WARN] 缺少 blessing.json，抽經文卡功能將無法使用
[INFO] 正在啟動前台網站伺服器 (Port: 18190)...
[SUCCESS] 前台網站已啟動 (PID: 1907234, Port: 18190)
[SUCCESS] 管理後台已啟動 (PID: 1907252, Port: 18191)
start rc=0
```

| 檢查項 | 結果 |
|---|---|
| 只印警告 | **是**（`[WARN] 缺少 blessing.json，抽經文卡功能將無法使用`） |
| `build_data.py` 是否被呼叫 | **否**（`BUILD_DATA_CALLED` 不存在） |
| 是否中止啟動 | **否**，`rc=0`，18190/18191 都正常監聽 |
| 前台 `/`、`/site/home.html` | 200／200 |
| `/data/blessing.json` | 404（缺檔如預期） |

### 4-2 反向驗證：刪掉四卷之一的 `luk.json` — **通過**

為確認「四卷條件真的有效、不是永遠不觸發」而補測：

```
[WARN] 經文資料庫尚未建置，正在自動建置經文資料 (build_data.py)...
!!! build_data.py WAS CALLED !!!
start.sh 實際結束碼: 1
build_data 替身被呼叫: 是
18190 是否啟動: 0
```

條件正確觸發 `build_data.py`；替身回傳 1 後因腳本 `set -eo pipefail` 而中止（未留下半啟動的服務）。這證明 92-1 的四卷條件與 92-2 的 blessing 警告是**兩條獨立路徑**，互不干擾。

> 修正紀錄：此項第一次測時我用 `cmd | grep ...; echo $?` 取結束碼，`$?` 其實是 `sed` 的結束碼；已改用 `out=$(...)` 後的 `$?` 重測，結果如上。

## 五、線上服務與 PID 檔未受影響 — **通過**

| 項目 | BEFORE | AFTER | 判定 |
|---|---|---|---|
| 8090 監聽 | `0.0.0.0:8090` PID 1439868 | 同 | 不變 |
| 8091 監聽 | `0.0.0.0:8091` PID 1439888 | 同 | 不變 |
| `logs/frontend-8090.pid` | 1439868，md5 `8cdef394…` | 同 | 未被改或刪 |
| `logs/backend-8091.pid` | 1439888，md5 `a04aae87…` | 同 | 未被改或刪 |
| 線上回應 | fe 200／be 200 | fe 200／be 200 | 正常 |
| `git log` | `2f3e8c7` | `2f3e8c7` | 未 commit |

`diff` 前後快照皆完全相同。

## 六、其他觀察

- `launcher_checks.py` 的 `--grep` 有空結果保護（`if ONLY and not results: results.append(False)` + 印「沒有對到任何檢查」），比先前 `site_checks.py` 的版本嚴謹，無假陽性風險。
- `service_checks.py service` 會用 18190/18191 實測，且在 `finally` 內比對線上 PID 與 `logs/*.pid` 雜湊，設計正確。
- `logs/` 目前的 PID 檔命名已帶埠號（`frontend-8090.pid`／`backend-8091.pid`），與 52 號任務的規格一致。

---

## 結論

**通過。**

規格 91、92 的每一項都已在原始碼與實際執行兩個層面驗證：

1. 4 行入口網址都指向根目錄 `/`，並各自多一行「四福音目錄」指向 `/site/index.html`（Tailscale 行仍正確包在 `TAILSCALE_IP` 條件內）。
2. L26 的目錄判斷未被動到；全檔無簡體字與日文。
3. 經文資料檢查已涵蓋 `mat`／`mrk`／`luk`／`jhn`；`blessing.json` 缺檔走獨立警告路徑，**只警告、不呼叫 `build_data`、不中止**（實測 `rc=0` 且服務正常）。
4. 兩支指定檢查結束碼皆為 **0**；獨立以 18190/18191 啟停、`status`、`curl`、`stop` 全部符合預期，且測試後無任何殘留。
5. 線上 8090／8091 的 PID 與 `logs/*.pid` 前後完全一致，未被改動；未 commit。

**不通過項目：無。**

總計：通過 26 項、不通過 0 項、需人工 0 項（共 26 項）。
