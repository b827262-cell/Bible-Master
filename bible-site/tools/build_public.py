#!/usr/bin/env python3
"""Build the public Cloudflare Pages bundle: dist/ at the repo root.
Whitelist copy of bible-site/index.html (plus a generated 404.html and _headers), bible-site/site/ and the data files the pages fetch; the layout of bible-site/ is kept
because the pages read ../data/*.json. Never ships admin/, tests/, tools/, reports, .verify/ or unreferenced uploads.
Usage: python3 bible-site/tools/build_public.py [--out DIR] [--root DIR]   (default out: <repo>/dist; --root: a copy of bible-site/, for tests)"""
import argparse, json, os, re, shutil, sys

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(SITE_ROOT, ".."))
DATA_FILES = ["mat.json", "mrk.json", "luk.json", "jhn.json", "blessing.json", "home.json", "zone-music.json", "blessing-art.json", "devotional.json"]
ALWAYS_ASSETS = {"assets/jordan.jpg", "assets/home-music.mp3"}
MAX_FILE = 25 * 1024 * 1024
# Cloudflare joins the values of every matching rule for the same header, so each path may match at most ONE Cache-Control rule.
# Only the media assets get one; HTML, CSS, JS and JSON keep the Pages default (public, max-age=0, must-revalidate).
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/site/assets/*
  Cache-Control: public, max-age=86400
"""


NOT_FOUND = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>找不到頁面 - 四福音（和合本）</title>
  <link rel="icon" href="data:,">
  <style>
    body { margin: 0; font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif; background: #f6f4ef; color: #2b2622; line-height: 1.75; }
    main { max-width: 32em; margin: 0 auto; padding: 4rem 1rem; text-align: center; }
    h1 { font-size: 1.5rem; }
    a { display: inline-block; min-height: 44px; padding: 0.6em 1.4em; border-radius: 8px; background: #7a4a1e; color: #fff; text-decoration: none; }
    a:focus-visible { outline: 2px solid #1a56c7; outline-offset: 2px; }
    @media (prefers-color-scheme: dark) { body { background: #1c1a17; color: #ece7df; } a { background: #d9a566; color: #1c1a17; } }
  </style>
</head>
<body>
  <main>
    <h1>找不到這個頁面</h1>
    <p>網址可能已更改，或輸入有誤。</p>
    <p><a href="/site/home.html">回到首頁</a></p>
  </main>
</body>
</html>
"""


def referenced_assets():
    """assets/<name> paths used by the pages, scripts and styles, plus the ones named in data/home.json."""
    used = set(ALWAYS_ASSETS)
    site = os.path.join(SITE_ROOT, "site")
    for dp, _, fs in os.walk(site):
        for f in fs:
            if f.endswith((".html", ".css", ".js")):
                used.update(re.findall(r"assets/[A-Za-z0-9._-]+\.[A-Za-z0-9]+", open(os.path.join(dp, f), encoding="utf-8").read()))
    home = os.path.join(SITE_ROOT, "data", "home.json")
    if os.path.exists(home):
        cfg = json.load(open(home, encoding="utf-8"))
        used.update(v for k, v in cfg.items() if k in ("image", "music") and isinstance(v, str))
    zone_music = os.path.join(SITE_ROOT, "data", "zone-music.json")
    if os.path.exists(zone_music):
        zone_cfg = json.load(open(zone_music, encoding="utf-8"))
        used.update(v for k, v in zone_cfg.items() if k == "music" and isinstance(v, str))

    blessing_art = os.path.join(SITE_ROOT, "data", "blessing-art.json")
    if os.path.exists(blessing_art):
        blessing_cfg = json.load(open(blessing_art, encoding="utf-8"))
        for work in blessing_cfg.values():
            if isinstance(work, dict) and "image" in work and isinstance(work["image"], str):
                used.add(work["image"])
    return used


def build(out):
    out = os.path.abspath(out)
    if out in (REPO, SITE_ROOT, "/") or not os.path.basename(out):
        raise SystemExit(f"拒絕使用 {out} 當輸出目錄")
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    shutil.copy(os.path.join(SITE_ROOT, "index.html"), os.path.join(out, "index.html"))
    used = referenced_assets()
    skipped = []
    for dp, dn, fs in os.walk(os.path.join(SITE_ROOT, "site")):
        dn[:] = [d for d in dn if not d.startswith(".")]
        for f in fs:
            if f.startswith("."):
                continue
            src = os.path.join(dp, f)
            rel = os.path.relpath(src, os.path.join(SITE_ROOT, "site"))
            if rel.startswith("assets" + os.sep) and rel.replace(os.sep, "/") not in used:
                skipped.append(rel)
                continue
            dst = os.path.join(out, "site", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
    os.makedirs(os.path.join(out, "data"))
    for f in DATA_FILES:
        src = os.path.join(SITE_ROOT, "data", f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(out, "data", f))
    open(os.path.join(out, "_headers"), "w", encoding="utf-8").write(HEADERS)
    open(os.path.join(out, "404.html"), "w", encoding="utf-8").write(NOT_FOUND)
    for dp, dn, fs in os.walk(out):
        for d in dn:
            os.chmod(os.path.join(dp, d), 0o755)
        for f in fs:
            os.chmod(os.path.join(dp, f), 0o644)
    return skipped


def main():
    global SITE_ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "dist"))
    ap.add_argument("--root", default=SITE_ROOT)
    args = ap.parse_args()
    SITE_ROOT = os.path.abspath(args.root)
    skipped = build(args.out)
    files = [os.path.join(dp, f) for dp, _, fs in os.walk(args.out) for f in fs]
    total = sum(os.path.getsize(f) for f in files)
    print(f"已建置 {args.out}：{len(files)} 個檔案，共 {total / 1024 / 1024:.1f} MB")
    for s in skipped:
        print(f"略過未使用的素材：{s}")
    big = [f for f in files if os.path.getsize(f) > MAX_FILE]
    if big:
        print("不通過：單檔超過 25 MiB（Cloudflare Pages 上限）：" + "、".join(big))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
