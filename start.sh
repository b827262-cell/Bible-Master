#!/usr/bin/env bash
# ==============================================================================
# 📖 Bible-Master · 和合本四福音專案：一鍵啟動前台與後台服務
# ==============================================================================
# 前台 (Frontend): 聖經靜態網站 (Port 8090: index.html / chapter / search / card)
# 後台 (Backend):  管理與運維儀表板 (Port 8091: 經文統計 / 模型探測 / 測試控制台)
# ==============================================================================

set -eo pipefail

# 終端機顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 定位專案目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -d "${SCRIPT_DIR}/bible-site" ]; then
  PROJECT_ROOT="${SCRIPT_DIR}"
  SITE_ROOT="${SCRIPT_DIR}/bible-site"
elif [ -f "${SCRIPT_DIR}/site/index.html" ]; then
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
  SITE_ROOT="${SCRIPT_DIR}"
else
  PROJECT_ROOT="${SCRIPT_DIR}"
  SITE_ROOT="${SCRIPT_DIR}/bible-site"
fi

cd "${PROJECT_ROOT}"

# 參數與目錄配置
FRONTEND_PORT="${FRONTEND_PORT:-8090}"
BACKEND_PORT="${BACKEND_PORT:-8091}"
BIND_HOST="${BIND_HOST:-0.0.0.0}"
BACKEND_BIND="${BACKEND_BIND:-127.0.0.1}"

LOG_DIR="${PROJECT_ROOT}/logs"
PID_DIR="${LOG_DIR}"
mkdir -p "${LOG_DIR}"

FRONTEND_PID_FILE="${PID_DIR}/frontend-${FRONTEND_PORT}.pid"
BACKEND_PID_FILE="${PID_DIR}/backend-${BACKEND_PORT}.pid"
FRONTEND_LOG_FILE="${LOG_DIR}/frontend.log"
BACKEND_LOG_FILE="${LOG_DIR}/backend.log"

print_banner() {
  echo -e "${CYAN}${BOLD}"
  echo "=============================================================================="
  echo "           📖  Bible-Master 和合本四福音 · 前台 & 後台一鍵服務系統          "
  echo "=============================================================================="
  echo -e "${NC}"
}

print_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# 取得本機 IP 與 Tailscale IP
get_ips() {
  LOCAL_IP="127.0.0.1"
  TAILSCALE_IP="$(ip -4 addr show tailscale0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || true)"
}

# 檢查環境依賴
check_environment() {
  print_info "檢查環境依賴..."
  if ! command -v python3 >/dev/null 2>&1; then
    print_error "未檢測到 Python 3，請先安裝 Python 3！"
    exit 1
  fi

  if [ ! -f "${SITE_ROOT}/data/mat.json" ] || [ ! -f "${SITE_ROOT}/data/mrk.json" ] || [ ! -f "${SITE_ROOT}/data/luk.json" ] || [ ! -f "${SITE_ROOT}/data/jhn.json" ]; then
    print_warn "經文資料庫尚未建置，正在自動建置經文資料 (build_data.py)..."
    python3 "${SITE_ROOT}/tools/build_data.py"
    print_success "經文資料建置完成！"
  fi

  if [ ! -f "${SITE_ROOT}/data/blessing.json" ]; then
    print_warn "缺少 blessing.json，抽經文卡功能將無法使用"
  fi
}

# 檢測指定 PID 是否仍活著
is_pid_running() {
  local pid="$1"
  [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null
}

# 依 port 找出監聽的 PID
get_port_pid() {
  local port="$1"
  lsof -ti tcp:"${port}" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

# 判斷指定 PID 是否為本腳本啟動的服務（kind: frontend|backend）
# 符合回傳 0，否則回傳 1
is_our_service() {
  local pid="$1" kind="$2"
  local cmdline
  cmdline="$(ps -o args= -p "${pid}" 2>/dev/null || true)"
  case "${kind}" in
    frontend)
      if [[ "${cmdline}" == *"http.server ${FRONTEND_PORT}"* ]]; then
        # 前台必須是在 SITE_ROOT 目錄下啟動的，避免指令列相同的外來行程被沿用／被殺
        local cwd
        cwd="$(readlink "/proc/${pid}/cwd" 2>/dev/null || true)"
        if [ "${cwd}" = "${SITE_ROOT}" ]; then
          return 0
        fi
      fi
      return 1
      ;;
    backend)
      # 後台必須使用完整絕對路徑 ${SITE_ROOT}/admin/server.py（而非相對路徑 admin/server.py）
      if [[ "${cmdline}" == *"${SITE_ROOT}/admin/server.py"* && "${cmdline}" == *"--port ${BACKEND_PORT}"* ]]; then
        return 0
      fi
      return 1
      ;;
    *)
      return 1
      ;;
  esac
}

