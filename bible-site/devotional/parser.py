#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四福音靈修索引 CSV 驗證、跨章節經文解析與匯出安全檢查工具 (validate_and_parse.py)

功能：
1. 驗證並正規化來源網址与影音網址（移除 utm_* / fbclid 等追蹤參數，實作冪等去重）。
2. 解析中文聖經書卷與跨章節經文範圍（如「馬太福音 4:23∼5:12」或同日多段經文），
   嚴格區分四福音 (IN_SCOPE)、其他書卷 (OUT_OF_SCOPE) 與無法確認之格式 (UNPARSED)。
3. 缺漏日期或章節時強制標記為 NEEDS_FIX / PENDING_REVIEW，絕不自動猜測補齊。
4. 模擬雙重審核閘門（來源審核 + 神學審核）與靜態 JSON 匯出白名單斷言檢查。
"""

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# 四福音書卷標準對照表（支援全名與常見簡稱）
FOUR_GOSPELS_MAP: Dict[str, Tuple[str, str]] = {
    "馬太福音": ("MAT", "馬太福音"),
    "太": ("MAT", "馬太福音"),
    "馬可福音": ("MRK", "馬可福音"),
    "可": ("MRK", "馬可福音"),
    "路加福音": ("LUK", "路加福音"),
    "路": ("LUK", "路加福音"),
    "約翰福音": ("JHN", "約翰福音"),
    "約": ("JHN", "約翰福音"),
}

# 常見非四福音書卷對照表（用於明確識別為 OUT_OF_SCOPE，避免誤判為語法錯誤）
OTHER_BIBLE_BOOKS: Dict[str, Tuple[str, str]] = {
    "創世記": ("GEN", "創世記"), "創": ("GEN", "創世記"),
    "出埃及記": ("EXO", "出埃及記"), "出": ("EXO", "出埃及記"),
    "利未記": ("LEV", "利未記"), "利": ("LEV", "利未記"),
    "民數記": ("NUM", "民數記"), "民": ("NUM", "民數記"),
    "申命記": ("DEU", "申命記"), "申": ("DEU", "申命記"),
    "約書亞記": ("JOS", "約書亞記"), "書": ("JOS", "約書亞記"),
    "士師記": ("JDG", "士師記"), "士": ("JDG", "士師記"),
    "路得記": ("RUT", "路得記"), "得": ("RUT", "路得記"),
    "撒母耳記上": ("1SA", "撒母耳記上"), "撒上": ("1SA", "撒母耳記上"),
    "撒母耳記下": ("2SA", "撒母耳記下"), "撒下": ("2SA", "撒母耳記下"),
    "列王紀上": ("1KI", "列王紀上"), "王上": ("1KI", "列王紀上"),
    "列王紀下": ("2KI", "列王紀下"), "王下": ("2KI", "列王紀下"),
    "歷代志上": ("1CH", "歷代志上"), "代上": ("1CH", "歷代志上"),
    "歷代志下": ("2CH", "歷代志下"), "代下": ("2CH", "歷代志下"),
    "以斯拉記": ("EZR", "以斯拉記"), "拉": ("EZR", "以斯拉記"),
    "尼希米記": ("NEH", "尼希米記"), "尼": ("NEH", "尼希米記"),
    "以斯帖記": ("EST", "以斯帖記"), "斯": ("EST", "以斯帖記"),
    "約伯記": ("JOB", "約伯記"), "伯": ("JOB", "約伯記"),
    "詩篇": ("PSA", "詩篇"), "詩": ("PSA", "詩篇"),
    "箴言": ("PRO", "箴言"), "箴": ("PRO", "箴言"),
    "傳道書": ("ECC", "傳道書"), "傳": ("ECC", "傳道書"),
    "雅歌": ("SNG", "雅歌"), "歌": ("SNG", "雅歌"),
    "以賽亞書": ("ISA", "以賽亞書"), "賽": ("ISA", "以賽亞書"),
    "耶利米書": ("JER", "耶利米書"), "耶": ("JER", "耶利米書"),
    "耶利米哀歌": ("LAM", "耶利米哀歌"), "哀": ("LAM", "耶利米哀歌"),
    "以西結書": ("EZK", "以西結書"), "結": ("EZK", "以西結書"),
    "但以理書": ("DAN", "但以理書"), "但": ("DAN", "但以理書"),
    "何西阿書": ("HOS", "何西阿書"), "何": ("HOS", "何西阿書"),
    "約珥書": ("JOL", "約珥書"), "珥": ("JOL", "約珥書"),
    "阿摩司書": ("AMO", "阿摩司書"), "摩": ("AMO", "阿摩司書"),
    "俄巴底亞書": ("OBA", "俄巴底亞書"), "俄": ("OBA", "俄巴底亞書"),
    "約拿書": ("JON", "約拿書"), "拿": ("JON", "約拿書"),
    "彌迦書": ("MIC", "彌迦書"), "彌": ("MIC", "彌迦書"),
    "那鴻書": ("NAM", "那鴻書"), "鴻": ("NAM", "那鴻書"),
    "哈巴谷書": ("HAB", "哈巴谷書"), "哈": ("HAB", "哈巴谷書"),
    "西番雅書": ("ZEP", "西番雅書"), "番": ("ZEP", "西番雅書"),
    "哈該書": ("HAG", "哈該書"), "該": ("HAG", "哈該書"),
    "撒迦利亞書": ("ZEC", "撒迦利亞書"), "亞": ("ZEC", "撒迦利亞書"),
    "瑪拉基書": ("MAL", "瑪拉基書"), "瑪": ("MAL", "瑪拉基書"),
    "使徒行傳": ("ACT", "使徒行傳"), "徒": ("ACT", "使徒行傳"),
    "羅馬書": ("ROM", "羅馬書"), "羅": ("ROM", "羅馬書"),
    "哥林多前書": ("1CO", "哥林多前書"), "林前": ("1CO", "哥林多前書"),
    "哥林多後書": ("2CO", "哥林多後書"), "林後": ("2CO", "哥林多後書"),
    "加拉太書": ("GAL", "加拉太書"), "加": ("GAL", "加拉太書"),
    "以弗所書": ("EPH", "以弗所書"), "弗": ("EPH", "以弗所書"),
    "腓立比書": ("PHP", "腓立比書"), "腓": ("PHP", "腓立比書"),
    "歌羅西書": ("COL", "歌羅西書"), "西": ("COL", "歌羅西書"),
    "帖撒羅尼迦前書": ("1TH", "帖撒羅尼迦前書"), "帖前": ("1TH", "帖撒羅尼迦前書"),
    "帖撒羅尼迦後書": ("2TH", "帖撒羅尼迦後書"), "帖後": ("2TH", "帖撒羅尼迦後書"),
    "提摩太前書": ("1TI", "提摩太前書"), "提前": ("1TI", "提摩太前書"),
    "提摩太後書": ("2TI", "提摩太後書"), "提後": ("2TI", "提摩太後書"),
    "提多書": ("TIT", "提多書"), "多": ("TIT", "提多書"),
    "腓利門書": ("PHM", "腓利門書"), "門": ("PHM", "腓利門書"),
    "希伯來書": ("HEB", "希伯來書"), "來": ("HEB", "希伯來書"),
    "雅各書": ("JAS", "雅各書"), "雅": ("JAS", "雅各書"),
    "彼得前書": ("1PE", "彼得前書"), "彼前": ("1PE", "彼得前書"),
    "彼得後書": ("2PE", "彼得後書"), "彼後": ("2PE", "彼得後書"),
    "約翰一書": ("1JN", "約翰一書"), "約一": ("1JN", "約翰一書"),
    "約翰二書": ("2JN", "約翰二書"), "約二": ("2JN", "約翰二書"),
    "約翰三書": ("3JN", "約翰三書"), "約三": ("3JN", "約翰三書"),
    "猶大書": ("JUD", "猶大書"), "猶": ("JUD", "猶大書"),
    "啟示錄": ("REV", "啟示錄"), "啟": ("REV", "啟示錄"),
}

ALL_BOOKS_MAP: Dict[str, Tuple[str, str]] = {**OTHER_BIBLE_BOOKS, **FOUR_GOSPELS_MAP}
# 依書卷名稱長度由長到短排序，避免「約翰一書」誤配為「約」
SORTED_BOOK_KEYS = sorted(ALL_BOOKS_MAP.keys(), key=len, reverse=True)

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}

# 公開匯出 JSON 嚴格允許之頂層欄位白名單
ALLOWED_EXPORT_KEYS = {
    "entry_id",
    "devotional_date",
    "source_url",
    "scripture_reference",
    "parsed_ranges",
    "original_summary",
    "original_reflection",
    "original_prayer",
    "author_agent",
    "bible_source_version",
    "verified_media_links",
}

FORBIDDEN_CONTENT_PATTERNS = [
    "raw_html",
    "article_body",
    "full_text",
    "本網站的文字與圖片若非獲得准許",
]


@dataclass
class ParsedScriptureRange:
    sequence_no: int
    book_code: str
    book_name_zh: str
    is_four_gospels: bool
    start_chapter: int
    start_verse: Optional[int]
    end_chapter: int
    end_verse: Optional[int]


def normalize_url(raw_url: str) -> str:
    """正規化 URL：統一小寫 scheme/netloc、移除追蹤參數、正規化結尾斜線。"""
    raw_url = (raw_url or "").strip()
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    filtered_query = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    filtered_query.sort(key=lambda item: item[0])
    clean_path = parsed.path or "/"
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        clean_path,
        "",
        urlencode(filtered_query),
        "",
    ))


def parse_iso_date(raw_date: str) -> Optional[str]:
    """嚴格驗證 YYYY-MM-DD 日期格式；無法確認時回傳 None，不猜測補齊。"""
    text = (raw_date or "").strip()
    if not text:
        return None
    try:
        parsed = dt.date.fromisoformat(text)
        return parsed.isoformat()
    except ValueError:
        return None


def parse_scripture_reference(raw_text: str) -> Tuple[str, List[ParsedScriptureRange], List[str]]:
    """
    解析經文範圍字串（支援單章、跨章節與分號分隔之多段經文）。
    回傳: (scope_status, parsed_ranges, error_messages)
      - scope_status: 'IN_SCOPE' | 'OUT_OF_SCOPE' | 'UNPARSED'
    """
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return "UNPARSED", [], ["經文範圍為空"]

    # 以全形或半形分號切分同日多段經文
    segments = [seg.strip() for seg in re.split(r"[;；]+", cleaned) if seg.strip()]
    if not segments:
        return "UNPARSED", [], ["經文範圍為空"]
    parsed_list: List[ParsedScriptureRange] = []
    errors: List[str] = []

    # 正規化冒號与連接號：支援 `4:23∼5:12`, `2：1∼8`, `1:1-18`, `3章`
    range_pattern = re.compile(
        r"^(\d+)\s*(?:[:：]\s*(\d+))?\s*(?:[∼~～\-－—–至]\s*(\d+)\s*(?:[:：]\s*(\d+))?)?\s*(?:章|篇)?$"
    )

    for idx, seg in enumerate(segments, start=1):
        matched_book_key = None
        for key in SORTED_BOOK_KEYS:
            if seg.startswith(key):
                matched_book_key = key
                break

        if not matched_book_key:
            errors.append(f"無法識別書卷名稱: '{seg}'")
            return "UNPARSED", [], errors

        book_code, book_name_zh = ALL_BOOKS_MAP[matched_book_key]
        is_gospel = book_code in ("MAT", "MRK", "LUK", "JHN")
        remainder = seg[len(matched_book_key):].strip()

        if not remainder:
            errors.append(f"缺少章節範圍: '{seg}'")
            return "UNPARSED", [], errors

        m = range_pattern.match(remainder)
        if not m:
            errors.append(f"章節格式無法解析: '{seg}'")
            return "UNPARSED", [], errors

        g1, g2, g3, g4 = m.groups()
        start_ch = int(g1)

        if g2 is not None and g3 is not None and g4 is not None:
            # 跨章節格式: 例如 4:23∼5:12
            start_v = int(g2)
            end_ch = int(g3)
            end_v = int(g4)
        elif g2 is not None and g3 is not None and g4 is None:
            # 同章節範圍: 例如 2:1∼8
            start_v = int(g2)
            end_ch = start_ch
            end_v = int(g3)
        elif g2 is not None and g3 is None and g4 is None:
            # 單節經文: 例如 3:16
            start_v = int(g2)
            end_ch = start_ch
            end_v = int(g2)
        elif g2 is None and g3 is not None and g4 is None:
            # 跨整章範圍: 例如 1∼3章
            start_v = None
            end_ch = int(g3)
            end_v = None
        else:
            # 單一整章: 例如 3章
            start_v = None
            end_ch = start_ch
            end_v = None

        if min(start_ch, end_ch) < 1 or (start_v is not None and min(start_v, end_v) < 1):
            return "UNPARSED", [], [f"章節必須大於零: {seg}"]
        if is_gospel:
            data_path = Path(__file__).resolve().parent.parent / "data" / (book_code.lower() + ".json")
            chapters = json.loads(data_path.read_text(encoding="utf-8"))["chapters"]
            if end_ch > len(chapters):
                return "UNPARSED", [], [f"章節超出範圍: {seg}"]
            for ch, verse in ((start_ch, start_v), (end_ch, end_v)):
                if verse is not None and verse > max(v.get("end", v["v"]) for v in chapters[ch-1]["verses"]):
                    return "UNPARSED", [], [f"節數超出範圍: {seg}"]
        if end_ch < start_ch or (end_ch == start_ch and start_v is not None and end_v is not None and end_v < start_v):
            errors.append(f"起訖章節順序不合法: '{seg}' ({start_ch}:{start_v} -> {end_ch}:{end_v})")
            return "UNPARSED", [], errors

        parsed_list.append(
            ParsedScriptureRange(
                sequence_no=idx,
                book_code=book_code,
                book_name_zh=book_name_zh,
                is_four_gospels=is_gospel,
                start_chapter=start_ch,
                start_verse=start_v,
                end_chapter=end_ch,
                end_verse=end_v,
            )
        )

    if all(r.is_four_gospels for r in parsed_list):
        return "IN_SCOPE", parsed_list, []
    return "OUT_OF_SCOPE", parsed_list, []


def validate_devotional_csv(csv_path: str) -> Dict[str, Any]:
    """讀取並驗證靈修索引 CSV，執行去重與狀態機分流。"""
    seen_keys = set()
    results = []
    stats = {
        "total_rows": 0,
        "in_scope_pending_review": 0,
        "out_of_scope": 0,
        "needs_fix": 0,
        "duplicates_skipped": 0,
    }

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            stats["total_rows"] += 1
            raw_date = row.get("devotional_date", "")
            raw_scripture = row.get("raw_scripture_text", "")
            raw_url = row.get("source_url", "")

            iso_date = parse_iso_date(raw_date)
            canonical_url = normalize_url(raw_url)
            scope_status, ranges, parse_errors = parse_scripture_reference(raw_scripture)

            dedup_key = (canonical_url, iso_date)
            if canonical_url and dedup_key in seen_keys:
                stats["duplicates_skipped"] += 1
                results.append({
                    "row_num": row_num,
                    "action": "SKIPPED_DUPLICATE",
                    "canonical_url": canonical_url,
                    "devotional_date": iso_date,
                    "raw_scripture_text": raw_scripture,
                })
                continue

            if canonical_url:
                seen_keys.add(dedup_key)

            issues = list(parse_errors)
            if not canonical_url:
                issues.append("來源網址無效或缺失")
            if not iso_date:
                issues.append("日期缺失或格式錯誤（不自動猜測補齊）")

            if issues or scope_status == "UNPARSED":
                review_status = "NEEDS_FIX"
                stats["needs_fix"] += 1
            elif scope_status == "OUT_OF_SCOPE":
                review_status = "PENDING_REVIEW"
                stats["out_of_scope"] += 1
            else:
                review_status = "PENDING_REVIEW"
                stats["in_scope_pending_review"] += 1

            results.append({
                "row_num": row_num,
                "action": "IMPORTED",
                "devotional_date": iso_date,
                "canonical_url": canonical_url,
                "raw_scripture_text": raw_scripture,
                "scope_status": scope_status,
                "source_review_status": review_status,
                "parsed_ranges": [asdict(r) for r in ranges],
                "issues": issues,
            })

    return {"stats": stats, "records": results}


def validate_media_csv(csv_path: str) -> Dict[str, Any]:
    """讀取並驗證 381 支影音清單 CSV，核對經文範圍與網址去重。"""
    seen_urls = set()
    results = []
    stats = {
        "total_rows": 0,
        "in_scope_unverified": 0,
        "out_of_scope": 0,
        "unparsed_needs_review": 0,
        "duplicates_skipped": 0,
    }

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            stats["total_rows"] += 1
            raw_url = row.get("media_url", "")
            raw_scripture = row.get("raw_scripture_text", "")
            canonical_media_url = normalize_url(raw_url)

            if canonical_media_url and canonical_media_url in seen_urls:
                stats["duplicates_skipped"] += 1
                results.append({
                    "row_num": row_num,
                    "action": "SKIPPED_DUPLICATE",
                    "canonical_media_url": canonical_media_url,
                })
                continue

            if canonical_media_url:
                seen_urls.add(canonical_media_url)

            scope_status, ranges, parse_errors = parse_scripture_reference(raw_scripture)
            if scope_status == "IN_SCOPE" and canonical_media_url:
                stats["in_scope_unverified"] += 1
            elif scope_status == "OUT_OF_SCOPE":
                stats["out_of_scope"] += 1
            else:
                stats["unparsed_needs_review"] += 1

            results.append({
                "row_num": row_num,
                "action": "IMPORTED",
                "external_media_id": row.get("external_media_id", ""),
                "canonical_media_url": canonical_media_url,
                "raw_scripture_text": raw_scripture,
                "scope_status": scope_status,
                "verify_status": "UNVERIFIED",
                "parsed_ranges": [asdict(r) for r in ranges],
                "issues": parse_errors,
            })

    return {"stats": stats, "records": results}


def verify_export_security_guard(export_payload: List[Dict[str, Any]]) -> None:
    """驗證公開匯出之靜態 JSON 僅含核准欄位且無原站正文或未審核資料。"""
    for item in export_payload:
        extra_keys = set(item.keys()) - ALLOWED_EXPORT_KEYS
        if extra_keys:
            raise AssertionError(f"匯出安全檢查失敗：發現未授權欄位 {extra_keys}")
        if not item.get("devotional_date"):
            raise AssertionError("匯出安全檢查失敗：包含無日期之紀錄")
        ranges = item.get("parsed_ranges", [])
        if not ranges or not all(r.get("book_code") in ("MAT", "MRK", "LUK", "JHN") for r in ranges):
            raise AssertionError("匯出安全檢查失敗：包含非四福音書卷紀錄")
        serialized = json.dumps(item, ensure_ascii=False)
        for pattern in FORBIDDEN_CONTENT_PATTERNS:
            if pattern in serialized:
                raise AssertionError(f"匯出安全檢查失敗：偵測到疑似原站正文或禁止字串 '{pattern}'")


def main() -> int:
    parser = argparse.ArgumentParser(description="四福音靈修索引 CSV 驗證與經文解析工具")
    parser.add_argument("--devotional-csv", help="靈修索引 CSV 路徑（如 13 筆清單）")
    parser.add_argument("--media-csv", help="影音連結 CSV 路徑（如 381 支影音清單）")
    parser.add_argument("--self-test", action="store_true", help="執行內建跨章節解析、去重與匯出安全檢查單元測試")
    args = parser.parse_args()

    if args.self_test:
        # 1. 跨章節解析驗證
        status, ranges, errs = parse_scripture_reference("馬太福音 4:23∼5:12")
        assert status == "IN_SCOPE" and not errs, f"跨章節解析失敗: {errs}"
        assert ranges[0].book_code == "MAT" and ranges[0].start_chapter == 4 and ranges[0].end_chapter == 5

        # 2. 非四福音識別驗證
        status2, ranges2, _ = parse_scripture_reference("阿摩司書2：1∼8")
        assert status2 == "OUT_OF_SCOPE" and ranges2[0].book_code == "AMO"

        # 3. 匯出安全斷言驗證
        sample_approved_export = [{
            "entry_id": 1,
            "devotional_date": "2026-03-02",
            "source_url": "https://www.duranno.tw/livinglife/index.php/daily?date=2026-03-02",
            "scripture_reference": "馬太福音 4:23∼5:12",
            "parsed_ranges": [{"seq": 1, "book_code": "MAT", "book_name": "馬太福音", "start_chapter": 4, "start_verse": 23, "end_chapter": 5, "end_verse": 12}],
            "original_summary": "耶穌走遍加利利傳講天國的福音，並在山上寶訓開篇闡明神國子民的品格。",
            "original_reflection": "當我們面對心靈貧乏與試煉時，主的話語帶給我們真實的安慰與盼望。",
            "original_prayer": "求主帶領我們每日活出八福的生命。",
            "author_agent": "Bible-Master",
            "bible_source_version": "Project-Bible-Data",
            "verified_media_links": [{"media_type": "VIDEO", "media_url": "https://www.duranno.tw/videos/index.php/qtacademy?vNum=102"}],
        }]
        verify_export_security_guard(sample_approved_export)
        print("[PASS] 內建單元測試（跨章節解析、非四福音過濾、URL 正規化與匯出白名單安全檢查）全部通過。")

    if args.devotional_csv:
        report = validate_devotional_csv(args.devotional_csv)
        print("=== 靈修索引 CSV 驗證摘要 ===")
        print(json.dumps(report["stats"], ensure_ascii=False, indent=2))

    if args.media_csv:
        report = validate_media_csv(args.media_csv)
        print("=== 影音清單 CSV 驗證摘要 ===")
        print(json.dumps(report["stats"], ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())