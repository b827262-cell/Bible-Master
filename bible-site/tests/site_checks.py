#!/usr/bin/env python3
"""Automatic site checks (exit code 0 only when all pass):
1. Links: every relative href/src in the HTML, and every *.html/.css/.js/.json path in the JS, points to an existing file.
2. External resources: no http(s):// or protocol-relative URL is loaded (xmlns namespace strings are allowed).
3. Rendering (headless Chrome): chapter.html?ch=1 and ?ch=16 show every verse of that chapter;
   search.html?q=耶穌 shows exactly as many "馬可福音 章:節" results as mark.json has verses containing 耶穌.
4. blessing (data/blessing.json + site/blessing.html): see blessing_data() and blessing_render().
5. home (site/home.html, assets, root redirect): see home_static() and home_render().
"""
import functools, html, http.server, json, os, re, socketserver, subprocess, sys, tempfile, threading, urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "site")
CHROME = next((c for c in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/snap/bin/chromium") if os.path.exists(c)), None)
results = []
ONLY = None  # --grep REGEX: only checks whose name matches count (one task's share)


def check(name, ok, detail=""):
    if ONLY and not re.search(ONLY, name):
        return
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
SIMPLIFIED = "们这个为与发开关没还会过对门问说书经时间点见觉东车长头实现国学应该从来让给总样种两边头"  # Simplified-only characters
CJK = re.compile(r"[一-鿿]")


def cjk(s):
    return "".join(CJK.findall(s))


def blessing_data():
    """data/blessing.json: only references and original messages; every card points at a real verse; the page hard-codes no scripture."""
    path = os.path.join(ROOT, "data", "blessing.json")
    if not os.path.exists(path):
        check("data/blessing.json 存在", False, "找不到檔案")
        return
    raw = open(path, encoding="utf-8").read()
    b = json.loads(raw)
    themes, cards = b.get("themes", []), b.get("cards", [])
    verses = {}
    for k, _ in BOOKS:
        for c in json.load(open(os.path.join(ROOT, "data", k + ".json"), encoding="utf-8"))["chapters"]:
            for v in c["verses"]:
                verses[(k, c["ch"], v["v"])] = v["text"]
    ids = [c.get("id") for c in cards]
    tids = {t.get("id") for t in themes}
    check("blessing.json 的卡片 id 不重複，且每張卡都有 theme、book、ch、v、message",
          len(set(ids)) == len(ids) and all(c.get("theme") and c.get("book") and c.get("ch") and c.get("v") and c.get("message") for c in cards))
    check("blessing.json 每張卡的 theme 都有定義", all(c.get("theme") in tids for c in cards),
          "、".join(sorted({c.get("theme") for c in cards} - tids)))
    missing = [c["id"] for c in cards if (c.get("book"), c.get("ch"), c.get("v")) not in verses]
    check("blessing.json 每張卡的書卷／章／節在 data/*.json 都存在", not missing, "、".join(missing[:8]))
    defaults = [t["id"] for t in themes if t.get("default")]
    check("blessing.json 恰有一個預設主題，而且是 work", defaults == ["work"], str(defaults))
    check("blessing.json 的 work 主題至少 15 張卡", sum(c.get("theme") == "work" for c in cards) >= 15)
    check("blessing.json 其他每個主題至少 3 張卡", all(sum(c.get("theme") == t for c in cards) >= 3 for t in tids - {"work"}))
    check("blessing.json 每張祝福短文 30–120 字、署名不寫在短文裡", all(30 <= len(c.get("message", "")) <= 120 and "愛你的天父" not in c.get("message", "") for c in cards),
          "、".join(c["id"] for c in cards if not 30 <= len(c.get("message", "")) <= 120 or "愛你的天父" in c.get("message", ""))[:80])
    check("blessing.json 沒有簡體字", not [ch for ch in SIMPLIFIED if ch in raw], "".join(ch for ch in SIMPLIFIED if ch in raw))
    # no scripture text outside data/<book>.json: no 8-character run of a verse may appear in blessing.json or blessing.html
    grams = set()
    for t in verses.values():
        s = cjk(t)
        grams.update(s[i:i + 8] for i in range(len(s) - 7))
    page = os.path.join(SITE, "blessing.html")
    for name, src in (("blessing.json 的祝福短文", " ".join(c.get("message", "") for c in cards)),
                      ("blessing.html", open(page, encoding="utf-8").read() if os.path.exists(page) else "")):
        s = cjk(src)
        hit = sorted({s[i:i + 8] for i in range(len(s) - 7) if s[i:i + 8] in grams})
        check(f"{name} 沒有寫死經文（沒有任何連續 8 字與和合本經文相同）", not hit, "；".join(hit[:3]))


def blessing_state(port, url, act=None, width=None):
    q = "u=" + urllib.parse.quote("../site/" + url, safe="") + ("&act=" + urllib.parse.quote(json.dumps(act)) if act else "") + (f"&w={width}" if width else "")
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=20000",
                              f"--user-data-dir={profile}", "--dump-dom", f"http://127.0.0.1:{port}/tests/blessing_probe.html?{q}"],
                             capture_output=True, text=True, timeout=90).stdout
    out = re.sub(r"<[^>]+>", "", out)
    found = re.findall(r"PROBE (\{[^\n]*\})\s*$", out, re.M)
    try:
        return json.loads(html.unescape(found[-1])) if found else {}
    except ValueError:
        return {}


