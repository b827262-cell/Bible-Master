#!/usr/bin/env python3
"""Test daily publication with a disposable PostgreSQL database and a local Git remote."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from publish_daily import BUILT, REPO, TARGET

TEST_DB = "bible_devotional_test"
TODAY = "2026-11-09"
TEST_URL = "https://example.test/approved-today"
SEED = """
BEGIN;
INSERT INTO entries (source_url, canonical_url, devotional_date, raw_reference, scope, title, summary, reflection, prayer)
SELECT url, url, reading_date::date, '馬太福音 4:1', 'IN_SCOPE', title, '測試默想', '測試反思', '測試禱告'
FROM (VALUES
  ('https://example.test/approved-today', '2026-11-09', '今日已核准'),
  ('https://example.test/approved-future', '2026-11-10', '未來已核准'),
  ('https://example.test/pending-today', '2026-11-09', '今日待審')
) AS fixtures(url, reading_date, title);
INSERT INTO scripture_ranges (entry_id, sequence_no, book_code, start_chapter, start_verse, end_chapter, end_verse)
SELECT id, 1, 'MAT', 4, 1, 4, 1 FROM entries;
UPDATE entries SET source_status='APPROVED', source_reviewer='隔離測試', source_reviewed_at=now()
WHERE canonical_url IN ('https://example.test/approved-today', 'https://example.test/approved-future');
UPDATE entries SET theology_status='APPROVED', theology_reviewer='隔離測試', theology_reviewed_at=now()
WHERE source_status='APPROVED';
COMMIT;
"""


def run(*args, cwd=REPO, env=None, input=None):
    process = subprocess.run(
        args, cwd=cwd, env=env, input=input, capture_output=True, text=True, timeout=120,
    )
    if process.returncode:
        raise RuntimeError(f"{args[0]} 執行失敗：{process.stderr.strip() or process.stdout.strip()}")
    return process.stdout.strip()


def git(*args, cwd=REPO):
    return run("git", *args, cwd=cwd)


def postgres(host, *args, input=None):
    return run("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "--", host,
               "sudo", "-n", "-u", "postgres", *args, input=input)


def require_only_today(path):
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert len(rows) == 1, rows
    assert rows[0]["devotional_date"] == TODAY and rows[0]["source_url"] == TEST_URL, rows


def verify_crawler(temp):
    fixture = temp / "source.html"
    fixture.write_text(
        '<time datetime="2026-11-09"></time>'
        '<h2>原站主題測試</h2><div class="range"><span>馬太福音</span> 4:1</div>'
        '<script>var MyJSStringVar = "原站經文測試";</script>'
        '<div><b>全心禱告</b><br>原站禱告測試</div>',
        encoding="utf-8",
    )
    command = (sys.executable, "-B", "bible-site/devotional/crawler.py", "--fixture", str(fixture))
    output = run(*command, "--json")
    data = json.loads(output)
    assert set(data) == {
        "source_url", "devotional_date", "is_four_gospels", "scope", "經文範圍",
        "ranges", "issues", "status", "matched",
    }, data
    assert data["status"] == "CANDIDATE" and data["devotional_date"] == TODAY, data
    assert data["經文範圍"] == "馬太福音 4:1" and data["ranges"][0]["book_code"] == "MAT", data
    assert "原站" not in output and "原站" not in run(*command)
    print("通過：爬蟲 JSON 與文字輸出皆僅含索引")


def verify_publish(temp, env):
    # Snapshot tracked files from the current checkout, including fixes before they are committed.
    # Untracked review drafts and credentials are excluded from the disposable Git repository.
    seed = temp / "seed"
    seed.mkdir()
    for name in git("ls-files", "-z", "--", "bible-site").split("\0"):
        if not name:
            continue
        destination = seed / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, destination)
    git("init", "-q", "-b", "main", cwd=seed)
    git("add", "--", "bible-site", cwd=seed)
    git("-c", "user.name=Devotional Test", "-c", "user.email=devotional@example.test",
        "commit", "-qm", "Seed isolated publication test", cwd=seed)
    remote = temp / "remote.git"
    git("init", "-q", "--bare", "--initial-branch=main", str(remote))
    git("push", "-q", str(remote), "HEAD:main", cwd=seed)
    checkout = temp / "checkout"
    git("clone", "-q", str(remote), str(checkout))
    git("config", "user.name", "Devotional Test", cwd=checkout)
    git("config", "user.email", "devotional@example.test", cwd=checkout)

    command = (sys.executable, "-B", "bible-site/devotional/publish_daily.py", "--date", TODAY)
    initial = git("rev-parse", "HEAD", cwd=checkout)
    assert "會更新" in run(*command, "--dry-run", cwd=checkout, env=env)
    assert git("rev-parse", "HEAD", cwd=checkout) == initial
    assert not git("status", "--porcelain", cwd=checkout)
    assert "已上架" in run(*command, cwd=checkout, env=env)
    published = git("rev-parse", "HEAD", cwd=checkout)
    assert published != initial
    assert git("rev-parse", "HEAD^", cwd=checkout) == initial
    assert git("diff-tree", "--no-commit-id", "--name-only", "-r", published, cwd=checkout) == TARGET
    assert git("--git-dir", str(remote), "rev-parse", "refs/heads/main") == published

    exported = checkout / TARGET
    require_only_today(exported)
    build = temp / "built"
    run(sys.executable, "-B", "bible-site/tools/build_public.py", "--out", str(build), cwd=checkout)
    require_only_today(build / BUILT)
    assert (build / BUILT).read_bytes() == exported.read_bytes()
    assert "沒有變化" in run(*command, cwd=checkout, env=env)
    assert git("rev-parse", "HEAD", cwd=checkout) == published
    assert git("--git-dir", str(remote), "rev-parse", "refs/heads/main") == published
    assert not git("status", "--porcelain", cwd=checkout)
    print("通過：只有當日已核准資料進入匯出與建置，本機遠端收到單檔提交，重跑沒有新增提交")


def main():
    host = os.environ.get("DEVOTIONAL_SSH_HOST", "debian-toshiba")
    env = dict(os.environ, DEVOTIONAL_DATABASE=TEST_DB)
    # If the database already exists, createdb fails before we own or clean up anything.
    postgres(host, "createdb", "-p", "5433", TEST_DB)
    try:
        psql = ("psql", "-Xq", "-v", "ON_ERROR_STOP=1", "-p", "5433", "-d", TEST_DB)
        for name in ("schema.sql", "grants.sql", "002_policy.sql", "003_scripture_bounds.sql", "004_title.sql"):
            postgres(host, *psql, input=(REPO / "bible-site" / "devotional" / name).read_text(encoding="utf-8"))
        postgres(host, *psql, input=SEED)
        with tempfile.TemporaryDirectory(prefix="bible-devotional-publish-") as directory:
            temp = Path(directory)
            verify_crawler(temp)
            verify_publish(temp, env)
    finally:
        postgres(host, "dropdb", "-p", "5433", TEST_DB)


if __name__ == "__main__":
    main()
