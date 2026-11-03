#!/usr/bin/env python3
"""Checks for the ops services (exit code 0 only when all pass). Never touches the live 8090/8091 services.
  admin    bible-site/admin/server.py, started here on a free 127.0.0.1 port:
           no CORS headers, 404s answered, only index.html/admin.js/admin.css served, report whitelist,
           POST actions need the X-Bible-Admin header and a same-origin (or absent) Origin, build_data removed,
           default --host 127.0.0.1, no Simplified Chinese, no hard-coded 127.0.0.1:8090 links, no stale "47 項"
  homeadmin  the write endpoints of the admin server (home page settings + uploads), run against a temp copy of data/ and
           site/assets/ (BIBLE_SITE_ROOT, BIBLE_ADMIN_TOKEN_FILE): token, auth, validation, magic bytes, size limits
  zoneadmin  the endpoints that choose the background music of the four front-end zones (GET/POST /api/zone-music, /api/zone-music/reset)
           and the admin page block "前台音樂", on a temp copy like homeadmin
  blessartadmin  the endpoints for the per-theme collectible art of 抽經文卡 (GET/POST /api/blessing-art, /api/blessing-art/reset) and the admin block "收藏卡圖片";
           also proves that no admin operation touches blessing.json (the 37 cards are fixed)
  service  start.sh on FRONTEND_PORT=18190 BACKEND_PORT=18191: start/stop cycle, per-port PID files,
           back end bound to 127.0.0.1, a foreign listener is neither adopted nor killed
Usage: python3 bible-site/tests/service_checks.py [admin] [service] [--grep REGEX]   (no group: both)"""
import hashlib, json, os, re, socket, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request

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


def req2(url, method="GET", headers=None, body=None, timeout=60):
    """Like request() but with a request body; returns (status, headers, text)."""
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, {}, str(e)


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest() if os.path.exists(path) else None


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 2000
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 2000
WEBP = b"RIFF\x00\x10\x00\x00WEBPVP8 " + b"\x00" * 2000
MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" + b"\x00" * 2000


