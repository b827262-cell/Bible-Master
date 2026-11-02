#!/usr/bin/env python3
"""Automatic site checks (exit code 0 only when all pass):
1. Links: every relative href/src in the HTML, and every *.html/.css/.js/.json path in the JS, points to an existing file.
2. External resources: no http(s):// or protocol-relative URL is loaded (xmlns namespace strings are allowed).
3. Rendering (headless Chrome): chapter.html?ch=1 and ?ch=16 show every verse of that chapter;
   search.html?q=耶穌 shows exactly as many "馬可福音 章:節" results as mark.json has verses containing 耶穌.
"""
import functools, html, http.server, json, os, re, socketserver, subprocess, sys, tempfile, threading, urllib.parse

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


def single_book_text():
    """No page may hard-code one book's name in static markup (footer, text): the pages serve four books."""
    bad = []
    for p in site_files(".html"):
        src = open(p, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r"<footer>(.*?)</footer>", src, re.S):
            if re.search(r"馬太福音|馬可福音|路加福音|約翰福音", m.group(1)):
                bad.append(f"{os.path.basename(p)} 頁尾「{m.group(1).strip()}」")
    check("頁尾沒有寫死單一書卷名稱", not bad, "；".join(bad))


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


def page_state(port, url, act=None):
    """Open a page in tests/page_probe.html (iframe) and return its state as a dict."""
    q = "u=" + urllib.parse.quote("../site/" + url, safe="") + ("&act=" + urllib.parse.quote(json.dumps(act)) if act else "")
    out = dump(f"http://127.0.0.1:{port}/tests/page_probe.html?{q}")
    found = re.findall(r"PROBE (\{[^\n]*\})\s*$", out, re.M)      # the last one: the page's own comment shows an example
    try:
        return json.loads(html.unescape(found[-1])) if found else {}
    except ValueError:
        return {}


BOOKS = [("mat", "馬太福音"), ("mrk", "馬可福音"), ("luk", "路加福音"), ("jhn", "約翰福音")]


