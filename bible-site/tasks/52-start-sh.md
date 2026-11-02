---
role: e500
files: [start.sh]
checks:
  - bash -n start.sh
  - python3 bible-site/tests/service_checks.py service
---
只改專案根目錄的 start.sh（service.sh 與 bible-site/start.sh 是指向它的軟連結，不要動它們）。目前的問題：埠被別的程式佔用時，start 會把那個外來行程「沿用」成自己的服務，stop 再把它殺掉；PID 檔不分埠號、只寫不讀；後台綁在 0.0.0.0。請先讀完整個 start.sh，再依清單修改：

1. PID 檔名帶埠號：FRONTEND_PID_FILE="${PID_DIR}/frontend-${FRONTEND_PORT}.pid"、BACKEND_PID_FILE="${PID_DIR}/backend-${BACKEND_PORT}.pid"。
2. 新增函式 is_our_service <pid> <kind>：用 `ps -o args= -p <pid>` 取得指令列；kind=frontend 時必須包含 "http.server ${FRONTEND_PORT}"，kind=backend 時必須包含 "admin/server.py" 且包含 "--port ${BACKEND_PORT}"；符合回傳 0，否則回傳 1。
3. start_frontend／start_backend：埠已被佔用時，若 is_our_service 成立 → 維持現在的「沿用既有服務」並寫 PID 檔；若不成立 → print_error「Port X 被其他程式（PID N：<指令列>）佔用，未啟動」並 exit 1，不寫 PID 檔。
4. stop_services：對前台、後台各自，找到監聽的 PID 後，只有 is_our_service 成立才 kill；不成立就 print_warn「Port X 由其他程式佔用，不處理」，不 kill。PID 檔只刪除本埠號的那一個。
5. 後台綁定：新增 BACKEND_BIND="${BACKEND_BIND:-127.0.0.1}"，start_backend 用 --host "${BACKEND_BIND}"（前台仍用 BIND_HOST，預設 0.0.0.0 不變）。status 與啟動完成訊息裡的後台 Tailscale 網址，只有 BACKEND_BIND 是 0.0.0.0 時才顯示；否則顯示「後台只限本機（設定 BACKEND_BIND=0.0.0.0 可開放）」。
6. 啟動後確認：把「sleep 1 後 PID 還活著」改成最多等 5 秒、每 0.5 秒檢查 get_port_pid 是否有值且等於剛啟動的 PID；逾時就 print_error 並 exit 1。
7. 不准使用 pkill、killall 或依名稱比對來殺行程。其他指令（restart、status、test、logs、-f、--systemd）保留原有行為。

驗收（腳本自動跑）：bash -n start.sh 通過，且 python3 bible-site/tests/service_checks.py service 全部通過（它會用 FRONTEND_PORT=18190 BACKEND_PORT=18191 實際啟停，並確認線上 8090/8091 服務與其 PID 檔沒有被動到）。改完只回報改了哪些地方。
