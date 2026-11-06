#!/usr/bin/env python3
"""Daily devotional release: export today's approved entries and push them to the live site.

Run by the systemd user timer bible-devotional-publish.timer at 06:00 Asia/Taipei, inside a
dedicated checkout of origin/main (never the developer's working copy). Steps:
  1. Do nothing before START (first release day).
  2. cli.py export --through <today>: only entries that passed BOTH human reviews and whose
     date is today or earlier. Drafts and future days never reach the public repository.
  3. If bible-site/data/devotional.json did not change, stop.
  4. Build the public bundle into a temporary folder as a sanity check.
  5. Commit only that one file and push it to origin/main (Cloudflare Pages deploys main).
Usage: python3 bible-site/devotional/publish_daily.py [--date YYYY-MM-DD] [--dry-run]
"""
import argparse
import datetime
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

START = datetime.date(2026, 11, 9)
REPO = Path(__file__).resolve().parents[2]
TARGET = 'bible-site/data/devotional.json'


def git(*args, check=True):
    p = subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f'git {" ".join(args)}：{p.stderr.strip()}')
    return p


def run(*cmd):
    p = subprocess.run([sys.executable, '-B', *cmd], cwd=REPO, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f'{cmd[0]}：{(p.stderr or p.stdout).strip()[-400:]}')
    return p.stdout


def export(today):
    run('bible-site/devotional/cli.py', 'export', '--output', TARGET, '--through', today)
    entries = json.loads((REPO / TARGET).read_text(encoding='utf-8'))
    if not isinstance(entries, list) or any(e['devotional_date'] > today for e in entries):
        raise RuntimeError('匯出內容含有未來日期，停止發佈')
    return len(entries)


def main():
    p = argparse.ArgumentParser(description='每日禱讀上架：匯出已核准且日期已到的內容並推送到正式網站')
    p.add_argument('--date', help='以此日期為今天（測試用），預設台灣時間今天')
    p.add_argument('--dry-run', action='store_true', help='只匯出與檢查，不提交也不推送')
    args = p.parse_args()
    today = args.date or datetime.datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
    if datetime.date.fromisoformat(today) < START:
        print(f'{today}：每日上架自 {START} 起，今天不動作')
        return 0
    if git('status', '--porcelain').stdout.strip():
        raise RuntimeError('發佈用 checkout 有未提交的變更，停止')
    for attempt in range(2):
        count = export(today)
        if not git('status', '--porcelain', '--', TARGET).stdout.strip():
            print(f'{today}：已核准 {count} 篇，內容沒有變化，不需上架')
            return 0
        with tempfile.TemporaryDirectory() as out:
            run('bible-site/tools/build_public.py', '--out', out)
            if not (Path(out) / TARGET).exists():
                raise RuntimeError('發佈包沒有 devotional.json')
        if args.dry_run:
            print(f'{today}：--dry-run，已核准 {count} 篇，會更新 {TARGET}')
            git('checkout', '--', TARGET)
            return 0
        git('add', '--', TARGET)
        git('commit', '-q', '-m', f'Publish daily devotional {today}', '--', TARGET)
        if git('push', '-q', 'origin', 'HEAD:main', check=False).returncode == 0:
            print(f'{today}：已上架，公開 {count} 篇（至 {today}）')
            return 0
        # main moved meanwhile: start again from the new tip
        git('fetch', '-q', 'origin', 'main')
        git('checkout', '-q', '--detach', '-f', 'origin/main')
    raise RuntimeError('推送失敗兩次，請人工檢查')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, OSError) as e:
        print(f'每日上架失敗：{e}', file=sys.stderr)
        sys.exit(1)