# 檢查服務狀態
check_status() {
  get_ips
  echo -e "${BOLD}--- [ 服務運行狀態 ] ---${NC}"

  # 1. 前台狀態
  local fe_pid=""
  if [ -f "${FRONTEND_PID_FILE}" ]; then
    fe_pid="$(cat "${FRONTEND_PID_FILE}" 2>/dev/null || true)"
  fi
  local fe_listen_pid="$(get_port_pid "${FRONTEND_PORT}")"

  if [ -n "${fe_listen_pid}" ]; then
    echo -e " 🌐 ${BOLD}前台網站 (Port ${FRONTEND_PORT})${NC}: ${GREEN}● 運行中${NC} (PID: ${fe_listen_pid})"
    echo -e "    - 本機入口:   ${CYAN}http://127.0.0.1:${FRONTEND_PORT}/${NC}"
    echo -e "    - 四福音目錄: ${CYAN}http://127.0.0.1:${FRONTEND_PORT}/site/index.html${NC}"
    if [ -n "${TAILSCALE_IP}" ]; then
      echo -e "    - Tailscale:  ${CYAN}http://${TAILSCALE_IP}:${FRONTEND_PORT}/${NC}"
      echo -e "    - 四福音目錄: ${CYAN}http://${TAILSCALE_IP}:${FRONTEND_PORT}/site/index.html${NC}"
    fi
  else
    echo -e " 🌐 ${BOLD}前台網站 (Port ${FRONTEND_PORT})${NC}: ${RED}○ 未運行${NC}"
  fi

  # 2. 後台狀態
  local be_pid=""
  if [ -f "${BACKEND_PID_FILE}" ]; then
    be_pid="$(cat "${BACKEND_PID_FILE}" 2>/dev/null || true)"
  fi
  local be_listen_pid="$(get_port_pid "${BACKEND_PORT}")"

  if [ -n "${be_listen_pid}" ]; then
    echo -e " ⚙️  ${BOLD}管理後台 (Port ${BACKEND_PORT})${NC}: ${GREEN}● 運行中${NC} (PID: ${be_listen_pid})"
    echo -e "    - 儀表板入口: ${CYAN}http://127.0.0.1:${BACKEND_PORT}/${NC}"
    if [ -n "${TAILSCALE_IP}" ]; then
      if [ "${BACKEND_BIND}" = "0.0.0.0" ]; then
        echo -e "    - Tailscale:  ${CYAN}http://${TAILSCALE_IP}:${BACKEND_PORT}/${NC}"
      else
        echo -e "    - Tailscale:  ${YELLOW}後台只限本機（設定 BACKEND_BIND=0.0.0.0 可開放）${NC}"
      fi
    fi
  else
    echo -e " ⚙️  ${BOLD}管理後台 (Port ${BACKEND_PORT})${NC}: ${RED}○ 未運行${NC}"
  fi

  echo ""
  echo -e "${BOLD}--- [ 地端 AI 模型叢集連線狀態 ] ---${NC}"
  probe() { curl -s -m 2 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || echo "000"; }
  
  [ "$(probe http://127.0.0.1:8082/health)" = "200" ] && \
    echo -e " 🤖 E500 主編 (RTX 3060 · 27B · :8082):        ${GREEN}● 在線${NC}" || \
    echo -e " 🤖 E500 主編 (RTX 3060 · 27B · :8082):        ${YELLOW}○ 離線${NC}"

  [ "$(probe http://127.0.0.1:18083/health)" = "200" ] && \
    echo -e " 🤖 A16 審核 Tunnel (Bonsai 9B · :18083):      ${GREEN}● 在線${NC}" || \
    echo -e " 🤖 A16 審核 Tunnel (Bonsai 9B · :18083):      ${YELLOW}○ 離線${NC}"

  [ "$(probe http://127.0.0.1:18087/api/tags)" = "200" ] && \
    echo -e " 🤖 De1050 測試 Tunnel (Qwen 4B · :18087):     ${GREEN}● 在線${NC}" || \
    echo -e " 🤖 De1050 測試 Tunnel (Qwen 4B · :18087):     ${YELLOW}○ 離線${NC}"

  [ "$(probe http://127.0.0.1:3080/)" != "000" ] && \
    echo -e " 🖥️  Harness Web 控制台 (:3080):                ${GREEN}● 在線${NC}" || \
    echo -e " 🖥️  Harness Web 控制台 (:3080):                ${YELLOW}○ 離線${NC}"
  echo ""
}

