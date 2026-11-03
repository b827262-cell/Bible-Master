#!/usr/bin/env python3
"""Visual / accessibility checks for FRONTEND-VISUAL-OPTIMIZATION-PLAN.md (exit code 0 only when all pass).
Opens each page in tests/visual_probe.html (headless Chrome, light and dark colour scheme, several widths) and checks:
  p0  style.css: every rule survives the browser's parser; every link/button/input/select draws a solid >=2px focus
      outline; text contrast >=4.5:1 in light and dark; every input/select has an accessible name
  p1  touch targets (nav, book tabs, search controls >=44px; chapter cards, chapter links >=48px); current page/book
      marked by more than colour; h1 1.375rem on phones / 1.625rem on desktop; verse text aligned in one column
  p2  card page controls >=44px and canvas scaled to its container; no horizontal overflow at 320/375/768/1440px
Usage: python3 bible-site/tests/visual_checks.py [p0] [p1] [p2] [--grep REGEX]   (no group: all three)"""
import functools, html, http.server, json, os, re, socketserver, sys, tempfile, threading, urllib.parse, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = next((c for c in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/snap/bin/chromium") if os.path.exists(c)), None)
WIDTHS = [320, 375, 768, 1440]
PAGES = ["index.html?book=luk", "chapter.html?book=luk&ch=2", "search.html?q=" + urllib.parse.quote("彼得"),
         "search.html?q=zzzz", "card.html?book=luk&ch=1&v=1", "blessing.html?card=work-01", "home.html"]
results = []
ONLY = None  # --grep REGEX: only checks whose name matches count (one task's share of the plan)


def check(name, ok, detail=""):
    if ONLY and not re.search(ONLY, name):
        return
    results.append(ok)
    print(("通過" if ok else "不通過") + f"：{name}" + (f"（{detail}）" if detail else ""))


def top_level_rules(css):
    """Number of top-level rules in a stylesheet (an @media block counts as one), as the source text says."""
    css, depth, n = re.sub(r"/\*.*?\*/", "", css, flags=re.S), 0, 0
    for ch in css:
        if ch == "{":
            n += depth == 0
            depth += 1
        elif ch == "}":
            depth -= 1
    return n


def probe(port, page, dark):
    q = "u=" + urllib.parse.quote("../site/" + page, safe="") + "&w=" + ",".join(map(str, WIDTHS))
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                              "--virtual-time-budget=15000", f"--user-data-dir={profile}",
                              f"--blink-settings=preferredColorScheme={0 if dark else 1}",
                              "--dump-dom", f"http://127.0.0.1:{port}/tests/visual_probe.html?{q}"],
                             capture_output=True, text=True, timeout=90).stdout
    found = re.findall(r"VISUAL (\{.*\})", re.sub(r"<[^>]+>", "", out))
    try:
        return {int(k): v for k, v in json.loads(html.unescape(found[-1])).items()} if found else {}
    except ValueError:
        return {}


