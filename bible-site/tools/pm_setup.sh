#!/usr/bin/env bash
# PM setup: check the environment, rebuild the data, and print the baseline. Read-only except for
# data/mark.json (regenerated from .verify/mark.txt) and the check_all.py reports.
# Usage: bash bible-site/tools/pm_setup.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
ok()   { printf '  [OK]   %s\n' "$1"; }
warn() { printf '  [WARN] %s\n' "$1"; WARNED=1; }
WARNED=0

echo "== Project layout =="
[ -f "$ROOT/.verify/mark.txt" ] && ok ".verify/mark.txt (source text)" || warn ".verify/mark.txt missing (build_data.py needs it one level above bible-site/)"
[ -d "$HERE/prompts" ] && ok "prompts/ ($(ls "$HERE/prompts" | wc -l) files)" || warn "prompts/ missing"

echo "== Tools =="
command -v python3 >/dev/null && ok "$(python3 --version)" || warn "python3 missing"
command -v node >/dev/null && ok "node $(node -v)" || warn "node missing (tests/smoke.js)"
CHROME=""; for c in /usr/bin/google-chrome /usr/bin/google-chrome-stable /snap/bin/chromium; do [ -x "$c" ] && CHROME="$c" && break; done
[ -n "$CHROME" ] && ok "headless browser: $CHROME" || warn "no Chrome/Chromium (tests/site_checks.py)"

echo "== Local model hosts (only needed for the Harness steps) =="
probe() { curl -s -m 3 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null; }
[ "$(probe http://127.0.0.1:8082/health)" = "200" ] && ok "E500 llama-server :8082" || warn "E500 :8082 down  -> ~/project/Bonsai-demo/start_e500_pq2_160k.sh"
[ "$(probe http://127.0.0.1:18083/health)" = "200" ] && ok "TUF A16 tunnel :18083" || warn "A16 tunnel :18083 down (start the server on 10.0.3.67, then systemctl --user start bonsai-a16-tunnel)"
[ "$(probe http://127.0.0.1:18087/api/tags)" = "200" ] && ok "De1050 Ollama tunnel :18087" || warn "De1050 tunnel :18087 down (ssh 10.0.3.70: sudo systemctl start ollama; systemctl --user start bonsai-de1050-tunnel)"
[ -n "$(probe http://127.0.0.1:3080/)" ] && [ "$(probe http://127.0.0.1:3080/)" != "000" ] && ok "Harness web :3080" || warn "Harness :3080 down -> npx @deepseek-ai/dsh web --no-open"

echo "== Data and baseline =="
python3 "$HERE/tools/build_data.py" && python3 "$HERE/tools/verify_text.py" || warn "data build / verify failed"
python3 "$HERE/tools/check_all.py" | tail -3
echo "== PM progress =="
python3 "$HERE/tools/pm_status.py" --no-checks | tail -12
[ "$WARNED" = 0 ] && echo "Setup: all good" || echo "Setup: finished with warnings (see [WARN] lines)"