PALETTE = {  # BLESSING-STYLE-REVIEW-PM.md (B): light, dark
    "--bg": ("#f7f5ef", "#161513"), "--surface": ("#ffffff", "#22201c"), "--card-bg": ("#fffcf5", "#28251f"),
    "--fg": ("#2c2b28", "#ede9df"), "--muted": ("#635f56", "#aba69b"), "--border": ("#ded8cc", "#3d3932"),
    "--accent": ("#7a4a1f", "#deb068"), "--accent-fg": ("#ffffff", "#171614"), "--accent-soft": ("#f3ead8", "#352c1e")}


def blessing_style(port, card_ok):
    css = open(os.path.join(SITE, "style.css"), encoding="utf-8").read()
    light = re.search(r"^:root\s*\{(.*?)\}", css, re.S | re.M)
    dark = re.search(r"prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{(.*?)\}", css, re.S)
    for i, (scheme, block) in enumerate((("淺色", light), ("深色", dark))):
        got = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", block.group(1))) if block else {}
        bad = [f"{k} {got.get(k)}≠{v[i]}" for k, v in PALETTE.items() if (got.get(k) or "").lower() != v[i]]
        check(f"style.css {scheme}配色變數等於審查定案的配色表（含 --card-bg、--accent-soft）", not bad, "；".join(bad))
    st = blessing_state(port, "blessing.html?card=work-01")
    s = st.get("style") or {}
    ok, why = card_ok(st.get("card"), st.get("canvasRef"), "work-01")
    px = st.get("canvasPixels") or {}
    check("blessing.html 的 canvas 圖卡不顯示在頁面上，但仍在背景畫好（≥600px、data-ref 正確、底色 #fbf7ee、真的畫了字）供下載",
          ok and s.get("canvasShown") is False and st.get("canvasW", 0) >= 600 and px.get("corner") == [251, 247, 238] and px.get("dark", 0) > 500,
          why or json.dumps({"canvasShown": s.get("canvasShown"), "pixels": px}, ensure_ascii=False))
    active = [t["id"] for t in s.get("tabs", []) if t["active"]]
    want = sorted(["again-btn"] + ["theme:" + a for a in active])
    check("blessing.html 實心 accent 按鈕只有兩顆：選中的主題與「再抽一次」", sorted(s.get("solid", [])) == want and len(want) == 2,
          f"實心：{s.get('solid')}")
    tabs = s.get("tabs", [])
    for w in (320, 375, 1000):
        tw = (blessing_state(port, "blessing.html?card=work-01", width=w).get("style") or {}).get("tabs", []) if w != 1000 else tabs
        grid = (len(tw) == 4 and max(t["w"] for t in tw) - min(t["w"] for t in tw) <= 1 and tw[0]["y"] == tw[1]["y"] and tw[2]["y"] == tw[3]["y"]
                and tw[0]["y"] < tw[2]["y"] and tw[0]["x"] == tw[2]["x"] and len({t["h"] for t in tw}) == 1 and not any(t["clipped"] for t in tw))
        check(f"{w}px blessing.html 四顆主題按鈕排成 2×2、等寬等高、文字沒有被裁切", grid,
              json.dumps([{k: t[k] for k in ("id", "x", "y", "w", "h", "clipped")} for t in tw]))
    on = [t for t in tabs if t["active"]]
    off = [t for t in tabs if not t["active"]]
    good = (len(on) == 1 and "✦" in on[0]["before"] and "underline" not in on[0]["deco"]
            and off and all(t["bg"] != s.get("accent") and t["border"] >= 1 and "✦" not in t["before"] for t in off))
    check("blessing.html 選中的主題前有「✦」、沒有底線；未選中的不是實心、有邊框", good, json.dumps(tabs, ensure_ascii=False)[:300])
    sec = s.get("secondary", [])
    check("blessing.html「下載圖片」「分享」是次要樣式（surface 底色＋邊框）",
          len(sec) == 2 and all(b.get("bg") == s.get("surface") and b.get("border", 0) >= 1 for b in sec), json.dumps(sec))
    v = s.get("verse") or {}
    check("blessing.html 經文用明體（serif），左側有 ≥3px accent 豎線",
          "serif" in v.get("font", "") and "sans-serif" not in v.get("font", "") and v.get("left", 0) >= 3 and v.get("leftColor") == s.get("accent"),
          json.dumps(v, ensure_ascii=False))
    check("blessing.html 署名前有「——」（用 CSS 加，署名文字仍是「愛你的天父」）", "——" in (s.get("signBefore") or ""), str(s.get("signBefore")))
    rl = s.get("readLink") or {}
    check("blessing.html「閱讀本章 →」連結在卡片內、與出處同一列、在動作按鈕之前",
          rl.get("inCard") and rl.get("sameRow") and rl.get("beforeActions") and "閱讀本章" in rl.get("text", ""), json.dumps(rl, ensure_ascii=False))


