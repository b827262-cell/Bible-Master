#!/usr/bin/env python3
"""Automatic site checks (exit code 0 only when all pass):
1. Links: every relative href/src in the HTML, and every *.html/.css/.js/.json path in the JS, points to an existing file.
2. External resources: no http(s):// or protocol-relative URL is loaded (xmlns namespace strings are allowed).
3. Rendering (headless Chrome): chapter.html?ch=1 and ?ch=16 show every verse of that chapter;
   search.html?q=耶穌 shows exactly as many "馬可福音 章:節" results as mark.json has verses containing 耶穌.
4. blessing (data/blessing.json + site/blessing.html): see blessing_data() and blessing_render().
5. home (site/home.html, assets, root redirect): see home_static() and home_render().
6. zonemusic (site/music.js on index/search/card/blessing, data/zone-music.json, tests/zone_probe.html): see zone_static() and zone_render().
7. blessart (data/blessing-art.json + site/blessing.html: one collectible art image per theme, direct download, canvas composite) and blessing_frozen() (the 37 cards are fixed).
8. devotional (site/devotional.html + site/devotional.js): the fake data/devotional.json is written only into a /tmp copy of site/ + data/, carries just ids, dates, titles, references, ranges and placeholder prose, and the expected scripture is computed at run time from data/{mat,mrk,luk,jhn}.json — no verse is ever hard-coded here. See devotional_static() and devotional_variants().
9. restyle (2026-11 redesign, the checks come first): the two gold-eagle card images (size/weight/licence and registered in ASSETS-LICENSE.md), the sample's colour tokens in style.css (light and dark), the sunlight verse colour, the five-item bottom floating dock on every front-end page, the hero picture never overlapping today's verse at 320/375/768/1440px, the bento entrances with the B-A-B fan cards, and the three micro-interaction states (busy / ok / fix) with text, distinct icons and a live region. See restyle_assets(), restyle_shared() and restyle_render() — they fail until the pages are restyled, by design.
"""
import datetime, functools, html, http.server, json, os, re, socketserver, subprocess, sys, tempfile, threading, urllib.parse, urllib.request

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


def blessing_state(port, url, act=None, width=None, dark=False, reduce=False):
    """?dark=1 用深色模式、?reduce=1 強制 prefers-reduced-motion: reduce（第三輪 B 要分兩套色與動效關掉三種情境量）。"""
    q = "u=" + urllib.parse.quote("../site/" + url, safe="") + ("&act=" + urllib.parse.quote(json.dumps(act)) if act else "") + (f"&w={width}" if width else "")
    extra = ["--blink-settings=preferredColorScheme=0"] if dark else []
    extra += ["--force-prefers-reduced-motion"] if reduce else []
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=20000",
                              *extra, f"--user-data-dir={profile}", "--dump-dom", f"http://127.0.0.1:{port}/tests/blessing_probe.html?{q}"],
                             capture_output=True, text=True, timeout=90).stdout
    out = re.sub(r"<[^>]+>", "", out)
    found = re.findall(r"PROBE (\{[^\n]*\})\s*$", out, re.M)
    try:
        return json.loads(html.unescape(found[-1])) if found else {}
    except ValueError:
        return {}


PALETTE = {  # design/sample-2026-11.html 的 :root（2026-11 改版唯一的視覺依據）：淺色, 深色
    "--paper": ("#f3f6f2", "#0a1412"), "--surface": ("#ffffff", "#121f1c"), "--ink": ("#10231f", "#e9f1ee"),
    "--muted": ("#586a64", "#94a8a1"), "--river": ("#0e6b5b", "#55d3b7"), "--river-soft": ("#dcefe9", "#16302a"),
    "--lamp": ("#c98a1b", "#f0bf5c"), "--mat": ("#c98a1b", "#f0bf5c"), "--mrk": ("#d9583b", "#ff8a6b"),
    "--luk": ("#0e6b5b", "#55d3b7"), "--jhn": ("#3d55c4", "#8fa2ff")}
SUNLIGHT = "#fdf2da"          # 樣本取樣：照片裡灑在人物身上的光；首页今日經文必須同色
SUNLIGHT_RGB = "rgb(253, 242, 218)"
NAV5 = [("首頁", "home.html"), ("目錄", "index.html"), ("禱讀", "devotional.html"), ("抽卡", "blessing.html"), ("搜尋", "search.html")]
DOCK_PAGES = ["home.html", "index.html", "chapter.html?book=mat&ch=1", "search.html?q=耶穌", "card.html?book=luk&ch=1&v=1",
              "blessing.html", "devotional.html"]


def css_vars(css):
    """取 :root 淺色與深色兩套變數（深色可以是 @media 或 :root[data-theme="dark"]）。"""
    light = re.search(r"^:root\s*\{(.*?)\}", css, re.S | re.M)
    dark = re.search(r"prefers-color-scheme:\s*dark\)\s*\{\s*:root[^{]*\{(.*?)\}", css, re.S | re.M)
    if not dark:
        dark = re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', css, re.S)
    got = {}
    for i, block in enumerate((light, dark)):
        for k, v in re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", block.group(1) if block else ""):
            got.setdefault(k, [None, None])[i] = v.lower()
    return got, bool(light), bool(dark)


def blessing_style(port, card_ok):
    css = open(os.path.join(SITE, "style.css"), encoding="utf-8").read()
    got, has_light, has_dark = css_vars(css)
    for i, scheme in enumerate(("淺色", "深色")):
        bad = [f"{k} {got.get(k, [None, None])[i]}≠{v[i]}" for k, v in PALETTE.items() if (got.get(k, [None, None])[i] or "") != v[i]]
        check(f"style.css {scheme}配色變數等於 2026-11 樣本（--paper／--ink／--river／--lamp＋四卷色，含 --river-soft）",
              (has_light if i == 0 else has_dark) and not bad, "；".join(bad) or "找不到該套 :root 變數")
    st = blessing_state(port, "blessing.html?card=work-01")
    s = st.get("style") or {}
    ok, why = card_ok(st.get("card"), st.get("canvasRef"), "work-01")
    px = st.get("canvasPixels") or {}
    check("blessing.html 的 canvas 圖卡不顯示在頁面上，但仍在背景畫好（≥600px、data-ref 正確、底色 #fbf7ee、真的畫了字）供下載",
          ok and s.get("canvasShown") is False and st.get("canvasW", 0) >= 600 and px.get("corner") == [251, 247, 238] and px.get("dark", 0) > 500,
          why or json.dumps({"canvasShown": s.get("canvasShown"), "pixels": px}, ensure_ascii=False))
    active = [t["id"] for t in s.get("tabs", []) if t["active"]]
    want = sorted(["again-btn"] + ["theme:" + a for a in active])
    check("blessing.html 實心主色（翠綠）按鈕只有兩顆：選中的主題與「再抽一次」", sorted(s.get("solid", [])) == want and len(want) == 2,
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
    check("blessing.html 經文用明體（--display 那組系統字型），不再是舊版左側 3px 棕色豎線（改以大號明體呈現）",
          "serif" in v.get("font", "") and "sans-serif" not in v.get("font", "") and v.get("left", 99) <= 1 and v.get("px", 0) >= 20,
          json.dumps(v, ensure_ascii=False))
    pill = s.get("pills") or {}
    check("blessing.html 的動作按鈕是膠囊形（圓角 ≥ 元素高度的一半）",
          bool(pill) and pill.get("radius", 0) + 0.5 >= pill.get("h", 1e9) / 2, json.dumps(pill))
    cov = s.get("cover") or {}
    check("blessing.html 抽卡前的畫面顯示金色飛鷹卡背圖（eagle-A 由共用樣式提供，不是愛心＋空白）",
          bool(cov.get("hasA")) and cov.get("shown") is True and not cov.get("blankBlock"), json.dumps(cov, ensure_ascii=False)[:200])
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
        app = open(os.path.join(SITE, "app.js"), encoding="utf-8").read()
        for page in ("index.html", "chapter.html?ch=1", "search.html", "card.html"):
            src = dump(base + page)
            check(f"{page.split('?')[0]} 的導覽列有「抽卡」（或含「抽」字）連結，指向 blessing.html",
                  re.search(r"抽[^\s<]{0,3}", src) is not None and "blessing.html" in app,
                  "找不到抽卡連結" if "blessing.html" not in app else "導覽文字沒有「抽」字")
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


def home_state(port, click=False, width=None, page="home.html", do=None, wides=False):
    """Open a front-end page in tests/home_probe.html (autoplay allowed, so the music button can be tested) and return its state.
    ?do=empty|hit|miss 跑一趟搜尋三種狀態；?wides=1 在同一輪內依序量 320／375／768／1440 的主視覺幾何。"""
    q = "u=" + urllib.parse.quote("../site/" + page, safe="") + ("&click=1" if click else "") + (f"&w={width}" if width else "") \
        + (f"&do={do}" if do else "") + ("&wides=1" if wides else "")
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
    ev = set(re.findall(r'document\.addEventListener\("(\w+)",\s*onFirstGesture', src))
    arr = re.search(r"var GESTURES = \[([^\]]*)\]", src)
    if arr and re.search(r"GESTURES\.forEach\(function \(name\) \{\s*document\.addEventListener\(name, onFirstGesture\)", src):
        ev |= set(re.findall(r'"(\w+)"', arr.group(1)))
    check("home.html 的「第一次觸碰就播」只掛在能取得使用者啟動權限的事件（click／pointerup／touchend＋keydown），不掛 pointerdown／touchstart／mousedown（手機瀏覽器不認，會播不出來）",
          bool(ev & {"click", "pointerup", "touchend"}) and "keydown" in ev and not ev & {"pointerdown", "touchstart", "mousedown"}, "、".join(sorted(ev)) or "找不到 onFirstGesture 監聽")
    check("home.html 第一次觸碰播放被拒絕時（例如那次觸碰只是捲動），會重新掛回監聽，下一次觸碰再試", bool(re.search(r"tryPlay\(\)\.then\([^)]*armFirstGesture|armFirstGesture\(\);\s*\}\s*\}\);\s*\}", src)) or "rearm" in src.lower())
    btn = re.search(r'musicBtn\.addEventListener\("click", function \(\) \{(.*?)\n      \}\);', src, re.S)
    check("home.html 使用者按了 #music-btn 之後，就拆掉「第一次觸碰」的監聽（否則按暫停後，點別處又會自己播起來）",
          bool(btn) and "disarmFirstGesture()" in btn.group(1) and "var disarmFirstGesture" in src and "disarmFirstGesture = cleanup" in src, "按鈕的 click 處理沒有呼叫 disarmFirstGesture()")
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
    check("home.html 的導覽列有五項（首頁、目錄、禱讀、抽卡、搜尋）、恰有一項標成目前頁、h1 是「四福音」",
          st.get("navCount") == 5 and st.get("navActive") == 1 and "四福音" in st.get("h1", ""), f"nav {st.get('navCount')}/{st.get('navActive')} h1 {st.get('h1')}")


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


ZONE_PAGES = ["index.html", "search.html", "card.html", "blessing.html"]   # the four zones that play the shared background music
ZONE_DEFAULT = {"music": "assets/home-music.mp3"}


def zone_config(root=None):
    """data/zone-music.json of `root` (default: the real site); the built-in default when the file is missing."""
    path = os.path.join(root or ROOT, "data", "zone-music.json")
    cfg = dict(ZONE_DEFAULT)
    if os.path.exists(path):
        cfg.update(json.load(open(path, encoding="utf-8")))
    return cfg


def zone_data():
    """data/zone-music.json: exactly one field, `music`, an existing mp3 under site/assets/."""
    path = os.path.join(ROOT, "data", "zone-music.json")
    if not os.path.exists(path):
        check("zonemusic：data/zone-music.json 存在", False, "找不到檔案")
        return
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except ValueError as e:
        check("zonemusic：data/zone-music.json 是合法 JSON", False, str(e))
        return
    check("zonemusic：zone-music.json 保留 music、只允許選填 zones", isinstance(cfg, dict) and "music" in cfg and set(cfg) <= {"music", "zones"}, ",".join(sorted(cfg)) if isinstance(cfg, dict) else "不是物件")
    val = cfg.get("music", "") if isinstance(cfg, dict) else ""
    zones = cfg.get("zones", {}) if isinstance(cfg, dict) else {}
    valid = lambda m: isinstance(m, str) and bool(ASSET_NAME.match(m)) and ".." not in m and m.lower().endswith(".mp3") and os.path.isfile(os.path.join(SITE, m))
    check("zonemusic：zones 只能使用四區名、可省略或留空、各值為存在的 mp3",
          isinstance(zones, dict) and set(zones) <= {"index", "search", "card", "blessing"} and all(valid(m) for m in zones.values()), str(zones))

    check("zonemusic：zone-music.json 的 music 是 assets/ 底下的 .mp3 檔名且檔案存在、不是空檔",
          isinstance(val, str) and bool(ASSET_NAME.match(val)) and val.lower().endswith(".mp3") and os.path.isfile(os.path.join(SITE, val)) and os.path.getsize(os.path.join(SITE, val)) > 10000, str(val))


def zone_static():
    """The four zone pages load music.js; home.html and chapter.html do not; music.js and style.css follow the contract."""
    for p in ZONE_PAGES:
        src = open(os.path.join(SITE, p), encoding="utf-8").read()
        m = re.search(r'<script src="app\.js"></script>.*?<script src="music\.js"></script>', src, re.S)
        check(f"zonemusic：{p} 在 app.js 之後載入 music.js", m is not None)
        check(f"zonemusic：{p} 沒有自己放 <audio> 或 #zone-music-btn（由 music.js 產生）", "<audio" not in src and "zone-music-btn" not in src)
    for p in ("home.html", "chapter.html"):
        src = open(os.path.join(SITE, p), encoding="utf-8").read()
        check(f"zonemusic：{p} 不載入 music.js（首頁自有音樂、閱讀頁安靜）", "music.js" not in src)
    path = os.path.join(SITE, "music.js")
    js = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    check("zonemusic：site/music.js 存在", bool(js), "找不到檔案")
    check("zonemusic：music.js 讀 ../data/zone-music.json，失敗時退回 assets/home-music.mp3", "zone-music.json" in js and "assets/home-music.mp3" in js and "fetch(" in js)
    check("zonemusic：music.js 產生 #zone-music-btn（aria-pressed）與 #zone-music（loop、preload=none），不用 autoplay 屬性",
          "zone-music-btn" in js and "aria-pressed" in js and "zone-music" in js and "loop" in js and "preload" in js and "autoplay" not in js.lower().replace("autoplay-policy", ""))
    ev = set()
    arr = re.search(r"GESTURES\s*=\s*\[([^\]]*)\]", js)
    if arr:
        ev |= set(re.findall(r'"(\w+)"', arr.group(1)))
    ev |= set(re.findall(r'document\.addEventListener\("(\w+)",\s*onFirstGesture', js))
    check("zonemusic：music.js 的「第一次觸碰就播」只掛 click／pointerup／touchend＋keydown，不掛 pointerdown／touchstart／mousedown",
          bool(ev & {"click", "pointerup", "touchend"}) and "keydown" in ev and not ev & {"pointerdown", "touchstart", "mousedown"}, "、".join(sorted(ev)) or "找不到 GESTURES")
    check("zonemusic：music.js 用 sessionStorage 的 bm.zone.on／bm.zone.t／bm.zone.src，且存取都包在 try 裡，pagehide 時存秒數",
          all(k in js for k in ("sessionStorage", "bm.zone.on", "bm.zone.t", "bm.zone.src", "pagehide", "timeupdate")) and js.count("try") >= 2)
    check("zonemusic：music.js 按過按鈕後就拆掉「第一次觸碰」監聽（disarm），且忽略來自 #zone-music-btn 的事件", "disarm" in js.lower() and "zone-music-btn" in js and bool(re.search(r"closest\(|contains\(|\.id\s*===?\s*[\"']zone-music-btn|=== *btn", js)))
    check("zonemusic：music.js 沒有寫死經文、沒有載入外部資源", "http://" not in js and "https://" not in js and "//cdn" not in js)
    css = open(os.path.join(SITE, "style.css"), encoding="utf-8").read()
    check("zonemusic：style.css 有 #zone-music-btn 的樣式（固定位置、最小 44px）", "#zone-music-btn" in css and "position: fixed" in css.replace("position:fixed", "position: fixed") and bool(re.search(r"min-height:\s*44px", css)))
    bare = strip_blocks(strip_blocks(css, "@media (prefers-reduced-motion: no-preference)"), "@keyframes")
    moving = [m.group(0) for m in re.finditer(r"animation\s*:\s*(?!none)[^;}]+", bare)]
    check("zonemusic：style.css 的 animation 都包在 prefers-reduced-motion: no-preference 裡", not moving, "；".join(moving[:3]))


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    """Static handler that also answers `Range: bytes=a-b` (206). Real hosts do; without it headless Chrome cannot seek inside an mp3
    it has not fully downloaded, and the probe's jump to second 7 silently stays at 0."""

    def log_message(self, *a):
        pass

    def send_head(self):
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "").strip())
        path = self.translate_path(self.path)
        if not m or not (m.group(1) or m.group(2)) or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        if m.group(1):
            start, end = int(m.group(1)), min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
        else:
            start, end = max(size - int(m.group(2)), 0), size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        self._range_left = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        left = getattr(self, "_range_left", None)
        if left is None:
            return super().copyfile(source, outputfile)
        self._range_left = None
        while left > 0:
            buf = source.read(min(65536, left))
            if not buf:
                break
            outputfile.write(buf)
            left -= len(buf)