def rendering(groups):
    if not CHROME:
        check("頁面實際顯示（headless Chrome）", False, "找不到 Chrome")
        return
    data = {k: json.load(open(os.path.join(ROOT, "data", k + ".json"), encoding="utf-8"))["chapters"] for k, _ in BOOKS}
    names = dict(BOOKS)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}/site/"
        # every book: first and last chapter show every verse (and the default book is Matthew)
        for key, name in BOOKS if "chapter" in groups else ():
            for ch in (1, len(data[key])):
                text = dump(f"{base}chapter.html?book={key}&ch={ch}")
                verses = data[key][ch - 1]["verses"]
                missing = [v["v"] for v in verses if v["text"].strip("　 ")[:15] not in text]
                check(f"chapter.html?book={key}&ch={ch} 顯示 {name} 第 {ch} 章全部 {len(verses)} 節", not missing,
                      f"缺少第 {missing[:10]} 節" if missing else "")
        text = dump(f"{base}chapter.html?ch=1") if "chapter" in groups else ""
        first = data["mat"][0]["verses"][0]["text"].strip("　 ")[:15]
        if "chapter" in groups:
            check("chapter.html?ch=1（沒帶 book）預設顯示馬太福音第 1 章", first in text and "馬太福音" in text)
        # merged verses in the source are shown with a range label
        if "chapter" in groups:
            text = dump(f"{base}chapter.html?book=luk&ch=1")
            check("路加福音 1:1–2 合併節以「1-2」顯示", re.search(r"1\s*[-–]\s*2", text) is not None)
        # search: one book, then all four books
        q = "耶穌"
        for key, name in BOOKS if "search" in groups else ():
            want = sum(q in v["text"] for c in data[key] for v in c["verses"])
            text = dump(f"{base}search.html?q={urllib.parse.quote(q)}&book={key}")
            got = len(set(re.findall(name + r"\s*(\d+)\s*[:：]\s*(\d+)", text)))
            check(f"search.html?q={q}&book={key} 顯示 {want} 筆結果", got == want,
                  "" if got == want else f"實際 {got} 筆；結果要顯示「{name} 章:節」")
        want = sum(q in v["text"] for k in data for c in data[k] for v in c["verses"])
        text = dump(f"{base}search.html?q={urllib.parse.quote(q)}") if "search" in groups else ""
        got = sum(len(set(re.findall(n + r"\s*(\d+)\s*[:：]\s*(\d+)", text))) for _, n in BOOKS)
        if "search" in groups:
            check(f"search.html?q={q}（預設搜全部四卷）顯示 {want} 筆結果", got == want,
                  "" if got == want else f"實際 {got} 筆；沒帶 book 時要搜尋四卷並顯示各卷書名")
        # deep links: the page must scroll to the verse itself (verses are drawn after a fetch)
        for target, vid in (("book=mrk&ch=1", "v40"), ("book=luk&ch=1", "v2"), ("book=jhn&ch=21", "v25")) if "chapter" in groups else ():
            probe = dump(f"http://127.0.0.1:{port}/tests/anchor_probe.html?u=" + urllib.parse.quote(f"../site/chapter.html?{target}#{vid}") + f"&id={vid}")
            m = re.search(r"ANCHOR (OK|FAIL|不通過)\s*(.*)", probe)
            good = bool(m) and m.group(1) == "OK"
            check(f"chapter.html?{target}#{vid} 會捲動到該節", good,
                  "" if good else (m.group(0) if m else "探測頁沒有輸出") + "；經文是 fetch 後才畫出來的，畫完要自己捲動到網址 # 指定的節")
        if "index" in groups:
            for key, name in BOOKS + [("zzz", "不合法的 book"), ("", "沒帶 book")]:
                want = key if key in names else "mat"
                st = page_state(port, "index.html" + (f"?book={key}" if key else ""))
                n = len(data[want])
                last = f"第 {n} 章・{len(data[want][-1]['verses'])} 節"
                sel = st.get("selects", {}).get("search-book", {})
                good = (st.get("cards") == n and st.get("last", "").replace(" ", "") == last.replace(" ", "")
                        and st.get("tabs", "").count("*") == 1 and f"{names[want]}*" in st.get("tabs", "")
                        and sel.get("options") == 5 and sel.get("value") == want)
                check(f"index.html?book={key or '（無）'} 顯示 {names[want]} 的 {n} 章、書卷標籤、搜尋下拉預設{names[want]}", good,
                      "" if good else f"實際 {json.dumps(st, ensure_ascii=False)[:300]}")
        if "card" in groups:
            def card_ok(st, key, ch, v, label):
                sel = st.get("selects", {})
                chap = len(data[key])
                nv = len(data[key][ch - 1]["verses"])
                want_ref = f"{names[key]} {ch}:{label}（和合本）"
                return (sel.get("book-select", {}).get("value") == key and sel.get("ch-select", {}).get("value") == str(ch)
                        and sel.get("ch-select", {}).get("options") == chap and sel.get("v-select", {}).get("value") == str(v)
                        and sel.get("v-select", {}).get("options") == nv and st.get("ref") == want_ref)
            cases = [("card.html", "mat", 1, 1, "1"), ("card.html?book=luk&ch=1&v=1", "luk", 1, 1, "1-2"),
                     ("card.html?book=jhn&ch=21&v=25", "jhn", 21, 25, "25"), ("card.html?book=mrk&ch=3&v=5", "mrk", 3, 5, "5"),
                     ("card.html?book=zzz&ch=99&v=99", "mat", 1, 1, "1")]
            for url, key, ch, v, label in cases:
                st = page_state(port, url)
                check(f"{url} 的三個下拉與卡片出處都是 {names[key]} {ch}:{v}", card_ok(st, key, ch, v, label),
                      "" if card_ok(st, key, ch, v, label) else f"實際 {json.dumps(st, ensure_ascii=False)[:300]}")
            st = page_state(port, "card.html?book=mat&ch=5&v=3", [{"id": "book-select", "value": "mrk"}, {"id": "ch-select", "value": "3"}, {"id": "v-select", "value": "5"}])
            check("card.html 依序換書卷→章→節（馬可福音 3:5）後三個下拉與出處同步", card_ok(st, "mrk", 3, 5, "5"),
                  "" if card_ok(st, "mrk", 3, 5, "5") else f"實際 {json.dumps(st, ensure_ascii=False)[:300]}")
        srv.shutdown()


if __name__ == "__main__":
    if not os.path.isdir(SITE) or not any(site_files(".html")):
        print("不通過：site/ 裡還沒有任何 HTML 檔案")
        sys.exit(1)
    # optional page filter: `site_checks.py chapter|search|index|card` runs links, external and only that page's rendering checks
    groups = set(sys.argv[1:]) or {"chapter", "search", "index", "card"}
    links()
    external()
    single_book_text()
    rendering(groups)
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
