---
role: e500
files: [start.sh]
depends: [53-admin-review-fixes]
checks:
  - bash -n start.sh
  - python3 bible-site/tests/service_checks.py
---
只改專案根目錄的 start.sh（service.sh、bible-site/start.sh 是軟連結，不要動）。

問題（見 bible-site/FRONTEND-REVIEW-ADMIN-R2.md「新問題 1」）：透過軟連結路徑（例如 /tmp/x/proj -> 專案）執行 start 再 stop，前台停不掉。原因：SCRIPT_DIR 用 `cd "$(dirname "${BASH_SOURCE[0]}")" && pwd` 算出，pwd 保留軟連結；但 is_our_service 比對的 /proc/<pid>/cwd 是實體路徑，兩者不相等。

修法：只改 SCRIPT_DIR 那一行，把 `pwd` 改成 `pwd -P`，讓 SCRIPT_DIR、PROJECT_ROOT、SITE_ROOT 都是實體路徑：
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
其他地方不要改。

禁止：不准用預設埠 8090/8091 執行 start.sh，不准動 logs/frontend.pid、logs/backend.pid，不准使用 pkill、killall。

驗收（腳本自動跑）：bash -n 通過，且 python3 bible-site/tests/service_checks.py 全部通過（新增項目：經由軟連結路徑啟動、同路徑 stop 後兩個埠都釋放）。改完只回報改了哪些地方。