def zone_state(port, pages, width=None):
    """Run tests/zone_probe.html through the local server with up to three pages in a row (same iframe); returns its ZPROBE object."""
    q = "u=" + urllib.parse.quote("../site/" + pages[0], safe="")
    for key, p in zip(("u2", "u3"), pages[1:]):
        q += f"&{key}=" + urllib.parse.quote("../site/" + p, safe="")
    if width:
        q += f"&w={width}"
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=40000",
                              "--autoplay-policy=no-user-gesture-required", f"--user-data-dir={profile}", "--dump-dom",
                              f"http://127.0.0.1:{port}/tests/zone_probe.html?{q}"], capture_output=True, text=True, timeout=120).stdout
    found = re.findall(r"ZPROBE (\{.*\})", re.sub(r"<[^>]+>", "", out))
    try:
        return json.loads(html.unescape(found[-1])) if found else {}
    except ValueError:
        return {}


def zone_render(port, root=None, label="", pages=None, width=None):
    """Drive the shared music button on `pages` (first page → click → second page → click → third page) and check state, config, layout."""
    cfg = zone_config(root)
    pages = pages or ZONE_PAGES[:3]
    def selected(p):
        return (cfg.get("zones") or {}).get(p.removesuffix(".html"), cfg["music"])
    for _ in range(3):                                 # headless Chrome sometimes drops the probe's own seek to 7 s on page 2; that is setup, not the site
        st = zone_state(port, pages, width)
        if st and st.get("s1") and ((st.get("s2click") or {}).get("t") or 0) >= 6.5:
            break
    if not st or not st.get("s1"):
        check(f"zonemusic{label}：探測頁有輸出", False, "沒有 ZPROBE 輸出")
        return
    tag = f"{label}（{' → '.join(pages)}）"
    sync = lambda s: s and s.get("btn") and s.get("pressed") in ("true", "false") and (s["pressed"] == "true") == (s.get("paused") is False)
    labelled = lambda s: s and s.get("btn") and ("播放音樂" in s.get("text", "")) == (s.get("pressed") == "false") and ("暫停音樂" in s.get("text", "")) == (s.get("pressed") == "true")
    seq = [st.get(k) for k in ("s1", "s1click", "s2", "s2click", "s3")]
    brief = json.dumps(seq, ensure_ascii=False)[:600]
    s1, c1, s2, c2, s3 = seq
    check(f"zonemusic{tag}：每一頁都有 #zone-music-btn 與 #zone-music，aria-pressed 永遠和 audio 是否播放一致", all(sync(s) for s in seq if s), brief)
    check(f"zonemusic{tag}：按鈕文字是「播放音樂」或「暫停音樂」，隨狀態改變", all(labelled(s) for s in seq if s), brief)
    check(f"zonemusic{tag}：<audio> 是 zone-music.json 指定的音樂、loop、preload=none", all(s.get("src", "").endswith(selected(p)) and s.get("loop") is True and s.get("preload") == "none" for s, p in zip(seq, [pages[0], pages[0], pages[1], pages[1], pages[2]]) if s), brief)
    check(f"zonemusic{tag}：第一次進來（沒有任何紀錄）會嘗試自動播放", s1 and s1.get("pressed") == "true" and s1.get("on") in (None, "1"), brief)
    check(f"zonemusic{tag}：按下按鈕暫停，並記下 bm.zone.on=0", c1 and c1.get("pressed") == "false" and c1.get("paused") is True and c1.get("on") == "0", brief)
    check(f"zonemusic{tag}：跳到下一頁，暫停狀態被記住（不自己播起來）", s2 and s2.get("pressed") == "false" and s2.get("paused") is True and s2.get("on") == "0", brief)
    check(f"zonemusic{tag}：再按一次開始播放，記下 bm.zone.on=1", c2 and c2.get("pressed") == "true" and c2.get("on") == "1", brief)
    check(f"zonemusic{tag}：跳到第三頁，開著的狀態被記住並從上一頁的位置（第 7 秒）續播", bool(s3) and s3.get("pressed") == "true" and ((s3.get("t") or 0) >= 6.5 if selected(pages[1]) == selected(pages[2]) else (s3.get("t") or 0) < 6.5) and s3.get("savedSrc", "").endswith(selected(pages[2])), brief)
    err = st.get("errors", [])
    check(f"zonemusic{tag}：沒有 JavaScript 錯誤", not err, "；".join(err[:3]))
    box = [s for s in seq if s]
    check(f"zonemusic{tag}：按鈕至少 44×44、在視窗內、頁面沒有水平溢出", bool(box) and all(s.get("w", 0) >= 44 and s.get("h", 0) >= 44 and s.get("right", 9999) <= s.get("vw", 0) and s.get("bottom", 9999) <= s.get("vh", 0) and s.get("scrollW", 9999) <= s.get("vw", 0) for s in box), json.dumps(box[:1], ensure_ascii=False))
    check(f"zonemusic{tag}：導覽列是五項（首頁、目錄、禱讀、抽卡、搜尋）、恰有一項標成目前頁", bool(box) and all(s.get("count") == 5 and s.get("active") == 1 for s in box), json.dumps([(s.get("count"), s.get("active")) for s in box]))


def zone_variants():
    """Serve temp copies: (a) a different zone-music.json with a copied mp3, (b) no zone-music.json at all (falls back to home-music.mp3)."""
    import shutil
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    for label, cfg in ((" (自訂設定)", {"music": "assets/custom-zone.mp3"}),
                       # every zone gets its own file (blessing has no key and falls back to `music`), so swapped zone keys show up as a wrong <audio src>
                       (" (四區獨立)", {"music": "assets/home-music.mp3", "zones": {"index": "assets/custom-zone.mp3", "search": "assets/custom-zone-b.mp3", "card": "assets/custom-zone-c.mp3"}}),
                       (" (兩區同曲)", {"music": "assets/home-music.mp3", "zones": {"index": "assets/custom-zone.mp3", "search": "assets/custom-zone.mp3", "blessing": "assets/custom-zone-b.mp3"}}),   # blessing has its own file here
                       (" (沒有 zone-music.json)", None)):
        with tempfile.TemporaryDirectory() as tmp:
            for d in ("site", "data"):
                shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d))
            os.makedirs(os.path.join(tmp, "tests"))
            shutil.copy(os.path.join(ROOT, "tests", "zone_probe.html"), os.path.join(tmp, "tests"))
            zf = os.path.join(tmp, "data", "zone-music.json")
            if cfg:
                for name in ("custom-zone.mp3", "custom-zone-b.mp3", "custom-zone-c.mp3"):
                    shutil.copy(os.path.join(tmp, "site", "assets", "home-music.mp3"), os.path.join(tmp, "site", "assets", name))
                json.dump(cfg, open(zf, "w", encoding="utf-8"), ensure_ascii=False)
            elif os.path.exists(zf):
                os.remove(zf)
            handler = functools.partial(RangeHandler, directory=tmp)
            with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                zone_render(srv.server_address[1], tmp, label, pages=["card.html", "search.html", "blessing.html"])
                if cfg and "zones" in cfg:
                    same = cfg["zones"].get("index") == cfg["zones"].get("search")
                    zone_render(srv.server_address[1], tmp, label + ("（同曲跨頁）" if same else "（換曲跨頁）"), pages=["card.html", "index.html", "search.html"] if same else ["index.html", "search.html", "card.html"])
                srv.shutdown()


def blessing_frozen():
    """The 37 blessing cards are fixed (user decision): ids, themes, verse references and message texts must equal tests/blessing_frozen.json."""
    import hashlib
    fz = json.load(open(os.path.join(ROOT, "tests", "blessing_frozen.json"), encoding="utf-8"))
    b = json.load(open(os.path.join(ROOT, "data", "blessing.json"), encoding="utf-8"))
    cur = [{"id": c["id"], "theme": c["theme"], "book": c["book"], "ch": c["ch"], "v": c["v"], "message_sha256": hashlib.sha256(c["message"].encode("utf-8")).hexdigest()} for c in b["cards"]]
    check("blessing.json 凍結：固定 37 張卡，四個主題 20／6／5／6 張", len(cur) == 37 and [sum(c["theme"] == t for c in cur) for t in ("work", "peace", "rest", "faith")] == [20, 6, 5, 6])
    diff = [c["id"] for c in fz["cards"] if c not in cur] + [c["id"] for c in cur if c not in fz["cards"]]
    check("blessing.json 凍結：每張卡的 id、主題、書卷章節、短文都和 tests/blessing_frozen.json 相同", cur == fz["cards"], "、".join(sorted(set(diff))[:8]))
    check("blessing.json 凍結：四個主題的 id 與標題沒變", [{"id": t["id"], "title": t["title"]} for t in b["themes"]] == fz["themes"])


