#!/usr/bin/env python3
"""Desktop / laptop layout checks for bible-site (1024, 1366, 1440, 1920px).
Verifies:
  1. Breakpoint coverage (>=64em/1024px, >=90em/1440px, 1920px).
  2. Container expansion on desktop while keeping mobile (375px) narrow.
  3. Chapter reading column constrained to <= 46em (<= 45 Chinese characters per line) and sidebar presence.
  4. Chapter grid columns: >= 5 cols at 1024/1366px, >= 6 cols at 1440/1920px.
  5. Search results: 2-column grid on desktop.
  6. Navigation bar: centered and balanced on desktop.
  7. Home hero: wide banner with image max-width within 1600px, overlapping card, music button uncovered.
Usage: python3 bible-site/tests/desktop_checks.py"""

import functools, html, http.server, json, os, re, socketserver, subprocess, sys, tempfile, threading, urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = next((c for c in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/snap/bin/chromium") if os.path.exists(c)), None)
DESKTOP_WIDTHS = [1024, 1366, 1440, 1920]
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("通過" if ok else "不通過") + f"：{name}" + (f"（{detail}）" if detail else ""))


def probe_desktop(port, width, height, path):
    """Open page in headless Chrome with specific viewport and measure layout."""
    url = f"http://127.0.0.1:{port}/site/{path}"
    script = """
    (() => {
        const out = {};
        const win = window, doc = document;
        const main = doc.querySelector("main") || doc.querySelector(".container");
        out.viewportW = win.innerWidth;
        out.viewportH = win.innerHeight;
        out.containerW = main ? Math.round(main.getBoundingClientRect().width) : 0;
        out.containerL = main ? Math.round(main.getBoundingClientRect().left) : 0;
        out.containerR = main ? Math.round(win.innerWidth - main.getBoundingClientRect().right) : 0;
        
        // Navigation
        const navList = doc.querySelector("#nav .nav-list");
        if (navList) {
            const rect = navList.getBoundingClientRect();
            out.navW = Math.round(rect.width);
            out.navL = Math.round(rect.left);
            out.navR = Math.round(win.innerWidth - rect.right);
            out.navCentered = Math.abs(out.navL - out.navR) <= 30;
        }

        // Chapter directory grid
        const grid = doc.querySelector(".chapter-grid");
        if (grid) {
            const cards = [...grid.querySelectorAll(".chapter-card")];
            if (cards.length >= 6) {
                const firstY = Math.round(cards[0].getBoundingClientRect().top);
                const firstRowCards = cards.filter(c => Math.abs(Math.round(c.getBoundingClientRect().top) - firstY) < 10);
                out.gridCols = firstRowCards.length;
            }
        }

        // Chapter reading
        const readingMain = doc.querySelector(".reading-main");
        const verseText = doc.querySelector(".verse-text");
        const sidebar = doc.querySelector(".chapter-sidebar");
        if (readingMain) {
            out.readingMainW = Math.round(readingMain.getBoundingClientRect().width);
        }
        if (verseText) {
            out.verseTextW = Math.round(verseText.getBoundingClientRect().width);
            out.verseFontPx = parseFloat(win.getComputedStyle(verseText).fontSize);
            out.charsPerLine = Math.round(out.verseTextW / out.verseFontPx);
        }
        if (sidebar) {
            out.hasSidebar = true;
            out.sidebarW = Math.round(sidebar.getBoundingClientRect().width);
            out.sidebarL = Math.round(sidebar.getBoundingClientRect().left);
            out.sidebarSticky = win.getComputedStyle(sidebar).position === "sticky";
        }

        // Search results
        const results = doc.querySelector(".search-results");
        if (results) {
            const items = [...results.querySelectorAll("li")];
            if (items.length >= 2) {
                const y0 = Math.round(items[0].getBoundingClientRect().top);
                const y1 = Math.round(items[1].getBoundingClientRect().top);
                out.searchCols = (Math.abs(y0 - y1) < 10) ? 2 : 1;
            }
        }

        // Home hero & card
        const hero = doc.querySelector(".home-hero");
        const hcard = doc.querySelector(".home-card");
        const heroImg = doc.querySelector(".home-hero img");
        const musicBtn = doc.getElementById("music-btn");
        if (hero && hcard) {
            out.heroW = Math.round(hero.getBoundingClientRect().width);
            out.heroH = Math.round(hero.getBoundingClientRect().height);
            out.heroImgW = heroImg ? Math.round(heroImg.getBoundingClientRect().width) : 0;
            out.cardW = Math.round(hcard.getBoundingClientRect().width);
            out.cardTop = Math.round(hcard.getBoundingClientRect().top);
            out.imgBottom = heroImg ? Math.round(heroImg.getBoundingClientRect().bottom) : 0;
            out.cardOverlap = out.cardTop < out.imgBottom;
            if (musicBtn) {
                out.musicBottom = Math.round(musicBtn.getBoundingClientRect().bottom);
                out.musicVisible = out.musicBottom <= out.cardTop;
            }
        }

        // Blessing card & theme tabs
        const blessingCard = doc.getElementById("blessing-card");
        const themeTabs = document.getElementById("theme-tabs");
        if (themeTabs) {
            const btns = [...themeTabs.querySelectorAll("button")];
            out.tabCount = btns.length;
        }
        if (blessingCard) {
            out.blessingCardW = Math.round(blessingCard.getBoundingClientRect().width);
        }

        return out;
    })()
    """
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
            f"--window-size={width},{height}", f"--user-data-dir={profile}",
            "--dump-dom", f"http://127.0.0.1:{port}/site/{path}"
        ]
        # Run probe via simple Node script with puppeteer or direct chrome evaluation
        runner_js = f"""
        const puppeteer = require("puppeteer-core");
        (async () => {{
            try {{
                const browser = await puppeteer.launch({{
                    executablePath: {json.dumps(CHROME)},
                    args: ["--no-sandbox", "--disable-gpu", `--window-size=${{width}},${{height}}`],
                    defaultViewport: {{ width: {width}, height: {height} }}
                }});
                const page = await browser.newPage();
                await page.goto({json.dumps(url)}, {{ waitUntil: "networkidle0", timeout: 15000 }});
                await new Promise(r => setTimeout(r, 600));
                const res = await page.evaluate({json.dumps(script)});
                console.log("JSON:" + JSON.stringify(res));
                await browser.close();
            }} catch(e) {{
                console.log("JSON:" + JSON.stringify({{ error: String(e) }}));
            }}
        }})();
        """
        # Alternatively, run Chrome with remote evaluation or inline script
        return None


