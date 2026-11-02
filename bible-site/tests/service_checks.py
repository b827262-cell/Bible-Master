#!/usr/bin/env python3
"""Checks for the ops services (exit code 0 only when all pass). Never touches the live 8090/8091 services.
  admin    bible-site/admin/server.py, started here on a free 127.0.0.1 port:
           no CORS headers, 404s answered, only index.html/admin.js/admin.css served, report whitelist,
           POST actions need the X-Bible-Admin header and a same-origin (or absent) Origin, build_data removed,
           default --host 127.0.0.1, no Simplified Chinese, no hard-coded 127.0.0.1:8090 links, no stale "47 項"
  service  start.sh on FRONTEND_PORT=18190 BACKEND_PORT=18191: start/stop cycle, per-port PID files,
           back end bound to 127.0.0.1, a foreign listener is neither adopted nor killed
Usage: python3 bible-site/tests/service_checks.py [admin] [service] [--grep REGEX]   (no group: both)"""
import hashlib, json, os, re, socket, subprocess, sys, tempfile, time, urllib.error, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ADMIN = os.path.join(ROOT, "bible-site", "admin")
START = os.path.join(ROOT, "start.sh")
LIVE = (8090, 8091)
FE, BE = 18190, 18191
SIMPLIFIED = ["后台", "运行", "启动", "状态", "检查", "数据", "报告", "服务", "测试", "连接", "节点", "获取", "页面",
              "错误", "时间", "执行", "动作", "终端", "网站", "监听", "进程"]  # Simplified-only words
results = []
ONLY = None  # --grep REGEX: only checks whose name matches count


def check(name, ok, detail=""):
    if ONLY and not re.search(ONLY, name):
        return
    results.append(ok)
    print(("通過" if ok else "不通過") + f"：{name}" + (f"（{detail}）" if detail else ""))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def request(url, method="GET", headers=None, timeout=60):
    """Returns (status, headers, body); status 0 means the server closed the connection without an answer."""
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, {}, str(e)


def listeners():
    out = subprocess.run(["ss", "-ltnpH"], capture_output=True, text=True).stdout
    found = {}
    for line in out.splitlines():
        m = re.search(r"\s(\S+):(\d+)\s.*pid=(\d+)", line)
        if m:
            found[int(m.group(2))] = (m.group(1), int(m.group(3)))
    return found


