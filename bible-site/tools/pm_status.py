#!/usr/bin/env python3
"""PM progress report for the Bible site. Reads the real state of the project (files, check_all.py,
REVIEW.md, TODO.md) and rewrites the auto-generated block in PROGRESS.md between the
<!-- pm:auto:start --> and <!-- pm:auto:end --> markers. Nothing here asks a model for a verdict.
Usage: python3 bible-site/tools/pm_status.py [--no-checks]   (--no-checks skips running check_all.py)"""
import datetime, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_FILES = ["app.js", "style.css", "chapter.html", "index.html", "search.html", "card.html"]
START, END = "<!-- pm:auto:start -->", "<!-- pm:auto:end -->"


def exists(rel):
    p = os.path.join(ROOT, rel)
    return os.path.isfile(p) and os.path.getsize(p) > 0


def last_check_all():
    """Run check_all.py and return (exit code, last line)."""
    p = subprocess.run([sys.executable, "tools/check_all.py"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    return p.returncode, (lines[-1] if lines else "(no output)")


def review_state():
    p = os.path.join(ROOT, "REVIEW.md")
    if not os.path.isfile(p):
        return "尚未審核（沒有 REVIEW.md）"
    s = open(p, encoding="utf-8").read()
    return f"通過 {len(re.findall('通過', s)) - len(re.findall('不通過', s))} 項，不通過 {len(re.findall('不通過', s))} 項（粗略計數，請人工看 REVIEW.md）"


def todo_open():
    p = os.path.join(ROOT, "TODO.md")
    if not os.path.isfile(p):
        return None
    return sum(1 for l in open(p, encoding="utf-8") if l.lstrip().startswith("- [ ]"))


def main():
    present = [f for f in SITE_FILES if exists(f"site/{f}")]
    if "--no-checks" in sys.argv:
        fails = os.path.join(ROOT, "FAILS.md")
        passed = os.path.isfile(fails) and "全部通過" in open(fails, encoding="utf-8").read()
        code, summary = (0 if passed else 1), "沿用上次 check_all.py 的結果（FAILS.md）：" + ("全部通過" if passed else "有不通過項目")
    else:
        code, summary = last_check_all()
    todo = todo_open()
    steps = [
        ("0 資料產生（mark.json 678 節）", exists("data/mark.json")),
        ("1 建站（site/ 6 個檔案）", len(present) == len(SITE_FILES)),
        ("2 自動檢查 check_all.py 全過", code == 0),
        ("3 審核（REVIEW.md）", exists("REVIEW.md")),
        ("4 修正與 CHANGELOG.md", exists("CHANGELOG.md")),
        ("5 TODO.md 清空或不存在", todo in (None, 0)),
    ]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    block = [START, f"更新時間：{now}（由 `python3 bible-site/tools/pm_status.py` 產生，請勿手改此區塊）", "",
             "| 步驟 | 狀態 |", "|---|---|"]
    block += [f"| {name} | {'完成' if ok else '未完成'} |" for name, ok in steps]
    block += ["", f"- site 檔案：{len(present)}/{len(SITE_FILES)}（缺：{'、'.join(f for f in SITE_FILES if f not in present) or '無'}）",
              f"- check_all.py：{summary}", f"- 審核：{review_state()}",
              f"- TODO.md 未完成項目：{'沒有 TODO.md' if todo is None else todo}", END]
    path = os.path.join(ROOT, "PROGRESS.md")
    text = open(path, encoding="utf-8").read() if os.path.isfile(path) else f"# PM 進度\n\n{START}\n{END}\n"
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), "\n".join(block), text, flags=re.S)
    else:
        text += "\n" + "\n".join(block) + "\n"
    open(path, "w", encoding="utf-8").write(text)
    print("\n".join(block[1:-1]))
    all_done = all(ok for _, ok in steps)
    print("\n整體：" + ("全部完成" if all_done else "還有未完成的步驟"))
    return 0 if all_done else 1


if __name__ == "__main__":
    sys.exit(main())