def blessing_render(port, groups):
    b = json.load(open(os.path.join(ROOT, "data", "blessing.json"), encoding="utf-8"))
    names = dict(BOOKS)
    by_id = {c["id"]: c for c in b["cards"]}
    titles = {t["id"]: t["title"] for t in b["themes"]}
    verse = {}
    for k, _ in BOOKS:
        for c in json.load(open(os.path.join(ROOT, "data", k + ".json"), encoding="utf-8"))["chapters"]:
            for v in c["verses"]:
                verse[(k, c["ch"], v["v"])] = v["text"]

    def norm(s):
        return re.sub(r"\s+", "", s.replace("　", ""))

    def card_ok(card, canvas_ref, cid=None):
        if not card or card.get("id") not in by_id:
            return False, f"沒有卡片或 id 不在 blessing.json：{card}"
        c = by_id[card["id"]]
        want_ref = f"{names[c['book']]} {c['ch']}:{c['v']}（和合本）"
        bad = []
        if cid and card["id"] != cid:
            bad.append(f"id={card['id']}")
        if card.get("theme") != c["theme"]:
            bad.append("theme")
        if not card.get("shown"):
            bad.append("卡片沒有顯示")
        if card.get("title") != titles[c["theme"]]:
            bad.append("標題")
        if norm(card.get("verse", "")) != norm(verse[(c["book"], c["ch"], c["v"])]):
            bad.append("經文與 data/*.json 不同")
        if card.get("ref") != want_ref:
            bad.append(f"出處 {card.get('ref')}≠{want_ref}")
        if canvas_ref != want_ref:
            bad.append(f"canvas data-ref {canvas_ref}≠{want_ref}")
        if card.get("message") != c["message"]:
            bad.append("祝福短文")
        if card.get("sign") != "愛你的天父":
            bad.append("署名")
        return not bad, "、".join(bad)

    base = f"http://127.0.0.1:{port}/site/"
    if "blessnav" in groups:
        for page in ("index.html", "chapter.html?ch=1", "search.html", "card.html"):
            check(f"{page.split('?')[0]} 的導覽列有「抽經文卡」連結（指向 blessing.html）", "抽經文卡" in dump(base + page) and "blessing.html" in open(os.path.join(SITE, "app.js"), encoding="utf-8").read())
    if "blessindex" in groups:
        idx = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
        check("index.html 的 <main> 內有指向 blessing.html 的入口連結", re.search(r"<main[^>]*>.*?<a[^>]+href=\"blessing\.html\"[^>]*>[^<]*抽[^<]*</a>.*?</main>", idx, re.S) is not None)
    if "blessstyle" in groups:
        blessing_style(port, card_ok)
    if "blessing" not in groups:
        return
    st = blessing_state(port, "blessing.html")
    good = (st.get("cover") is True and "點選領受祝福" in st.get("drawBtn", "") and not st.get("card")
            and [t["id"] for t in st.get("themes", []) if t["active"]] == ["work"]
            and [t["id"] for t in st.get("themes", [])] == [t["id"] for t in b["themes"]])
    check("blessing.html 一開始顯示封面與「點選領受祝福」按鈕、尚未出現卡片、預設主題是 work、主題標籤與 blessing.json 一致", good,
          "" if good else json.dumps(st, ensure_ascii=False)[:300])
    check("blessing.html 載入時沒有 JavaScript 錯誤", not st.get("errors"), "；".join(st.get("errors", [])[:3]))
    st = blessing_state(port, "blessing.html", [{"click": "#draw-btn"}])
    ok, why = card_ok(st.get("card"), st.get("canvasRef"))
    check("blessing.html 按「點選領受祝福」後出現 work 主題的卡：標題、經文原文、出處、短文、署名「愛你的天父」都對",
          ok and (st.get("card") or {}).get("theme") == "work" and not st.get("errors"), why or "；".join(st.get("errors", [])[:3]))
    st = blessing_state(port, "blessing.html?card=work-01")
    ok, why = card_ok(st.get("card"), st.get("canvasRef"), "work-01")
    check("blessing.html?card=work-01 不用按鍵就直接顯示 work-01 那張卡", ok and not st.get("cover"), why or "封面還在")
    st = blessing_state(port, "blessing.html?theme=peace", [{"click": "#draw-btn"}])
    ok, why = card_ok(st.get("card"), st.get("canvasRef"))
    check("blessing.html?theme=peace 抽到的是 peace 主題的卡", ok and (st.get("card") or {}).get("theme") == "peace" and
          [t["id"] for t in st.get("themes", []) if t["active"]] == ["peace"], why)
    st = blessing_state(port, "blessing.html", [{"click": "#theme-tabs button[data-theme=rest]"}, {"click": "#draw-btn"}])
    ok, why = card_ok(st.get("card"), st.get("canvasRef"))
    check("blessing.html 先點主題標籤「rest」再抽，抽到 rest 主題的卡", ok and (st.get("card") or {}).get("theme") == "rest", why)
    st = blessing_state(port, "blessing.html", [{"click": "#theme-tabs button[data-theme=peace]"}])
    check("blessing.html 還在封面時點主題標籤，只切換主題（peace 變成目前主題）、不抽卡、封面仍在",
          not st.get("card") and st.get("cover") is True and [t["id"] for t in st.get("themes", []) if t["active"]] == ["peace"],
          json.dumps({k: st.get(k) for k in ("cover", "card", "themes")}, ensure_ascii=False)[:200])
    st = blessing_state(port, "blessing.html", [{"click": "#draw-btn"}, {"click": "#theme-tabs button[data-theme=peace]"}])
    card = st.get("card") or {}
    check("blessing.html 已抽出卡片後點主題標籤「peace」，立刻換成 peace 主題的新卡", card.get("theme") == "peace" and str(card.get("id", "")).startswith("peace-")
          and card.get("draws") == "2" and not st.get("errors"), json.dumps(card, ensure_ascii=False)[:200])
    st = blessing_state(port, "blessing.html", [{"click": "#draw-btn"}] + [{"click": "#again-btn"}] * 6)
    ids = st.get("ids", [])
    check("blessing.html「再抽一次」連按 6 次，每次都是同主題而且不會連續抽到同一張", len(ids) == 7 and all(i in by_id and by_id[i]["theme"] == "work" for i in ids)
          and all(a != b_ for a, b_ in zip(ids, ids[1:])), json.dumps(ids))


