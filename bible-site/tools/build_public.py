#!/usr/bin/env python3
"""Build the public Cloudflare Pages bundle: dist/ at the repo root.
Whitelist copy of bible-site/index.html, bible-site/site/ and the data files the pages fetch; the layout of bible-site/ is kept
because the pages read ../data/*.json. Never ships admin/, tests/, tools/, reports, .verify/ or unreferenced uploads.
Usage: python3 bible-site/tools/build_public.py [--out DIR] [--root DIR]   (default out: <repo>/dist; --root: a copy of bible-site/, for tests)"""
import argparse, json, os, re, shutil, sys

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(SITE_ROOT, ".."))
DATA_FILES = ["mat.json", "mrk.json", "luk.json", "jhn.json", "blessing.json", "home.json"]
ALWAYS_ASSETS = {"assets/jordan.jpg", "assets/home-music.mp3"}
MAX_FILE = 25 * 1024 * 1024
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/*.html
  Cache-Control: public, max-age=0, must-revalidate

/site/*
  Cache-Control: public, max-age=0, must-revalidate

/data/*
  Cache-Control: public, max-age=0, must-revalidate

/site/assets/*
  Cache-Control: public, max-age=86400
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
