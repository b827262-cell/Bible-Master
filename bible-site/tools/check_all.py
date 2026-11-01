#!/usr/bin/env python3
"""Run every automatic check for the Bible site in one go:
  tools/verify_text.py   scripture matches the verified text, nothing hard-coded in site/
  tests/smoke.js         verse counts per chapter, required site files
  tests/site_checks.py   links, external resources, pages rendered in headless Chrome
Appends a timestamped section to TEST-REPORT.md and rewrites FAILS.md with every failing line
(verbatim, for the chief editor's fix round). Exit code 0 only when all three pass.
Usage: python3 bible-site/tools/check_all.py   (from any directory)"""
import datetime, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHECKS = [("經文比對", [sys.executable, "tools/verify_text.py"]),
          ("節數與檔案", ["node", "tests/smoke.js"]),
          ("網站檢查", [sys.executable, "tests/site_checks.py"])]


def run(cmd):
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
        return p.returncode == 0, (p.stdout + p.stderr).strip()
    except Exception as e:  # missing node/chrome, timeout
        return False, f"無法執行：{e}"


def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report, fails, passed = [f"\n## {now}\n"], [], 0
    for name, cmd in CHECKS:
        ok, out = run(cmd)
        passed += ok
        print(f"[{'通過' if ok else '不通過'}] {name}\n{out}\n")
        report.append(f"### {name}：{'通過' if ok else '不通過'}\n```\n{out}\n```\n")
        if not ok:
            lines = [l for l in out.splitlines() if not l.startswith("結果：")
                     and ("不通過" in l or "不符" in l or "無法執行" in l or "缺少" in l)]
            fails += [f"- [ ] {name}｜{l.strip()}" for l in (lines or [out.splitlines()[-1] if out else "沒有輸出"])]
    summary = f"總結：{passed}/{len(CHECKS)} 項檢查通過"
    report.append(f"**{summary}**\n")
    with open(os.path.join(ROOT, "TEST-REPORT.md"), "a", encoding="utf-8") as f:
        if f.tell() == 0:
            f.write("# 測試報告（由 tools/check_all.py 產生）\n")
        f.write("".join(report))
    with open(os.path.join(ROOT, "FAILS.md"), "w", encoding="utf-8") as f:
        f.write(f"# 不通過項目（{now}，由 tools/check_all.py 產生，主編只修這些）\n\n" + ("\n".join(fails) if fails else "全部通過，沒有要修的項目。") + "\n")
    print(summary)
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