HOME_DEFAULT = {"book": "luk", "ch": 4, "v": 27, "image": "assets/jordan.jpg", "music": "assets/home-music.mp3"}
ASSET_NAME = re.compile(r"^assets/[A-Za-z0-9._-]+$")


def home_config(root=None):
    """data/home.json of `root` (default: the real site); the built-in defaults when the file is missing."""
    path = os.path.join(root or ROOT, "data", "home.json")
    cfg = dict(HOME_DEFAULT)
    if os.path.exists(path):
        cfg.update(json.load(open(path, encoding="utf-8")))
    return cfg


def home_data():
    """data/home.json: only a reference (book/ch/v) plus asset paths and alt text; the verse must exist; no scripture text inside."""
    path = os.path.join(ROOT, "data", "home.json")
    if not os.path.exists(path):
        check("data/home.json 存在", False, "找不到檔案")
        return
    raw = open(path, encoding="utf-8").read()
    try:
        cfg = json.loads(raw)
    except ValueError as e:
        check("data/home.json 是合法 JSON", False, str(e))
        return
    check("home.json 只有 book、ch、v、image、alt、music 六個欄位", set(cfg) == {"book", "ch", "v", "image", "alt", "music"}, ",".join(sorted(cfg)))
    verses = {}
    for k, _ in BOOKS:
        for c in json.load(open(os.path.join(ROOT, "data", k + ".json"), encoding="utf-8"))["chapters"]:
            for v in c["verses"]:
                verses[(k, c["ch"], v["v"])] = v["text"]
    check("home.json 的書卷／章／節在 data/*.json 存在", (cfg.get("book"), cfg.get("ch"), cfg.get("v")) in verses, f"{cfg.get('book')} {cfg.get('ch')}:{cfg.get('v')}")
    for key in ("image", "music"):
        val = cfg.get(key, "")
        check(f"home.json 的 {key} 是 assets/ 底下的檔名且檔案存在", bool(ASSET_NAME.match(val)) and os.path.isfile(os.path.join(SITE, val)), val)
    check("home.json 的 image 副檔名是 jpg／png／webp，music 是 mp3",
          cfg.get("image", "").lower().endswith((".jpg", ".png", ".webp")) and cfg.get("music", "").lower().endswith(".mp3"))
    check("home.json 的 alt 是 1–120 字且含繁體中文", 1 <= len(cfg.get("alt", "")) <= 120 and bool(CJK.search(cfg.get("alt", ""))))
    check("home.json 沒有簡體字", not [ch for ch in SIMPLIFIED if ch in raw], "".join(ch for ch in SIMPLIFIED if ch in raw))
    grams = set()
    for t in verses.values():
        z = cjk(t)
        grams.update(z[i:i + 8] for i in range(len(z) - 7))
    z = cjk(raw)
    hit = sorted({z[i:i + 8] for i in range(len(z) - 7) if z[i:i + 8] in grams})
    check("home.json 沒有任何經文文字（沒有連續 8 字與經文相同）", not hit, "；".join(hit[:3]))


