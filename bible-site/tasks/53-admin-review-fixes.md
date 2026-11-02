---
role: e500
files: [bible-site/admin/server.py, start.sh]
depends: [50-admin-server, 52-start-sh]
checks:
  - python3 -m py_compile bible-site/admin/server.py
  - bash -n start.sh
  - python3 bible-site/tests/service_checks.py
---
只改 bible-site/admin/server.py 與專案根目錄的 start.sh（service.sh、bible-site/start.sh 是軟連結，不要動）。這是複審報告 bible-site/FRONTEND-REVIEW-ADMIN.md 的三個問題，先讀完兩個檔案再修改；其他行為保持不變。

1. server.py：HEAD 請求繞過了靜態檔白名單（父類別的 do_HEAD 沒經過 do_GET 的判斷，HEAD /server.py 回 200）。
   在 AdminRequestHandler 加上 do_HEAD，套用和 do_GET 完全相同的路由規則：
   - "/"、"/index.html"、"/admin.js"、"/admin.css" → 呼叫 super().do_HEAD()
   - 其他任何路徑（包含 /api/ 開頭）→ 只送 404 標頭，不寫內容：
     self.send_response(404); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", "0"); self.end_headers()

2. start.sh 的 is_our_service：frontend 條件多比對了 "--bind ${BIND_HOST}"，導致用 BIND_HOST=127.0.0.1 啟動、再用預設環境 stop 時停不掉。刪掉 --bind 的比對。

3. start.sh 的 is_our_service 只比對指令列文字，與本服務指令列相同的外來行程會被沿用、被殺。改成：
   - frontend：指令列包含 "http.server ${FRONTEND_PORT}"，而且 "$(readlink /proc/${pid}/cwd 2>/dev/null)" 等於 "${SITE_ROOT}"（前台是在 SITE_ROOT 目錄下啟動的）。
   - backend：指令列包含 "${SITE_ROOT}/admin/server.py"（完整絕對路徑，不是只有 admin/server.py）而且包含 "--port ${BACKEND_PORT}"。
   - start_backend 啟動時已經用 "${SITE_ROOT}/admin/server.py" 絕對路徑，保持如此。
   線上服務（8090：cwd 是 bible-site 的 http.server；8091：python3 -u /home/b827262/project/AI/Bible-Master/bible-site/admin/server.py --port 8091）都符合新條件，不要破壞。

禁止：不准用預設埠 8090/8091 執行 start.sh，不准動 logs/frontend.pid、logs/backend.pid，不准使用 pkill、killall。

驗收（腳本自動跑）：py_compile、bash -n 通過，且 python3 bible-site/tests/service_checks.py 全部通過（它用 18190/18191 測試，包含 HEAD 白名單、BIND_HOST 不同時 stop、兩種外來仿冒行程不沿用也不殺）。改完只回報改了哪些地方。
