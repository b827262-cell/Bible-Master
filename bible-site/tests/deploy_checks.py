#!/usr/bin/env python3
"""Checks for the public bundle built by tools/build_public.py (exit code 0 only when all pass).
Builds into a temp dir, never into the real dist/. Groups: bundle (content + references), publish (tools/publish.py contract).
Usage: python3 bible-site/tests/deploy_checks.py [bundle] [publish] [--grep REGEX]"""
import functools, http.server, json, os, re, shutil, socketserver, subprocess, sys, tempfile, threading, urllib.request

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(SITE_ROOT, ".."))
BUILD = os.path.join(SITE_ROOT, "tools", "build_public.py")
PUBLISH = os.path.join(SITE_ROOT, "tools", "publish.py")
results = []
ONLY = None


def check(name, ok, detail=""):
    if ONLY and not re.search(ONLY, name):
        return
    results.append(ok)
    print(("通過" if ok else "不通過") + f"：{name}" + (f"（{detail}）" if detail else ""))


def listing(root):
    return sorted(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/") for dp, _, fs in os.walk(root) for f in fs)


def bundle():
    if not os.path.exists(BUILD):
        check("tools/build_public.py 存在", False, "找不到檔案")
        return
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "dist")
    try:
        p = subprocess.run([sys.executable, BUILD, "--out", out], capture_output=True, text=True, timeout=120)
        check("build_public.py 結束碼 0", p.returncode == 0, (p.stdout + p.stderr).strip()[-200:])
        files = listing(out) if os.path.isdir(out) else []
        check("dist 有 index.html、site/home.html、site/index.html、data/ 四卷經文、_headers", all(f in files for f in (
            "index.html", "site/home.html", "site/index.html", "site/app.js", "site/style.css", "data/mat.json", "data/mrk.json", "data/luk.json", "data/jhn.json", "_headers")))
        check("dist 有 data/blessing.json 與 data/home.json", "data/blessing.json" in files and "data/home.json" in files)
        check("dist 有 data/zone-music.json 與 site/music.js（前台四區音樂）", "data/zone-music.json" in files and "site/music.js" in files)
        check("dist 有 data/blessing-art.json（抽經文卡主題收藏卡圖）", "data/blessing-art.json" in files)
        bad = [f for f in files if re.match(r"(admin|tests|tools|tasks|prompts|logs|\.verify|\.git)/", f) or f.endswith((".md", ".py", ".sh", ".pid", ".log")) or os.path.basename(f).startswith(".") or "token" in f.lower()]
        check("dist 不含 admin／tests／tools／報告／腳本／token／隱藏檔", not bad, "、".join(bad[:6]))
        check("dist 只含 index.html、404.html、_headers、site/、data/ 五種頂層項目", {f.split("/")[0] for f in files} <= {"index.html", "404.html", "_headers", "site", "data"})
        nf = open(os.path.join(out, "404.html"), encoding="utf-8").read() if "404.html" in files else ""
        check("dist 有繁體中文的 404.html：說明找不到頁面、連回 /site/home.html、noindex、不載入外部資源、不是首頁轉址頁",
              "找不到" in nf and 'href="/site/home.html"' in nf and "noindex" in nf and "http-equiv" not in nf and not re.search(r"https?://|<script", nf))
        big = [f for f in files if os.path.getsize(os.path.join(out, f)) > 25 * 1024 * 1024]
        check("dist 單檔都小於 25 MiB、檔案數小於 20000", not big and len(files) < 20000, "、".join(big))
        modes = [f for f in files if (os.stat(os.path.join(out, f)).st_mode & 0o777) != 0o644]
        check("dist 的檔案權限統一為 644", not modes, "、".join(modes[:5]))
        hdr = open(os.path.join(out, "_headers"), encoding="utf-8").read() if "_headers" in files else ""
        check("_headers 有 nosniff、Referrer-Policy、X-Frame-Options，且 /site/assets/* 有一條 Cache-Control",
              all(k in hdr for k in ("X-Content-Type-Options: nosniff", "Referrer-Policy", "X-Frame-Options", "/site/assets/*")))
        rules, cur = [], None
        for line in hdr.splitlines():
            if line and not line[0].isspace():
                cur = [line.strip(), []]
                rules.append(cur)
            elif line.strip() and cur:
                cur[1].append(line.strip())
        cache_rules = [(pat, [h for h in hs if h.lower().startswith("cache-control")]) for pat, hs in rules]
        cache_rules = [(pat, hs) for pat, hs in cache_rules if hs]
        rx = lambda pat: re.compile("^" + re.escape(pat).replace(r"\*", ".*") + "$")
        multi = []
        for f in files + ["site/home", "404.html"]:
            path = "/" + f
            hit = [pat for pat, _ in cache_rules if rx(pat).match(path)]
            vals = [h for pat, hs in cache_rules if rx(pat).match(path) for h in hs]
            if len(hit) > 1 or len(vals) > 1:
                multi.append(f"{path}→{len(hit)} 條")
        check("_headers 任何網址最多只符合一條 Cache-Control 規則（Cloudflare 會把多條的值串在一起）", not multi and len(cache_rules) == 1, "、".join(multi[:4]) or f"共 {len(cache_rules)} 條")
        check("_headers 唯一的 Cache-Control 是 /site/assets/* 的 public, max-age=86400", cache_rules == [("/site/assets/*", ["Cache-Control: public, max-age=86400"])], str(cache_rules))
        # data files identical to the source (the bundle never rewrites scripture)
        same = all(open(os.path.join(out, "data", f), "rb").read() == open(os.path.join(SITE_ROOT, "data", f), "rb").read() for f in ("mat.json", "mrk.json", "luk.json", "jhn.json"))
        check("dist 的四卷經文與 bible-site/data 逐位元組相同", same)
        # assets: the ones home.json names (and the defaults) ship; an unreferenced upload does not
        cfg = json.load(open(os.path.join(out, "data", "home.json"), encoding="utf-8")) if "data/home.json" in files else {}
        check("home.json 指定的圖片與音樂、預設素材都在 dist/site/assets", all(os.path.isfile(os.path.join(out, "site", p)) for p in (cfg.get("image", "x"), cfg.get("music", "x"), "assets/jordan.jpg", "assets/home-music.mp3")))
        zcfg = json.load(open(os.path.join(out, "data", "zone-music.json"), encoding="utf-8")) if "data/zone-music.json" in files else {}
        check("zone-music.json 指定的音樂在 dist/site/assets", os.path.isfile(os.path.join(out, "site", zcfg.get("music", "x"))), str(zcfg))
        # unreferenced upload is skipped; a referenced one ships (built from a temp copy, never from the live files)
        copy = os.path.join(tmp, "copy")
        shutil.copytree(os.path.join(SITE_ROOT, "site"), os.path.join(copy, "site"))
        shutil.copytree(os.path.join(SITE_ROOT, "data"), os.path.join(copy, "data"))
        shutil.copy(os.path.join(SITE_ROOT, "index.html"), copy)
        for n in ("stray", "used"):
            open(os.path.join(copy, "site", "assets", f"upload-{n}.png"), "wb").write(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
        c = json.load(open(os.path.join(copy, "data", "home.json"), encoding="utf-8")) if os.path.exists(os.path.join(copy, "data", "home.json")) else {}
        c["image"] = "assets/upload-used.png"
        json.dump(c, open(os.path.join(copy, "data", "home.json"), "w", encoding="utf-8"), ensure_ascii=False)
        for n in ("zone-stray", "zone-used"):
            open(os.path.join(copy, "site", "assets", f"upload-{n}.mp3"), "wb").write(b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" + b"\0" * 64)
        json.dump({"music": "assets/upload-zone-used.mp3"}, open(os.path.join(copy, "data", "zone-music.json"), "w", encoding="utf-8"))
        for n in ("art-stray", "art-used"):
            open(os.path.join(copy, "site", "assets", f"upload-{n}.png"), "wb").write(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
        json.dump({"work": {"image": "assets/upload-art-used.png", "alt": "測試", "edition": "2026 年 11 月版"}}, open(os.path.join(copy, "data", "blessing-art.json"), "w", encoding="utf-8"), ensure_ascii=False)
        out2 = os.path.join(tmp, "dist2")
        subprocess.run([sys.executable, BUILD, "--out", out2, "--root", copy], capture_output=True, timeout=120)
        f2 = listing(out2) if os.path.isdir(out2) else []
        check("沒被使用的上傳檔不會發佈，home.json 指定的上傳檔會發佈", "site/assets/upload-stray.png" not in f2 and "site/assets/upload-used.png" in f2)
        check("沒被使用的收藏卡圖不會發佈，blessing-art.json 指定的圖會發佈", "site/assets/upload-art-stray.png" not in f2 and "site/assets/upload-art-used.png" in f2)
        check("沒被使用的上傳音樂不會發佈，zone-music.json 指定的上傳音樂會發佈", "site/assets/upload-zone-stray.mp3" not in f2 and "site/assets/upload-zone-used.mp3" in f2)
        # serve dist and fetch the pages the way a browser would (relative ../data paths must work)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=out)
        http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            codes = {}
            for path in ("/", "/index.html", "/site/home.html", "/site/index.html", "/site/chapter.html", "/site/search.html", "/site/blessing.html", "/site/card.html",
                         "/data/luk.json", "/data/home.json", "/data/zone-music.json", "/data/blessing-art.json", "/site/music.js", "/data/blessing.json", "/site/assets/jordan.jpg", "/site/assets/home-music.mp3", "/admin/index.html", "/tests/site_checks.py", "/FAILS.md"):
                try:
                    r = urllib.request.urlopen(base + path, timeout=10)
                    r.read()
                    codes[path] = r.status
                except urllib.error.HTTPError as e:
                    codes[path] = e.code
            ok = all(codes[p] == 200 for p in list(codes)[:-3]) and all(codes[p] == 404 for p in list(codes)[-3:])
            check("dist 以靜態伺服器開啟：各頁、資料、素材都 200；/admin／tests／報告 404", ok, json.dumps(codes))
            refs = []
            for dp, _, fs in os.walk(os.path.join(out, "site")):
                for f in fs:
                    if f.endswith(".html"):
                        for m in re.findall(r'(?:href|src)="([^"#?:]+)', open(os.path.join(dp, f), encoding="utf-8").read()):
                            if not m.startswith(("/", "http", "mailto", "data")) and not os.path.exists(os.path.normpath(os.path.join(dp, m))):
                                refs.append(f"{f}→{m}")
            check("dist 內每個頁面的相對連結與資源都存在", not refs, "、".join(refs[:5]))
            srv.shutdown()
        # real dist/ must stay out of git
        gi = open(os.path.join(REPO, ".gitignore"), encoding="utf-8").read()
        check(".gitignore 排除 dist/", re.search(r"^/?dist/?$", gi, re.M) is not None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def publish():
    if not os.path.exists(PUBLISH):
        check("tools/publish.py 存在", False, "找不到檔案")
        return
    src = open(PUBLISH, encoding="utf-8").read()
    p = subprocess.run([sys.executable, "-m", "py_compile", PUBLISH], capture_output=True, text=True)
    check("publish.py 語法正確", p.returncode == 0, p.stderr.strip()[-120:])
    check("publish.py 先跑 check_all.py、build_public.py、deploy_checks.py 才碰 git", all(k in src for k in ("check_all.py", "build_public.py", "deploy_checks.py")))
    check("publish.py 預設推到 preview 分支，--prod 才推 main", "preview" in src and "--prod" in src and "main" in src)
    check("publish.py 提交前顯示檔案清單並要求輸入 yes（--yes 可略過）", "--yes" in src and "yes" in src and "diff" in src)
    check("publish.py 不使用 git add -A／git add .、不使用 --force", not re.search(r"add['\", ]+(-A|\.)['\"\]]", src) and "--force" not in src and "-f'" not in src)
    check("publish.py 有 --dry-run（只跑檢查與建置，不做任何 git 寫入）", "--dry-run" in src)
    check("publish.py 沒有 remote 時給出設定說明而不是當掉", "remote" in src and "git remote add" in src)
    p = subprocess.run([sys.executable, PUBLISH, "--help"], capture_output=True, text=True, timeout=30)
    check("publish.py --help 結束碼 0，說明是繁體中文", p.returncode == 0 and re.search(r"[一-鿿]", p.stdout) is not None)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--grep" in args:
        i = args.index("--grep")
        ONLY = args[i + 1]
        del args[i:i + 2]
    groups = set(args) or {"bundle", "publish"}
    if "bundle" in groups:
        bundle()
    if "publish" in groups:
        publish()
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
