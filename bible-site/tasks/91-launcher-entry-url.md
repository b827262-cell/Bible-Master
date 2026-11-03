---
role: a16
files: [start.sh]
checks:
  - python3 bible-site/tests/launcher_checks.py syntax entry
  - python3 bible-site/tests/service_checks.py service
---
只改專案根目錄的 `start.sh`（`service.sh` 是指向它的符號連結，不要動、不要取代）。
入口首頁已經改成 `site/home.html`，網址根目錄 `/` 會自動轉過去，但 `start.sh` 啟動完成和 `status` 時印出的前台網址還是 `/site/index.html`。請改成：

1. 目前有 4 行 `echo` 印出前台網址（大約在第 142、144、325、327 行：啟動摘要與 `status` 各有「本機」和「Tailscale」）。把這 4 行的網址從 `.../site/index.html` 改成 `.../`，也就是 `http://127.0.0.1:${FRONTEND_PORT}/` 和 `http://${TAILSCALE_IP}:${FRONTEND_PORT}/`（後面接 `${NC}`，其餘文字、顏色、emoji 不變）。
2. 在每一組入口行的下面各加一行，標示目錄頁，文字用「四福音目錄」，格式跟上一行對齊，網址是 `.../site/index.html`：
   - 本機：`http://127.0.0.1:${FRONTEND_PORT}/site/index.html`
   - Tailscale：`http://${TAILSCALE_IP}:${FRONTEND_PORT}/site/index.html`（Tailscale 那行要跟原本一樣放在 `if [ -n "${TAILSCALE_IP}" ]` 的條件裡面）
3. 不要動第 26 行的 `-f "${SCRIPT_DIR}/site/index.html"`（那是在判斷目錄位置）、不要動第 78 行附近的經文資料檢查（另一個任務負責）。
4. 介面文字全部繁體中文，不要用簡體字與日文。

改完請跑：`bash -n start.sh`、`python3 bible-site/tests/launcher_checks.py syntax entry`。不要啟動或停止任何服務（線上 8090/8091 不可碰）；`service_checks.py service` 會自己用 18190/18191 測，交給驗收腳本跑就好。
