#!/usr/bin/env python3
"""Publish the site: local dev environment -> GitHub -> Cloudflare Pages (bible.b827262.org).
One-way sync, the local files are the source of truth. Order: check_all.py (must be 3/3) -> service_checks.py admin homeadmin -> build_public.py -> deploy_checks.py
-> list the files that would be committed and wait for a typed "yes" -> git commit -> git push.
Default target is the `preview` branch (Cloudflare gives it a preview URL); `--prod` pushes `main` (the live site).
Usage: python3 bible-site/tools/publish.py [--prod] [--yes] [--dry-run] [-m "message"]"""
import argparse, os, subprocess, sys

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(SITE_ROOT, ".."))
# only these paths are ever staged (explicit list: never `git add -A`, so logs/, .verify/ and tokens stay out)
STAGE = ["bible-site", "start.sh", "service.sh", ".gitignore", "CLAUDE.md", "HANDOFF.md"]


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, **kw)


def step(title, cmd):
    print(f"\n== {title} ==")
    p = subprocess.run(cmd, cwd=REPO)
    if p.returncode != 0:
        print(f"不通過：{title}，已中止，沒有做任何 git 寫入。")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="發佈網站：本機 → GitHub → Cloudflare Pages。先跑全部檢查，確認後才提交與推送。")
    ap.add_argument("--prod", action="store_true", help="推到 main（正式上線）；沒有這個選項只推到 preview 分支預覽")
    ap.add_argument("--yes", action="store_true", help="略過輸入 yes 的確認（給自動化使用）")
    ap.add_argument("--dry-run", action="store_true", help="只跑檢查與建置，不做任何 git 寫入")
    ap.add_argument("-m", "--message", default="Update site content", help="提交訊息")
    args = ap.parse_args()

    step("全部檢查 check_all.py（必須 3/3）", [sys.executable, os.path.join("bible-site", "tools", "check_all.py")])
    step("後台檢查 service_checks.py admin homeadmin", [sys.executable, os.path.join("bible-site", "tests", "service_checks.py"), "admin", "homeadmin"])
    step("建置發佈包 build_public.py", [sys.executable, os.path.join("bible-site", "tools", "build_public.py")])
    step("發佈包檢查 deploy_checks.py", [sys.executable, os.path.join("bible-site", "tests", "deploy_checks.py")])
    if args.dry_run:
        print("\n--dry-run：檢查與建置都通過，沒有做任何 git 寫入。")
        return 0

    remote = run(["git", "remote", "get-url", "origin"])
    if remote.returncode != 0:
        print("\n還沒有設定 GitHub remote。請先在 GitHub 建立私有儲存庫，再執行：\n"
              "  git remote add origin git@github.com:<帳號>/<儲存庫>.git\n然後重新執行本指令。")
        return 2
    branch = "main" if args.prod else "preview"
    run(["git", "add", "--"] + [p for p in STAGE if os.path.exists(os.path.join(REPO, p))])
    diff = run(["git", "diff", "--cached", "--stat"]).stdout.strip()
    print(f"\n將提交的檔案：\n{diff or '（沒有變更）'}\n推送目標：origin/{branch}" + ("（正式網站）" if args.prod else "（預覽）"))
    if diff and not args.yes:
        if input("確認提交並推送？請輸入 yes：").strip().lower() != "yes":
            run(["git", "reset", "-q"])
            print("已取消，暫存區已還原，沒有提交。")
            return 1
    if diff:
        p = run(["git", "commit", "-m", args.message])
        if p.returncode != 0:
            print(p.stdout + p.stderr)
            return 1
    p = subprocess.run(["git", "push", "origin", f"HEAD:{branch}"], cwd=REPO)
    if p.returncode != 0:
        print("推送失敗，請確認 GitHub 權限與網路。")
        return 1
    print(f"\n已推送到 origin/{branch}。Cloudflare Pages 約 1 分鐘內完成建置；" +
          ("正式網站：https://bible.b827262.org/" if args.prod else "請到 Cloudflare Dashboard → Pages → Deployments 開預覽網址確認，再用 --prod 上線。"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