# 停止服務（只殺本腳本啟動的服務；外來行程不碰）
stop_services() {
  print_info "正在停止 Bible-Master 前台與後台服務..."

  # 1. 停止前台
  local fe_pid="$(get_port_pid "${FRONTEND_PORT}")"
  if [ -n "${fe_pid}" ]; then
    if is_our_service "${fe_pid}" frontend; then
      print_info "停止前台服務 (PID: ${fe_pid}, Port: ${FRONTEND_PORT})..."
      kill -TERM "${fe_pid}" 2>/dev/null || true
      sleep 0.5
      if is_pid_running "${fe_pid}"; then
        kill -KILL "${fe_pid}" 2>/dev/null || true
      fi
      print_success "前台服務已停止。"
    else
      print_warn "Port ${FRONTEND_PORT} 由其他程式佔用，不處理"
    fi
  else
    print_info "前台服務未在運行。"
  fi
  rm -f "${FRONTEND_PID_FILE}"

  # 2. 停止後台
  local be_pid="$(get_port_pid "${BACKEND_PORT}")"
  if [ -n "${be_pid}" ]; then
    if is_our_service "${be_pid}" backend; then
      print_info "停止後台服務 (PID: ${be_pid}, Port: ${BACKEND_PORT})..."
      kill -TERM "${be_pid}" 2>/dev/null || true
      sleep 0.5
      if is_pid_running "${be_pid}"; then
        kill -KILL "${be_pid}" 2>/dev/null || true
      fi
      print_success "後台服務已停止。"
    else
      print_warn "Port ${BACKEND_PORT} 由其他程式佔用，不處理"
    fi
  else
    print_info "後台服務未在運行。"
  fi
  rm -f "${BACKEND_PID_FILE}"
}

# 啟動前台
start_frontend() {
  local existing_pid="$(get_port_pid "${FRONTEND_PORT}")"
  if [ -n "${existing_pid}" ]; then
    if is_our_service "${existing_pid}" frontend; then
      print_warn "Port ${FRONTEND_PORT} 已被本服務佔用（PID ${existing_pid}），沿用既有服務。"
      echo "${existing_pid}" > "${FRONTEND_PID_FILE}"
      return 0
    fi
    local cmdline="$(ps -o args= -p "${existing_pid}" 2>/dev/null || true)"
    print_error "Port ${FRONTEND_PORT} 被其他程式（PID ${existing_pid}：${cmdline}）佔用，未啟動"
    exit 1
  fi

  print_info "正在啟動前台網站伺服器 (Port: ${FRONTEND_PORT})..."
  cd "${SITE_ROOT}"
  setsid python3 -u -m http.server "${FRONTEND_PORT}" --bind "${BIND_HOST}" < /dev/null >> "${FRONTEND_LOG_FILE}" 2>&1 &
  local pid=$!
  echo "${pid}" > "${FRONTEND_PID_FILE}"
  cd "${PROJECT_ROOT}"

  # 最多等 5 秒（每 0.5 秒一次），確認該 PID 已監聽本埠
  local now_pid="" attempts=0
  while [ "${attempts}" -lt 10 ]; do
    now_pid="$(get_port_pid "${FRONTEND_PORT}")"
    if [ "${now_pid}" = "${pid}" ]; then
      break
    fi
    sleep 0.5
    attempts=$((attempts + 1))
  done
  if [ "${now_pid}" = "${pid}" ]; then
    print_success "前台網站已啟動 (PID: ${pid}, Port: ${FRONTEND_PORT})"
  else
    print_error "前台網站啟動失敗（5 秒內未確認 PID ${pid} 監聽 Port ${FRONTEND_PORT}），請檢查日誌：${FRONTEND_LOG_FILE}"
    exit 1
  fi
}