def homeadmin():
    import shutil
    src = open(os.path.join(ADMIN, "admin.js"), encoding="utf-8").read()
    check("admin.js 送出寫入請求時帶 X-Bible-Token 標頭", "X-Bible-Token" in src)
    page = open(os.path.join(ADMIN, "index.html"), encoding="utf-8").read()
    ids = ["home-settings", "home-book", "home-ch", "home-v", "home-verse-preview", "home-image-file", "home-image-select", "home-image-preview",
           "home-alt", "home-music-file", "home-music-select", "home-music-preview", "home-save", "home-reset", "home-open", "home-status"]
    miss = [i for i in ids if f'id="{i}"' not in page]
    check("後台 index.html 有「主頁設定」區塊需要的 16 個 id", not miss, "、".join(miss))
    check("後台「主頁設定」文字是繁體中文：有「主頁設定」「儲存」「還原預設」「記得執行發佈」", all(t in page + src for t in ("主頁設定", "儲存", "還原預設", "發佈")))
    check("admin.js 的素材預覽走同源 /site-assets/（不再指向 :8090/assets/）", "/site-assets/" in src and not re.search(r":8090/\$\{path\}", src))
    check("admin.js 使用 /api/token、/api/home、/api/home/reset、/api/upload", all(u in src for u in ("/api/token", "/api/home", "/api/home/reset", "/api/upload")))
    check("admin.js 的經文預覽用 /api/book/（不寫死經文）且不載入外部資源", "/api/book/" in src and "https://" not in src)
    gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read()
    check(".gitignore 排除 admin/.token", ".token" in gi)
    live_cfg = os.path.join(ROOT, "bible-site", "data", "home.json")
    live_before = md5(live_cfg)
    tmp = tempfile.mkdtemp()
    shutil.copytree(os.path.join(ROOT, "bible-site", "data"), os.path.join(tmp, "data"))
    os.makedirs(os.path.join(tmp, "site"))
    shutil.copytree(os.path.join(ROOT, "bible-site", "site", "assets"), os.path.join(tmp, "site", "assets"))
    cfgf, assets, tokf = os.path.join(tmp, "data", "home.json"), os.path.join(tmp, "site", "assets"), os.path.join(tmp, "token")
    if os.path.exists(cfgf):
        os.remove(cfgf)  # start from "no config": GET /api/home must report the defaults
    default_md5 = {n: md5(os.path.join(assets, n)) for n in ("jordan.jpg", "home-music.mp3")}
    port = free_port()
    env = dict(os.environ, BIBLE_SITE_ROOT=os.path.join(tmp), BIBLE_ADMIN_TOKEN_FILE=tokf)
    # BIBLE_SITE_ROOT is the directory that holds data/ and site/ (the real one is bible-site/)
    proc = subprocess.Popen([sys.executable, os.path.join(ADMIN, "server.py"), "--host", "127.0.0.1", "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            if request(base + "/api/ping", timeout=2)[0] == 200:
                break
            time.sleep(0.1)
        st, _, body = req2(base + "/api/token")
        token = json.loads(body).get("token", "") if st == 200 else ""
        check("GET /api/token 在本機位址回 200，給 32 字以上的 token", st == 200 and len(token) >= 32, f"HTTP {st}")
        check("token 檔存在、權限 600、內容就是 token", os.path.exists(tokf) and oct(os.stat(tokf).st_mode & 0o777) == "0o600" and open(tokf).read().strip() == token,
              oct(os.stat(tokf).st_mode & 0o777) if os.path.exists(tokf) else "沒有檔案")
        st, _, _ = req2(base + "/api/token", headers={"Host": "evil.example"})
        check("GET /api/token 的 Host 不是本機位址（DNS rebinding）回 403", st == 403, f"HTTP {st}")
        st, _, _ = req2(base + "/api/token", headers={"Origin": "http://evil.example"})
        check("GET /api/token 帶外站 Origin 回 403", st == 403, f"HTTP {st}")
        st, _, body = req2(base + "/api/book/luk")
        luk = json.loads(body) if st == 200 else {}
        check("GET /api/book/luk 回 200 與路加福音 24 章 1149 節", st == 200 and len(luk.get("chapters", [])) == 24 and sum(len(c["verses"]) for c in luk.get("chapters", [])) == 1149, f"HTTP {st}")
        st, _, _ = req2(base + "/api/book/..%2Fhome")
        st2, _, _ = req2(base + "/api/book/blessing")
        check("GET /api/book/ 只接受 mat／mrk／luk／jhn（其他回 404）", st == 404 and st2 == 404, f"HTTP {st}/{st2}")
        good = {"X-Bible-Admin": "1", "X-Bible-Token": token, "Content-Type": "application/json"}
        st, _, body = req2(base + "/api/home")
        info = json.loads(body) if st == 200 else {}
        cfg0 = info.get("config", {})
        check("GET /api/home 沒有設定檔時回預設值（luk 4:27、jordan.jpg、home-music.mp3）",
              st == 200 and (cfg0.get("book"), cfg0.get("ch"), cfg0.get("v"), cfg0.get("image"), cfg0.get("music")) == ("luk", 4, 27, "assets/jordan.jpg", "assets/home-music.mp3"), body[:120])
        check("GET /api/home 列出 assets/ 的圖片與音樂", "assets/jordan.jpg" in info.get("images", []) and "assets/home-music.mp3" in info.get("music", []), body[:160])
        ok_cfg = {"book": "jhn", "ch": 3, "v": 16, "image": "assets/jordan.jpg", "alt": "測試圖片說明", "music": "assets/home-music.mp3"}
        post = lambda path, obj, hdr=None, raw=None: req2(base + path, "POST", dict(good, **(hdr or {})), raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode("utf-8"))
        for label, hdr in (("沒帶 X-Bible-Token", {"X-Bible-Token": ""}), ("token 錯誤", {"X-Bible-Token": "x" * 43}), ("沒帶 X-Bible-Admin", {"X-Bible-Admin": ""}),
                           ("Origin 是外站", {"Origin": "http://evil.example"}), ("Host 不是本機", {"Host": "evil.example"})):
            st, _, _ = post("/api/home", ok_cfg, hdr)
            check(f"POST /api/home {label} 回 403", st == 403, f"HTTP {st}")
        check("驗證失敗時沒有寫出 home.json", not os.path.exists(cfgf))
        st, _, body = post("/api/home", ok_cfg)
        saved = json.load(open(cfgf, encoding="utf-8")) if os.path.exists(cfgf) else {}
        check("POST /api/home 合法設定回 200，home.json 寫入的內容與送出的相同", st == 200 and saved == ok_cfg, f"HTTP {st} {body[:100]}")
        st, _, body = req2(base + "/api/home")
        check("GET /api/home 回傳剛存的設定", st == 200 and json.loads(body).get("config") == ok_cfg)
        before = md5(cfgf)
        bad = {"書卷不存在": dict(ok_cfg, book="xyz"), "章不存在": dict(ok_cfg, ch=99), "節不存在": dict(ok_cfg, v=999), "章是字串": dict(ok_cfg, ch="3"),
               "圖片跳出 assets/": dict(ok_cfg, image="assets/../../data/luk.json"), "圖片指向 data/": dict(ok_cfg, image="data/luk.json"),
               "圖片檔不存在": dict(ok_cfg, image="assets/nope.jpg"), "圖片是 mp3": dict(ok_cfg, image="assets/home-music.mp3"), "音樂是 jpg": dict(ok_cfg, music="assets/jordan.jpg"),
               "圖片是絕對路徑": dict(ok_cfg, image="/etc/passwd"), "圖片是網址": dict(ok_cfg, image="https://evil.example/a.jpg"),
               "alt 空白": dict(ok_cfg, alt="  "), "alt 超過 120 字": dict(ok_cfg, alt="字" * 121), "多出欄位": dict(ok_cfg, extra="x"), "缺欄位": {k: v for k, v in ok_cfg.items() if k != "music"}}
        for label, obj in bad.items():
            st, _, _ = post("/api/home", obj)
            check(f"POST /api/home 拒絕「{label}」回 400", st == 400, f"HTTP {st}")
        st, _, _ = post("/api/home", None, raw=b"not json")
        check("POST /api/home 拒絕不是 JSON 的內容回 400", st == 400, f"HTTP {st}")
        st, _, _ = post("/api/home", None, raw=b"{" + b" " * 70000 + b"}")
        check("POST /api/home 內容超過 64 KB 回 413", st == 413, f"HTTP {st}")
        check("所有被拒絕的請求都沒有改動 home.json", md5(cfgf) == before)
        up = lambda kind, data, name="photo.jpg", hdr=None: req2(base + f"/api/upload?kind={kind}&name={urllib.parse.quote(name)}", "POST",
                                                                   {k: v for k, v in dict(good, **{"Content-Type": "application/octet-stream"}, **(hdr or {})).items()}, data)
        # previews: the admin page shows uploaded files through its own origin (/site-assets/<name>), never through :8090
        st, h, body = req2(base + "/site-assets/jordan.jpg")
        check("GET /site-assets/jordan.jpg 回 200、Content-Type 是 image/jpeg、內容與檔案相同", st == 200 and h.get("Content-Type", "").startswith("image/jpeg") and md5(os.path.join(assets, "jordan.jpg")) == hashlib.md5(urllib.request.urlopen(base + "/site-assets/jordan.jpg").read()).hexdigest(), f"HTTP {st} {h.get('Content-Type')}")
        st, h, _ = req2(base + "/site-assets/home-music.mp3", headers={"Range": "bytes=0-9"})
        check("GET /site-assets/home-music.mp3 支援 Range（回 206、Content-Range、10 位元組），音訊才能拖曳進度", st == 206 and h.get("Content-Range", "").startswith("bytes 0-9/") and h.get("Content-Length") == "10", f"HTTP {st} {h.get('Content-Range')}")
        st, h, _ = req2(base + "/site-assets/home-music.mp3")
        check("GET /site-assets/home-music.mp3 回 200、audio/mpeg、Accept-Ranges: bytes", st == 200 and h.get("Content-Type", "").startswith("audio/mpeg") and h.get("Accept-Ranges") == "bytes", f"HTTP {st} {h.get('Content-Type')}")
        codes = {n: req2(base + "/site-assets/" + n)[0] for n in ("nope.jpg", "..%2f..%2fdata%2fluk.json", "%2e%2e/data/luk.json", "a.json", ".hidden.jpg", "jordan.jpg/x")}
        check("GET /site-assets/ 不存在、跳出目錄、非素材副檔名的檔名都回 404", all(c == 404 for c in codes.values()), json.dumps(codes))
        st, _, _ = req2(base + "/site-assets/jordan.jpg", "POST", good)
        check("POST /site-assets/ 不接受（不回 200）", st != 200, f"HTTP {st}")
        st, _, _ = up("image", JPEG, hdr={"X-Bible-Token": ""})
        check("POST /api/upload 沒帶 token 回 403", st == 403, f"HTTP {st}")
        names = {}
        for label, kind, data, name, ext in (("jpg", "image", JPEG, "photo.jpg", "jpg"), ("png", "image", PNG, "photo.png", "png"), ("webp", "image", WEBP, "photo.webp", "webp"), ("mp3", "music", MP3, "song.mp3", "mp3")):
            st, _, body = up(kind, data, name)
            path = json.loads(body).get("path", "") if st == 200 else ""
            names[label] = path
            check(f"POST /api/upload 收下真的 {label}，存成 assets/upload-*.{ext}，內容與上傳的相同",
                  st == 200 and re.fullmatch(r"assets/upload-[A-Za-z0-9._-]+\." + ext, path) is not None and open(os.path.join(tmp, "site", path), "rb").read() == data, f"HTTP {st} {path}")
        st, _, got = req2(base + "/site-assets/" + names["jpg"].split("/")[-1])
        check("剛上傳的檔案可以經 /site-assets/ 預覽（回 200，位元組相同）", st == 200 and len(got) > 0 and hashlib.md5(urllib.request.urlopen(base + "/site-assets/" + names["jpg"].split("/")[-1]).read()).hexdigest() == hashlib.md5(JPEG).hexdigest(), f"HTTP {st}")
        st, _, body2 = up("image", JPEG, "photo.jpg")
        check("連續上傳同一個檔案不會覆蓋前一個（檔名不重複）", st == 200 and json.loads(body2).get("path") != names["jpg"], body2[:100])
        for label, kind, data, name in (("文字檔改名 .jpg", "image", b"hello world" * 300, "fake.jpg"), ("mp3 當圖片", "image", MP3, "a.jpg"), ("png 當音樂", "music", PNG, "a.mp3"),
                                        ("不認得的 kind", "video", JPEG, "a.jpg"), ("副檔名 .svg", "image", JPEG, "a.svg"), ("副檔名 .html", "image", JPEG, "a.html"), ("空檔案", "image", b"", "a.jpg")):
            n_before = len(os.listdir(assets))
            st, _, _ = up(kind, data, name)
            check(f"POST /api/upload 拒絕「{label}」回 400，且沒有留下檔案", st == 400 and len(os.listdir(assets)) == n_before, f"HTTP {st}")
        n_before = len(os.listdir(assets))
        st, _, body = up("image", JPEG, "../../data/luk.json.jpg")
        path = json.loads(body).get("path", "") if st == 200 else ""
        check("上傳檔名含 ../ 時，存檔名與原檔名無關、仍在 assets/ 底下", st == 200 and re.fullmatch(r"assets/upload-[A-Za-z0-9._-]+\.jpg", path) is not None and ".." not in path, f"HTTP {st} {path}")
        n_before = len(os.listdir(assets))
        st, _, _ = up("image", JPEG + b"\x00" * (5 * 1024 * 1024))
        check("POST /api/upload 圖片超過 5 MB 回 413，且沒有留下檔案", st == 413 and len(os.listdir(assets)) == n_before, f"HTTP {st}")
        st, _, _ = up("music", MP3 + b"\x00" * (8 * 1024 * 1024), "big.mp3")
        check("POST /api/upload 音樂超過 8 MB 回 413，且沒有留下檔案", st == 413 and len(os.listdir(assets)) == n_before, f"HTTP {st}")
        cfg_up = dict(ok_cfg, image=names["png"], music=names["mp3"])
        st, _, body = post("/api/home", cfg_up)
        check("上傳的圖片與音樂可以設為主頁（POST /api/home 回 200）", st == 200 and json.load(open(cfgf, encoding="utf-8")) == cfg_up, f"HTTP {st} {body[:100]}")
        st, _, body = post("/api/home/reset", {})
        check("POST /api/home/reset 回 200，設定回到預設值", st == 200 and (json.load(open(cfgf, encoding="utf-8")) if os.path.exists(cfgf) else {}).get("book") == "luk"
              and json.load(open(cfgf, encoding="utf-8")).get("image") == "assets/jordan.jpg", f"HTTP {st} {body[:100]}")
        check("還原預設後，上傳的檔案還在", all(os.path.exists(os.path.join(tmp, "site", p)) for p in names.values()))
        st, _, _ = post("/api/home/reset", {}, {"X-Bible-Token": ""})
        check("POST /api/home/reset 沒帶 token 回 403", st == 403, f"HTTP {st}")
        st, _, _ = req2(base + "/api/home", "DELETE", good)
        check("沒有刪除端點：DELETE /api/home 不回 200", st != 200, f"HTTP {st}")
        check("預設的 jordan.jpg、home-music.mp3 內容完全沒變", {n: md5(os.path.join(assets, n)) for n in default_md5} == default_md5)
        leftovers = [f for d in (os.path.join(tmp, "data"), assets) for f in os.listdir(d) if f.endswith((".tmp", ".part")) or f.startswith(".")]
        check("沒有留下暫存檔（原子寫入）", not leftovers, "、".join(leftovers))
        check("測試沒有動到真正的 data/home.json", md5(live_cfg) == live_before)
    finally:
        proc.terminate()
        try:
            _, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, err = proc.communicate()
        shutil.rmtree(tmp, ignore_errors=True)
    check("寫入端點處理請求時後台沒有 Traceback", "Traceback" not in err, err.strip().splitlines()[-1] if "Traceback" in err else "")


def zoneadmin():
    """The admin endpoints that choose the background music of the four zone pages (data/zone-music.json), on a temp copy."""
    import shutil
    src = open(os.path.join(ADMIN, "admin.js"), encoding="utf-8").read()
    page = open(os.path.join(ADMIN, "index.html"), encoding="utf-8").read()
    ids = ["zone-music-settings", "zone-music-file", "zone-music-select", "zone-music-preview", "zone-music-save", "zone-music-reset", "zone-music-status"]
    miss = [i for i in ids if f'id="{i}"' not in page]
    check("zoneadmin：後台 index.html 有「前台音樂」區塊需要的 7 個 id", not miss, "、".join(miss))
    check("zoneadmin：後台「前台音樂」文字是繁體中文：有「前台音樂」「儲存」「還原預設」「發佈」", all(t in page + src for t in ("前台音樂", "儲存", "還原預設", "發佈")))
    check("zoneadmin：admin.js 使用 /api/zone-music、/api/zone-music/reset，寫入時帶 X-Bible-Token，預覽走 /site-assets/", all(u in src for u in ("/api/zone-music", "/api/zone-music/reset", "X-Bible-Token", "/site-assets/")))
    live_cfg = os.path.join(ROOT, "bible-site", "data", "zone-music.json")
    live_before = md5(live_cfg)
    tmp = tempfile.mkdtemp()
    shutil.copytree(os.path.join(ROOT, "bible-site", "data"), os.path.join(tmp, "data"))
    os.makedirs(os.path.join(tmp, "site"))
    shutil.copytree(os.path.join(ROOT, "bible-site", "site", "assets"), os.path.join(tmp, "site", "assets"))
    cfgf, assets, tokf = os.path.join(tmp, "data", "zone-music.json"), os.path.join(tmp, "site", "assets"), os.path.join(tmp, "token")
    home_before = None
    if os.path.exists(cfgf):
        os.remove(cfgf)   # start from "no config": GET must report the default
    port = free_port()
    env = dict(os.environ, BIBLE_SITE_ROOT=tmp, BIBLE_ADMIN_TOKEN_FILE=tokf)
    proc = subprocess.Popen([sys.executable, os.path.join(ADMIN, "server.py"), "--host", "127.0.0.1", "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            if request(base + "/api/ping", timeout=2)[0] == 200:
                break
            time.sleep(0.1)
        st, _, body = req2(base + "/api/token")
        token = json.loads(body).get("token", "") if st == 200 else ""
        good = {"X-Bible-Admin": "1", "X-Bible-Token": token, "Content-Type": "application/json"}
        home_cfg = os.path.join(tmp, "data", "home.json")
        home_before = md5(home_cfg)
        st, _, body = req2(base + "/api/zone-music")
        info = json.loads(body) if st == 200 else {}
        check("zoneadmin：GET /api/zone-music 沒有設定檔時回 200 與預設值 assets/home-music.mp3", st == 200 and info.get("config") == {"music": "assets/home-music.mp3"} and info.get("default") == {"music": "assets/home-music.mp3"}, f"HTTP {st} {body[:120]}")
        check("zoneadmin：GET /api/zone-music 列出 assets/ 的 mp3", "assets/home-music.mp3" in info.get("music", []), body[:160])
        post = lambda path, obj, hdr=None, raw=None: req2(base + path, "POST", dict(good, **(hdr or {})), raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode("utf-8"))
        up = lambda data, name="song.mp3": req2(base + f"/api/upload?kind=music&name={urllib.parse.quote(name)}", "POST", dict(good, **{"Content-Type": "application/octet-stream"}), data)
        st, _, body = up(MP3)
        new = json.loads(body).get("path", "") if st == 200 else ""
        check("zoneadmin：先用既有 /api/upload 上傳一個 mp3（之後選它當前台音樂）", st == 200 and new.startswith("assets/upload-"), f"HTTP {st} {body[:100]}")
        for label, hdr in (("沒帶 X-Bible-Token", {"X-Bible-Token": ""}), ("token 錯誤", {"X-Bible-Token": "x" * 43}), ("沒帶 X-Bible-Admin", {"X-Bible-Admin": ""}),
                           ("Origin 是外站", {"Origin": "http://evil.example"}), ("Host 不是本機", {"Host": "evil.example"})):
            st, _, _ = post("/api/zone-music", {"music": new}, hdr)
            check(f"zoneadmin：POST /api/zone-music {label} 回 403", st == 403, f"HTTP {st}")
        check("zoneadmin：驗證失敗時沒有寫出 zone-music.json", not os.path.exists(cfgf))
        st, _, body = post("/api/zone-music", {"music": new})
        saved = json.load(open(cfgf, encoding="utf-8")) if os.path.exists(cfgf) else {}
        check("zoneadmin：POST /api/zone-music 合法設定回 200，檔案內容就是 {\"music\": 上傳的 mp3}", st == 200 and saved == {"music": new} and json.loads(body).get("config") == {"music": new}, f"HTTP {st} {body[:100]}")
        st, _, body = req2(base + "/api/zone-music")
        check("zoneadmin：GET /api/zone-music 回傳剛存的設定", st == 200 and json.loads(body).get("config") == {"music": new})
        before = md5(cfgf)
        bad = {"檔案不存在": {"music": "assets/nope.mp3"}, "跳出 assets/": {"music": "assets/../../data/luk.json"}, "指向 data/": {"music": "data/luk.json"},
               "是 jpg": {"music": "assets/jordan.jpg"}, "絕對路徑": {"music": "/etc/passwd"}, "網址": {"music": "https://evil.example/a.mp3"},
               "多出欄位": {"music": new, "extra": "x"}, "缺欄位": {}, "不是字串": {"music": 5}}
        for label, obj in bad.items():
            st, _, _ = post("/api/zone-music", obj)
            check(f"zoneadmin：POST /api/zone-music 拒絕「{label}」回 400", st == 400, f"HTTP {st}")
        st, _, _ = post("/api/zone-music", None, raw=b"not json")
        check("zoneadmin：POST /api/zone-music 拒絕不是 JSON 的內容回 400", st == 400, f"HTTP {st}")
        st, _, _ = post("/api/zone-music", None, raw=b"{" + b" " * 70000 + b"}")
        check("zoneadmin：POST /api/zone-music 內容超過 64 KB 回 413", st == 413, f"HTTP {st}")
        check("zoneadmin：所有被拒絕的請求都沒有改動 zone-music.json", md5(cfgf) == before)
        st, _, _ = post("/api/zone-music/reset", {}, {"X-Bible-Token": ""})
        check("zoneadmin：POST /api/zone-music/reset 沒帶 token 回 403", st == 403, f"HTTP {st}")
        st, _, body = post("/api/zone-music/reset", {})
        check("zoneadmin：POST /api/zone-music/reset 回 200，設定回到預設值，上傳的檔案還在",
              st == 200 and json.load(open(cfgf, encoding="utf-8")) == {"music": "assets/home-music.mp3"} and os.path.exists(os.path.join(tmp, "site", new)), f"HTTP {st} {body[:100]}")
        st, _, _ = req2(base + "/api/zone-music", "DELETE", good)
        check("zoneadmin：沒有刪除端點：DELETE /api/zone-music 不回 200", st != 200, f"HTTP {st}")
        check("zoneadmin：前台音樂的設定不影響首頁設定（home.json 完全沒變）", md5(home_cfg) == home_before)
        leftovers = [f for d in (os.path.join(tmp, "data"), assets) for f in os.listdir(d) if f.endswith((".tmp", ".part")) or f.startswith(".")]
        check("zoneadmin：沒有留下暫存檔（原子寫入）", not leftovers, "、".join(leftovers))
        check("zoneadmin：測試沒有動到真正的 data/zone-music.json", md5(live_cfg) == live_before)
    finally:
        proc.terminate()
        try:
            _, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, err = proc.communicate()
        shutil.rmtree(tmp, ignore_errors=True)
    check("zoneadmin：處理請求時後台沒有 Traceback", "Traceback" not in err, err.strip().splitlines()[-1] if "Traceback" in err else "")


def blessartadmin():
    """The admin endpoints for the per-theme collectible art of the 抽經文卡 page (data/blessing-art.json), on a temp copy. blessing.json stays untouched."""
    import shutil
    src = open(os.path.join(ADMIN, "admin.js"), encoding="utf-8").read()
    page = open(os.path.join(ADMIN, "index.html"), encoding="utf-8").read()
    themes = ("work", "peace", "rest", "faith")
    ids = ["blessing-art-settings", "art-status"] + [f"art-{t}-{k}" for t in themes for k in ("file", "alt", "edition", "preview", "save", "clear")]
    miss = [i for i in ids if f'id="{i}"' not in page]
    check("blessartadmin：後台 index.html 有「收藏卡圖片」區塊需要的 26 個 id（四個主題各 6 個＋區塊＋狀態）", not miss, "、".join(miss))
    check("blessartadmin：後台「收藏卡圖片」文字是繁體中文：有「收藏卡圖片」「每月」「版次」「儲存」「清除」「發佈」", all(t in page + src for t in ("收藏卡圖片", "每月", "版次", "儲存", "清除", "發佈")))
    check("blessartadmin：admin.js 使用 /api/blessing-art、/api/blessing-art/reset，寫入時帶 X-Bible-Token，預覽走 /site-assets/", all(u in src for u in ("/api/blessing-art", "/api/blessing-art/reset", "X-Bible-Token", "/site-assets/")))
    live_cfg = os.path.join(ROOT, "bible-site", "data", "blessing-art.json")
    live_before = md5(live_cfg)
    tmp = tempfile.mkdtemp()
    shutil.copytree(os.path.join(ROOT, "bible-site", "data"), os.path.join(tmp, "data"))
    os.makedirs(os.path.join(tmp, "site"))
    shutil.copytree(os.path.join(ROOT, "bible-site", "site", "assets"), os.path.join(tmp, "site", "assets"))
    cfgf, assets, tokf = os.path.join(tmp, "data", "blessing-art.json"), os.path.join(tmp, "site", "assets"), os.path.join(tmp, "token")
    if os.path.exists(cfgf):
        os.remove(cfgf)
    port = free_port()
    env = dict(os.environ, BIBLE_SITE_ROOT=tmp, BIBLE_ADMIN_TOKEN_FILE=tokf)
    proc = subprocess.Popen([sys.executable, os.path.join(ADMIN, "server.py"), "--host", "127.0.0.1", "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    base = f"http://127.0.0.1:{port}"
    guard = {n: md5(os.path.join(tmp, "data", n)) for n in ("blessing.json", "home.json", "zone-music.json", "mat.json")}
    try:
        for _ in range(50):
            if request(base + "/api/ping", timeout=2)[0] == 200:
                break
            time.sleep(0.1)
        st, _, body = req2(base + "/api/token")
        token = json.loads(body).get("token", "") if st == 200 else ""
        good = {"X-Bible-Admin": "1", "X-Bible-Token": token, "Content-Type": "application/json"}
        st, _, body = req2(base + "/api/blessing-art")
        info = json.loads(body) if st == 200 else {}
        th = {t.get("id"): t for t in info.get("themes", [])}
        check("blessartadmin：GET /api/blessing-art 回 200，四個主題 work／peace／rest／faith 的張數是 20／6／5／6、每個主題列出每張卡的出處",
              st == 200 and [th.get(t, {}).get("count") for t in themes] == [20, 6, 5, 6] and all(len(th[t].get("refs", [])) == th[t]["count"] for t in themes if t in th), body[:160])
        check("blessartadmin：GET /api/blessing-art 沒有設定檔時 config 是空物件，並列出 assets 的圖片", info.get("config") == {} and "assets/jordan.jpg" in info.get("images", []), body[:160])
        check("blessartadmin：出處用書卷代號、章、節（不含經文文字）", all(set(r) >= {"book", "ch", "v"} and "text" not in r for t in th.values() for r in t.get("refs", [])) and "耶穌" not in body.split('"refs"')[-1][:200])
        post = lambda path, obj, hdr=None, raw=None: req2(base + path, "POST", dict(good, **(hdr or {})), raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode("utf-8"))
        up = lambda data, name="art.png": req2(base + f"/api/upload?kind=image&name={urllib.parse.quote(name)}", "POST", dict(good, **{"Content-Type": "application/octet-stream"}), data)
        st, _, body = up(PNG)
        new = json.loads(body).get("path", "") if st == 200 else ""
        check("blessartadmin：先用既有 /api/upload 上傳一張 png", st == 200 and new.startswith("assets/upload-"), f"HTTP {st} {body[:100]}")
        ent = {"image": new, "alt": "測試用主題圖：金黃麥田", "edition": "2026 年 11 月版"}
        ok_cfg = {"work": ent}
        for label, hdr in (("沒帶 X-Bible-Token", {"X-Bible-Token": ""}), ("token 錯誤", {"X-Bible-Token": "x" * 43}), ("沒帶 X-Bible-Admin", {"X-Bible-Admin": ""}),
                           ("Origin 是外站", {"Origin": "http://evil.example"}), ("Host 不是本機", {"Host": "evil.example"})):
            st, _, _ = post("/api/blessing-art", ok_cfg, hdr)
            check(f"blessartadmin：POST /api/blessing-art {label} 回 403", st == 403, f"HTTP {st}")
        check("blessartadmin：驗證失敗時沒有寫出 blessing-art.json", not os.path.exists(cfgf))
        st, _, body = post("/api/blessing-art", ok_cfg)
        saved = json.load(open(cfgf, encoding="utf-8")) if os.path.exists(cfgf) else {}
        check("blessartadmin：POST /api/blessing-art 合法設定回 200，檔案內容與送出的相同", st == 200 and saved == ok_cfg and json.loads(body).get("config") == ok_cfg, f"HTTP {st} {body[:100]}")
        st, _, body = req2(base + "/api/blessing-art")
        check("blessartadmin：GET /api/blessing-art 回傳剛存的設定", st == 200 and json.loads(body).get("config") == ok_cfg)
        two = {"work": ent, "peace": dict(ent, alt="另一張", edition="")}
        st, _, _ = post("/api/blessing-art", two)
        check("blessartadmin：可以同時設定多個主題，edition 可以是空字串", st == 200 and json.load(open(cfgf, encoding="utf-8")) == two, f"HTTP {st}")
        before = md5(cfgf)
        bad = {"主題不存在": {"xyz": ent}, "圖片檔不存在": {"work": dict(ent, image="assets/nope.png")}, "圖片是 mp3": {"work": dict(ent, image="assets/home-music.mp3")},
               "圖片跳出 assets/": {"work": dict(ent, image="assets/../../data/luk.json")}, "圖片指向 data/": {"work": dict(ent, image="data/luk.json")},
               "圖片是絕對路徑": {"work": dict(ent, image="/etc/passwd")}, "圖片是網址": {"work": dict(ent, image="https://evil.example/a.png")},
               "alt 空白": {"work": dict(ent, alt="  ")}, "alt 超過 120 字": {"work": dict(ent, alt="字" * 121)}, "版次超過 20 字": {"work": dict(ent, edition="字" * 21)},
               "多出欄位": {"work": dict(ent, extra="x")}, "缺 edition": {"work": {"image": new, "alt": "測試"}}, "設定不是物件": {"work": "assets/jordan.jpg"},
               "整份是陣列": [ent], "版次不是字串": {"work": dict(ent, edition=202611)}}
        for label, obj in bad.items():
            st, _, _ = post("/api/blessing-art", obj)
            check(f"blessartadmin：POST /api/blessing-art 拒絕「{label}」回 400", st == 400, f"HTTP {st}")
        st, _, _ = post("/api/blessing-art", None, raw=b"not json")
        check("blessartadmin：POST /api/blessing-art 拒絕不是 JSON 的內容回 400", st == 400, f"HTTP {st}")
        st, _, _ = post("/api/blessing-art", None, raw=b"{" + b" " * 70000 + b"}")
        check("blessartadmin：POST /api/blessing-art 內容超過 64 KB 回 413", st == 413, f"HTTP {st}")
        check("blessartadmin：所有被拒絕的請求都沒有改動 blessing-art.json", md5(cfgf) == before)
        st, _, _ = post("/api/blessing-art/reset", {}, {"X-Bible-Token": ""})
        check("blessartadmin：POST /api/blessing-art/reset 沒帶 token 回 403", st == 403, f"HTTP {st}")
        st, _, body = post("/api/blessing-art/reset", {})
        check("blessartadmin：POST /api/blessing-art/reset 回 200，設定清空（全部主題回到純文字），上傳的圖還在",
              st == 200 and json.load(open(cfgf, encoding="utf-8")) == {} and os.path.exists(os.path.join(tmp, "site", new)), f"HTTP {st} {body[:100]}")
        st, _, _ = post("/api/blessing-art", {})
        check("blessartadmin：POST 空物件 {} 是合法的（清除全部）", st == 200, f"HTTP {st}")
        st, _, _ = req2(base + "/api/blessing-art", "DELETE", good)
        check("blessartadmin：沒有刪除端點：DELETE /api/blessing-art 不回 200", st != 200, f"HTTP {st}")
        st, _, _ = post("/api/blessing", {"cards": []})
        st2, _, _ = post("/api/blessing/cards", {"cards": []})
        check("blessartadmin：沒有任何寫 blessing.json 的端點（/api/blessing、/api/blessing/cards 都不是 200）", st != 200 and st2 != 200, f"HTTP {st}/{st2}")
        now = {n: md5(os.path.join(tmp, "data", n)) for n in guard}
        check("blessartadmin：所有操作後 blessing.json（37 張經文卡）、home.json、zone-music.json、四福音經文位元組完全沒變", now == guard, json.dumps([n for n in guard if now[n] != guard[n]]))
        leftovers = [f for d in (os.path.join(tmp, "data"), assets) for f in os.listdir(d) if f.endswith((".tmp", ".part")) or f.startswith(".")]
        check("blessartadmin：沒有留下暫存檔（原子寫入）", not leftovers, "、".join(leftovers))
        check("blessartadmin：測試沒有動到真正的 data/blessing-art.json", md5(live_cfg) == live_before)
    finally:
        proc.terminate()
        try:
            _, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, err = proc.communicate()
        shutil.rmtree(tmp, ignore_errors=True)
    check("blessartadmin：處理請求時後台沒有 Traceback", "Traceback" not in err, err.strip().splitlines()[-1] if "Traceback" in err else "")


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
    groups = set(args) or {"admin", "homeadmin", "zoneadmin", "blessartadmin", "service"}
    if "admin" in groups:
        admin()
    if "homeadmin" in groups:
        homeadmin()
    if "zoneadmin" in groups:
        zoneadmin()
    if "blessartadmin" in groups:
        blessartadmin()
    if "service" in groups:
        service()
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