def home_state(port, click=False, width=None):
    """Open site/home.html in tests/home_probe.html (autoplay allowed, so the music button can be tested) and return its state."""
    q = "u=" + urllib.parse.quote("../site/home.html", safe="") + ("&click=1" if click else "") + (f"&w={width}" if width else "")
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=15000",
                              "--autoplay-policy=no-user-gesture-required", f"--user-data-dir={profile}", "--dump-dom",
                              f"http://127.0.0.1:{port}/tests/home_probe.html?{q}"], capture_output=True, text=True, timeout=90).stdout
    found = re.findall(r"PROBE (\{.*\})", re.sub(r"<[^>]+>", "", out))
    try:
        return json.loads(html.unescape(found[-1])) if found else {}
    except ValueError:
        return {}


def strip_blocks(css, header):
    """css without every block that starts with `header` (brace matched)."""
    out, i = [], 0
    while True:
        j = css.find(header, i)
        if j < 0:
            out.append(css[i:])
            return "".join(out)
        out.append(css[i:j])
        k, depth = css.find("{", j), 0
        while k < len(css):
            depth += css[k] == "{"
            depth -= css[k] == "}"
            k += 1
            if depth == 0:
                break
        i = k


def home_static():
    """site/home.html + the two redirects: no scripture in the source, motion only under prefers-reduced-motion, root redirect, back link."""
    page = os.path.join(SITE, "home.html")
    src = open(page, encoding="utf-8").read() if os.path.exists(page) else ""
    check("site/home.html 存在", bool(src), "找不到檔案")
    luk = json.load(open(os.path.join(ROOT, "data", "luk.json"), encoding="utf-8"))["chapters"]
    cfg = home_config()
    chosen = json.load(open(os.path.join(ROOT, "data", cfg["book"] + ".json"), encoding="utf-8"))["chapters"]
    v27 = cjk(next(v["text"] for c in luk if c["ch"] == 4 for v in c["verses"] if v["v"] == 27)) + cjk(next(v["text"] for c in chosen if c["ch"] == cfg["ch"] for v in c["verses"] if v["v"] == cfg["v"]))
    s = cjk(src)
    hit = sorted({v27[i:i + 8] for i in range(len(v27) - 7) if v27[i:i + 8] in s})
    check("home.html 沒有寫死經文（路加福音 4:27 與 home.json 指定的節，沒有任何連續 8 字相同）", not hit, "；".join(hit[:3]))
    check("home.html 從 data/home.json 讀設定（fetch home.json，失敗時用預設值）", "home.json" in src and "Bible.load(" in src)
    check("home.html 讀經文用 Bible.load（不自己 fetch、不寫死）", "Bible.load" in src and 'Bible.nav(' in src)
    bare = strip_blocks(strip_blocks(src, "@media (prefers-reduced-motion: no-preference)"), "@keyframes")
    moving = [m.group(0) for m in re.finditer(r"animation\s*:\s*(?!none)[^;}]+|transition\s*:\s*(?!none)[^;}]+", bare)]
    check("home.html 所有 animation／transition 都包在 prefers-reduced-motion: no-preference 裡", not moving and "animation" in src, "；".join(moving[:3]) or "沒有任何動態效果")
    check("home.html 有 @keyframes（圖片緩慢放大、淡入、音量條）", len(re.findall(r"@keyframes", src)) >= 3)
    check("home.html 的 audio 是 assets/home-music.mp3、loop、preload=none", bool(re.search(r"<audio[^>]*id=\"home-music\"", src)) and "assets/home-music.mp3" in src and bool(re.search(r"<audio[^>]*\bloop\b", src)) and bool(re.search(r"<audio[^>]*preload=\"none\"", src)))
    root = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    check("根目錄 index.html 的 meta refresh、location.replace、備援連結都指向 site/home.html",
          root.count("site/home.html") >= 3 and "site/index.html" not in root, f"home.html 出現 {root.count('site/home.html')} 次")
    idx = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    check("site/index.html 的 <main> 內有「回首頁」連到 home.html", re.search(r"<main[^>]*>.*?<a[^>]+href=\"home\.html\"[^>]*>[^<]*回首頁[^<]*</a>.*?</main>", idx, re.S) is not None)
    for f in ("jordan.jpg", "home-music.mp3", os.path.basename(cfg["image"]), os.path.basename(cfg["music"])):
        check(f"site/assets/{f} 存在且不是空檔", os.path.getsize(os.path.join(SITE, "assets", f)) > 10000 if os.path.exists(os.path.join(SITE, "assets", f)) else False)


