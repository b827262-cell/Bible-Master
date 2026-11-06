#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
從推喇奴《活潑的生命》每日經文頁面 (https://www.duranno.tw/livinglife/index.php/daily)
或本機 HTML 測試檔擷取四福音（馬太、馬可、路加、約翰福音）相關日誌純文字：
- 今日的主題
- 經文範圍（設定為馬太福音／四福音的範圍）
- 經文內容（由本機驗證之四福音 JSON 或頁面經文附上）
- 全心禱告
"""
import argparse
import datetime
import html as html_lib
import json
import re
import sys
import time
import urllib.robotparser
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Any

from cli import sql
from parser import parse_scripture_reference, ParsedScriptureRange

URL = "https://www.duranno.tw/livinglife/index.php/daily"
AGENT = "Mozilla/5.0 (compatible; BibleMasterBot/1.0)"
ROBOTS = "https://www.duranno.tw/robots.txt"
FOUR_GOSPEL_CODES = ("MAT", "MRK", "LUK", "JHN")


class DurannoDailyExtractor(HTMLParser):
    """解析 duranno.tw/livinglife/index.php/daily 的今日主題與經文範圍。"""

    VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "source"}

    def __init__(self) -> None:
        super().__init__()
        self.range_depth = 0
        self.in_h2 = False
        self.range_parts: List[str] = []
        self.h2_parts: List[str] = []
        self.dates: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = dict(attrs)
        if tag == "div":
            if self.range_depth:
                self.range_depth += 1
            elif "range" in (a.get("class") or "").split():
                self.range_depth = 1

        if tag == "h2":
            self.in_h2 = True
        elif self.in_h2 and tag == "br":
            self.h2_parts.append(" ")

        if tag == "time" and a.get("datetime"):
            self.dates.append(a["datetime"][:10])

    def handle_endtag(self, tag: str) -> None:
        if self.range_depth and tag == "div":
            self.range_depth -= 1
        if tag == "h2":
            self.in_h2 = False

    def handle_data(self, data: str) -> None:
        if self.range_depth:
            self.range_parts.append(data)
        if self.in_h2:
            self.h2_parts.append(data)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("拒絕轉址，需人工確認")


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.build_opener(NoRedirect).open(req, timeout=15) as resp:
        if not resp.geturl().startswith("https://www.duranno.tw/"):
            raise ValueError("不允許站外轉址")
        body = resp.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("來源回應超過大小上限")
        return body.decode("utf-8")


def extract_date(raw_html: str, parsed_dates: List[str]) -> Optional[str]:
    for d in parsed_dates:
        try:
            return datetime.date.fromisoformat(d).isoformat()
        except ValueError:
            pass
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", raw_html)
    if m:
        try:
            y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return datetime.date(y, mo, da).isoformat()
        except ValueError:
            return None
    return None


def lookup_local_scripture(ranges: List[ParsedScriptureRange]) -> str:
    """從本機已驗證之 bible-site/data/{mat,mrk,luk,jhn}.json 附上四福音經文內容。"""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    pieces: List[str] = []
    for r in ranges:
        if r.book_code not in FOUR_GOSPEL_CODES:
            continue
        json_path = data_dir / f"{r.book_code.lower()}.json"
        if not json_path.exists():
            continue
        book_data = json.loads(json_path.read_text(encoding="utf-8"))
        chapters = book_data.get("chapters", [])
        for ch_num in range(r.start_chapter, r.end_chapter + 1):
            if ch_num < 1 or ch_num > len(chapters):
                continue
            verses = chapters[ch_num - 1].get("verses", [])
            for v in verses:
                v_num = v.get("v", 0)
                v_end = v.get("end", v_num)
                if ch_num == r.start_chapter and r.start_verse is not None and v_end < r.start_verse:
                    continue
                if ch_num == r.end_chapter and r.end_verse is not None and v_num > r.end_verse:
                    continue
                label = f"{v_num}-{v_end}" if v_end != v_num else f"{v_num}"
                verse_text = v.get("text", v.get("t", ""))
                if len(ranges) > 1 or r.start_chapter != r.end_chapter:
                    pieces.append(f"{ch_num}:{label} {verse_text}")
                else:
                    pieces.append(f"{label} {verse_text}")
    return " ".join(pieces)


def extract_scripture_content(raw_html: str, ranges: List[ParsedScriptureRange], use_local_first: bool = True) -> str:
    """附上經文內容：優先使用本機驗證過的四福音和合本經文，若無則解析頁面 MyJSStringVar。"""
    if use_local_first:
        local_text = lookup_local_scripture(ranges)
        if local_text:
            return local_text
    m = re.search(r'var\s+MyJSStringVar\s*=\s*"((?:[^"\\]|\\.)*)"', raw_html, re.DOTALL)
    if m:
        raw_js_str = m.group(1).replace('\\"', '"').replace("\\n", "\n")
        cleaned = " ".join(html_lib.unescape(raw_js_str).split())
        if cleaned:
            return cleaned
    return lookup_local_scripture(ranges)


def extract_prayer(raw_html: str) -> str:
    """擷取『全心禱告』段落純文字。"""
    m = re.search(
        r"<b>\s*全心禱告\s*</b>\s*(?:<br\s*/?>)?(.*?)(?:★\s*(?:&nbsp;)?\s*<b>|</div>)",
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return ""
    fragment = re.sub(r"<[^>]+>", " ", m.group(1))
    fragment = html_lib.unescape(fragment).replace("\xa0", " ")
    return " ".join(fragment.split())


def parse_daily_page(
    raw_html: str,
    source_url: Optional[str] = URL,
    override_range: Optional[str] = None,
) -> Dict[str, Any]:
    extractor = DurannoDailyExtractor()
    extractor.feed(raw_html)

    theme = " ".join("".join(extractor.h2_parts).split())
    page_ref = " ".join("".join(extractor.range_parts).split())
    ref = override_range.strip() if override_range else page_ref
    devotional_date = extract_date(raw_html, extractor.dates)
    scope, ranges, errors = parse_scripture_reference(ref)
    scripture_content = (
        extract_scripture_content(raw_html, ranges, use_local_first=bool(override_range))
        if scope == "IN_SCOPE"
        else ""
    )
    prayer = extract_prayer(raw_html)

    return {
        "source_url": source_url,
        "devotional_date": devotional_date,
        "is_four_gospels": scope == "IN_SCOPE",
        "scope": scope,
        "今日的主題": theme,
        "經文範圍": ref,
        "經文內容": scripture_content,
        "全心禱告": prayer,
        "ranges": [vars(r) for r in ranges],
        "issues": errors + ([] if devotional_date else ["日期未能確認，須人工核對"]),
    }


def format_text_output(data: Dict[str, Any]) -> str:
    return (
        f"今日的主題：{data['今日的主題']}\n"
        f"經文範圍：{data['經文範圍']}\n"
        f"經文內容：{data['經文內容']}\n"
        f"全心禱告：{data['全心禱告']}"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="推喇奴《活潑的生命》四福音每日靈修純文字爬蟲")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--fixture", help="讀取本機 HTML 檔案測試")
    g.add_argument("--live", action="store_true", help="抓取 duranno.tw 每日經文頁面（需 source_policy APPROVED）")
    p.add_argument("--book", choices=["MAT", "MRK", "LUK", "JHN"], help="可選：僅限特定福音書（預設允許四福音 MAT/MRK/LUK/JHN）")
    p.add_argument("--range", dest="override_range", help="可選：將經文範圍設定為指定四福音經文（例如 '馬太福音 4:1∼11'）並附上經文內容")
    p.add_argument("--json", action="store_true", help="以 JSON 格式輸出")
    args = p.parse_args()

    if args.fixture:
        raw_html = Path(args.fixture).read_text(encoding="utf-8")
        source_url = None
    else:
        if sql("SELECT mode FROM source_policy WHERE id=1;") != "APPROVED":
            raise ValueError("目前為人工模式，禁止抓取官方網站")
        sql("SELECT claim_source_fetch();")
        robots = urllib.robotparser.RobotFileParser(ROBOTS)
        robots.parse(fetch_html(ROBOTS).splitlines())
        if not robots.can_fetch(AGENT, URL):
            raise ValueError("robots.txt 禁止抓取")
        time.sleep(15)
        raw_html = fetch_html(URL)
        source_url = URL

    result = parse_daily_page(raw_html, source_url=source_url, override_range=args.override_range)

    if result["scope"] == "UNPARSED":
        status = "NEEDS_FIX"
    elif result["scope"] == "OUT_OF_SCOPE":
        status = "SKIPPED_OUT_OF_SCOPE"
    elif args.book and any(r["book_code"] != args.book for r in result["ranges"]):
        status = "SKIPPED_BOOK_FILTER"
    else:
        status = "NEEDS_FIX" if result["issues"] else "CANDIDATE"

    result["status"] = status
    result["matched"] = status == "CANDIDATE"
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["scope"] == "IN_SCOPE" and status in ("CANDIDATE", "NEEDS_FIX"):
            print(format_text_output(result))
        else:
            print(f"[{status}] 經文範圍「{result['經文範圍']}」非目標四福音範圍，已略過。")
        for issue in result["issues"]:
            print(f"[提醒] {issue}", file=sys.stderr)
    return 1 if result["scope"] == "UNPARSED" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError, urllib.error.URLError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