def main(groups):
    if not CHROME:
        check("visual checks（headless Chrome）", False, "找不到 Chrome")
        return
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        light = {p: probe(port, p, False) for p in PAGES}
        dark = {p: probe(port, p, True) for p in PAGES} if "p0" in groups else {}
        srv.shutdown()
    for p in PAGES:
        if not light[p] or any("crash" in m for m in light[p].values()):
            check(f"{p} 量測", False, "探測頁沒有輸出：" + json.dumps(light[p], ensure_ascii=False)[:200])
            return
    want_rules = top_level_rules(open(os.path.join(ROOT, "site", "style.css"), encoding="utf-8").read())

    if "p0" in groups:
        got = light[PAGES[0]][375]["cssRules"]
        check(f"style.css 每條規則都被瀏覽器接受（原始碼 {want_rules} 條）", got == want_rules,
              "" if got == want_rules else f"瀏覽器只保留 {got} 條：有規則的選擇器或語法不合法，整條被丟掉")
        for scheme, data in (("淺色", light), ("深色", dark)):
            if scheme == "深色" and not all(data[p][375].get("dark") for p in PAGES):
                check("深色模式量測", False, "Chrome 沒有套用深色模式")
                continue
            for p in PAGES:
                m = data[p][1440]
                check(f"{scheme} {p} 所有可聚焦元件的焦點外框為實線且至少 2px", not m["focus"], "；".join(m["focus"][:6]))
                low = {k: v for k, v in data[p][375]["contrast"].items() if v < 4.5}
                check(f"{scheme} {p} 文字對比都至少 4.5:1", not low, "；".join(f"{k} {v}" for k, v in low.items()))
        for p in PAGES:
            un = light[p][375]["unnamed"]
            check(f"{p} 輸入框與選單都有可存取名稱（label 或 aria-label）", not un, "、".join(un))

    if "p1" in groups:
        for p in PAGES:
            m = light[p][375]
            small = [f"{k} {v['h']}×{v['w']}px（至少 {v['min']}）" for k, v in m["targets"].items()
                     if not k.startswith("select") and (v["h"] < v["min"] - 0.5 or v["w"] < v["min"] - 0.5)]
            check(f"375px {p} 導覽、書卷、章節、搜尋控制項的觸控區域夠大", not small, "；".join(small))
            plain = [k for k, ok in m["current"].items() if not ok]
            check(f"{p} 目前頁面／書卷除了顏色還有粗體或底線", not plain, "、".join(plain))
            na = m.get("navActive")
            if na is not None:   # chapter.html has no current nav entry
                check(f"{p} 導覽列目前頁不是實心色塊：背景透明、粗體、底部 ≥2px 指示線",
                      na.get("bg") in ("rgba(0, 0, 0, 0)", "transparent") and na.get("weight", 0) >= 600 and na.get("bottom", 0) >= 2,
                      json.dumps(na))
            want = {375: 22, 1440: 26}
            bad = [f"{w}px 時 h1 {light[p][w]['h1']}px（要 {px}px）" for w, px in want.items() if abs(light[p][w]["h1"] - px) > 0.5]
            check(f"{p} 主標題字級：手機 1.375rem、桌面 1.625rem", not bad, "；".join(bad))
        for w in (375, 1440):
            lefts = light[PAGES[1]][w]["verseLefts"]
            check(f"{w}px {PAGES[1]} 經文左緣對齊成一欄（含合併節 34-35）", len(lefts) == 1, f"左緣位置 {lefts}")

    if "p2" in groups:
        m = light[PAGES[4]][375]
        small = [f"{k} {v['h']}×{v['w']}px（至少 {v['min']}）" for k, v in m["targets"].items()
                 if k in ("select", "button") and (v["h"] < v["min"] - 0.5 or v["w"] < v["min"] - 0.5)]
        check("375px card.html 書卷／章／節選單與下載按鈕至少 44px", not small, "；".join(small))
        for w in WIDTHS:
            c = light[PAGES[4]][w].get("canvas", {})
            good = c.get("attrW", 0) >= 600 and 0 < c.get("shownW", 0) <= w and c.get("ref", "").startswith("路加福音 1:1-2")
            check(f"{w}px card.html 畫布實際像素 ≥600、顯示寬度不超出畫面、仍畫出路加福音 1:1-2", good, json.dumps(c, ensure_ascii=False))
        for p in PAGES:
            bad = [f"{w}px scrollWidth {light[p][w]['scrollWidth']}>{light[p][w]['clientWidth']} {light[p][w]['overflow']}"
                   for w in WIDTHS if light[p][w]["scrollWidth"] > light[p][w]["clientWidth"] or light[p][w]["overflow"]]
            check(f"{p} 在 320/375/768/1440px 都沒有水平溢出", not bad, "；".join(bad))
        m = light[PAGES[5]][375]
        small = [f"{k} {v['h']}×{v['w']}px（至少 {v['min']}）" for k, v in m["targets"].items()
                 if k == "button" and (v["h"] < v["min"] - 0.5 or v["w"] < v["min"] - 0.5)]
        check("375px blessing.html 的按鈕（抽卡、再抽、主題標籤、下載、分享）至少 44px", not small, "；".join(small))
        for w in WIDTHS:
            h = light[PAGES[6]][w].get("home") or {}
            check(f"{w}px home.html 經文卡壓在英雄圖的底緣（卡片頂端比圖片底端高）、圖高 ≥ 240px", bool(h) and h["cardTop"] < h["imgBottom"] and h["heroH"] >= 240, json.dumps(h))
        h = light[PAGES[6]][375].get("home") or {}
        bg = h.get("musicBg") or [255, 255, 255, 1]
        check("home.html 音樂按鈕在圖上、半透明深色底、字是淺色（對比 ≥ 4.5:1）", bool(h) and h.get("musicInHero") and 0 < bg[3] < 1 and sum(bg[:3]) < 200 and h.get("musicLum", 0) >= 0.7, json.dumps(h))
        for w in WIDTHS:
            h = light[PAGES[6]][w].get("home") or {}
            check(f"{w}px home.html 音樂按鈕完整露出在圖上（沒有被經文卡蓋住）", bool(h) and h.get("musicBottom") is not None and h["musicBottom"] <= h["cardTop"], json.dumps(h))
        check("home.html 圖上的小標是淺色字並有 text-shadow", bool(h) and h.get("kickerLum", 0) >= 0.7 and h.get("kickerShadow") not in (None, "none"), json.dumps(h))
        check("home.html 經文用明體", bool(h) and h.get("serif") is True, json.dumps(h))
        for w in WIDTHS:
            c = light[PAGES[5]][w].get("canvas", {})
            good = c.get("attrW", 0) >= 600 and c.get("shownW", -1) == 0 and c.get("ref", "").startswith("馬太福音 25:21")
            check(f"{w}px blessing.html?card=work-01 畫布實際像素 ≥600、畫出馬太福音 25:21、頁面上不顯示（只供下載）", good, json.dumps(c, ensure_ascii=False))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--grep" in args:
        i = args.index("--grep")
        ONLY = args[i + 1]
        del args[i:i + 2]
    main(set(args) or {"p0", "p1", "p2"})
    if ONLY and not results:
        results.append(False)   # a typo in --grep must not pass silently
        print(f"不通過：--grep {ONLY} 沒有對到任何檢查")
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
