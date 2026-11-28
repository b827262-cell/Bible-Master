#!/usr/bin/env python3
"""福音藝廊（gallery.html）全自動檢查 — exit 0 才算通過。

三大項：
  (a) 靜態檢查：gallery.html / gallery.js / data/gospel-gallery.json
      零寫死經文（四福音全部經文逐字掃描，經文必須由 Bible.load 讀取）、
      無外部資源（http/https/cdn）、全繁體中文（無簡體字、無日文假名）、
      7 張 gallery-N-*.jpg 均 1600x900 且 <1MB、7 首 .wav 存在且 <3MB。
  (b) 發佈包檢查：tools/build_public.py 輸出到 tempfile 暫存目錄（不碰 repo dist），
      確認 data/gospel-gallery.json、site/gallery.html、site/gallery.js 與全部 14 個圖音素材。
  (c) Headless Chrome 實機渲染（/usr/bin/google-chrome，375px 與 1440px）：
      day=1/3/7 主圖 naturalWidth>=1200、畫面經文與 data/*.json 逐字一致、
      audio 元素 src 正確且具 loop、點擊「下一幅」切換正常、0 個 JS 錯誤、
      375px 無橫向捲動。全程唯讀瀏覽，不送任何終端按鍵、不耗任何模型額度。

Usage: python3 -B bible-site/tests/gallery_checks.py
"""
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import urllib.parse

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # bible-site/
CHROME = next((c for c in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable") if os.path.exists(c)), None)
GALLERY_DAYS = [1, 3, 7]
WIDTHS = [375, 1440]
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("通過" if ok else "不通過") + f"：{name}" + (f"（{detail}）" if detail else ""))


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------- (a) 靜態檢查

def expected_verse_text(book, ch, v):
    """與 gallery.js findVerse 相同的找節邏輯，從 data/<book>.json 取經文原文。"""
    data = json.loads(read(os.path.join(SITE_ROOT, "data", f"{book}.json")))
    for chapter in data["chapters"]:
        if int(chapter["ch"]) != int(ch):
            continue
        for item in chapter["verses"]:
            if int(item["v"]) == int(v):
                return item["text"]
            end = item.get("end")
            if end is not None and int(v) >= int(item["v"]) and int(v) <= int(end):
                return item["text"]
    return None


def jpeg_size(path):
    """解析 JPEG SOF 段取得（寬, 高）；不倚賴 PIL。"""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height = int.from_bytes(data[i + 5:i + 7], "big")
            width = int.from_bytes(data[i + 7:i + 9], "big")
            return width, height
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return None


# 常見簡體專用字（正體皆作他字）；用於「無簡體」掃描。
SIMPLIFIED_CHARS = (
    "万与专业东两严丧个临为丽举义乐书买乱亏云亚产亲亵仪价从众优会伟传伤伪体余佣俩俭债倾偿储儿兑兰关兴养内"
    "写军农冲决冻净减凑凤凭凯击凿划刘则刚创剂剐剑剧劝办动势勋匀医华协单卖卢卫厂厅历压厌县双发号叶吗员呐咏"
    "哑唤啸啰团圆围囤囵国帧师帮带归当录彻忆忧怀态怜总恋恳恶悯惊惧惨惩愤悬懒扩扫扬扰抚抛抢护报担拟拢拣拥挚"
    "挛挟挠挡挣挤挥捞损捡换捣掷揽摄"
)
SIMPLIFIED_CHARS = "".join(dict.fromkeys(SIMPLIFIED_CHARS))  # 去重


def static_checks():
    html_path = os.path.join(SITE_ROOT, "site", "gallery.html")
    js_path = os.path.join(SITE_ROOT, "site", "gallery.js")
    data_path = os.path.join(SITE_ROOT, "data", "gospel-gallery.json")
    html_src, js_src, json_src = read(html_path), read(js_path), read(data_path)
    gallery = json.loads(json_src)
    texts = {"gallery.html": html_src, "gallery.js": js_src, "gospel-gallery.json": json_src}

    # (a1) 零寫死經文：四福音每一節（含合併節）逐字掃描三個檔案
    leaked = []
    total_verses = 0
    for book in ("mat", "mrk", "luk", "jhn"):
        data = json.loads(read(os.path.join(SITE_ROOT, "data", f"{book}.json")))
        for chapter in data["chapters"]:
            for item in chapter["verses"]:
                total_verses += 1
                text = str(item["text"]).strip()
                if len(text) < 6:
                    continue
                for name, src in texts.items():
                    if text in src:
                        leaked.append(f"{book} {chapter['ch']}:{item['v']} 出現在 {name}")
    check(f"(a) 零寫死經文：四福音 {total_verses} 節逐字掃描 gallery.html/gallery.js/gospel-gallery.json 均未出現",
          not leaked, "；".join(leaked[:4]))

    # (a2) 經文必須由 Bible.load 讀取；資料檔不得夾帶經文文字欄位
    check("(a) gallery.js 透過 Bible.load(...) 從 data/*.json 讀取經文", "Bible.load(" in js_src)
    bad_keys = []
    for item in gallery.get("items", []):
        hit = [k for k in item if k in ("text", "verse", "content", "verse_text")]
        if hit:
            bad_keys.append(f"day={item.get('day')} 有欄位 {'、'.join(hit)}")
    check("(a) gospel-gallery.json 七個 items 都不夾帶經文文字欄位（座標 book/ch/v 而已）",
          not bad_keys, "；".join(bad_keys))

    # (a3) 無外部資源
    external = []
    for name, src in texts.items():
        for match in re.findall(r"https?://[^\s\"'<>)]+", src):
            external.append(f"{name}: {match[:60]}")
        if re.search(r"""(src|href)\s*=\s*["']//""", src):
            external.append(f"{name}: protocol-relative URL (//...)")
    check("(a) gallery.html / gallery.js / gospel-gallery.json 無任何外部（http/cdn）資源",
          not external, "；".join(external[:4]))

    # (a4) 全繁體中文：無簡體字、無日文假名、lang=zh-Hant
    kana = []
    simplified = []
    for name, src in texts.items():
        # U+30FB（・）是中文慣用間隔號，不算日文假名
        hit_kana = sorted(set(re.findall(r"[\u3040-\u30fa\u30fc-\u30ff\u31f0-\u31ff]", src)))
        if hit_kana:
            kana.append(f"{name}: {''.join(hit_kana[:10])}")
        hit_sc = sorted(set(ch for ch in src if ch in SIMPLIFIED_CHARS))
        if hit_sc:
            simplified.append(f"{name}: {''.join(hit_sc[:10])}")
    check("(a) 三檔無日文假名", not kana, "；".join(kana))
    check("(a) 三檔無簡體字（常見簡體專用字掃描）", not simplified, "；".join(simplified))
    check("(a) gallery.html 標示 lang=zh-Hant", re.search(r'<html\s+lang="zh-Hant"', html_src) is not None)

    # (a5) 7 張圖 1600x900 且 <1MB；7 首 wav 存在、RIFF/WAVE、<3MB
    img_bad, wav_bad = [], []
    for item in gallery.get("items", []):
        img = os.path.join(SITE_ROOT, "site", item["image"])
        wav = os.path.join(SITE_ROOT, "site", item["audio"])
        day = item.get("day")
        if not os.path.exists(img):
            img_bad.append(f"day={day} 缺 {item['image']}")
        else:
            size = os.path.getsize(img)
            dims = jpeg_size(img)
            if dims != (1600, 900):
                img_bad.append(f"day={day} 尺寸 {dims}（要 1600x900）")
            if size >= 1024 * 1024:
                img_bad.append(f"day={day} {size} bytes（要 <1MB）")
        if not os.path.exists(wav):
            wav_bad.append(f"day={day} 缺 {item['audio']}")
        else:
            with open(wav, "rb") as fh:
                head = fh.read(12)
            size = os.path.getsize(wav)
            if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
                wav_bad.append(f"day={day} 不是 RIFF/WAVE")
            if size >= 3 * 1024 * 1024:
                wav_bad.append(f"day={day} {size} bytes（要 <3MB）")
    check("(a) 7 張經文油畫都是 1600x900 且 <1MB", not img_bad, "；".join(img_bad[:4]))
    check("(a) 7 首配樂 .wav 都存在、為 RIFF/WAVE 且 <3MB", not wav_bad, "；".join(wav_bad[:4]))


# ---------------------------------------------------------------- (b) 發佈包檢查

def build_checks():
    gallery = json.loads(read(os.path.join(SITE_ROOT, "data", "gospel-gallery.json")))
    want_assets = sorted({item["image"] for item in gallery["items"]} | {item["audio"] for item in gallery["items"]})
    with tempfile.TemporaryDirectory(prefix="gallery-build-") as out:
        proc = subprocess.run(
            [sys.executable, os.path.join(SITE_ROOT, "tools", "build_public.py"), "--out", out],
            capture_output=True, text=True, timeout=120,
        )
        check("(b) build_public.py --out 暫存目錄 結束碼 0（repo dist/ 不被觸碰）", proc.returncode == 0,
              (proc.stdout + proc.stderr).strip()[:160])
        if proc.returncode != 0:
            return
        missing = []
        for rel in ("data/gospel-gallery.json", "site/gallery.html", "site/gallery.js"):
            if not os.path.exists(os.path.join(out, rel)):
                missing.append(rel)
        check("(b) 發佈包含 data/gospel-gallery.json、site/gallery.html、site/gallery.js", not missing,
              "缺 " + "、".join(missing))
        miss_assets = [rel for rel in want_assets if not os.path.exists(os.path.join(out, "site", rel))]
        check(f"(b) 發佈包含全部 {len(want_assets)} 個圖音素材（7 jpg + 7 wav）",
              len(want_assets) == 14 and not miss_assets, "缺 " + "、".join(miss_assets[:4]))


# ---------------------------------------------------------------- (c) Headless Chrome 實機渲染

# 探測頁：以 iframe 載入 /site/gallery.html?day=N&probe=1（handler 會注入 JS 錯誤攔截），
# 等圖片與經文載完，量測後點擊「下一幅」再量測一次，結果以 GALLERY_RESULT {...} 輸出。
PROBE_PAGE = """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><title>gallery probe</title></head>
<body>
<script>
(async function () {
  var q = new URLSearchParams(location.search);
  var day = q.get("day"), w = q.get("w");
  var frame = document.createElement("iframe");
  frame.style.border = "0";
  frame.width = w; frame.height = 900;
  frame.src = "/site/gallery.html?day=" + day + "&probe=1";
  document.body.appendChild(frame);
  await new Promise(function (r) { frame.addEventListener("load", r, { once: true }); });
  var doc = frame.contentDocument, win = frame.contentWindow;
  function until(fn, ticks) {
    ticks = ticks || 160;
    return new Promise(function (resolve) {
      var n = 0;
      (function poll() {
        if (fn() || n++ > ticks) { resolve(fn()); } else { setTimeout(poll, 50); }
      })();
    });
  }
  function el(id) { return doc.getElementById(id); }
  function snapshot() {
    var img = el("gal-img"), audio = el("gal-audio");
    return {
      img: img.getAttribute("src"),
      naturalWidth: img.naturalWidth,
      badge: el("gal-day-badge").textContent,
      theme: el("gal-theme").textContent,
      ref: el("gal-ref").textContent,
      verse: el("gal-verse").textContent,
      audioSrc: audio.getAttribute("src"),
      audioLoop: audio.hasAttribute("loop")
    };
  }
  var loadingTexts = ["正在載入經文…", "正在載入福音藝廊資料。", "無法載入經文資料。", "無法載入福音藝廊資料。"];
  function verseReady() {
    var t = el("gal-verse").textContent;
    return t && loadingTexts.indexOf(t) === -1;
  }
  await until(function () { return verseReady() && el("gal-img").complete && el("gal-img").naturalWidth > 0; });
  var before = snapshot();
  var stripCount = doc.querySelectorAll(".gal-thumb").length;

  el("gal-next").click();
  await until(function () {
    var img = el("gal-img");
    return img.getAttribute("src") !== before.img && img.complete && img.naturalWidth > 0;
  });
  await until(function () { return verseReady() && el("gal-verse").textContent !== before.verse; });
  var after = snapshot();

  var out = {
    before: before,
    after: after,
    stripCount: stripCount,
    errors: (win.__jsErrors || []).slice(),
    scroll: {
      sw: doc.documentElement.scrollWidth,
      cw: doc.documentElement.clientWidth
    }
  };
  var pre = document.createElement("pre");
  pre.id = "gallery-result";
  pre.textContent = "GALLERY_RESULT " + JSON.stringify(out);
  document.body.appendChild(pre);
})();
</script>
</body></html>
"""

# 注入到 gallery.html <head> 開頭的錯誤攔截（在任何頁面腳本之前執行）
ERROR_HOOK = (
    '<script>window.__jsErrors=[];'
    'window.addEventListener("error",function(e){window.__jsErrors.push(String((e&&e.message)||e.type))});'
    'window.addEventListener("unhandledrejection",function(e){'
    'window.__jsErrors.push("unhandledrejection:"+String((e&&e.reason)||""))});</script>'
)


class ProbeHandler(http.server.SimpleHTTPRequestHandler):
    """唯讀靜態服務 + 兩個記憶體產生的探測端點（不寫任何檔案）。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SITE_ROOT, **kwargs)

    def log_message(self, *args):  # 靜音
        pass

    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        path = parts.path
        if path.endswith("/tests/gallery_probe.html"):
            self._serve_bytes(PROBE_PAGE.encode("utf-8"))
            return
        if path.endswith("/site/gallery.html"):
            query = urllib.parse.parse_qs(parts.query)
            if query.get("probe", [""])[0] == "1":
                src = read(os.path.join(SITE_ROOT, "site", "gallery.html"))
                if "<head>" in src:
                    src = src.replace("<head>", "<head>" + ERROR_HOOK, 1)
                self._serve_bytes(src.encode("utf-8"))
                return
        super().do_GET()

    def _serve_bytes(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def probe(port, day, width):
    """跑一次 headless Chrome，回傳探測結果 dict（失敗回 {}）。"""
    query = urllib.parse.urlencode({"day": day, "w": width})
    with tempfile.TemporaryDirectory(prefix="gallery-chrome-") as profile:
        proc = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--virtual-time-budget=20000", f"--user-data-dir={profile}",
             f"--window-size={width},900", "--dump-dom",
             f"http://127.0.0.1:{port}/tests/gallery_probe.html?{query}"],
            capture_output=True, text=True, timeout=120,
        )
    found = re.findall(r"GALLERY_RESULT (\{.*\})", re.sub(r"<[^>]+>", "", proc.stdout))
    try:
        return json.loads(found[-1]) if found else {}
    except ValueError:
        return {}


def chrome_checks():
    if not CHROME:
        check("(c) Headless Chrome 實機渲染", False, "找不到 /usr/bin/google-chrome")
        return
    gallery = json.loads(read(os.path.join(SITE_ROOT, "data", "gospel-gallery.json")))
    items = {int(i["day"]): i for i in gallery["items"]}
    order = [int(i["day"]) for i in gallery["items"]]

    handler = ProbeHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        runs = {}
        for day in GALLERY_DAYS:
            for width in WIDTHS:
                runs[(day, width)] = probe(port, day, width)
        srv.shutdown()

    for day in GALLERY_DAYS:
        item = items[day]
        next_item = items[order[(order.index(day) + 1) % len(order)]]
        want_verse = expected_verse_text(item["book"], item["ch"], item["v"])
        next_verse = expected_verse_text(next_item["book"], next_item["ch"], next_item["v"])

        for width in WIDTHS:
            data = runs.get((day, width)) or {}
            tag = f"day={day} {width}px"
            if not data:
                check(f"(c) {tag} 探測頁輸出", False, "沒有 GALLERY_RESULT（頁面載入失敗或逾時）")
                continue
            before, after = data.get("before") or {}, data.get("after") or {}

            # 圖片：naturalWidth>=1200 且為當日素材
            check(f"(c) {tag} 主圖載入且為當日素材、naturalWidth>=1200",
                  before.get("img", "").endswith(item["image"]) and (before.get("naturalWidth") or 0) >= 1200,
                  f"img={before.get('img')} naturalWidth={before.get('naturalWidth')}")

            # 經文逐字一致（切換前）
            check(f"(c) {tag} 畫面經文與 data/{item['book']}.json 逐字一致",
                  before.get("verse") == want_verse,
                  f"畫面={str(before.get('verse'))[:40]!r} 資料={str(want_verse)[:40]!r}")

            # 0 個 JS 錯誤
            errs = data.get("errors") or []
            check(f"(c) {tag} 0 個 JS 錯誤", not errs, "；".join(errs[:3]))

            if width == 375:
                # audio：src 正確且具 loop
                check(f"(c) {tag} audio src={item['audio']} 且具 loop 屬性",
                      (before.get("audioSrc") or "").endswith(item["audio"]) and before.get("audioLoop") is True,
                      f"src={before.get('audioSrc')} loop={before.get('audioLoop')}")
                # 點擊「下一幅」
                check(f"(c) {tag} 點擊「下一幅」切到 day={next_item['day']}：圖、主題、經文、audio 皆正確",
                      after.get("img", "").endswith(next_item["image"])
                      and after.get("theme") == next_item["theme"]
                      and after.get("verse") == next_verse
                      and (after.get("audioSrc") or "").endswith(next_item["audio"])
                      and after.get("badge", "").find(next_item["weekday"]) != -1,
                      json.dumps({k: after.get(k) for k in ("img", "theme", "verse", "audioSrc", "badge")},
                                 ensure_ascii=False)[:200])
                # 375 無橫向捲動
                sc = data.get("scroll") or {}
                check(f"(c) {tag} 無橫向捲動（scrollWidth <= clientWidth）",
                      sc.get("sw", 1) <= sc.get("cw", 0), json.dumps(sc))


def main():
    print(f"== 福音藝廊檢查（site_root={SITE_ROOT}）==")
    static_checks()
    build_checks()
    chrome_checks()
    passed = sum(1 for r in results if r)
    print(f"\n總結：{passed}/{len(results)} 項檢查通過")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