ART_ENTRY_KEYS = {"image", "alt", "edition"}


def blessart_data():
    """data/blessing-art.json: one optional entry per blessing theme: {image: assets/<jpg|png|webp>, alt: 1-120 chars, edition: 0-20 chars}."""
    path = os.path.join(ROOT, "data", "blessing-art.json")
    if not os.path.exists(path):
        check("blessart：data/blessing-art.json 存在", False, "找不到檔案")
        return
    try:
        art = json.load(open(path, encoding="utf-8"))
    except ValueError as e:
        check("blessart：data/blessing-art.json 是合法 JSON", False, str(e))
        return
    themes = {t["id"] for t in json.load(open(os.path.join(ROOT, "data", "blessing.json"), encoding="utf-8"))["themes"]}
    check("blessart：blessing-art.json 是物件，鍵只能是主題 id 或 cards", isinstance(art, dict) and set(art) <= themes | {"cards"}, ",".join(sorted(set(art) - themes)) if isinstance(art, dict) else "不是物件")
    cards = art.get("cards", {}) if isinstance(art, dict) else {}
    ids = {c["id"] for c in json.load(open(os.path.join(ROOT, "data", "blessing.json"), encoding="utf-8"))["cards"]}
    check("blessart：cards 可省略、卡 id 只能是 blessing.json 的 37 張",
          isinstance(cards, dict) and set(cards) <= ids, str(set(cards) - ids) if isinstance(cards, dict) else "不是物件")
    ents = [v for k, v in art.items() if k != "cards"] + list(cards.values()) if isinstance(art, dict) and isinstance(cards, dict) else []
    check("blessart：每個主題的設定剛好有 image、alt、edition 三個欄位", all(isinstance(e, dict) and set(e) == ART_ENTRY_KEYS for e in ents))
    check("blessart：image 是 assets/ 底下的 jpg／png／webp 且檔案存在", all(isinstance(e, dict) and isinstance(e.get("image"), str) and bool(ASSET_NAME.match(e["image"])) and e["image"].lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
                                                                  and os.path.isfile(os.path.join(SITE, e["image"])) for e in ents))
    check("blessart：alt 是 1–120 字、edition 是 0–20 字", all(isinstance(e, dict) and 1 <= len(e.get("alt", "")) <= 120 and len(e.get("edition", "")) <= 20 for e in ents))
    raw = open(path, encoding="utf-8").read()
    check("blessart：blessing-art.json 沒有簡體字", not [ch for ch in SIMPLIFIED if ch in raw])


def blessart_static():
    src = open(os.path.join(SITE, "blessing.html"), encoding="utf-8").read()
    check("blessart：blessing.html 讀 ../data/blessing-art.json（失敗時當作沒有圖）", "blessing-art.json" in src and "fetch(" in src)
    check("blessart：blessing.html 有 .card-art 畫框、.card-edition 版次、a#art-download（有 download 屬性）", "card-art" in src and "card-edition" in src and 'id="art-download"' in src and "download" in src)
    check("blessart：blessing.html 的收藏卡主題圖只來自設定檔（原始碼沒有寫死上傳圖檔名；2026-11 的固定飛鷹卡背由 style.css／app.js 提供，另有檢查）",
          not re.search(r"assets/(upload-[A-Za-z0-9._-]+\.(?:jpg|jpeg|png|webp))", src, re.I),
          "、".join(re.findall(r"assets/upload-[A-Za-z0-9._-]+", src, re.I)[:4]))
    art_convert_check()


def art_convert_check():
    """tools/art_convert.py: keeps the ratio, never crops or adds a frame (the generator draws the frame), long side ≤ 2400, JPG ≤ 3 MB."""
    try:
        from PIL import Image
    except ImportError:
        check("blessart：tools/art_convert.py（需要 Pillow）", False, "沒有安裝 Pillow")
        return
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.jpg")
        open(src, "wb").write(solid_png(1800, 2400, (255, 0, 0)))
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "art_convert.py"), src, "-o", out], capture_output=True, text=True, timeout=60)
        ok = r.returncode == 0 and os.path.exists(out)
        im = Image.open(out).convert("RGB") if ok else None
        edge = [im.getpixel((x, y)) for x, y in ((2, 1200), (1797, 1200), (900, 2), (900, 2397))] if im else []
        check("blessart：tools/art_convert.py 產生 JPG、3 MB 以內、比例與尺寸不變（1800×2400 不縮、不裁）", ok and im.size == (1800, 2400) and Image.open(out).format == "JPEG" and os.path.getsize(out) <= 3 * 1024 * 1024, (r.stderr or r.stdout)[-200:])
        check("blessart：tools/art_convert.py 不加框（邊緣仍是原圖的顏色）", bool(edge) and all(p[0] > 200 and p[1] < 60 and p[2] < 60 for p in edge), json.dumps(edge))


def solid_png(w, h, rgb):
    """A solid-colour PNG (test fixture), standard library only."""
    import struct, zlib
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def blessart_variants():
    """Serve temp copies of the site with a test blessing-art.json (work = solid red, peace = solid blue; rest/faith have no art) and check the card."""
    import shutil
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    ed = "2026 年 11 月版"
    good = {"work": {"image": "assets/art-work.png", "alt": "測試用主題圖：金黃麥田", "edition": ed}, "peace": {"image": "assets/art-peace.png", "alt": "測試用主題圖：靜水旁的羊群", "edition": ed}}
    per_card = dict(good)
    per_card["cards"] = {"work-01": {"image": "assets/art-peace.png", "alt": "單卡獨立藍圖", "edition": "單卡版"}}
    cases = ((" (work 紅、peace 藍)", good), (" (單卡蓋過主題)", per_card),
             (" (只有單卡)", {"cards": per_card["cards"]}),
             (" (圖檔不存在)", {"work": {"image": "assets/art-missing.png", "alt": "測試用主題圖", "edition": ed}}),
             (" (沒有 blessing-art.json)", None))
    for label, art in cases:
        with tempfile.TemporaryDirectory() as tmp:
            for d in ("site", "data"):
                shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d))
            os.makedirs(os.path.join(tmp, "tests"))
            shutil.copy(os.path.join(ROOT, "tests", "blessing_probe.html"), os.path.join(tmp, "tests"))
            af = os.path.join(tmp, "data", "blessing-art.json")
            if art is None:
                if os.path.exists(af):
                    os.remove(af)
            else:
                json.dump(art, open(af, "w", encoding="utf-8"), ensure_ascii=False)
            open(os.path.join(tmp, "site", "assets", "art-work.png"), "wb").write(solid_png(600, 900, (255, 0, 0)))
            open(os.path.join(tmp, "site", "assets", "art-peace.png"), "wb").write(solid_png(600, 900, (0, 0, 255)))
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
            with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                port = srv.server_address[1]
                if art and "cards" in art:
                    one = blessing_state(port, "blessing.html?card=work-01")
                    other = blessing_state(port, "blessing.html?card=work-02")
                    own = art["cards"]["work-01"]
                    a = one.get("art") or {}
                    b = other.get("art") or {}
                    check(f"blessart{label}：單卡圖優先於主題圖、下載連結取原單卡圖",
                          a.get("shown") and a.get("src") == own["image"] and a.get("dlHref") == own["image"] and a.get("artAttr") == own["image"])
                    check(f"blessart{label}：同主題另一張卡回退主題圖、無主題時純文字",
                          (b.get("src") == art["work"]["image"]) if "work" in art else (not b.get("shown") and not b.get("dlShown") and not b.get("artAttr")))
                    bbytes = open(os.path.join(tmp, "site", own["image"]), "rb").read()
                    try:
                        got = urllib.request.urlopen(f"http://127.0.0.1:{port}/site/{a.get('dlHref', '')}", timeout=10).read()
                    except Exception:
                        got = b""
                    check(f"blessart{label}：單卡直接下載原檔位元組相同", got == bbytes)
                    errs = one.get("errors", []) + other.get("errors", [])
                    check(f"blessart{label}：兩張卡都沒有 JavaScript 錯誤", not errs, str(errs[:2]))
                else:
                    blessart_render(port, tmp, label, art)
                srv.shutdown()


def blessart_render(port, root, label, art):
    work = blessing_state(port, "blessing.html?card=work-01")
    rest = blessing_state(port, "blessing.html?card=rest-01")
    swap = blessing_state(port, "blessing.html?card=work-01", act=[{"click": '#theme-tabs button[data-theme="peace"]'}])
    narrow = blessing_state(port, "blessing.html?card=work-01", width=320)
    if not work.get("card"):
        check(f"blessart{label}：blessing.html?card=work-01 有輸出", False, "探測頁沒有輸出")
        return
    a, ra, sa, na = work.get("art") or {}, rest.get("art") or {}, swap.get("art") or {}, narrow.get("art") or {}
    px, rpx, spx = work.get("canvasPixels") or {}, rest.get("canvasPixels") or {}, swap.get("canvasPixels") or {}
    entry = (art or {}).get("work")
    usable = bool(entry) and entry["image"] != "assets/art-missing.png"
    if usable:
        ent = art["work"]
        ext = os.path.splitext(ent["image"])[1]
        check(f"blessart{label}：有圖的主題（work）卡片頂部顯示 .card-art，img 的 src／alt 等於設定，圖真的載入", a.get("shown") is True and a.get("src") == ent["image"] and a.get("alt") == ent["alt"] and a.get("natural", 0) >= 600, json.dumps(a, ensure_ascii=False)[:300])
        check(f"blessart{label}：版次徽章 .card-edition 顯示設定的版次文字", a.get("editionShown") is True and ent["edition"] in a.get("edition", ""), a.get("edition", ""))
        check(f"blessart{label}：#blessing-card 的 data-art 等於該主題的圖片路徑", a.get("artAttr") == ent["image"], str(a.get("artAttr")))
        check(f"blessart{label}：「下載經文圖」a#art-download 顯示，href 是原圖路徑，download 檔名是 blessing-work-…{ext}", a.get("dlTag") == "A" and a.get("dlShown") is True and a.get("dlHref") == ent["image"]
              and (a.get("dlName") or "").startswith("blessing-work") and (a.get("dlName") or "").endswith(ext), json.dumps({k: a.get(k) for k in ("dlTag", "dlShown", "dlHref", "dlName")}, ensure_ascii=False))
        src_bytes = open(os.path.join(root, "site", ent["image"]), "rb").read()
        try:
            got = urllib.request.urlopen(f"http://127.0.0.1:{port}/site/{a.get('dlHref', '')}", timeout=10).read()
        except Exception as e:
            got = str(e).encode()
        check(f"blessart{label}：下載連結抓到的檔案與上傳的原圖位元組相同（不重新壓縮）", got == src_bytes)
        total = (work.get("canvasW", 0) or 1) * (work.get("canvasH", 0) or 1)
        check(f"blessart{label}：下載圖片（canvas）把主題圖合成進去（紅色像素 ≥ 10%），文字仍在，直式比原本更高", px.get("red", 0) >= total * 0.10 and px.get("dark", 0) > 500 and work.get("canvasH", 0) > 900, json.dumps({"canvasPixels": px, "H": work.get("canvasH")}))
        fr = a.get("frame") or {}
        check(f"blessart{label}：金框只在圖檔裡（生成時畫好），頁面不另加框（.card-art 沒有邊框、沒有漸層），三處看到的是同一張圖", fr.get("border", 9) == 0 and "gradient" not in (fr.get("bg", "") + fr.get("borderImage", "")), json.dumps(fr))
        check(f"blessart{label}：下載圖片（canvas）不另畫框（測試圖是純紅，canvas 不該出現金色）", px.get("gold", 0) < 500, json.dumps(px))
        peace = (art or {}).get("peace")
        if peace:
            check(f"blessart{label}：切換到有圖的另一主題（peace）會換圖，canvas 也跟著換成藍色", sa.get("shown") is True and sa.get("src") == peace["image"] and spx.get("blue", 0) >= total * 0.10 and spx.get("red", 0) < total * 0.01, json.dumps(sa, ensure_ascii=False)[:300])
        check(f"blessart{label}：320px 寬時畫框在視窗內、頁面沒有水平溢出", bool(na.get("box")) and na["box"]["right"] <= na.get("vw", 0) and na.get("scrollW", 9999) <= na.get("vw", 0), json.dumps(na.get("box")))
    else:
        check(f"blessart{label}：沒有可用的圖時，work 卡片維持純文字（沒有 .card-art、沒有版次、#art-download 隱藏、data-art 為空）", not a.get("shown") and not a.get("editionShown") and not a.get("dlShown") and not a.get("artAttr"), json.dumps(a, ensure_ascii=False)[:300])
        check(f"blessart{label}：沒有可用的圖時，下載圖片照舊只畫文字（底色 #fbf7ee、沒有紅色像素、文字在）", px.get("corner") == [251, 247, 238] and px.get("red", 0) == 0 and px.get("dark", 0) > 500, json.dumps(px))
    check(f"blessart{label}：沒有設定圖的主題（rest）維持純文字卡", not ra.get("shown") and not ra.get("editionShown") and not ra.get("dlShown") and not ra.get("artAttr") and (rpx.get("red", 0) == 0 and rpx.get("blue", 0) == 0 and rpx.get("gold", 0) < 500), json.dumps(ra, ensure_ascii=False)[:300])
    errs = work.get("errors", []) + rest.get("errors", []) + swap.get("errors", [])
    check(f"blessart{label}：沒有 JavaScript 錯誤", not errs, "；".join(errs[:3]))