def home_render(port, root=None, label=""):
    """Render home.html served from `root` (default: the real site) and compare with that root's home.json."""
    cfg = home_config(root)
    book = json.load(open(os.path.join(root or ROOT, "data", cfg["book"] + ".json"), encoding="utf-8"))["chapters"]
    want = next(v["text"] for c in book if c["ch"] == cfg["ch"] for v in c["verses"] if v["v"] == cfg["v"])
    ref = f"{dict(BOOKS)[cfg['book']]} {cfg['ch']}:{cfg['v']}"
    st = home_state(port, click=True)
    if not st:
        check("home.html 量測", False, "探測頁沒有輸出")
        return
    brief = json.dumps(st, ensure_ascii=False)[:400]
    check(f"home.html{label} 的 .home-verse 逐字等於 home.json 指定的經文", st.get("verse", "").replace(" ", "") == want.strip().replace(" ", ""), st.get("verse", "")[:60])
    check(f"home.html{label} 的 .home-ref 是 home.json 指定的出處", ref in st.get("ref", ""), f"{st.get('ref', '')} / 預期 {ref}")
    check("home.html 沒有 JavaScript 錯誤", not st.get("errors"), "；".join(st.get("errors", [])[:3]))
    img = st.get("img") or {}
    check(f"home.html{label} 的英雄圖是 home.json 指定的圖、真的載入、alt 等於 home.json 的 alt", img.get("src") == cfg["image"] and img.get("naturalWidth", 0) >= 1000 and img.get("alt") == cfg.get("alt", img.get("alt")), json.dumps(img, ensure_ascii=False))
    aud = st.get("audio") or {}
    check(f"home.html{label} 的 <audio> 是 home.json 指定的音樂、loop、preload=none", aud.get("src", "").endswith(cfg["music"]) and aud.get("loop") is True and aud.get("preload") == "none", json.dumps(aud))
    m0, m1, m2 = st.get("initialMusic") or {}, st.get("afterClick") or {}, st.get("afterSecond") or {}
    sync = lambda m: m.get("pressed") in ("true", "false") and (m.get("pressed") == "true") == (m.get("paused") is False)
    check("#music-btn 的 aria-pressed 永遠和 audio 是否正在播放一致", sync(m0) and sync(m1) and sync(m2), brief)
    check("#music-btn 點一下就切換播放／暫停，再點一下切回來", m1.get("pressed") != m0.get("pressed") and m2.get("pressed") == m0.get("pressed"), json.dumps([m0, m1, m2], ensure_ascii=False))
    check("#music-btn 的文字是「播放音樂」或「暫停音樂」，隨狀態改變", all(m.get("pressed") in ("true", "false") and ("播放音樂" in m.get("text", "")) == (m.get("pressed") == "false") and ("暫停音樂" in m.get("text", "")) == (m.get("pressed") == "true") for m in (m0, m1, m2)), json.dumps([m0, m1, m2], ensure_ascii=False))
    links = {l["text"]: l["href"] for l in st.get("links", [])}
    get = lambda key: next((h for t, h in links.items() if key in t), None)
    check("「進入四福音」連到 index.html、「抽一張經文卡」連到 blessing.html", get("進入四福音") == "index.html" and get("抽一張經文卡") == "blessing.html", json.dumps(links, ensure_ascii=False))
    check(f"「閱讀本章」{label}連到 home.json 指定那一章的那一節", get("閱讀本章") == f"chapter.html?book={cfg['book']}&ch={cfg['ch']}#v{cfg['v']}", str(get("閱讀本章")))
    check("home.html 的導覽列有四項、沒有任何一項標成目前頁、h1 是「四福音」", st.get("navCount") == 4 and st.get("navActive") == 0 and "四福音" in st.get("h1", ""), f"nav {st.get('navCount')}/{st.get('navActive')} h1 {st.get('h1')}")


