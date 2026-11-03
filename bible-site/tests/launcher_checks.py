#!/usr/bin/env python3
"""Static checks of start.sh (service.sh is a symlink to it); exit code 0 only when all pass.
  syntax  bash -n passes, service.sh is still a symlink to start.sh
  entry   every printed front-end URL points at the root (/), and the book index is listed separately as 四福音目錄
  data    the "data not built" test covers mat/mrk/luk/jhn; a missing blessing.json only warns and never runs build_data.py
Usage: python3 bible-site/tests/launcher_checks.py [syntax] [entry] [data] [--grep REGEX]   (no group: all)"""
import os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
START = os.path.join(ROOT, "start.sh")
results = []
ONLY = None


def check(name, ok, detail=""):
    if ONLY and not re.search(ONLY, name):
        return
    results.append(ok)
    print(("通過" if ok else "不通過") + f"：{name}" + (f"（{detail}）" if detail else ""))


def main(groups):
    src = open(START, encoding="utf-8").read()
    lines = src.splitlines()
    if "syntax" in groups:
        p = subprocess.run(["bash", "-n", START], capture_output=True, text=True)
        check("start.sh 語法正確（bash -n）", p.returncode == 0, p.stderr.strip()[:200])
        s = os.path.join(ROOT, "service.sh")
        check("service.sh 仍然是指向 start.sh 的符號連結", os.path.islink(s) and os.readlink(s) == "start.sh")
    if "entry" in groups:
        urls = [(i + 1, l) for i, l in enumerate(lines) if "echo" in l and "FRONTEND_PORT}" in l and "http" in l]
        check("start.sh 至少印出 4 行前台網址（啟動與 status 各有本機與 Tailscale）", len(urls) >= 4, f"{len(urls)} 行")
        entry = [(n, l) for n, l in urls if "四福音目錄" not in l]
        bad = [n for n, l in entry if not re.search(r"\$\{FRONTEND_PORT\}/(?!site/)", l) and not re.search(r"\$\{FRONTEND_PORT\}/\$\{NC\}", l)]
        check("入口網址都指向根目錄 /（不再是 site/index.html）", len(entry) >= 4 and not bad, "行 " + "、".join(map(str, bad)) if bad else f"{len(entry)} 行")
        cat = [l for n, l in urls if "四福音目錄" in l and "/site/index.html" in l]
        check("目錄頁另外以「四福音目錄」標示並連到 /site/index.html（本機與 Tailscale 各一行以上）", len(cat) >= 2, f"{len(cat)} 行")
        stale = [n for n, l in urls if "四福音目錄" not in l and "site/index.html" in l]
        check("沒有任何入口行還指向 site/index.html", not stale, "行 " + "、".join(map(str, stale)))
    if "data" in groups:
        cond = next((l for l in lines if l.lstrip().startswith("if [") and "data/mat.json" in l), "")
        full = " ".join(lines[lines.index(cond):lines.index(cond) + 3]) if cond else ""
        check("經文資料檢查涵蓋 mat、mrk、luk、jhn 四個 json", all(f"data/{k}.json" in full for k in ("mat", "mrk", "luk", "jhn")), full.strip()[:160])
        check("經文資料檢查條件沒有提到 blessing.json（缺它不應重建經文）", "blessing" not in full)
        warn = [l for l in lines if "blessing.json" in l and re.search(r"print_warn|warn", l)]
        check("缺少 blessing.json 時只印警告（有 print_warn 提到 blessing.json）", bool(warn), warn[0].strip()[:100] if warn else "")
        i = next((i for i, l in enumerate(lines) if "blessing.json" in l and "print_warn" in l), None)
        blk = "\n".join(lines[max(0, i - 3):i + 3]) if i is not None else ""
        check("blessing.json 的警告附近沒有呼叫 build_data.py", i is not None and "build_data" not in blk)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--grep" in args:
        i = args.index("--grep")
        ONLY = args[i + 1]
        del args[i:i + 2]
    main(set(args) or {"syntax", "entry", "data"})
    if ONLY and not results:
        results.append(False)
        print(f"不通過：--grep {ONLY} 沒有對到任何檢查")
    print(f"結果：{'全部通過' if all(results) else f'不通過（{results.count(False)} 項）'}")
    sys.exit(0 if all(results) else 1)