# ---------- devotional：每日禱讀（site/devotional.html + site/devotional.js + data/devotional.json）
# 鐵則：這個段落不寫死任何經文。測試用的 data/devotional.json 只在 /tmp 的暫存副本裡產生，
# 內容只有 id、日期、標題、出處文字、ranges 與佔位內文；預期的經文一律由 Python 在測試時
# 依 ranges 從 data/{mat,mrk,luk,jhn}.json 動態讀出，再與 headless Chrome 渲染後的結果逐節比對。
DEVOTIONAL_TITLES = {"MAT": "mat", "MRK": "mrk", "LUK": "luk", "JHN": "jhn"}
DEVOTIONAL_MSG_NONE = "此日期尚無已審核的禱讀內容。"
DEVOTIONAL_MSG_DATA = "禱讀資料載入失敗，請稍後再試。"
DEVOTIONAL_MSG_VERSE = "經文載入失敗，請稍後再試。"

DEVOTIONAL_PROBE = """<!doctype html>
<meta charset="utf-8">
<!-- 由 tests/site_checks.py 寫進 /tmp 的暫存副本後使用（不要放進工作樹）。
     在 iframe 裡開啟 ?u=<頁面>，可帶 ?acts=<[{setdate:"YYYY-MM-DD"}]> 換日期、?widths=320,375 依序量多種寬度。
     寫入一行 JSON：PROBE {"cases":[{status,nodes,dateValue,dateMax,nav,home,ext,scrollW,clientW,over,width}],"errors":[..]} -->
<pre id="out">running</pre>
<script>
const qs = new URLSearchParams(location.search);
const ACTS = JSON.parse(qs.get("acts") || "[]");
const WIDTHS = (qs.get("widths") || "").split(",").filter(Boolean).map(Number);
const errors = [];
const sleep = t => new Promise(r => setTimeout(r, t));
window.addEventListener("message", e => {
  if (e.origin === location.origin && e.data && e.data.kind === "devotional-probe-error") {
    errors.push(e.data.type + ": " + e.data.message);
  }
});
async function openFrame(url, w, h) {
  const f = document.createElement("iframe");
  f.style.cssText = "width:" + w + "px;height:" + h + "px;border:0;display:block";
  const loaded = new Promise(resolve => f.addEventListener("load", resolve, {once: true}));
  f.src = url;
  document.body.appendChild(f);
  await loaded;
  // 等頁面把「正在載入…」換成最終狀態（最長 8 秒）
  for (let i = 0; i < 80; i++) {
    await sleep(100);
    const s = f.contentDocument.getElementById("reading-status");
    if (s && s.textContent.indexOf("正在") !== 0) break;
  }
  await sleep(200);
  return f;
}
function snapshot(f, w) {
  const d = f.contentDocument, win = f.contentWindow, read = d.getElementById("reading");
  const leaves = read ? [...read.querySelectorAll("*")].filter(e => !e.querySelector("*")).map(e => ({tag: e.tagName.toLowerCase(), text: e.textContent})) : [];
  const date = d.getElementById("reading-date") || {};
  const cw = d.documentElement.clientWidth;
  // 第三輪 C：當天標題（h2）必須比分段標題（h3）大，而且用明體
  const h2 = read ? read.querySelector("h2") : null, h3 = read ? read.querySelector("h3") : null;
  const px = e => e ? parseFloat(win.getComputedStyle(e).fontSize) : null;
  const ff = e => e ? win.getComputedStyle(e).fontFamily : "";
  return {status: (d.getElementById("reading-status") || {}).textContent || "", nodes: leaves,
          headings: leaves.filter(n => /^h\\d$/.test(n.tag)).map(n => n.text),
          h2Px: px(h2), h3Px: px(h3), h2Font: ff(h2), h3Font: ff(h3),
          dateValue: date.value || "", dateMax: date.max || "",
          nav: [...d.querySelectorAll("#nav a, .dock a")].map(a => ({href: a.getAttribute("href"), text: a.textContent.trim()})),
          navActive: [...d.querySelectorAll("#nav a, .dock a")].filter(a => a.getAttribute("aria-current") === "page" || a.classList.contains("active")).length,
          home: !!d.querySelector('a[href="home.html"]'),
          ext: win.performance.getEntriesByType("resource").map(r => r.name).filter(u => u.indexOf(location.origin) !== 0 && !/^data:/.test(u)),
          scrollW: d.documentElement.scrollWidth, clientW: cw,
          over: [...d.querySelectorAll("#reading *, #reading")].filter(e => e.getBoundingClientRect().right > cw + 1).map(e => e.tagName.toLowerCase()).slice(0, 6),
          width: w};
}
(async () => {
  const url = qs.get("u"), cases = [];
  if (WIDTHS.length) {
    for (const w of WIDTHS) { cases.push(snapshot(await openFrame(url, w, 900), w)); }
  } else {
    const f = await openFrame(url, Number(qs.get("w") || 1000), 1400);
    cases.push(snapshot(f, Number(qs.get("w") || 1000)));
    for (const a of ACTS) {
      const el = f.contentDocument.getElementById("reading-date");
      if (el && a.setdate) { el.value = a.setdate; el.dispatchEvent(new Event("change", {bubbles: true})); }
      await sleep(1200);
      cases.push(snapshot(f, Number(qs.get("w") || 1000)));
    }
  }
  await sleep(50);
  document.getElementById("out").textContent = "PROBE " + JSON.stringify({cases, errors});
})();
</script>
"""


def devotional_today():
    """台灣（Asia/Taipei，無日光節約）今天的 YYYY-MM-DD，以及昨天。"""
    tw = datetime.timezone(datetime.timedelta(hours=8))
    today = datetime.datetime.now(tw).date()
    return today.isoformat(), (today - datetime.timedelta(days=1)).isoformat()


def devotional_fake(today, yday):
    """暫存副本用的假資料：只有 id／日期／標題／出處文字／ranges＋佔位內文，一個經文字句都不寫。"""
    def rng(book, ch, vend, ch2=None, vend2=None):
        return {"book": book, "start_chapter": ch, "start_verse": 1, "end_chapter": ch2 or ch, "end_verse": vend2 or vend}
    return [
        {"id": 1, "devotional_date": today, "title": "測試禱讀標題甲", "scripture_reference": "測試出處甲 MAT 5",
         "ranges": [rng("MAT", 5, 12)], "summary": "測試默想段落甲", "reflection": "測試反思問題甲", "prayer": "測試禱告內容甲"},
        {"id": 2, "devotional_date": yday, "title": "測試禱讀標題乙", "scripture_reference": "測試出處乙 LUK 1＋JHN 3",
         "ranges": [rng("LUK", 1, 4), rng("JHN", 3, 3)],
         "summary": "測試默想段落乙", "reflection": "測試反思問題乙", "prayer": "測試禱告內容乙"},
    ]


def devotional_expected(entry, books):
    """依 ranges 從四福音 JSON 算出預期經文：每節「章:節 文字」，合併節「章:節–末節 文字」。"""
    if not isinstance(entry, dict) or not isinstance(entry.get("ranges"), list) or not entry["ranges"]:
        return None
    out = []
    for r in entry["ranges"]:
        if not isinstance(r, dict):
            return None
        key = DEVOTIONAL_TITLES.get(r.get("book"))
        start_ch = r.get("start_chapter")
        start_v = r.get("start_verse")
        end_ch = r.get("end_chapter")
        end_v = r.get("end_verse")
        if (not key or any(type(n) is not int or n < 1 for n in (start_ch, start_v, end_ch, end_v))
                or end_ch < start_ch):
            return None
        chapters = books.get(key, [])
        start_data = next((ch for ch in chapters if ch["ch"] == start_ch), None)
        end_data = next((ch for ch in chapters if ch["ch"] == end_ch), None)
        contains = lambda ch, number: ch is not None and any(
            v["v"] <= number <= (v.get("end") or v["v"]) for v in ch["verses"])
        if not contains(start_data, start_v) or not contains(end_data, end_v):
            return None
        if start_ch == end_ch and start_v > end_v:
            return None
        selected = []
        for ch in chapters:
            if not start_ch <= ch["ch"] <= end_ch:
                continue
            for v in ch["verses"]:
                if ch["ch"] == start_ch and max(v["v"], v.get("end") or v["v"]) < start_v:
                    continue
                if ch["ch"] == end_ch and v["v"] > end_v:
                    continue
                label = f"{v['v']}–{v['end']}" if v.get("end") else str(v["v"])
                selected.append(f"{ch['ch']}:{label} {v['text']}")
        if not selected:
            return None
        out.extend(selected)
    return out or None


def devotional_scripture(case):
    """渲染結果裡「經文」小標之後、下一個小標之前的段落文字（不假設有沒有外層容器）。"""
    nodes, i = case.get("nodes") or [], 0
    while i < len(nodes) and not (nodes[i]["tag"].startswith("h") and nodes[i]["text"].strip() == "經文"):
        i += 1
    got = []
    for n in nodes[i + 1:]:
        if n["tag"].startswith("h"):
            break
        if n["tag"] == "p":
            got.append(n["text"])
    return got


def devotional_state(port, acts=None, widths=None):
    """用暫存副本裡的探測頁渲染 devotional.html，回傳 PROBE 的 JSON。"""
    q = "u=" + urllib.parse.quote("../site/devotional.html", safe="")
    if acts:
        q += "&acts=" + urllib.parse.quote(json.dumps(acts))
    if widths:
        q += "&widths=" + ",".join(str(w) for w in widths)
    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=25000",
                               f"--user-data-dir={profile}", "--dump-dom", f"http://127.0.0.1:{port}/tests/devotional_probe.html?{q}"],
                              capture_output=True, text=True, timeout=120)
    out = proc.stdout
    out = re.sub(r"<[^>]+>", "", out)
    found = re.findall(r"PROBE (\{[^\n]*\})\s*$", out, re.M)
    try:
        if found:
            return json.loads(html.unescape(found[-1]))
    except ValueError:
        pass
    if not found:
        diagnostic = (proc.stderr or proc.stdout or "headless Chrome returned no DOM").strip()
        return {"_probe_error": diagnostic[-1200:]}
    return {"_probe_error": "PROBE JSON could not be parsed"}