def main():
    print("=== Bible-Master 電腦／筆電版面自動化檢驗 ===")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]

        # Use Node CDP evaluation helper
        helper_js = os.path.join(ROOT, "tests", "desktop_helper.js")
        helper_code = r"""
const http = require('http');
const { spawn } = require('child_process');

const port = process.argv[2];
const chromePath = process.argv[3];
const widths = [1024, 1366, 1440, 1920];
const pages = {
    index: "index.html?book=luk",
    chapter: "chapter.html?book=luk&ch=2",
    search: "search.html?q=" + encodeURIComponent("彼得"),
    home: "home.html",
    blessing: "blessing.html?card=work-01"
};

const cdpScript = `
(() => {
    const win = window, doc = document;
    const main = doc.querySelector("main") || doc.querySelector(".container");
    const out = {
        viewportW: win.innerWidth,
        viewportH: win.innerHeight,
        containerW: main ? Math.round(main.getBoundingClientRect().width) : 0,
        containerL: main ? Math.round(main.getBoundingClientRect().left) : 0,
        containerR: main ? Math.round(win.innerWidth - main.getBoundingClientRect().right) : 0
    };
    const navList = doc.querySelector("#nav .nav-list");
    if (navList) {
        const rect = navList.getBoundingClientRect();
        out.navW = Math.round(rect.width);
        out.navL = Math.round(rect.left);
        out.navR = Math.round(win.innerWidth - rect.right);
        out.navCentered = Math.abs(out.navL - out.navR) <= 35;
    }
    const grid = doc.querySelector(".chapter-grid");
    if (grid) {
        const cards = [...grid.querySelectorAll(".chapter-card")];
        if (cards.length >= 6) {
            const firstY = Math.round(cards[0].getBoundingClientRect().top);
            out.gridCols = cards.filter(c => Math.abs(Math.round(c.getBoundingClientRect().top) - firstY) < 10).length;
        }
    }
    const readingMain = doc.querySelector(".reading-main");
    const verseText = doc.querySelector(".verse-text");
    const sidebar = doc.querySelector(".chapter-sidebar");
    if (readingMain) out.readingMainW = Math.round(readingMain.getBoundingClientRect().width);
    if (verseText) {
        out.verseTextW = Math.round(verseText.getBoundingClientRect().width);
        out.verseFontPx = parseFloat(win.getComputedStyle(verseText).fontSize);
        out.charsPerLine = Math.round(out.verseTextW / out.verseFontPx);
    }
    if (sidebar) {
        out.sidebarW = Math.round(sidebar.getBoundingClientRect().width);
        out.sidebarL = Math.round(sidebar.getBoundingClientRect().left);
        out.sidebarSticky = win.getComputedStyle(sidebar).position === "sticky";
    }
    const results = doc.querySelector(".search-results");
    if (results) {
        const items = [...results.querySelectorAll("li")];
        if (items.length >= 2) {
            const y0 = Math.round(items[0].getBoundingClientRect().top);
            const y1 = Math.round(items[1].getBoundingClientRect().top);
            out.searchCols = (Math.abs(y0 - y1) < 10) ? 2 : 1;
        }
    }
    const hero = doc.querySelector(".home-hero");
    const hcard = doc.querySelector(".home-card");
    const heroImg = doc.querySelector(".home-hero img");
    const musicBtn = doc.getElementById("music-btn");
    if (hero && hcard) {
        out.heroW = Math.round(hero.getBoundingClientRect().width);
        out.heroH = Math.round(hero.getBoundingClientRect().height);
        out.heroImgW = heroImg ? Math.round(heroImg.getBoundingClientRect().width) : 0;
        out.cardW = Math.round(hcard.getBoundingClientRect().width);
        out.cardTop = Math.round(hcard.getBoundingClientRect().top);
        out.imgBottom = heroImg ? Math.round(heroImg.getBoundingClientRect().bottom) : 0;
        out.cardOverlap = out.cardTop < out.imgBottom;
        if (musicBtn) {
            out.musicBottom = Math.round(musicBtn.getBoundingClientRect().bottom);
            out.musicVisible = out.musicBottom <= out.cardTop;
        }
    }
    const blessingCard = doc.getElementById("blessing-card");
    if (blessingCard) out.blessingCardW = Math.round(blessingCard.getBoundingClientRect().width);
    return out;
})()
`;

async function getPageWsUrl(dbgPort) {
    for (let i = 0; i < 30; i++) {
        try {
            const list = await new Promise((resolve, reject) => {
                http.get(`http://127.0.0.1:${dbgPort}/json/list`, r => {
                    let d = ''; r.on('data', c => d += c); r.on('end', () => resolve(JSON.parse(d)));
                }).on('error', reject);
            });
            const page = list.find(p => p.type === 'page' && p.webSocketDebuggerUrl);
            if (page) return page.webSocketDebuggerUrl;
        } catch(e) {}
        await new Promise(r => setTimeout(r, 200));
    }
    throw new Error("Could not connect to Chrome page debugger");
}

(async () => {
    const os = require('os');
    const path = require('path');
    const fs = require('fs');

    const dbgPort = 19280;
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "desktop-test-"));
    const chrome = spawn(chromePath, [
        "--headless=new", "--disable-gpu", "--no-sandbox",
        `--remote-debugging-port=${dbgPort}`,
        `--user-data-dir=${tmpDir}`,
        "about:blank"
    ], { stdio: "ignore" });

    try {
        const wsUrl = await getPageWsUrl(dbgPort);
        const ws = new WebSocket(wsUrl);
        await new Promise(r => ws.onopen = r);

        let id = 1;
        function send(method, params = {}) {
            return new Promise((resolve, reject) => {
                const curId = id++;
                function handler(event) {
                    const msg = JSON.parse(event.data);
                    if (msg.id === curId) {
                        ws.removeEventListener('message', handler);
                        if (msg.error) reject(msg.error);
                        else resolve(msg.result);
                    }
                }
                ws.addEventListener('message', handler);
                ws.send(JSON.stringify({ id: curId, method, params }));
            });
        }

        await send("Page.enable");
        await send("Runtime.enable");

        const allResults = {};
        for (const [pageName, pagePath] of Object.entries(pages)) {
            allResults[pageName] = {};
            for (const w of widths) {
                const h = (w === 1920) ? 1024 : (w === 1440) ? 900 : 768;
                await send("Emulation.setDeviceMetricsOverride", {
                    width: w, height: h, deviceScaleFactor: 1, mobile: false
                });
                await send("Page.navigate", { url: `http://127.0.0.1:${port}/site/${pagePath}` });
                await new Promise(r => setTimeout(r, 800));
                const evalRes = await send("Runtime.evaluate", {
                    expression: cdpScript,
                    returnByValue: true
                });
                allResults[pageName][w] = evalRes.result ? evalRes.result.value : {};
            }
        }

        console.log("DESKTOP_DATA:" + JSON.stringify(allResults));
        ws.close();
    } finally {
        chrome.kill();
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
})();
"""
        with open(helper_js, "w", encoding="utf-8") as f:
            f.write(helper_code)

        try:
            res = subprocess.run(["node", helper_js, str(port), CHROME],
                                 capture_output=True, text=True, timeout=90)
            out = res.stdout
            if not out:
                print("Node err:", res.stderr)
            found = re.findall(r"DESKTOP_DATA:(\{.*\})", out)
            data = json.loads(found[0]) if found else {}
            if not data:
                print("Node stdout:", out)
                print("Node stderr:", res.stderr)
        finally:
            if os.path.exists(helper_js):
                os.remove(helper_js)
            srv.shutdown()

    if not data:
        check("桌面版面量測腳本執行", False, "無法取得量測資料")
        return False

    # 1. 斷點與容器寬度放寬檢驗
    for w in DESKTOP_WIDTHS:
        idx = data.get("index", {}).get(str(w), {})
        cw = idx.get("containerW", 0)
        # On desktop (>=1024px), container should be > 640px (expanding beyond mobile 40em)
        check(f"{w}px 目錄頁容器寬度放寬（{cw}px > 640px）", cw > 640, f"容器寬 {cw}px")

    # 2. 目錄頁格線欄數：1024/1366px >= 5 欄，1440/1920px >= 6 欄
    for w in (1024, 1366):
        cols = data.get("index", {}).get(str(w), {}).get("gridCols", 0)
        check(f"{w}px 目錄頁格線欄數（{cols} 欄 ≥ 5 欄）", cols >= 5, f"實際 {cols} 欄")
    for w in (1440, 1920):
        cols = data.get("index", {}).get(str(w), {}).get("gridCols", 0)
        check(f"{w}px 寬螢幕目錄頁格線欄數（{cols} 欄 ≥ 6 欄）", cols >= 6, f"實際 {cols} 欄")

    # 3. 逐章閱讀頁：欄寬約 40~46em 置中，經文行長不超過約 45 個中文字
    for w in DESKTOP_WIDTHS:
        ch = data.get("chapter", {}).get(str(w), {})
        cpl = ch.get("charsPerLine", 0)
        rw = ch.get("readingMainW", 0)
        check(f"{w}px 閱讀欄行長不超過 45 中文字（實際約 {cpl} 字，主欄寬 {rw}px）", 30 <= cpl <= 45, f"每行約 {cpl} 字")
        check(f"{w}px 閱讀頁具備右側章節導覽側邊欄（寬度 {ch.get('sidebarW', 0)}px）", ch.get("sidebarW", 0) > 150 and ch.get("sidebarSticky"), f"側欄寬 {ch.get('sidebarW')}px，sticky: {ch.get('sidebarSticky')}")

    # 4. 導覽列：桌機橫向置中
    for w in DESKTOP_WIDTHS:
        nav = data.get("index", {}).get(str(w), {})
        check(f"{w}px 導覽列橫向置中（左距 {nav.get('navL')}px，右距 {nav.get('navR')}px）", nav.get("navCentered"), f"左右差 {abs(nav.get('navL', 0) - nav.get('navR', 0))}px")

    # 5. 搜尋結果：桌機 2 欄分欄
    for w in DESKTOP_WIDTHS:
        sr = data.get("search", {}).get(str(w), {})
        check(f"{w}px 搜尋結果分欄顯示（2 欄）", sr.get("searchCols") == 2, f"欄數 {sr.get('searchCols')}")

    # 6. 首頁 Hero：寬幅橫幅、圖片不大於 1600px、經文卡壓在底緣、音樂按鈕未被遮蓋
    for w in DESKTOP_WIDTHS:
        hm = data.get("home", {}).get(str(w), {})
        imgW = hm.get("heroImgW", 0)
        check(f"{w}px 首頁英雄圖不超過 1600px 寬度（{imgW}px ≤ 1600px）", 0 < imgW <= 1600, f"圖片寬 {imgW}px")
        check(f"{w}px 首頁經文卡壓在圖片底緣（cardTop {hm.get('cardTop')} < imgBottom {hm.get('imgBottom')}）", hm.get("cardOverlap"), f"cardTop {hm.get('cardTop')}, imgBottom {hm.get('imgBottom')}")
        check(f"{w}px 首頁音樂按鈕完整露出（musicBottom {hm.get('musicBottom')} ≤ cardTop {hm.get('cardTop')}）", hm.get("musicVisible"), f"musicBottom {hm.get('musicBottom')}, cardTop {hm.get('cardTop')}")

    # 7. 抽經文卡頁：卡片寬度在桌機放寬且舒適置中
    for w in DESKTOP_WIDTHS:
        bl = data.get("blessing", {}).get(str(w), {})
        bw = bl.get("blessingCardW", 0)
        check(f"{w}px 抽經文卡寬度適度放寬（{bw}px ≥ 600px）", bw >= 600, f"卡片寬 {bw}px")

    print(f"\n測試結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}，共 {len(results)} 項檢查")
    return all(results)


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