# 啟動後台
start_backend() {
  local existing_pid="$(get_port_pid "${BACKEND_PORT}")"
  if [ -n "${existing_pid}" ]; then
    if is_our_service "${existing_pid}" backend; then
      print_warn "Port ${BACKEND_PORT} 已被本服務佔用（PID ${existing_pid}），沿用既有服務。"
      echo "${existing_pid}" > "${BACKEND_PID_FILE}"
      return 0
    fi
    local cmdline="$(ps -o args= -p "${existing_pid}" 2>/dev/null || true)"
    print_error "Port ${BACKEND_PORT} 被其他程式（PID ${existing_pid}：${cmdline}）佔用，未啟動"
    exit 1
  fi

  print_info "正在啟動管理後台伺服器 (Port: ${BACKEND_PORT})..."
  setsid python3 -u "${SITE_ROOT}/admin/server.py" --host "${BACKEND_BIND}" --port "${BACKEND_PORT}" < /dev/null >> "${BACKEND_LOG_FILE}" 2>&1 &
  local pid=$!
  echo "${pid}" > "${BACKEND_PID_FILE}"

  # 最多等 5 秒（每 0.5 秒一次），確認該 PID 已監聽本埠
  local now_pid="" attempts=0
  while [ "${attempts}" -lt 10 ]; do
    now_pid="$(get_port_pid "${BACKEND_PORT}")"
    if [ "${now_pid}" = "${pid}" ]; then
      break
    fi
    sleep 0.5
    attempts=$((attempts + 1))
  done
  if [ "${now_pid}" = "${pid}" ]; then
    print_success "管理後台已啟動 (PID: ${pid}, Port: ${BACKEND_PORT})"
  else
    print_error "管理後台啟動失敗（5 秒內未確認 PID ${pid} 監聽 Port ${BACKEND_PORT}），請檢查日誌：${BACKEND_LOG_FILE}"
    exit 1
  fi
}

# 一鍵啟動
start_all() {
  check_environment
  get_ips
  start_frontend
  start_backend

  echo ""
  echo -e "${GREEN}${BOLD}==============================================================================${NC}"
  echo -e "${GREEN}${BOLD}  🎉  Bible-Master 前台與後台服務已全部成功啟動！                           ${NC}"
  echo -e "${GREEN}${BOLD}==============================================================================${NC}"
  echo ""
  echo -e "  🌐  ${BOLD}前台網站 (聖經四福音閱讀器)${NC}"
  echo -e "      👉 本機連結:   ${CYAN}${BOLD}http://127.0.0.1:${FRONTEND_PORT}/${NC}"
  echo -e "      👉 四福音目錄: ${CYAN}${BOLD}http://127.0.0.1:${FRONTEND_PORT}/site/index.html${NC}"
  if [ -n "${TAILSCALE_IP}" ]; then
    echo -e "      👉 區網/VPN:   ${CYAN}${BOLD}http://${TAILSCALE_IP}:${FRONTEND_PORT}/${NC}"
    echo -e "      👉 四福音目錄: ${CYAN}${BOLD}http://${TAILSCALE_IP}:${FRONTEND_PORT}/site/index.html${NC}"
  fi
  echo ""
  echo -e "  ⚙️   ${BOLD}管理後台 (運維儀表板 & 自動化測試)${NC}"
  echo -e "      👉 本機連結:   ${CYAN}${BOLD}http://127.0.0.1:${BACKEND_PORT}/${NC}"
  if [ -n "${TAILSCALE_IP}" ]; then
    if [ "${BACKEND_BIND}" = "0.0.0.0" ]; then
      echo -e "      👉 區網/VPN:   ${CYAN}${BOLD}http://${TAILSCALE_IP}:${BACKEND_PORT}/${NC}"
    else
      echo -e "      👉 後台只限本機（設定 BACKEND_BIND=0.0.0.0 可開放）"
    fi
  fi
  echo ""
  echo -e "  📝  日誌查看:      ${YELLOW}./start.sh logs${NC}"
  echo -e "  🛑  停止服務:      ${YELLOW}./start.sh stop${NC}"
  echo -e "  🔍  檢查狀態:      ${YELLOW}./start.sh status${NC}"
  echo -e "${GREEN}==============================================================================${NC}"
  echo ""
}