def devotional_render(port, root, label=""):
    """對暫存副本（含假 devotional.json）跑一遍禱讀頁的渲染檢查。"""
    books = {k: json.load(open(os.path.join(root, "data", k + ".json"), encoding="utf-8"))["chapters"] for k, _ in BOOKS}
    fake = json.load(open(os.path.join(root, "data", "devotional.json"), encoding="utf-8"))
    by_date = {e["devotional_date"]: e for e in fake}
    today, yday = devotional_today()
    nodata = (datetime.date.fromisoformat(today) - datetime.timedelta(days=2)).isoformat()
    st = devotional_state(port, acts=[{"setdate": yday}, {"setdate": nodata}])
    cases, errs = st.get("cases") or [], st.get("errors") or []
    if len(cases) < 3:
        check(f"devotional{label}：暫存副本的禱讀頁能渲染並回報狀態", False,
              f"探測頁只拿到 {len(cases)} 組結果；{st.get('_probe_error', '')[:900]}")
        return
    a, b, c = cases[0], cases[1], cases[2]
    entry, yentry = by_date[today], by_date[yday]
    want, got = devotional_expected(entry, books), devotional_scripture(a)
    nodes = a.get("nodes") or []

    check(f"devotional{label}：有資料的日期顯示 h2 標題、scripture_reference 段落與「經文」小標",
          len(nodes) > 1 and nodes[0]["tag"] == "h2" and nodes[0]["text"] == entry["title"]
          and nodes[1]["tag"] == "p" and nodes[1]["text"] == entry["scripture_reference"]
          and "經文" in (a.get("headings") or []),
          json.dumps(nodes[:3], ensure_ascii=False)[:260])
    diff = next((i for i in range(max(len(want), len(got))) if (got[i] if i < len(got) else None) != (want[i] if i < len(want) else None)), None)
    if not want or got == want:
        verse_detail = "" if want else "暫存副本的測試範圍算不出預期經文"
    else:
        verse_detail = f"預期 {len(want)} 節、實際 {len(got)} 節"
        if diff is not None:
            should = want[diff].split(" ")[0] if diff < len(want) else "（這節不該出現）"
            actual = got[diff].split(" ")[0] if diff < len(got) else "（少了這一節）"
            verse_detail += f"；第一處不同在第 {diff + 1} 節：應為 {should}、實際是 {actual}"
    check(f"devotional{label}：渲染出的經文節數與內容完全等於四福音 JSON 該範圍（{entry['ranges'][0]['book']} {len(want)} 節，逐節比對）",
          bool(want) and got == want, verse_detail)
    h3 = [n["text"] for n in nodes if n["tag"] == "h3"]
    body = [n["text"] for n in nodes if n["tag"] == "p"]
    check(f"devotional{label}：「默想」「反思」「禱告」三段標題與對應內容都渲染出來",
          all(t in h3 for t in ("默想", "反思", "禱告")) and all(entry[k] in body for k in ("summary", "reflection", "prayer")),
          json.dumps({"h3": h3}, ensure_ascii=False)[:200])
    # 第三輪 C：主次要分明——當天標題（h2）最大且用明體，段落標題（h3）次之
    check(f"devotional{label}：當天標題（h2）字級大於段落標題（h3）字級，且當天標題使用明體",
          bool(a.get("h2Px")) and bool(a.get("h3Px")) and a["h2Px"] > a["h3Px"]
          and "serif" in (a.get("h2Font") or "").lower(),
          json.dumps({k: a.get(k) for k in ("h2Px", "h3Px", "h2Font", "h3Font")}, ensure_ascii=False)[:300])
    check(f"devotional{label}：內容渲染成功時 #reading-status 是空字串", a.get("status") == "", repr(a.get("status"))[:120])
    check(f"devotional{label}：#reading-date 的預設值與 max 都是台灣時間今天 {today}",
          a.get("dateValue") == today and a.get("dateMax") == today, json.dumps({"value": a.get("dateValue"), "max": a.get("dateMax")}))

    want2, got2 = devotional_expected(yentry, books), devotional_scripture(b)
    check(f"devotional{label}：把日期換到另一個有資料的日期（{yday}）會重新渲染該日內容與標題",
          got2 == want2 and yentry["title"] in (b.get("headings") or []) and b.get("status") == "",
          f"預期 {len(want2)} 節、實際 {len(got2)} 節；小標：{b.get('headings')[:3]}")
    merged = [v.split(" ")[0] for v in want2 if "–" in v.split(" ")[0]]
    check(f"devotional{label}：合併節以「章:節–末節 文字」呈現，且測試範圍真的涵蓋合併節（{len(merged)} 處）",
          bool(merged) and all(v in got2 for v in want2 if "–" in v.split(" ")[0]),
          json.dumps({"預期合併節": merged, "渲染有": [v.split(' ')[0] for v in got2 if '–' in v.split(' ')[0]]}, ensure_ascii=False)[:260])
    check(f"devotional{label}：換到沒有資料的日期會清空 #reading 並顯示「{DEVOTIONAL_MSG_NONE}」",
          c.get("status") == DEVOTIONAL_MSG_NONE and not (c.get("nodes") or []),
          json.dumps({"status": c.get("status"), "節點數": len(c.get("nodes") or [])}, ensure_ascii=False)[:200])
    check(f"devotional{label}：導覽列有五項（首頁、目錄、禱讀、抽卡、搜尋）、恰一項標成目前頁且有回首頁連結",
          [n["text"] for n in a.get("nav") or []] == [t for t, _ in NAV5]
          and [n["href"] for n in a.get("nav") or []] == [h for _, h in NAV5]
          and a.get("navActive") == 1 and a.get("home"),
          json.dumps({"nav": a.get("nav"), "active": a.get("navActive")}, ensure_ascii=False)[:260])
    check(f"devotional{label}：頁面沒有載入外部資源", not a.get("ext"), "；".join(a.get("ext") or [])[:200])
    check(f"devotional{label}：沒有未捕捉的 JavaScript 錯誤（含切換日期）", not errs, "；".join(errs[:3]))


def devotional_static():
    """源碼層的多個鐵則：頁面需要的元素、不寫死經文、提示訊息用繁體中文。"""
    page = os.path.join(SITE, "devotional.html")
    js = os.path.join(SITE, "devotional.js")
    if not (os.path.exists(page) and os.path.exists(js)):
        check("devotional：site/devotional.html 與 site/devotional.js 存在", False, "找不到檔案")
        return
    html_src = open(page, encoding="utf-8").read()
    js_src = open(js, encoding="utf-8").read()
    missing = [i for i in ('id="reading-date"', 'id="reading-status"', 'id="reading"', 'id="nav"') if i not in html_src]
    check("devotional：devotional.html 有日期選擇、狀態區、內容區與導覽列，且回首頁連結指向 home.html",
          not missing and 'href="home.html"' in html_src, "、".join(missing))
    check("devotional：devotional.html 只載入站內的 app.js 與 devotional.js",
          re.findall(r'src="([^"]+)"', html_src) == ["app.js", "devotional.js"], str(re.findall(r'src="([^"]+)"', html_src)))

    verses, grams = {}, set()
    for k, _ in BOOKS:
        for ch in json.load(open(os.path.join(ROOT, "data", k + ".json"), encoding="utf-8"))["chapters"]:
            for v in ch["verses"]:
                verses[(k, ch["ch"], v["v"])] = v["text"]
    for t in verses.values():
        s = cjk(t)
        grams.update(s[i:i + 8] for i in range(len(s) - 7))

    def hits(name, src):
        s = cjk(re.sub(r"<[^>]+>", " ", src))
        return sorted({s[i:i + 8] for i in range(len(s) - 7) if s[i:i + 8] in grams})

    check("devotional：devotional.html 與 devotional.js 都沒有寫死經文（沒有任何連續 8 字與和合本經文相同）",
          not hits("h", html_src) and not hits("j", js_src),
          "；".join((hits("h", html_src) + hits("j", js_src))[:3]))
    mine = re.search(r"# ---------- devotional：.*?(?=\ndef rendering|\Z)", open(__file__, encoding="utf-8").read(), re.S)
    check("devotional：site_checks.py 的禱讀檢查本身也沒有寫死經文（鐵則自我要求）",
          mine and not hits("self", mine.group(0)), "；".join(hits("self", mine.group(0))[:3]) if mine else "找不到該段落")
    need = [DEVOTIONAL_MSG_NONE, DEVOTIONAL_MSG_DATA, DEVOTIONAL_MSG_VERSE]
    check("devotional：三種狀態提示都寫在 devotional.js 且為繁體中文",
          all(m in js_src for m in need) and not [w for w in SIMPLIFIED if w in js_src],
          "、".join(m for m in need if m not in js_src) or "".join(w for w in SIMPLIFIED if w in js_src))
    check("devotional：devotional.js 的日期預設取台灣時間（Asia/Taipei）並用 date.max 限制在今天",
          "Asia/Taipei" in js_src and re.search(r"date\.max\s*=", js_src) is not None and "'change', display" in js_src.replace('"', "'"))
    path = os.path.join(ROOT, "data", "devotional.json")
    if os.path.exists(path):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError) as e:
            d = None
            check("devotional：data/devotional.json 是合法 JSON 陣列", False, str(e))
        if d is not None:
            books = {k: json.load(open(os.path.join(ROOT, "data", k + ".json"), encoding="utf-8"))["chapters"] for k, _ in BOOKS}
            bad, nofound, dates = [], [], []
            if isinstance(d, list):
                for ent in d:
                    if not isinstance(ent, dict):
                        bad.append("非物件項目")
                        continue
                    date = ent.get("devotional_date")
                    try:
                        valid_date = isinstance(date, str) and datetime.date.fromisoformat(date).isoformat() == date
                    except ValueError:
                        valid_date = False
                    if not (ent.get("id") is not None and valid_date and ent.get("title")
                            and ent.get("scripture_reference") and isinstance(ent.get("ranges"), list) and ent["ranges"]):
                        bad.append(ent.get("id"))
                    dates.append(date)
                    if not devotional_expected(ent, books):
                        nofound.append(ent.get("id"))
            else:
                bad.append("不是陣列")
            check("devotional：data/devotional.json 是合法 JSON 陣列", isinstance(d, list), "不是陣列" if not isinstance(d, list) else "")
            check("devotional：每筆資料有 id、日期、標題、出處與 ranges，書卷只限四福音且日期不重複",
                  isinstance(d, list) and not bad and len(dates) == len(set(dates)), "、".join(str(x) for x in bad[:6]))
            check("devotional：每筆 ranges 都能在四福音資料裡找到經文", isinstance(d, list) and not nofound,
                  "、".join(str(x) for x in nofound[:6]))


def devotional_variants():
    """在 /tmp 的暫存副本上跑全部禱讀檢查：正常渲染、四種視窗寬度，以及空陣列／404／壞 JSON／壞範圍等情境。"""
    import shutil
    if not CHROME:
        check("devotional：找不到 Chrome，無法渲染檢查", False)
        return
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    today, yday = devotional_today()
    dfake = os.path.join(ROOT, "data", "devotional.json")
    keep = open(dfake, encoding="utf-8").read() if os.path.exists(dfake) else None
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(os.path.join(ROOT, "site"), os.path.join(tmp, "site"))
        os.makedirs(os.path.join(tmp, "data"))
        for name in ("mat", "mrk", "luk", "jhn", "zone-music", "home", "blessing", "blessing-art"):
            shutil.copy(os.path.join(ROOT, "data", name + ".json"), os.path.join(tmp, "data", name + ".json"))
        os.makedirs(os.path.join(tmp, "tests"))
        open(os.path.join(tmp, "tests", "devotional_probe.html"), "w", encoding="utf-8").write(DEVOTIONAL_PROBE)
        page_path = os.path.join(tmp, "site", "devotional.html")
        page_html = open(page_path, encoding="utf-8").read()
        marker = '<script src="app.js"></script>'
        instrument = '''<script>
(() => {
  const send = (type, message) => {
    try { parent.postMessage({kind: "devotional-probe-error", type, message: String(message)}, location.origin); } catch (e) {}
  };
  addEventListener("error", e => send("pageerror", e.message || e.error || "window error"));
  addEventListener("unhandledrejection", e => send("unhandledrejection", e.reason && e.reason.stack || e.reason));
  const original = console.error.bind(console);
  console.error = (...args) => { send("console.error", args.join(" ")); original(...args); };
})();
</script>\n'''
        if page_html.count(marker) != 1:
            check("devotional：能在頁面腳本執行前安裝錯誤探測器", False, "找不到唯一的 app.js 標記")
            return
        open(page_path, "w", encoding="utf-8").write(page_html.replace(marker, instrument + marker, 1))
        zf = os.path.join(tmp, "data", "devotional.json")
        json.dump(devotional_fake(today, yday), open(zf, "w", encoding="utf-8"), ensure_ascii=False)
        handler = functools.partial(RangeHandler, directory=tmp)
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            port = srv.server_address[1]
            devotional_render(port, tmp)
            for w in (320, 375, 768, 1440):
                probe = devotional_state(port, widths=[w])
                case = ((probe.get("cases") or [{}])[0])
                rendered = len(devotional_scripture(case)) > 0
                check(f"devotional：{w}px 有渲染禱讀內容時不水平溢出（scrollWidth {case.get('scrollW')} ≤ clientWidth {case.get('clientW')}）",
                      rendered and (case.get("scrollW") or 0) <= (case.get("clientW") or 0),
                      json.dumps({"rendered": rendered, "over": case.get("over")}, ensure_ascii=False)[:200])
                check(f"devotional：{w}px 渲染沒有 Console／pageerror JavaScript 錯誤",
                      not probe.get("errors"), "；".join(probe.get("errors") or [])[:200])
            # 各種異常情境：每次改寫暫存副本的 devotional.json 再渲染一次
            for label, payload, want in (
                    ("空陣列", "[]", DEVOTIONAL_MSG_NONE),
                    ("檔案不存在（HTTP 404）", None, DEVOTIONAL_MSG_NONE),
                    ("不是合法 JSON", "{這不是 JSON", DEVOTIONAL_MSG_DATA),
                    ("是非陣列的物件", "{}", DEVOTIONAL_MSG_DATA)):
                if payload is None:
                    os.remove(zf)
                else:
                    open(zf, "w", encoding="utf-8").write(payload)
                probe = devotional_state(port)
                case = (probe.get("cases") or [{}])[0]
                check(f"devotional：devotional.json {label}時顯示「{want}」，且內容區是空的",
                      case.get("status") == want and not (case.get("nodes") or []),
                      json.dumps({"status": case.get("status"), "節點數": len(case.get("nodes") or [])}, ensure_ascii=False)[:200])
                check(f"devotional：devotional.json {label}時沒有 Console／pageerror JavaScript 錯誤",
                      not probe.get("errors"), "；".join(probe.get("errors") or [])[:200])
            bad = [{"id": 9, "devotional_date": today, "title": "測試不支援的書卷", "scripture_reference": "測試出處",
                    "ranges": [{"book": "ACT", "start_chapter": 2, "start_verse": 1, "end_chapter": 2, "end_verse": 5}],
                    "summary": "測試默想段落", "reflection": "測試反思問題", "prayer": "測試禱告內容"},
                   {"id": 10, "devotional_date": yday, "title": "測試找不到經文的範圍", "scripture_reference": "測試出處",
                    "ranges": [{"book": "MAT", "start_chapter": 99, "start_verse": 1, "end_chapter": 99, "end_verse": 2}],
                    "summary": "測試默想段落", "reflection": "測試反思問題", "prayer": "測試禱告內容"}]
            json.dump(bad, open(zf, "w", encoding="utf-8"), ensure_ascii=False)
            probe = devotional_state(port)
            case = (probe.get("cases") or [{}])[0]
            check(f"devotional：範圍書卷不支援時顯示「{DEVOTIONAL_MSG_VERSE}」且內容區是空的",
                  case.get("status") == DEVOTIONAL_MSG_VERSE and not (case.get("nodes") or []),
                  json.dumps({"status": case.get("status")}, ensure_ascii=False))
            check("devotional：範圍書卷不支援時沒有 Console／pageerror JavaScript 錯誤",
                  not probe.get("errors"), "；".join(probe.get("errors") or [])[:200])
            probe = devotional_state(port, acts=[{"setdate": yday}])
            pair = probe.get("cases") or [{}, {}]
            c2 = pair[1] if len(pair) > 1 else {}
            check(f"devotional：範圍在四福音資料裡找不到經文時顯示「{DEVOTIONAL_MSG_VERSE}」",
                  c2.get("status") == DEVOTIONAL_MSG_VERSE and not (c2.get("nodes") or []),
                  json.dumps({"status": c2.get("status")}, ensure_ascii=False))
            check("devotional：範圍在四福音資料裡找不到經文時沒有 Console／pageerror JavaScript 錯誤",
                  not probe.get("errors"), "；".join(probe.get("errors") or [])[:200])
            srv.shutdown()
    check("devotional：正式 data/devotional.json 沒有被檢查改動（假資料只存在 /tmp 副本）",
          keep == (open(dfake, encoding="utf-8").read() if os.path.exists(dfake) else None))


