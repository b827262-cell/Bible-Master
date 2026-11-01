#!/usr/bin/env python3
"""Automatic site checks (exit code 0 only when all pass):
1. Links: every relative href/src in the HTML, and every *.html/.css/.js/.json path in the JS, points to an existing file.
2. External resources: no http(s):// or protocol-relative URL is loaded (xmlns namespace strings are allowed).
3. Rendering (headless Chrome): chapter.html?ch=1 and ?ch=16 show every verse of that chapter;
   search.html?q=耶穌 shows exactly as many "馬可福音 章:節" results as mark.json has verses containing 耶穌.
"""
import functools, http.server, json, os, re, socketserver, subprocess, sys, tempfile, threading, urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "site")
CHROME = next((c for c in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/snap/bin/chromium") if os.path.exists(c)), None)
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("通過" if ok else "不通過") + f"：{name}" + (f"（{detail}）" if detail else ""))


def site_files(*exts):
    for dp, _, fs in os.walk(SITE):
        for f in fs:
            if f.endswith(exts):
                yield os.path.join(dp, f)


def links():
    bad = []
    for p in site_files(".html", ".js"):
        src = open(p, encoding="utf-8", errors="ignore").read()
        refs = re.findall(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', src) if p.endswith(".html") else []
        refs += re.findall(r'["\'`]((?:\.\./|\./)?[\w./-]+\.(?:html|css|js|json))(?:[?#][^"\'`]*)?["\'`]', src)
        for r in refs:
            if re.match(r"^(#|mailto:|javascript:|data:|blob:|https?:|//)", r) or "${" in r:
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(p), urllib.parse.urlsplit(r).path))
            if not os.path.exists(target):
                bad.append(f"{os.path.basename(p)} → {r}")
    check("連結都指向存在的檔案", not bad, "；".join(sorted(set(bad))[:8]))


def external():
    bad = []
    for p in site_files(".html", ".js", ".css"):
        src = open(p, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r'(?:https?:)?//[\w.-]+\.[a-z]{2,}[^\s"\'`)]*', src):
            u = m.group(0)
            if "w3.org/" in u:  # SVG/XHTML namespace strings, not loaded
                continue
            line = src[:m.start()].count("\n") + 1
            before = src[max(0, m.start() - 3):m.start()]
            if u.startswith("//") and not before.endswith(("\"", "'", "(", "=", "`")):
                continue  # a // comment, not a URL
            bad.append(f"{os.path.basename(p)}:{line} {u[:60]}")
    check("沒有載入外部資源", not bad, "；".join(bad[:8]))


def dump(url):
    # A private profile per call: concurrent runs (several agents) must not share Chrome's default profile,
    # otherwise the second instance hands the URL to the first and prints an empty page.
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=8000",
                              f"--user-data-dir={profile}", "--dump-dom", url], capture_output=True, text=True, timeout=60).stdout
    return re.sub(r"<[^>]+>", "", out)


def rendering():
    if not CHROME:
        check("頁面實際顯示（headless Chrome）", False, "找不到 Chrome")
        return
    data = json.load(open(os.path.join(ROOT, "data", "mark.json"), encoding="utf-8"))["chapters"]
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}/site/"
        for ch in (1, 16):
            text = dump(f"{base}chapter.html?ch={ch}")
            verses = data[ch - 1]["verses"]
            missing = [v["v"] for v in verses if v["text"].strip("　 ")[:15] not in text]
            check(f"chapter.html?ch={ch} 顯示全部 {len(verses)} 節", not missing, f"缺少第 {missing[:10]} 節" if missing else "")
        q = "耶穌"
        want = sum(q in v["text"] for c in data for v in c["verses"])
        text = dump(f"{base}search.html?q={urllib.parse.quote(q)}")
        got = len(set(re.findall(r"馬可福音\s*(\d+)\s*[:：]\s*(\d+)", text)))
        check(f"search.html?q={q} 顯示 {want} 筆結果", got == want,
              "" if got == want else f"實際 {got} 筆；search.html 需支援 ?q= 參數，結果要顯示「馬可福音 章:節」")
        probe = dump(f"http://127.0.0.1:{srv.server_address[1]}/tests/anchor_probe.html")
        m = re.search(r"ANCHOR (OK|FAIL|不通過)\s*(.*)", probe)
        check("chapter.html?ch=1#v40 會捲動到第 40 節", bool(m) and m.group(1) == "OK",
              "" if m and m.group(1) == "OK" else (m.group(0) if m else "探測頁沒有輸出") + "；經文是 fetch 後才畫出來的，畫完要自己捲動到網址 # 指定的節")
        srv.shutdown()


if __name__ == "__main__":
    if not os.path.isdir(SITE) or not any(site_files(".html")):
        print("不通過：site/ 裡還沒有任何 HTML 檔案")
        sys.exit(1)
    links()
    external()
    rendering()
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