def admin():
    src = {f: open(os.path.join(ADMIN, f), encoding="utf-8").read() for f in ("server.py", "admin.js", "index.html", "admin.css")}
    bad = [f"{f}:{w}" for f, s in src.items() for w in SIMPLIFIED if w in s]
    check("後台檔案沒有簡體字", not bad, "、".join(bad[:10]))
    m = re.search(r'add_argument\("--host"[^)]*default="([^"]+)"', src["server.py"])
    check("server.py 的 --host 預設是 127.0.0.1", bool(m) and m.group(1) == "127.0.0.1", m.group(1) if m else "找不到 --host")
    hard = [f for f in ("admin.js", "index.html") if "127.0.0.1:8090" in src[f]]
    check("admin.js、index.html 沒有寫死 127.0.0.1:8090（用 location.hostname 組網址）", not hard, "、".join(hard))
    check("index.html 沒有過時的「47 項」", "47 項" not in src["index.html"])
    check("admin.js 送出 POST 時帶 X-Bible-Admin 標頭", re.search(r"X-Bible-Admin", src["admin.js"]) is not None)

    port = free_port()
    proc = subprocess.Popen([sys.executable, os.path.join(ADMIN, "server.py"), "--host", "127.0.0.1", "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            if request(base + "/api/ping", timeout=2)[0] == 200:
                break
            time.sleep(0.1)
        st, h, body = request(base + "/api/status")
        check("GET /api/status 回 200 且 total_verses 為 3776", st == 200 and json.loads(body or "{}").get("total_verses") == 3776, f"HTTP {st}")
        cors = [p for p, meth in (("/api/status", "GET"), ("/api/action/smoke_test", "OPTIONS"), ("/api/ping", "GET"))
                if any(k.lower().startswith("access-control-") for k in request(base + p, meth)[1])]
        check("任何回應都沒有 Access-Control-* 標頭", not cors, "、".join(cors))
        st, _, body = request(base + "/api/unknown")
        check("GET /api/unknown 回 404 並有內容（不是空回應）", st == 404 and body.strip() != "", f"HTTP {st}")
        st, _, _ = request(base + "/nonexistent.png")
        check("GET /nonexistent.png 回 404（不是空回應）", st == 404, f"HTTP {st}")
        served = {p: request(base + p)[0] for p in ("/", "/index.html", "/admin.js", "/admin.css", "/server.py", "/__pycache__/")}
        good = all(served[p] == 200 for p in ("/", "/index.html", "/admin.js", "/admin.css")) and served["/server.py"] == 404 and served["/__pycache__/"] == 404
        check("靜態檔只提供 index.html、admin.js、admin.css（server.py 回 404）", good, json.dumps(served))
        head = {p: request(base + p, "HEAD")[0] for p in ("/", "/admin.js", "/server.py", "/__pycache__/", "/api/unknown")}
        good = head["/"] == 200 and head["/admin.js"] == 200 and all(head[p] == 404 for p in ("/server.py", "/__pycache__/", "/api/unknown"))
        check("HEAD 也套用同一份白名單（HEAD /server.py、/__pycache__/ 回 404）", good, json.dumps(head))
        rep = {n: request(base + "/api/report/" + n)[0] for n in ("TEST-REPORT.md", "FAILS.md", "DISPATCH-REPORT.md", "CLAUDE.md", "HANDOFF.md", "SERVICE-REPORT.md", "PLAN.md")}
        good = all(rep[n] == 200 for n in ("TEST-REPORT.md", "FAILS.md", "DISPATCH-REPORT.md")) and all(rep[n] == 404 for n in ("CLAUDE.md", "HANDOFF.md", "SERVICE-REPORT.md", "PLAN.md"))
        check("/api/report/ 只讀白名單報告（CLAUDE.md、HANDOFF.md 等回 404）", good, json.dumps(rep))
        st, _, _ = request(base + "/api/action/smoke_test", "POST")
        check("POST /api/action/smoke_test 沒帶 X-Bible-Admin 回 403", st == 403, f"HTTP {st}")
        st, _, _ = request(base + "/api/action/smoke_test", "POST", {"X-Bible-Admin": "1", "Origin": "http://evil.example"})
        check("POST 帶 X-Bible-Admin 但 Origin 是外站回 403", st == 403, f"HTTP {st}")
        st, _, body = request(base + "/api/action/smoke_test", "POST", {"X-Bible-Admin": "1", "Origin": base})
        ok = st == 200 and json.loads(body or "{}").get("success") is True
        check("POST 帶 X-Bible-Admin 與同源 Origin 可執行 smoke_test", ok, f"HTTP {st} {body[:120]}")
        # never POST build_data while the route may still exist: it rewrites data/*.json
        if "build_data" in src["server.py"]:
            check("POST /api/action/build_data 已移除", False, "server.py 仍有 build_data")
        else:
            st, _, _ = request(base + "/api/action/build_data", "POST", {"X-Bible-Admin": "1"})
            check("POST /api/action/build_data 已移除（回 404）", st == 404, f"HTTP {st}")
    finally:
        proc.terminate()
        try:
            _, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, err = proc.communicate()
    check("後台處理請求時沒有 Traceback", "Traceback" not in err, err.strip().splitlines()[-1] if "Traceback" in err else "")


def run_start(*args, root=ROOT, **extra):
    env = dict(os.environ, FRONTEND_PORT=str(FE), BACKEND_PORT=str(BE))
    env.pop("BIND_HOST", None)
    env.pop("BACKEND_BIND", None)
    env.update(extra)
    p = subprocess.run(["bash", os.path.join(root, "start.sh"), *args], cwd=root, env=env, capture_output=True, text=True, timeout=120)
    return p.returncode, re.sub(r"\x1b\[[0-9;]*m", "", p.stdout + p.stderr)


def cleanup_test_ports():
    """Kills whatever still listens on the test ports FE/BE (never the live ones), so a failed stop does not leak."""
    for port, (_, pid) in listeners().items():
        if port in (FE, BE):
            try:
                os.kill(pid, 15)
            except OSError:
                pass
    for _ in range(50):
        if not {FE, BE} & set(listeners()):
            break
        time.sleep(0.1)


def lookalike_check(label, port, argv):
    """A foreign process whose command line looks like ours, started outside the project: not adopted, not killed."""
    foreign = subprocess.Popen(argv, cwd="/tmp", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            if port in listeners():
                break
            time.sleep(0.1)
        rc, _ = run_start("start")
        check(f"{label}：start 不沿用並以非 0 結束", rc != 0, f"rc={rc}")
        run_start("stop")
        check(f"{label}：stop 不會殺掉它", foreign.poll() is None)
    finally:
        foreign.terminate()
        foreign.wait(timeout=5)
        cleanup_test_ports()


def service():
    src = open(START, encoding="utf-8").read()
    pattern = re.findall(r"\b(pkill|killall)\b", src)
    check("start.sh 沒有用 pkill／killall 依名稱殺行程", not pattern, "、".join(pattern))
    if pattern:
        return
    live_before = {p: listeners().get(p) for p in LIVE}
    pid_files = {f: hashlib.md5(open(os.path.join(ROOT, "logs", f), "rb").read()).hexdigest()
                 for f in ("frontend.pid", "backend.pid") if os.path.exists(os.path.join(ROOT, "logs", f))}
    try:
        rc, out = run_start("start")
        ls = listeners()
        check(f"start.sh start（{FE}/{BE}）成功且兩個埠都在監聽", rc == 0 and FE in ls and BE in ls, f"rc={rc}")
        check(f"後台預設只綁 127.0.0.1（{BE}）", ls.get(BE, ("?",))[0] == "127.0.0.1", str(ls.get(BE)))
        st = request(f"http://127.0.0.1:{FE}/site/index.html")[0], request(f"http://127.0.0.1:{BE}/api/ping")[0]
        check("前台 /site/index.html 與後台 /api/ping 都回 200", st == (200, 200), str(st))
        names = [f"frontend-{FE}.pid", f"backend-{BE}.pid"]
        have = [n for n in names if os.path.exists(os.path.join(ROOT, "logs", n))]
        check("PID 檔名帶埠號（logs/frontend-<port>.pid、backend-<port>.pid）", have == names, "、".join(have) or "沒有")
        rc, out = run_start("stop")
        ls = listeners()
        check("start.sh stop 後兩個埠都釋放", FE not in ls and BE not in ls, f"rc={rc}")
        # a foreign listener on the front-end port: start must refuse, stop must leave it alone
        foreign = subprocess.Popen([sys.executable, "-m", "http.server", str(FE), "--bind", "127.0.0.1"],
                                   cwd="/tmp", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                if FE in listeners():
                    break
                time.sleep(0.1)
            rc, out = run_start("start")
            check("埠被外來行程佔用時 start 回報錯誤並以非 0 結束（不沿用）", rc != 0, f"rc={rc}")
            run_start("stop")
            check("stop 不會殺掉外來行程", foreign.poll() is None)
        finally:
            foreign.terminate()
            foreign.wait(timeout=5)
            run_start("stop")
            cleanup_test_ports()
        # stop must not depend on the BIND_HOST of the shell that runs it
        run_start("start", BIND_HOST="127.0.0.1")
        rc, out = run_start("stop")
        ls = listeners()
        check("以 BIND_HOST=127.0.0.1 啟動、預設環境 stop 後兩個埠都釋放", FE not in ls and BE not in ls, f"rc={rc}")
        cleanup_test_ports()
        # the project reached through a symlink: /proc/<pid>/cwd is the real path, so start.sh must compare real paths
        link_dir = tempfile.mkdtemp(prefix="bible-link-")
        link = os.path.join(link_dir, "proj")
        os.symlink(ROOT, link)
        try:
            run_start("start", root=link)
            rc, out = run_start("stop", root=link)
            ls = listeners()
            check("經由軟連結路徑啟動、同路徑 stop 後兩個埠都釋放", FE not in ls and BE not in ls, f"rc={rc}")
        finally:
            os.remove(link)
            os.rmdir(link_dir)
            cleanup_test_ports()
        lookalike_check(f"外來行程的指令列與前台相同（/tmp 下的 http.server {FE} --bind 0.0.0.0）", FE,
                        [sys.executable, "-u", "-m", "http.server", str(FE), "--bind", "0.0.0.0"])
        fake = f"import http.server as h; h.HTTPServer(('127.0.0.1', {BE}), h.SimpleHTTPRequestHandler).serve_forever()"
        lookalike_check(f"外來行程的指令列含 admin/server.py --port {BE}（不是本專案的 server.py）", BE,
                        [sys.executable, "-c", fake, "admin/server.py", "--port", str(BE)])
    finally:
        cleanup_test_ports()
        live_after = {p: listeners().get(p) for p in LIVE}
        check("線上 8090/8091 服務的 PID 沒有變", live_before == live_after, f"{live_before} → {live_after}")
        changed = [f for f, h in pid_files.items() if not os.path.exists(os.path.join(ROOT, "logs", f))
                   or hashlib.md5(open(os.path.join(ROOT, "logs", f), "rb").read()).hexdigest() != h]
        check("線上服務的 logs/frontend.pid、backend.pid 沒有被改或刪", not changed, "、".join(changed))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--grep" in args:
        i = args.index("--grep")
        ONLY = args[i + 1]
        del args[i:i + 2]
    groups = set(args) or {"admin", "service"}
    if "admin" in groups:
        admin()
    if "service" in groups:
        service()
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