# ---------- restyle：2026-11 改版（金色飛鷹、底部膠囊導覽列、主視覺分離、便當格入口、微互動）
# 依據只有 design/sample-2026-11.html（不可改它）＋ logs/herdr-dispatch/brief-20261113-restyle.md。
# 這一組是「先寫客觀檢查」：頁面還沒改之前會不通過是預期的，檢查本身只準一個事實——數值與結構要跟樣本一致。

def jpeg_size(path):
    """回傳 (寬, 高)。優先用 PIL；沒有就自己讀 JPEG 的 SOF 標記。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.width, im.height
    except Exception:
        pass
    with open(path, "rb") as f:
        data = f.read()
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return 0, 0


def restyle_assets():
    """飛鷹正式圖：尺寸／檔案大小／授權登記，以及「路徑只由共用層提供」。"""
    lic_path = os.path.join(ROOT, "ASSETS-LICENSE.md")
    lic = open(lic_path, encoding="utf-8").read() if os.path.exists(lic_path) else ""
    bad, rows = [], []
    for name in ("eagle-A.jpg", "eagle-B.jpg"):
        p = os.path.join(SITE, "assets", name)
        if not os.path.exists(p):
            bad.append(f"{name} 不存在")
            continue
        w, h = jpeg_size(p)
        mb = os.path.getsize(p) / 1024 / 1024
        shape_ok = (w, h) == (1792, 2400) or (max(w, h) >= 1700 and abs(w / h - 0.75) < 0.03)
        if not shape_ok:
            bad.append(f"{name} 尺寸 {w}×{h}（要 1792×2400 或長邊≥1700 且 3:4）")
        if mb > 3:
            bad.append(f"{name} {mb:.2f} MB > 3 MB")
        row = [l for l in lic.splitlines() if name in l and l.strip().startswith("|")]
        if not row:
            bad.append(f"{name} 沒有登記在 ASSETS-LICENSE.md")
        elif not re.search(r"AGY|Google Imagen 3", row[0]):
            bad.append(f"{name} 的登記列沒寫生成來源（AGY／Google Imagen 3）")
        rows.append({"name": name, "w": w, "h": h, "mb": round(mb, 2), "lic": bool(row)})
    check("eagle-A.jpg 與 eagle-B.jpg 正式圖：存在、1792×2400（或長邊≥1700 且 3:4）、≤3MB，並在 ASSETS-LICENSE.md 登記生成來源",
          not bad, "；".join(bad) or json.dumps(rows, ensure_ascii=False))

    css = open(os.path.join(SITE, "style.css"), encoding="utf-8").read() if os.path.exists(os.path.join(SITE, "style.css")) else ""
    app = open(os.path.join(SITE, "app.js"), encoding="utf-8").read() if os.path.exists(os.path.join(SITE, "app.js")) else ""
    pages = {os.path.basename(p): open(p, encoding="utf-8").read() for p in site_files(".html")}
    in_pages = sorted({f for s in pages.values() for f in re.findall(r"eagle-[AB]\.(?:jpg|jpeg|png|webp)", s, re.I)})
    in_shared = sorted({f for f in re.findall(r"eagle-[AB]\.(?:jpg|jpeg|png|webp)", css + app, re.I)})
    check("改版素材：飛鷹圖路徑只出現在共用層（style.css 或 app.js），前台頁面不重複寫死檔名",
          len(in_shared) >= 1 and not in_pages,
          f"共用層：{in_shared or '無'}；頁面裡寫死：{in_pages or '無'}")


def restyle_shared():
    """style.css／app.js 的源碼層：配色 token、光色、圓角、膠囊、底部導覽列五項、三種狀態的圖示與 reduced-motion。"""
    css = open(os.path.join(SITE, "style.css"), encoding="utf-8").read() if os.path.exists(os.path.join(SITE, "style.css")) else ""
    app = open(os.path.join(SITE, "app.js"), encoding="utf-8").read() if os.path.exists(os.path.join(SITE, "app.js")) else ""
    check("style.css 有樣本的光色 token（--sunlight: #fdf2da），首頁經文用它當文字色",
          re.search(r"--sunlight\s*:\s*#fdf2da", css, re.I) is not None, "找不到 --sunlight")
    check("style.css 用樣本的大圓角（--r-lg 28px、--r-md 18px）與明體／黑體兩套系統字型變數",
          re.search(r"--r-lg\s*:\s*28px", css) is not None and re.search(r"--r-md\s*:\s*18px", css) is not None
          and "--display" in css and "--body" in css,
          "、".join(x for x, ok in (("--r-lg", "--r-lg" in css), ("--r-md", "--r-md" in css), ("--display", "--display" in css), ("--body", "--body" in css)) if not ok))
    nav = re.search(r"function nav\(active\)(.*?)\n  \}", app, re.S)
    links = re.findall(r'\{\s*href:\s*"([^"]+)",\s*label:\s*"([^"]+)"', nav.group(1)) if nav else []
    check("app.js 的共用導覽列是五項：首頁／目錄／禱讀／抽卡／搜尋，且 href 依序為 home／index／devotional／blessing／search",
          [l for _, l in links] == [t for t, _ in NAV5] and [h for h, _ in links] == [x for _, x in NAV5],
          json.dumps(links, ensure_ascii=False))
    check("app.js 在 nav() 裡用 aria-current=\"page\" 標目前頁（不是只有 .active，螢幕閱讀器才聽得到）",
          bool(nav) and "aria-current" in nav.group(1),
          "nav() 內部沒有 aria-current" if nav else "找不到 nav() 函式")
    check("style.css 有 @media (prefers-reduced-motion: reduce) 且把動畫關掉",
          "prefers-reduced-motion: reduce" in css and re.search(r"animation\s*:\s*none", css) is not None,
          "沒有 reduced-motion 區塊" if "prefers-reduced-motion: reduce" not in css else "區塊內找不到 animation: none")
    glyph = {m.group(1): m.group(2) for m in re.finditer(r'\.status\[data-state="(\w+)"\]::before\s*\{([^}]*)\}', css)}
    shapes = {"busy": bool(re.search(r"animation|border-right-color", glyph.get("busy", ""))) and "@keyframes" in css,
              "ok": "✓" in glyph.get("ok", ""), "fix": "!" in glyph.get("fix", "")}
    check("微互動：三種狀態在 style.css 各有不同圖示（處理中轉圈、已完成 ✓、待修正 !），不是只換顏色",
          all(k in glyph for k in ("busy", "ok", "fix")) and all(shapes.values()),
          json.dumps({"有定義": sorted(glyph), "圖示": shapes}, ensure_ascii=False))
    check("微互動：待修正時欄位是粗虛線（.find input[aria-invalid=true] 或同等的 border-style: dashed）",
          re.search(r"aria-invalid[^\n]*\{[^}]*dashed", css, re.S) is not None, "找不到 aria-invalid + dashed 的規則")
    missing = []
    for page in DOCK_PAGES:
        name = page.split("?")[0]
        src = open(os.path.join(SITE, name), encoding="utf-8").read() if os.path.exists(os.path.join(SITE, name)) else ""
        if not re.search(r'role="status"|aria-live', src):
            missing.append(name)
    check("每個前台頁面都有 role=status 或 aria-live 的回饋區（WCAG 2.2 4.1.3）", not missing, "、".join(missing))
    busy_src = []
    for name in ("index.html", "search.html", "home.html", "app.js", "search.js"):
        p = os.path.join(SITE, name)
        if os.path.exists(p) and re.search(r"aria-busy|data-state=\"busy\"|data-state = .busy.", open(p, encoding="utf-8").read()):
            busy_src.append(name)
    check("搜尋有「處理中」狀態（寫入 aria-busy 或 data-state=busy）", bool(busy_src), "各檔都找不到 busy 狀態的設定")


def restyle_render(port):
    """渲染層：底部導覽列（五項、觸控、不遮音樂鍵、不遮內容）、主視覺分離、便當格與扇形卡、搜尋三種狀態。"""
    for page in DOCK_PAGES:
        st = home_state(port, page=page)
        d = st.get("dock") or {}
        name = page.split("?")[0]
        if not d:
            check(f"restyle {name} 有底部導覽列可量測", False, "探測頁找不到 #nav／.dock")
            continue
        check(f"restyle {name}：導覽列恰好五項（首頁、目錄、禱讀、抽卡、搜尋）、恰有一項標為目前頁",
              d.get("count") == 5 and d.get("active") == 1 and [i["text"] for i in d.get("items", [])] == [t for t, _ in NAV5],
              json.dumps({"count": d.get("count"), "active": d.get("active"), "texts": [i["text"] for i in d.get("items", [])]}, ensure_ascii=False))
        check(f"restyle {name}：導覽列是 position: fixed 的浮動膠囊，每項觸控區 ≥44×44",
              d.get("fixed") and d.get("small", 1) == 0, json.dumps({"position": d.get("position"), "small": d.get("small"),
              "items": [(i["w"], i["h"]) for i in d.get("items", [])]}, ensure_ascii=False)[:220])
        check(f"restyle {name}：目前頁除了顏色還有粗體（font-weight ≥600）",
              any(i.get("active") and i.get("weight", 0) >= 600 for i in d.get("items", [])),
              json.dumps([i for i in d.get("items", []) if i.get("active")], ensure_ascii=False)[:200])
        check(f"restyle {name}：背景音樂按鈕不被導覽列遮住（矩形不重疊）",
              not d.get("musicOverlaps"), json.dumps({"musicBox": d.get("musicBox"), "navBox": d.get("box")}, ensure_ascii=False)[:240])
        roomy = (d.get("bodyPadBottom") or 0) >= 100 or (d.get("mainPadBottom") or 0) >= 100 or \
                (d.get("navTop") and d.get("lastBottom") is not None and d["lastBottom"] <= d["navTop"])
        check(f"restyle {name}：頁面底部留白足夠，捲到底時導覽列不會壓住最後一段內容（padding ≥100px 或最後元素在導覽列上方）",
              roomy, json.dumps({"bodyPadBottom": d.get("bodyPadBottom"), "mainPadBottom": d.get("mainPadBottom"),
              "lastBottom": d.get("lastBottom"), "navTop": d.get("navTop")}, ensure_ascii=False)[:220])

    st = home_state(port, page="home.html", wides=True)
    by = st.get("byWidth") or {}
    for w in (320, 375, 768, 1440):
        h = (by.get(str(w)) or by.get(w) or {}).get("hero") or {}
        check(f"restyle home.html {w}px：主視覺照片與今日經文矩形完全不重疊（人物不被蓋住），照片高 ≥200px",
              bool(h) and h.get("picOverlap") is False and h.get("picH", 0) >= 200,
              json.dumps({"pic": h.get("pic"), "verse": h.get("verse"), "picH": h.get("picH")}, ensure_ascii=False)[:260])
    hero = st.get("hero") or {}
    check("restyle home.html：今日經文與照片裡的光同色（#fdf2da）、有金色光暈 text-shadow、用明體",
          hero.get("color") == SUNLIGHT_RGB and hero.get("shadow") not in (None, "", "none") and hero.get("serif"),
          json.dumps({k: hero.get(k) for k in ("color", "shadow", "serif")}, ensure_ascii=False)[:260])
    check("restyle home.html：經文區塊有一道從照片方向照過來的暖光（.hero-body 帶 radial-gradient 背景）",
          bool(hero.get("bodyHasGradient")), str(hero.get("bodyBgImage"))[:200])
    check("restyle home.html：經文與底對比 ≥4.5:1", (hero.get("contrast") or 0) >= 4.5, json.dumps({"contrast": hero.get("contrast")}))
    t = st.get("tiles") or {}
    check("restyle home.html：便當格入口有齊全——四卷色塊、每日禱讀（→devotional.html）、抽經文卡（→blessing.html）、搜尋表單",
          t.get("bookCount") == 4 and t.get("dailyHref") == "devotional.html" and t.get("drawHref") == "blessing.html"
          and t.get("find") and t.get("findInput"),
          json.dumps({k: t.get(k) for k in ("bookCount", "dailyHref", "drawHref", "find", "findInput")}, ensure_ascii=False))
    check("restyle home.html：抽經文卡入口的三張扇形紙卡依序是 B、A、B（最上層那張是 eagle-B，而且淺深色都有圖、不是空白色塊）",
          t.get("fanCount") == 3 and [n.split("/")[-1] for n in t.get("fanNames", [])] == ["eagle-B.jpg", "eagle-A.jpg", "eagle-B.jpg"],
          json.dumps(t.get("fanNames"), ensure_ascii=False))
    for page, mode, want in (("home.html", "empty", "fix"), ("index.html", "empty", "fix"), ("search.html", "empty", "fix"),
                             ("search.html", "hit", "ok"), ("search.html", "miss", "fix")):
        st = home_state(port, page=page, do=mode)
        s = ((st.get("states") or {}).get(mode) or {}).get("final") or {}
        sreg, field = s.get("status") or {}, s.get("field") or {}
        if want == "ok":
            check(f"restyle {page} 搜尋有結果時：狀態 data-state=ok、圖示＋文字（找到 N 節）、不是只換顏色",
                  sreg.get("state") == "ok" and bool(sreg.get("text")) and (s.get("results") or 0) > 0,
                  json.dumps({"status": sreg, "results": s.get("results"), "info": s.get("info")}, ensure_ascii=False)[:260])
        else:
            cn = bool(re.search(r"[\u4e00-\u9fff]", sreg.get("text") or ""))
            check(f"restyle {page} 搜尋「{'空白送出' if mode == 'empty' else '查無結果'}」時：欄位 aria-invalid=true、aria-describedby 指向 role=status 區、狀態 data-state=fix 且有中文「怎麼修」文字",
                  sreg.get("state") == "fix" and field.get("invalid") == "true" and field.get("describedby")
                  and field.get("targetRole") in ("status", "polite", "assertive") and cn,
                  json.dumps({"status": sreg, "field": field}, ensure_ascii=False)[:300])
        check(f"restyle {page} 的搜尋回饋區在 live 區內（role=status 或 aria-live），不用取得焦點也讀得到",
              bool(sreg.get("role")) or bool(sreg.get("live")) or sreg.get("live") == "polite",
              json.dumps(sreg, ensure_ascii=False)[:200])
    cov = home_state(port, page="blessing.html").get("cover") or {}
    check("restyle blessing.html：抽卡前顯示飛鷹卡背（eagle-A 由共用樣式提供），不是空白色塊",
          bool(cov) and cov.get("hasA") and not cov.get("blankBlock"), json.dumps(cov, ensure_ascii=False)[:240])


HEART_ASSETS = ("heart-idle-light.gif", "heart-idle-dark.gif", "heart-surprise-light.gif",
                "heart-surprise-dark.gif", "heart-still.png", "pattern-light.png", "pattern-dark.png")
PAPER_LIGHT = "rgb(243, 246, 242)"    # --paper #f3f6f2：GIF 淺色版預混的底色
PAPER_DARK = "rgb(10, 20, 18)"        # --paper #0a1412：GIF 深色版預混的底色


def heart_assets():
    """第三輪 B：愛心與底紋七件素材都要存在、非空、<600KB，並登記生成來源。"""
    lic_path = os.path.join(ROOT, "ASSETS-LICENSE.md")
    lic = open(lic_path, encoding="utf-8").read() if os.path.exists(lic_path) else ""
    bad, rows = [], []
    for name in HEART_ASSETS:
        p = os.path.join(SITE, "assets", name)
        if not os.path.exists(p):
            bad.append(f"{name} 不存在")
            continue
        kb = os.path.getsize(p) / 1024
        if kb < 1:
            bad.append(f"{name} 是空檔")
        if kb >= 600:
            bad.append(f"{name} {kb:.0f} KB ≥ 600 KB")
        row = [l for l in lic.splitlines() if name in l and l.strip().startswith("|")]
        if not row:
            bad.append(f"{name} 沒有登記在 ASSETS-LICENSE.md")
        rows.append({"name": name, "kb": round(kb, 1), "lic": bool(row)})
    check("第三輪 B 素材：site/assets 有 heart-idle／heart-surprise 的 light／dark GIF、heart-still.png、pattern-light／dark.png 共 7 件，非空且每件 <600KB，並登記在 ASSETS-LICENSE.md",
          len(bad) == 0 and len(rows) == len(HEART_ASSETS), "；".join(bad) or json.dumps(rows, ensure_ascii=False))
    check("第三輪 B 素材登記寫明母圖由 Codex（OpenAI image_gen）產生、再用 Pillow 輸出 GIF／PNG",
          bool(re.search(r"image_gen", lic, re.I)) and bool(re.search(r"Pillow", lic, re.I)),
          "" if (re.search(r"image_gen", lic, re.I) and re.search(r"Pillow", lic, re.I))
          else "ASSETS-LICENSE.md 裡找不到：" + "、".join(x for x in ("image_gen", "Pillow") if not re.search(x, lic, re.I)))


def heart_source():
    """源碼層：待機／小驚喜圖、區塊底色、底紋平鋪尺寸、狀態文字與 aria-busy。"""
    page = os.path.join(SITE, "blessing.html")
    src = open(page, encoding="utf-8").read() if os.path.exists(page) else ""
    app = open(os.path.join(SITE, "app.js"), encoding="utf-8").read() if os.path.exists(os.path.join(SITE, "app.js")) else ""
    css = open(os.path.join(SITE, "style.css"), encoding="utf-8").read() if os.path.exists(os.path.join(SITE, "style.css")) else ""
    where = src + app + css          # 圖檔名允許只放在共用層（跟飛鷹圖一樣）

    def miss(names_, pool):
        return "、".join(x for x in names_ if x not in pool)

    bad = miss(("heart-idle-light.gif", "heart-idle-dark.gif", "heart-still.png", "prefers-reduced-motion"), where)
    check("第三輪 B：待機愛心有淺色 heart-idle-light.gif、深色 heart-idle-dark.gif，且 prefers-reduced-motion 改用 heart-still.png",
          not bad, "找不到：" + bad)
    bad = miss(("heart-surprise-light.gif", "heart-surprise-dark.gif"), where)
    check("第三輪 B：小驚喜動圖 heart-surprise-light／dark.gif 接進抽卡流程（點愛心後才翻卡）",
          not bad, "找不到：" + bad)
    # 區塊底色只能由這一頁的愛心舞台決定：style.css 的調色盤本來就有這兩個色，掃共用層會假綠
    bad = miss(("#f3f6f2", "#0a1412"), src)
    check("第三輪 B：blessing.html 的愛心區塊底色跟 GIF 預混底色一致（淺 #f3f6f2、深 #0a1412）",
          not bad, "blessing.html 裡找不到：" + bad)
    bad = miss(("pattern-light.png", "pattern-dark.png", "360px"), where)
    check("第三輪 B：抽卡頁背景鋪 pattern-light.png／pattern-dark.png 且平鋪尺寸約 360px",
          not bad, "找不到：" + bad)
    bad = miss(("點愛心領受今天的祝福", "正在為你抽一張卡"), src)
    check("第三輪 B：狀態列有「點愛心領受今天的祝福」待機文字與「正在為你抽一張卡…」處理中文字（不能只靠動畫傳達）",
          not bad, "blessing.html 裡找不到：" + bad)
    check("第三輪 B：點愛心期間設 aria-busy（防止重複觸發），動圖只播一次",
          "aria-busy" in src, "" if "aria-busy" in src else "blessing.html 沒有 aria-busy")


def heart_render(port):
    """實際渲染：淺色、深色、reduced-motion 三種情境，加上點下去那一瞬間的 busy 狀態。"""
    light = blessing_state(port, "blessing.html")
    hl = light.get("heart") or {}
    btn = hl.get("heartBtn") or {}
    img = hl.get("heartImg") or {}
    check("heart：blessing.html 抽卡前顯示待機愛心（#heart-btn 或 .heart 存在且可見）",
          bool(btn.get("found")) and btn.get("shown") is True, json.dumps(hl, ensure_ascii=False)[:300])
    check("heart：淺色模式待機圖是 assets/heart-idle-light.gif",
          img.get("srcName") == "heart-idle-light.gif", json.dumps(img, ensure_ascii=False)[:200])
    check("heart：愛心區塊底色淺色為 rgb(243, 246, 242)（GIF 預混色，錯一格就會看到邊框殘影）",
          hl.get("stageBg") == PAPER_LIGHT, json.dumps({"stageBg": hl.get("stageBg"), "stage": hl.get("stageTag")}, ensure_ascii=False))
    check("heart：抽卡頁背景鋪 pattern-light.png 且平鋪約 360px",
          hl.get("pagePattern", {}).get("file") == "pattern-light.png" and "360" in (hl.get("pagePattern", {}).get("size") or ""),
          json.dumps(hl.get("pagePattern"), ensure_ascii=False)[:240])
    si = hl.get("statusIdle") or {}
    check("heart：待機時狀態列（role=status）文字含「點愛心領受今天的祝福」",
          si.get("role") == "status" and "點愛心領受今天的祝福" in (si.get("text") or ""),
          json.dumps(si, ensure_ascii=False)[:200])
    check("heart：卡背標題（.cover-title）與抽卡按鈕（#draw-btn）不壓在老鷹身上（在卡外或卡片下半部 65% 以下）",
          hl.get("eagleOverlap") is False, json.dumps(hl.get("eagleDetail"), ensure_ascii=False)[:260])

    dark = blessing_state(port, "blessing.html", dark=True)
    hd = dark.get("heart") or {}
    check("heart：深色模式待機圖改用 assets/heart-idle-dark.gif、區塊底色 rgb(10, 20, 18)、背景鋪 pattern-dark.png",
          (hd.get("heartImg") or {}).get("srcName") == "heart-idle-dark.gif" and hd.get("stageBg") == PAPER_DARK
          and (hd.get("pagePattern") or {}).get("file") == "pattern-dark.png",
          json.dumps({k: hd.get(k) for k in ("stageBg", "heartImg", "pagePattern", "dark")}, ensure_ascii=False)[:300])

    red = blessing_state(port, "blessing.html", reduce=True)
    hr = red.get("heart") or {}
    check("heart：偏好減少動態（prefers-reduced-motion: reduce）時改用靜態 heart-still.png、不播 GIF",
          bool(hr.get("reduce")) and (hr.get("heartImg") or {}).get("srcName") == "heart-still.png",
          json.dumps({k: hr.get(k) for k in ("reduce", "heartImg")}, ensure_ascii=False)[:240])

    st = blessing_state(port, "blessing.html", act=[{"click": "#heart-btn"}])
    act0 = (st.get("heartActs") or [{}])[0]
    busy = act0.get("status") or {}
    settled = act0.get("settledStatus") or {}
    check("heart：點愛心時先設 aria-busy=true 且狀態列 data-state=busy、文字含「正在為你抽一張卡…」（期間不可重複觸發）",
          act0.get("clicked") is True and act0.get("ariaBusy") == "true" and busy.get("state") == "busy"
          and "正在為你抽一張卡" in (busy.get("text") or ""),
          json.dumps({"clicked": act0.get("clicked"), "ariaBusy": act0.get("ariaBusy"), "busy": busy}, ensure_ascii=False)[:300])
    check("heart：小驚喜播完後照舊抽出經文卡（37 張卡流程不壞），狀態列改成完成文字",
          bool(st.get("card")) and bool(st.get("ids") and st.get("ids")[0])
          and settled.get("state") != "busy" and bool(settled.get("text")),
          json.dumps({"card": bool(st.get("card")), "id": (st.get("ids") or [None])[0], "settled": settled}, ensure_ascii=False)[:300])
    check("heart：點愛心這條路徑本身沒有 JS 錯誤（動圖載入、翻卡、狀態更新都要乾淨）",
          act0.get("clicked") is True and not st.get("errors"),
          json.dumps({"clicked": act0.get("clicked"), "errors": st.get("errors", [])[:3]}, ensure_ascii=False)[:260])

    # 迴歸守門：這一項在接線前就該是綠的，接上愛心後也不准變紅（交辦單：現有 37 張卡、四個主題、下載、音樂不可壞）
    legacy = blessing_state(port, "blessing.html", act=[{"click": "#draw-btn"}, {"click": "#theme-tabs button[data-theme=peace]"}])
    check("heart：接上愛心後，原有的 #draw-btn 與主題標籤流程仍能出卡、沒有 JS 錯誤（37 張卡流程不可壞）",
          bool(legacy.get("card")) and bool((legacy.get("ids") or [None])[0]) and not legacy.get("errors"),
          json.dumps({"ids": legacy.get("ids"), "errors": legacy.get("errors", [])[:3]}, ensure_ascii=False)[:260])


def bm_state(port):
    """跑 tests/home_probe.html?bm=1：在 chapter／index 兩頁之間走一遍收藏流程。"""
    q = "u=" + urllib.parse.quote("../site/chapter.html?book=jhn&ch=3", safe="") + "&bm=1"
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                              "--virtual-time-budget=90000", f"--user-data-dir={profile}", "--dump-dom",
                              f"http://127.0.0.1:{port}/tests/home_probe.html?{q}"],
                             capture_output=True, text=True, timeout=240).stdout
    out = re.sub(r"<[^>]+>", "", out)
    found = re.findall(r"PROBE (\{.*\})", out)
    try:
        return json.loads(html.unescape(found[-1])) if found else {}
    except ValueError:
        return {}


def bookmarks_static():
    """第三輪 D：儲存鍵 bible.bookmarks.v1 與「原始碼不寫死經文」鐵則。"""
    names = ("chapter.html", "index.html", "app.js")
    srcs = {}
    for n in names:
        p = os.path.join(SITE, n)
        srcs[n] = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    joined = "".join(srcs.values())
    check("bookmarks：收藏功能用共用的 localStorage 鍵 bible.bookmarks.v1（chapter.html／index.html／app.js 其中一處定義即可）",
          "bible.bookmarks.v1" in joined, "三個檔案裡都找不到 bible.bookmarks.v1")
    grams = set()
    for key, _ in BOOKS:
        chapters = json.load(open(os.path.join(ROOT, "data", key + ".json"), encoding="utf-8"))["chapters"]
        for c in chapters:
            for v in c["verses"]:
                s = cjk(v["text"])
                grams.update(s[i:i + 8] for i in range(len(s) - 7))
    for n, src in srcs.items():
        s = cjk(src)
        hit = sorted({s[i:i + 8] for i in range(len(s) - 7) if s[i:i + 8] in grams})
        check(f"bookmarks：{n} 原始碼不含寫死經文（與和合本沒有任何連續 8 字相同）", not hit, "；".join(hit[:3]))
    bad = [ch for ch in SIMPLIFIED if ch in joined]
    check("bookmarks：收藏相關原始碼都是繁體中文（介面不混簡體字）", not bad, "".join(bad))


def bookmarks_render(port):
    """第三輪 D：實際點一遍收藏／取消／重整／目錄頁清單／移除／壞資料／四種寬度。"""
    st = bm_state(port)
    bm = st.get("bm") or {}
    if not bm:
        check("bookmarks：探測流程跑得起來（home_probe.html?bm=1 有回傳）", False, json.dumps(st, ensure_ascii=False)[:200])
        return
    chips = bm.get("chips") or {}
    check("bookmarks：chapter.html?book=jhn&ch=3 點選 #v16 後，操作列 .chips 出現收藏按鈕（aria-pressed=false、文字含「收藏這一節」）",
          bool(chips.get("found")) and chips.get("pressed") == "false" and "收藏這一節" in (chips.get("label") or ""),
          json.dumps(chips, ensure_ascii=False)[:260])
    marked = bm.get("marked") or {}
    check("bookmarks：按收藏後 aria-pressed 變 true、按鈕文字變「✓ 已收藏」（不只靠顏色）",
          marked.get("pressed") == "true" and "已收藏" in (marked.get("label") or ""),
          json.dumps(marked, ensure_ascii=False)[:260])
    ms = bm.get("markStatus") or {}
    check("bookmarks：狀態列（role=status）播報含「已收藏」、「約翰福音 3:16」與「本機儲存」",
          ms.get("role") == "status" and all(x in (ms.get("text") or "") for x in ("已收藏", "約翰福音 3:16", "本機儲存")),
          json.dumps(ms, ensure_ascii=False)[:260])
    store = bm.get("store") or {}
    only_coord = all(set(str(k).split("+")) and set(str(k).split("+")) <= {"book", "ch", "v", "at"} for k in (store.get("keys") or []))
    check("bookmarks：localStorage 的 bible.bookmarks.v1 是陣列、元素只有座標欄位（book／ch／v／at），完全不含經文文字",
          bool(store.get("isArray")) and bool(store.get("length")) and only_coord and store.get("hasCjk") is False,
          json.dumps(store, ensure_ascii=False)[:300])
    rl = bm.get("afterReload") or {}
    check("bookmarks：重新整理 chapter.html 後再點 #v16，按鈕仍是 aria-pressed=true 與「✓ 已收藏」",
          rl.get("pressed") == "true" and "已收藏" in (rl.get("label") or ""), json.dumps(rl, ensure_ascii=False)[:260])
    un = bm.get("unmarked") or {}
    us = bm.get("unmarkStatus") or {}
    check("bookmarks：再次點擊取消收藏 → aria-pressed 回到 false，狀態列播報「已取消收藏」＋約翰福音 3:16",
          un.get("pressed") == "false" and "已取消收藏" in (us.get("text") or "") and "約翰福音 3:16" in (us.get("text") or ""),
          json.dumps({"btn": un, "status": us}, ensure_ascii=False)[:300])
    ib = bm.get("indexBox") or {}
    check("bookmarks：收藏一節後打開 index.html 有「我的收藏（1 節）」摺疊區（#bookmarks-box 或 details＋summary）",
          bool(ib.get("found")) and "我的收藏" in (ib.get("summary") or "") and "1" in (ib.get("summary") or ""),
          json.dumps(ib, ensure_ascii=False)[:260])
    items = bm.get("indexItems") or []
    jhn = json.load(open(os.path.join(ROOT, "data", "jhn.json"), encoding="utf-8"))["chapters"]
    want = next(v["text"] for c in jhn if int(str(c["ch"])) == 3 for v in c["verses"] if int(str(v["v"])) == 16)
    one = len(items) == 1
    text0 = items[0]["text"] if one else ""
    check("bookmarks：收藏區列出出處約翰福音 3:16 與經文本節，經文由 Bible.load 動態載入、與 data/jhn.json 逐字一致",
          one and "約翰福音 3:16" in text0 and want in text0,
          json.dumps({"筆數": len(items), "含出處": "約翰福音 3:16" in text0, "經文逐字相符": want in text0,
                      "字數": {"清單": len(text0), "預期": len(want)}}, ensure_ascii=False))
    hrefs = [l["href"] for l in (items[0].get("links") or [])] if one else []
    check("bookmarks：每筆提供「前往閱讀」連 chapter.html?book=jhn&ch=3#v16、「做成經文卡片」連 card.html?book=jhn&ch=3&v=16 與「移除」按鈕",
          "chapter.html?book=jhn&ch=3#v16" in hrefs and "card.html?book=jhn&ch=3&v=16" in hrefs and bool(one and items[0].get("remove")),
          json.dumps({"hrefs": hrefs, "remove": bool(one and items[0].get("remove"))}, ensure_ascii=False)[:260])
    ar = bm.get("afterRemove") or {}
    arb = ar.get("box") or {}
    check("bookmarks：按「移除」後變成 0 節並顯示沒有收藏的說明文字（不是留白）",
          len(ar.get("items") or []) == 0 and "0" in (arb.get("summary") or "") and bool(cjk(ar.get("emptyText") or "")),
          json.dumps({"剩餘": len(ar.get("items") or []), "summary": arb.get("summary"), "emptyText": (ar.get("emptyText") or "")[:80]},
                     ensure_ascii=False)[:300])
    check("bookmarks：收藏區出現與消失時，底部導覽列都仍維持五項",
          bool(ib.get("found")) and ib.get("navCount") == 5 and arb.get("navCount") == 5,
          json.dumps({"打開時": [ib.get("found"), ib.get("navCount")], "移除後": arb.get("navCount")}, ensure_ascii=False))
    ci = bm.get("corruptIndex") or {}
    cc = bm.get("corruptChapter") or {}
    check("bookmarks：localStorage 塞壞 JSON 時，index.html 與 chapter.html 都不壞頁、沒有 JS 錯誤，並顯示繁體中文的「怎麼修」提示",
          ci.get("renders") is True and cc.get("renders") is True and not ci.get("newErrors") and not cc.get("newErrors")
          and bool(ci.get("notice")) and bool(cc.get("notice")),
          json.dumps({"index": ci, "chapter": cc}, ensure_ascii=False)[:300])
    sizes = bm.get("sizes") or {}
    for name, page in (("index.html 收藏區", "index"), ("chapter.html 操作列", "chapter")):
        got = sizes.get(page) or {}
        bad = [f"{w}px：scrollWidth {v.get('scrollWidth')} > clientWidth {v.get('clientWidth')}"
               for w, v in got.items() if (v.get("scrollWidth") or 0) > (v.get("clientWidth") or 0)]
        not_open = [w for w, v in got.items() if not v.get("opened")]
        check(f"bookmarks：{name}真的展開後，在 320／375／768／1440px 都沒有水平溢出",
              bool(got) and not bad and not not_open,
              "；".join(bad) + (f"；{','.join(sorted(not_open))}px 找不到可展開的收藏 UI" if not_open else ""))


def rendering(groups):
    if not CHROME:
        check("頁面實際顯示（headless Chrome）", False, "找不到 Chrome")
        return
    data = {k: json.load(open(os.path.join(ROOT, "data", k + ".json"), encoding="utf-8"))["chapters"] for k, _ in BOOKS}
    names = dict(BOOKS)
    handler = functools.partial(RangeHandler, directory=ROOT)
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
        if "zonemusic" in groups:
            zone_render(port)
            zone_render(port, pages=["blessing.html", "card.html", "index.html"], width=320)
            zone_variants()
        if "blessart" in groups:
            blessart_variants()
        if "devotional" in groups:
            devotional_variants()
        if "restyle" in groups:
            restyle_render(port)
        if "heart" in groups:
            heart_render(port)
        if "bookmarks" in groups:
            bookmarks_render(port)
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
    groups = set(args) or {"chapter", "search", "index", "card", "blessing", "blessnav", "blessindex", "blessstyle", "home", "zonemusic", "blessart", "devotional", "restyle", "heart", "bookmarks"}
    links()
    external()
    single_book_text()
    if "blessing" in groups:
        blessing_data()
        blessing_frozen()
    if "blessart" in groups:
        blessart_data()
        blessart_static()
    if "home" in groups:
        home_data()
        home_static()
    if "zonemusic" in groups:
        zone_data()
        zone_static()
    if "devotional" in groups:
        devotional_static()
    if "restyle" in groups:
        restyle_assets()
        restyle_shared()
    if "heart" in groups:
        heart_assets()
        heart_source()
    if "bookmarks" in groups:
        bookmarks_static()
    rendering(groups)
    if ONLY and not results:
        results.append(False)   # a typo in --grep must not pass silently
        print(f"不通過：--grep {ONLY} 沒有對到任何檢查")
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
