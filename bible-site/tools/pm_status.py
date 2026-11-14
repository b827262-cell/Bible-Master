#!/usr/bin/env python3
"""PM progress report for the Bible site. Reads the real state of the project (files, check_all.py,
REVIEW.md, TODO.md) and rewrites the auto-generated block in PROGRESS.md between the
<!-- pm:auto:start --> and <!-- pm:auto:end --> markers. Nothing here asks a model for a verdict.
Usage: python3 bible-site/tools/pm_status.py [--no-checks]   (--no-checks skips running check_all.py)"""
import datetime, os, re, subprocess, sys
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Updated list based on task 140: home/index/chapter/search/card/blessing/devotional + scripts
SITE_FILES = ["app.js", "style.css", "chapter.html", "index.html", "search.html", "card.html", "home.html", "blessing.html", "devotional.html", "music.js", "devotional.js"]
START, END = "<!-- pm:auto:start -->", "<!-- pm:auto:end -->"

# Target gospel details (Chapter count / Verse count)
GOSPEL_SPECS = {
    "mat": {"chapters": 28, "verses": 1071},
    "mrk": {"chapters": 16, "verses": 678},
    "luk": {"chapters": 24, "verses": 1149},
    "jhn": {"chapters": 21, "verses": 878}
}

def exists(rel):
    p = os.path.join(ROOT, rel)
    return os.path.isfile(p) and os.path.getsize(p) > 0

def check_gospel_json(book_key):
    """Checks a specific gospel JSON against required schema/counts."""
    file_path = f"data/{book_key}.json"
    if not exists(file_path):
        return False, "缺失檔案"
    try:
        with open(os.path.join(ROOT, file_path), 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return False, "JSON 格式錯誤"
    except Exception: # Other IO errors
        return False, "檔案讀取錯誤"

    # Check object type and chapters array existence
    if not isinstance(data, dict) or 'chapters' not in data or not isinstance(data['chapters'], list):
        return False, "無有效的章節陣列"

    chapters = data['chapters']
    expected_chapters = GOSPEL_SPECS[book_key]['chapters']

    if len(chapters) != expected_chapters:
        return False, f"章節數不符：實際 {len(chapters)}，預期 {expected_chapters}"

    # Check verse counts for each chapter and total verses (Fix 2 applied here)
    total_verses = 0
    for chapter in chapters:
        if not isinstance(chapter, dict) or 'verses' not in chapter or not isinstance(chapter['verses'], list):
             return False, "章節元素缺少有效的『verses』陣列"

        # Check if every element in verses array is a dictionary (Fix 2 complete)
        for verse_item in chapter['verses']:
            if not isinstance(verse_item, dict):
                return False, "經文元素非字典類型"

        total_verses += len(chapter['verses'])

    expected_verses = GOSPEL_SPECS[book_key]['verses']
    if total_verses != expected_verses:
         return False, f"逐節總數不符：實際 {total_verses}，預期 {expected_verses}"

    return True, "驗證成功"


def check_all_gospels():
    """Checks all four gospel JSONs and verifies the overall total."""
    results = {}
    overall_valid = True
    for book in GOSPEL_SPECS.keys():
        is_ok, reason = check_gospel_json(book)
        results[book] = is_ok
        if not is_ok:
            overall_valid = False
        print(f"福音 {book} 驗證結果：{reason}") # Print detailed results for tracing

    total_verses = sum(GOSPEL_SPECS[k]['verses'] for k in GOSPEL_SPECS.keys())
    if total_verses != 3776:
        return False, f"總逐節數不符（預期 3776）"

    # Fix 3 applied here: return specific failure reason instead of generic success message
    if overall_valid:
        return True, "四福音皆驗證成功"
    else:
        failure_list = [book for book, ok in results.items() if not ok]
        return False, f"{'、'.join(failure_list)} 驗證失敗，請檢查個別錯誤詳情。"


def last_check_all():
    """Run check_all.py and return (exit code, last line)."""
    p = subprocess.run([sys.executable, "tools/check_all.py"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    return p.returncode, (lines[-1] if lines else "(無輸出)")

def review_state():
    p = os.path.join(ROOT, "REVIEW.md")
    if not exists(p):
        return "尚未審核（沒有 REVIEW.md）"
    s = open(p, encoding="utf-8").read()
    return f"通過 {len(re.findall('通過', s)) - len(re.findall('不通過', s))} 項，不通過 {len(re.findall('不通過', s))} 項（粗略計數，請人工看 REVIEW.md）"

def todo_open():
    p = os.path.join(ROOT, "TODO.md")
    if not exists(p):
        return None
    # Only count pending tasks
    return sum(1 for l in open(p, encoding="utf-8") if l.lstrip().startswith("- [ ]"))

def main():
    present = [f for f in SITE_FILES if exists(f"site/{f}")]
    if "--no-checks" in sys.argv:
        # Use FAILS.md and state check based on task 140 ruling (Fix 1 applied here)
        fails = os.path.join(ROOT, "FAILS.md")
        passed = os.path.isfile(fails) and "全部通過" in open(fails, encoding="utf-8").read()
        # Maintain old result status (code/summary), not just always 1
        code, summary = (0 if passed else 1), "沿用上次 check_all.py 的結果（FAILS.md）：" + ("全部通過" if passed else "有不通過項目")
    else:
        # Run full check_all.py
        code, summary = last_check_all()

    gospel_ok, gospel_summary_text = check_all_gospels()

    # Determine the accurate summary text to display in PROGRESS.md
    if not gospel_ok:
        gospel_summary = f"驗證失敗：{gospel_summary_text}" # Use specific failure message (Fix 3)
    else:
        gospel_summary = "四福音皆驗證成功"

    todo = todo_open()
    steps = [
        ("0 資料產生（四福音 3776 節驗證）", gospel_ok),
        ("1 建站（site/ "+str(len(SITE_FILES))+" 個檔案）", len(present) == len(SITE_FILES)),
        # Step 2 now respects the previous check status even in --no-checks mode (Fix 1 handled above)
        ("2 自動檢查 check_all.py 全過", code == 0),
        ("3 審核（REVIEW.md）", exists("REVIEW.md")),
        ("4 修正與 CHANGELOG.md", exists("CHANGELOG.md")),
        ("5 TODO.md 清空或不存在", todo in (None, 0)),
    ]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    block = [START, f"更新時間：{now}（由 `python3 bible-site/tools/pm_status.py` 產生，請勿手改此區塊）", "",
             "| 步驟 | 狀態 |", "|---|---|"]

    # Update step descriptions to reflect the new scope (e.g., step 0)
    block += [f"| {name} | {'完成' if ok else '未完成'} |" for name, ok in steps]

    block += ["", f"- site 檔案：{len(present)}/{len(SITE_FILES)}（缺：{'、'.join(f for f in SITE_FILES if f not in present) or '無'}）",
              f"- check_all.py：{summary}", f"- 四福音JSON驗證：{gospel_summary}", f"- 審核：{review_state()}",
              f"- TODO.md 未完成項目：{'沒有 TODO.md' if todo is None else todo}", END]

    path = os.path.join(ROOT, "PROGRESS.md")
    text = open(path, encoding="utf-8").read() if exists(path) else f"# PM 進度\n\n{START}\n{END}\n"
    if START in text and END in text:
        # Use regex to replace the existing auto block content
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
