#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""擷取每日經文索引，包括日期、經文範圍、來源及解析狀態。"""
import argparse
import datetime
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
from parser import parse_scripture_reference

URL = "https://www.duranno.tw/livinglife/index.php/daily"
AGENT = "Mozilla/5.0 (compatible; BibleMasterBot/1.0)"
ROBOTS = "https://www.duranno.tw/robots.txt"


class DurannoDailyExtractor(HTMLParser):
    """解析 duranno.tw/livinglife/index.php/daily 的經文範圍與日期。"""

    def __init__(self) -> None:
        super().__init__()
        self.range_depth = 0
        self.range_parts: List[str] = []
        self.dates: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = dict(attrs)
        if tag == "div":
            if self.range_depth:
                self.range_depth += 1
            elif "range" in (a.get("class") or "").split():
                self.range_depth = 1

        if tag == "time" and a.get("datetime"):
            self.dates.append(a["datetime"][:10])

    def handle_endtag(self, tag: str) -> None:
        if self.range_depth and tag == "div":
            self.range_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.range_depth:
            self.range_parts.append(data)


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


def parse_daily_page(raw_html: str, source_url: Optional[str] = URL) -> Dict[str, Any]:
    extractor = DurannoDailyExtractor()
    extractor.feed(raw_html)

    reference = " ".join("".join(extractor.range_parts).split())
    devotional_date = extract_date(raw_html, extractor.dates)
    scope, ranges, issues = parse_scripture_reference(reference)
    return {
        "source_url": source_url,
        "devotional_date": devotional_date,
        "is_four_gospels": scope == "IN_SCOPE",
        "scope": scope,
        "經文範圍": reference,
        "ranges": [vars(passage) for passage in ranges],
        "issues": issues + ([] if devotional_date else ["日期未能確認，須人工核對"]),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="推喇奴《活潑的生命》四福音每日經文索引")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--fixture", help="讀取本機 HTML 檔案測試")
    g.add_argument("--live", action="store_true", help="抓取 duranno.tw 每日經文頁面（需 source_policy APPROVED）")
    p.add_argument("--book", choices=["MAT", "MRK", "LUK", "JHN"], help="可選：僅限特定福音書（預設允許四福音 MAT/MRK/LUK/JHN）")
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

    result = parse_daily_page(raw_html, source_url=source_url)

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
        print(f"[{status}] {result['devotional_date'] or '日期待核對'}｜{result['經文範圍'] or '經文範圍待核對'}")
        if result["source_url"]:
            print(result["source_url"])
        for issue in result["issues"]:
            print(f"[提醒] {issue}", file=sys.stderr)
    return 1 if result["scope"] == "UNPARSED" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError, urllib.error.URLError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

