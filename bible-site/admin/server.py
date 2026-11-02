#!/usr/bin/env python3
"""Bible-Master Admin & Operations Backend Server
零外部依賴（純 Python 3 標準庫），提供專案管理儀表板與 REST API：
  - 專案總覽與四福音統計（3,776 節）
  - 地端 AI 模型節點健康檢查 (E500, A16, De1050, Harness)
  - 自動化測試觸發 (check_all.py, visual_checks.py, verify_text.py)
  - 測試報告、派工進度與任務追蹤
"""
import argparse
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

HERE = os.path.abspath(os.path.dirname(__file__))
SITE_ROOT = os.path.abspath(os.path.join(HERE, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(SITE_ROOT, ".."))

BOOKS = [
    ("mat", "馬太福音", 28, 1071),
    ("mrk", "馬可福音", 16, 678),
    ("luk", "路加福音", 24, 1149),
    ("jhn", "約翰福音", 21, 878),
]

MODEL_NODES = [
    {
        "id": "e500",
        "name": "E500 (主編 · Bonsai 2 27B 160K)",
        "host": "127.0.0.1",
        "port": 8082,
        "url": "http://127.0.0.1:8082/health",
        "alt_url": "http://127.0.0.1:8082/v1/models",
        "hint": "~/project/Bonsai-demo/start_e500_pq2_160k.sh"
    },
    {
        "id": "a16",
        "name": "TUF A16 Tunnel (審核 · Bonsai 2 9B 128K)",
        "host": "127.0.0.1",
        "port": 18083,
        "url": "http://127.0.0.1:18083/health",
        "alt_url": "http://127.0.0.1:18083/v1/models",
        "hint": "systemctl --user start bonsai-a16-tunnel"
    },
    {
        "id": "de1050",
        "name": "De1050 Tunnel (測試 · Qwen 3.5 4B 48K)",
        "host": "127.0.0.1",
        "port": 18087,
        "url": "http://127.0.0.1:18087/api/tags",
        "alt_url": "http://127.0.0.1:18087/v1/models",
        "hint": "systemctl --user start bonsai-de1050-tunnel"
    },
    {
        "id": "harness",
        "name": "Harness Web 控制台",
        "host": "127.0.0.1",
        "port": 3080,
        "url": "http://127.0.0.1:3080/",
        "alt_url": None,
        "hint": "npx @deepseek-ai/dsh web --no-open"
    }
]

REPORT_WHITELIST = ["TEST-REPORT.md", "FAILS.md", "DISPATCH-REPORT.md", "PROGRESS.md", "CHANGELOG.md"]
ACTION_LOCK = threading.Lock()


def probe_url(url, timeout=2.0):
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BibleMaster-AdminProbe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            elapsed_ms = int((time.time() - start) * 1000)
            return True, code, elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        # 401/403/302 表示服務正在運行中（例如 Harness 需要登入 token）
        if e.code in (200, 301, 302, 401, 403):
            return True, f"HTTP {e.code}", elapsed_ms
        return False, f"HTTP {e.code}", elapsed_ms
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return False, str(e), elapsed_ms


class AdminRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def log_message(self, format, *args):
        # 簡易自訂日誌
        sys.stderr.write("[%s] 後台API: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), format % args))

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self.handle_api_status()
        elif path == "/api/models":
            self.handle_api_models()
        elif path == "/api/tasks":
            self.handle_api_tasks()
        elif path.startswith("/api/report/"):
            report_name = path[len("/api/report/"):]
            self.handle_api_report(report_name)
        elif path == "/api/ping":
            self.send_json({"status": "ok", "time": time.time()})
        elif path.startswith("/api/"):
            # 未認知的 API 端點
            self.send_json({"error": "找不到該操作端點"}, code=404)
        elif path in ("/", "/index.html", "/admin.js", "/admin.css"):
            # 靜態文件服務
            super().do_GET()
        else:
            # 其他路徑一律回 404
            self.send_json({"error": "找不到檔案"}, code=404)

    def do_HEAD(self):
        # HEAD 套用與 do_GET 完全相同的路由規則；非靜態檔只回標頭、不送內容
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html", "/admin.js", "/admin.css"):
            # 靜態文件服務（只送標頭，不送 body）
            super().do_HEAD()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_POST(self):
        # 權限檢查：必須有 X-Bible-Admin 標頭（值為 "1"）
        if self.headers.get("X-Bible-Admin") != "1":
            self.send_json({"error": "缺少 X-Bible-Admin 標頭"}, code=403)
            return

        # Origin 檢查：若有，必須與同源一致（http:// + Host）
        origin = self.headers.get("Origin")
        if origin is not None:
            host = self.headers.get("Host", "")
            if origin != "http://" + host:
                self.send_json({"error": "不允許的來源"}, code=403)
                return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/action/check_all":
            self.handle_run_command([sys.executable, "bible-site/tools/check_all.py"], "自動全檢驗 (check_all.py)")
        elif path == "/api/action/visual_checks":
            self.handle_run_command([sys.executable, "bible-site/tests/visual_checks.py"], "視覺與無障礙檢驗 (visual_checks.py)")
        elif path == "/api/action/verify_text":
            self.handle_run_command([sys.executable, "bible-site/tools/verify_text.py"], "經文原文比對 (verify_text.py)")
        elif path == "/api/action/smoke_test":
            self.handle_run_command(["node", "bible-site/tests/smoke.js"], "基礎冒煙測試 (smoke.js)")
        else:
            self.send_json({"error": "找不到該操作端點"}, code=404)

    def handle_api_status(self):
        # 1. 前台伺服器檢測
        fe_ok, fe_code, fe_latency = probe_url("http://127.0.0.1:8090/site/index.html", timeout=1.0)
        
        # 2. 四福音資料讀取
        books_stat = []
        total_verses = 0
        all_books_valid = True
        for key, name, exp_ch, exp_v in BOOKS:
            json_file = os.path.join(SITE_ROOT, "data", f"{key}.json")
            f_exists = os.path.isfile(json_file)
            cur_verses = 0
            cur_chapters = 0
            if f_exists:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        cur_chapters = len(d.get("chapters", []))
                        cur_verses = sum(len(c.get("verses", [])) for c in d.get("chapters", []))
                except Exception:
                    pass
            total_verses += cur_verses
            match = (cur_chapters == exp_ch and cur_verses == exp_v)
            if not match:
                all_books_valid = False
            books_stat.append({
                "key": key,
                "name": name,
                "expected_chapters": exp_ch,
                "chapters": cur_chapters,
                "expected_verses": exp_v,
                "verses": cur_verses,
                "file_exists": f_exists,
                "match": match
            })

        # 3. 測試報告狀態
        fails_path = os.path.join(SITE_ROOT, "FAILS.md")
        fails_content = ""
        fails_all_pass = False
        if os.path.isfile(fails_path):
            with open(fails_path, "r", encoding="utf-8") as f:
                fails_content = f.read()
                fails_all_pass = ("全部通過" in fails_content)

        # 4. site 前台核心檔案完整性
        site_required = ["index.html", "chapter.html", "search.html", "card.html", "style.css", "app.js"]
        site_files = {f: os.path.isfile(os.path.join(SITE_ROOT, "site", f)) for f in site_required}
        all_site_files_exist = all(site_files.values())

        data = {
            "project": "Bible-Master 四福音聖經網站",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "frontend": {
                "port": 8090,
                "online": fe_ok,
                "status_code": fe_code if fe_ok else None,
                "latency_ms": fe_latency,
                "url": "http://127.0.0.1:8090/site/index.html",
                "direct_url": "http://127.0.0.1:8090/site/index.html"
            },
            "backend": {
                "port": self.server.server_address[1],
                "online": True
            },
            "books": books_stat,
            "total_verses": total_verses,
            "expected_total_verses": 3776,
            "database_ok": all_books_valid and total_verses == 3776,
            "site_files": site_files,
            "site_files_ok": all_site_files_exist,
            "fails_pass": fails_all_pass,
            "fails_summary": fails_content.splitlines()[0] if fails_content else "無紀錄"
        }
        self.send_json(data)

    def handle_api_models(self):
        results = []
        for node in MODEL_NODES:
            ok, info, latency = probe_url(node["url"], timeout=1.5)
            if not ok and node.get("alt_url"):
                ok, info, latency = probe_url(node["alt_url"], timeout=1.5)
            
            results.append({
                "id": node["id"],
                "name": node["name"],
                "host": node["host"],
                "port": node["port"],
                "online": ok,
                "status_detail": str(info),
                "latency_ms": latency if ok else None,
                "hint": node["hint"]
            })
        self.send_json({"models": results, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})

    def handle_api_tasks(self):
        tasks_dir = os.path.join(SITE_ROOT, "tasks")
        tasks = []
        if os.path.isdir(tasks_dir):
            for fname in sorted(os.listdir(tasks_dir)):
                if fname.endswith(".md"):
                    fpath = os.path.join(tasks_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read(2048)
                    role_m = re.search(r"role:\s*([^\n]+)", content)
                    files_m = re.search(r"files:\s*\[([^\]]+)\]", content)
                    tasks.append({
                        "file": fname,
                        "role": role_m.group(1).strip() if role_m else "未指定",
                        "files": files_m.group(1).strip() if files_m else ""
                    })
        self.send_json({"tasks": tasks})

    def handle_api_report(self, report_name):
        safe_name = os.path.basename(report_name)
        if safe_name not in REPORT_WHITELIST:
            self.send_json({"error": "找不到指定報告檔案"}, code=404)
            return
        report_path = os.path.join(SITE_ROOT, safe_name)
        if not os.path.isfile(report_path):
            self.send_json({"error": "找不到指定報告檔案"}, code=404)
            return
        with open(report_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 最多返回後 250 行，避免過大
        tail = "".join(lines[-250:]) if len(lines) > 250 else "".join(lines)
        self.send_json({"name": safe_name, "content": tail, "total_lines": len(lines)})

    def handle_run_command(self, cmd, title):
        # 同一時間只能執行一個動作
        if not ACTION_LOCK.acquire(blocking=False):
            self.send_json({"error": "已有動作執行中"}, code=409)
            return
        start_t = time.time()
        try:
            p = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=180)
            elapsed = round(time.time() - start_t, 2)
            self.send_json({
                "action": title,
                "success": (p.returncode == 0),
                "exit_code": p.returncode,
                "elapsed_seconds": elapsed,
                "stdout": p.stdout,
                "stderr": p.stderr,
                "output": (p.stdout + "\n" + p.stderr).strip()
            })
        except subprocess.TimeoutExpired:
            self.send_json({
                "action": title,
                "success": False,
                "exit_code": -1,
                "output": f"執行逾時（超過 180 秒）"
            }, code=500)
        except Exception as e:
            self.send_json({
                "action": title,
                "success": False,
                "exit_code": -1,
                "output": f"執行異常：{e}"
            }, code=500)
        finally:
            ACTION_LOCK.release()


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server(host="127.0.0.1", port=8091):
    server = ThreadingHTTPServer((host, port), AdminRequestHandler)
    print(f"=================================================================")
    print(f" 📖 Bible-Master 後台管理與運維服務啟動成功！")
    print(f" 🌐 後台位址: http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/")
    print(f" 📂 服務目錄: {HERE}")
    print(f" ⏱️ 啟動時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n後台服務接收到終止信號，正常退出。")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bible-Master 後台管理與 API 伺服器")
    parser.add_argument("--host", default="127.0.0.1", help="監聽主機 IP（預設 127.0.0.1，只限本機）")
    parser.add_argument("--port", type=int, default=8091, help="監聽埠號 (預設 8091)")
    args = parser.parse_args()
    run_server(args.host, args.port)