def home_variants():
    """Serve temp copies of the site: (a) a different home.json with copied assets, (b) no home.json at all."""
    import shutil
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    for label, cfg in ((" (自訂設定)", {"book": "jhn", "ch": 3, "v": 16, "image": "assets/custom-pic.jpg", "alt": "測試用的替代圖片說明", "music": "assets/custom-song.mp3"}),
                       (" (沒有 home.json)", None)):
        with tempfile.TemporaryDirectory() as tmp:
            for d in ("site", "data"):
                shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d))
            os.makedirs(os.path.join(tmp, "tests"))
            shutil.copy(os.path.join(ROOT, "tests", "home_probe.html"), os.path.join(tmp, "tests"))
            if cfg:
                shutil.copy(os.path.join(tmp, "site", "assets", "jordan.jpg"), os.path.join(tmp, "site", "assets", "custom-pic.jpg"))
                shutil.copy(os.path.join(tmp, "site", "assets", "home-music.mp3"), os.path.join(tmp, "site", "assets", "custom-song.mp3"))
                json.dump(cfg, open(os.path.join(tmp, "data", "home.json"), "w", encoding="utf-8"), ensure_ascii=False)
            else:
                os.remove(os.path.join(tmp, "data", "home.json"))
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
            with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                home_render(srv.server_address[1], tmp, label)
                srv.shutdown()


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
        if groups & {"blessing", "blessnav", "blessindex", "blessstyle"}:
            blessing_render(port, groups)
        if "home" in groups:
            home_render(port)
            home_variants()
        srv.shutdown()


if __name__ == "__main__":
    if not os.path.isdir(SITE) or not any(site_files(".html")):
        print("不通過：site/ 裡還沒有任何 HTML 檔案")
        sys.exit(1)
    # optional page filter: `site_checks.py chapter|search|index|card` runs links, external and only that page's rendering checks
    args = sys.argv[1:]
    if "--grep" in args:
        i = args.index("--grep")
        ONLY = args[i + 1]
        del args[i:i + 2]
    groups = set(args) or {"chapter", "search", "index", "card", "blessing", "blessnav", "blessindex", "blessstyle", "home"}
    links()
    external()
    single_book_text()
    if "blessing" in groups:
        blessing_data()
    if "home" in groups:
        home_data()
        home_static()
    rendering(groups)
    if ONLY and not results:
        results.append(False)   # a typo in --grep must not pass silently
        print(f"不通過：--grep {ONLY} 沒有對到任何檢查")
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