# 前景模式（Ctrl+C 時自動終止）
run_foreground() {
  check_environment
  get_ips

  trap 'echo -e "\n${YELLOW}接收到中斷訊號，正在關閉服務...${NC}"; stop_services; exit 0' INT TERM

  print_info "以前景模式 (Foreground) 啟動服務，按 Ctrl+C 可一併停止前台與後台..."
  start_frontend
  start_backend

  echo -e "${GREEN}服務持續運行中... (按 Ctrl+C 結束)${NC}"
  tail -f "${FRONTEND_LOG_FILE}" "${BACKEND_LOG_FILE}"
}

# 執行自動化測試
run_tests() {
  print_info "執行 Bible-Master 完整自動化檢查 (check_all.py)..."
  python3 "${SITE_ROOT}/tools/check_all.py"
  echo ""
  print_info "執行視覺與無障礙檢驗 (visual_checks.py)..."
  python3 "${SITE_ROOT}/tests/visual_checks.py"
}

# 查看日誌
view_logs() {
  local target="${1:-all}"
  case "${target}" in
    frontend|fe)
      echo -e "${CYAN}=== 前台日誌 (${FRONTEND_LOG_FILE}) ===${NC}"
      tail -n 50 -f "${FRONTEND_LOG_FILE}"
      ;;
    backend|be)
      echo -e "${CYAN}=== 後台日誌 (${BACKEND_LOG_FILE}) ===${NC}"
      tail -n 50 -f "${BACKEND_LOG_FILE}"
      ;;
    all|*)
      echo -e "${CYAN}=== 雙端日誌 (${FRONTEND_LOG_FILE} + ${BACKEND_LOG_FILE}) ===${NC}"
      tail -n 30 -f "${FRONTEND_LOG_FILE}" "${BACKEND_LOG_FILE}"
      ;;
  esac
}

# 產生 systemd user service 單位檔
install_systemd() {
  local unit_dir="${HOME}/.config/systemd/user"
  mkdir -p "${unit_dir}"
  local unit_file="${unit_dir}/bible-master.service"

  cat << EOF > "${unit_file}"
[Unit]
Description=Bible-Master Frontend and Backend Service
After=network.target

[Service]
Type=forking
WorkingDirectory=${PROJECT_ROOT}
ExecStart=${PROJECT_ROOT}/start.sh start
ExecStop=${PROJECT_ROOT}/start.sh stop
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

  systemctl --user daemon-reload
  print_success "已建立 systemd user service 設定檔: ${unit_file}"
  echo "您可以使用以下指令管理服務："
  echo "  systemctl --user enable bible-master.service  # 設定開機自啟"
  echo "  systemctl --user start bible-master.service   # 啟動服務"
  echo "  systemctl --user status bible-master.service  # 查看狀態"
  echo "  systemctl --user stop bible-master.service    # 停止服務"
}

print_help() {
  echo -e "${BOLD}使用方式：${NC}"
  echo "  ./start.sh              - 一鍵啟動前台 (8090) 與後台 (8091)"
  echo "  ./start.sh start        - 背景啟動服務 (Daemon mode)"
  echo "  ./start.sh stop         - 停止前台與後台服務"
  echo "  ./start.sh restart      - 重新啟動前台與後台服務"
  echo "  ./start.sh status       - 查看目前服務運作狀態與模型連線"
  echo "  ./start.sh test         - 執行專案完整自動化測試套件"
  echo "  ./start.sh logs [fe|be] - 追蹤查看即時日誌"
  echo "  ./start.sh -f           - 前景模式運行 (按 Ctrl+C 可同時停止)"
  echo "  ./start.sh --systemd    - 安裝為 Linux systemd user 開機守護服務"
  echo "  ./start.sh help         - 顯示此說明"
}

# 主進入點
main() {
  local action="${1:-start}"

  case "${action}" in
    start)
      print_banner
      start_all
      ;;
    stop)
      print_banner
      stop_services
      ;;
    restart)
      print_banner
      stop_services
      sleep 1
      start_all
      ;;
    status)
      print_banner
      check_status
      ;;
    test)
      print_banner
      run_tests
      ;;
    logs)
      shift || true
      view_logs "$@"
      ;;
    -f|--foreground|foreground)
      print_banner
      run_foreground
      ;;
    --systemd|systemd|install-systemd)
      print_banner
      install_systemd
      ;;
    help|--help|-h)
      print_banner
      print_help
      ;;
    *)
      print_warn "未知指令: ${action}"
      print_help
      exit 1
      ;;
  esac
}

main "$@"
