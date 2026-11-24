#!/usr/bin/env python3
"""每日禱讀內容管理後端（task 145）。

只處理內容草稿與人工核准；不寫入公開檔、不執行排程發佈。
資料庫連線沿用專案既有方式：SSH + sudo postgres psql 5433 + SET ROLE。
"""
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.parse
import uuid

HERE = os.path.abspath(os.path.dirname(__file__))
DEVOTIONAL_DIR = os.path.abspath(os.path.join(HERE, "..", "devotional"))
if DEVOTIONAL_DIR not in sys.path:
    sys.path.insert(0, DEVOTIONAL_DIR)

from parser import normalize_url, parse_iso_date, parse_scripture_reference  # noqa: E402

DB_HOST_DEFAULT = "debian-toshiba"
DB_NAME_DEFAULT = "bible_devotional"
DB_PORT = "5433"
SSH_TIMEOUT = 15
STATEMENT_TIMEOUT = "8s"
LOCK_TIMEOUT = "2s"
EDITOR_BODY_MAX = 64 * 1024
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
CONTENT_KEYS = {"date", "reference", "title", "source_url", "summary", "reflection", "prayer"}
TEXT_LIMITS = {"title": 80, "reference": 240, "source_url": 2048, "summary": 6000, "prayer": 6000,
               "reflection": 2000}


class DevotionalEditorError(Exception):
    """可安全回給前端的錯誤；message 不含 SQL、正文、憑證或原始 stderr。"""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _db_target():
    host = (os.environ.get("DEVOTIONAL_SSH_HOST") or DB_HOST_DEFAULT).strip()
    db = (os.environ.get("DEVOTIONAL_DATABASE") or DB_NAME_DEFAULT).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", host) or host.startswith("-"):
        raise DevotionalEditorError("資料庫主機設定不正確", 503)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", db):
        raise DevotionalEditorError("資料庫名稱設定不正確", 503)
    return host, db


def _q(value):
    """安全 SQL literal；不把使用者字串拼進 DO/函式外層。"""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if "\x00" in text:
        raise DevotionalEditorError("內容含有不允許的字元", 400)
    return "'" + text.replace("'", "''") + "'"


def _jsonb(value):
    return _q(json.dumps(value, ensure_ascii=False)) + "::jsonb"


def _raise_db_error(stderr):
    text = stderr or ""
    mapping = [
        ("DRAFT_NOT_FOUND", 404, "找不到這份草稿"),
        ("ENTRY_NOT_FOUND", 404, "找不到這篇禱讀內容"),
        ("ENTRY_NOT_EDITABLE", 404, "找不到可編輯的禱讀內容"),
        ("BASE_VERSION_CONFLICT", 409, "原文章已被修改，請重新載入後再儲存"),
        ("VERSION_CONFLICT", 409, "草稿版本已更新，請重新載入"),
        ("DATE_CONFLICT", 409, "這個日期已有禱讀內容，不能覆蓋"),
        ("ENTRY_CHANGE_CONFLICT", 409, "草稿對應的文章已變更，請重新載入"),
        ("DRAFT_APPLIED", 409, "這份草稿已核准，請重新建立草稿"),
        ("APPROVAL_REQUIRED", 400, "必須由非空審核者並勾選來源與神學兩項確認"),
        ("SAMPLE_SOURCE", 400, "不接受 sample／template 或本機測試來源"),
        ("INVALID_PAYLOAD", 400, "草稿內容不完整或不合法"),
        ("invalid input syntax for type date", 400, "日期格式不正確"),
        ("四福音章節超出範圍", 400, "經文範圍超出四福音章節"),
        ("admin_devotional_drafts_active_date_uidx", 409, "這個日期已有草稿"),
        ("duplicate key value violates unique constraint", 409, "這個日期或來源已有內容"),
        ("violates check constraint", 400, "內容不符合資料庫限制"),
        ("canceling statement due to lock timeout", 409, "資料庫忙碌，請稍後重試"),
        ("canceling statement due to statement timeout", 503, "資料庫操作逾時"),
        ("statement timeout", 503, "資料庫操作逾時"),
        ("lock timeout", 409, "資料庫忙碌，請稍後重試"),
    ]
    for token, status, message in mapping:
        if token in text:
            raise DevotionalEditorError(message, status)
    lowered = text.lower()
    if ("does not exist" in lowered and ("admin_devotional" in lowered or "bible_devotional_operator" in lowered)) \
            or "permission denied for schema" in lowered:
        raise DevotionalEditorError("資料庫尚未安裝內容管理 schema，請通知管理員", 503)
    if any(token in lowered for token in ("could not connect", "connection refused", "connection timed out",
                                          "permission denied (publickey", "sudo:", "ssh:")):
        raise DevotionalEditorError("無法連線資料庫", 503)
    raise DevotionalEditorError("資料庫操作失敗", 500)


def _sql(statement):
    """以固定參數執行 psql；不經 shell，限制 timeout 與 statement_timeout。"""
    host, db = _db_target()
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host,
           "sudo", "-n", "-u", "postgres", "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
           "-p", DB_PORT, "-d", db]
    prelude = ("SET ROLE bible_devotional_operator;\n"
               "SET statement_timeout = %s;\n"
               "SET lock_timeout = %s;\n" % (_q(STATEMENT_TIMEOUT), _q(LOCK_TIMEOUT)))
    try:
        proc = subprocess.run(cmd, input=prelude + statement, text=True, encoding="utf-8",
                              errors="replace", capture_output=True, timeout=SSH_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise DevotionalEditorError("資料庫操作逾時", 503)
    except OSError:
        raise DevotionalEditorError("無法連線資料庫", 503)
    if proc.returncode != 0:
        _raise_db_error(proc.stderr)
    return (proc.stdout or "").strip()


def _json_result(text):
    if not text:
        raise DevotionalEditorError("資料庫沒有回傳結果", 500)
    try:
        return json.loads(text)
    except ValueError:
        raise DevotionalEditorError("資料庫回傳格式不正確", 500)


def _strict_date(value, label="日期"):
    if not isinstance(value, str) or not DATE_RE.match(value.strip()):
        raise DevotionalEditorError(label + "必須是 YYYY-MM-DD", 400)
    value = value.strip()
    parsed = parse_iso_date(value)
    if parsed != value:
        raise DevotionalEditorError(label + "不是有效日期", 400)
    return value


def _text(value, label, limit, required=True):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise DevotionalEditorError(label + "必須是文字", 400)
    if "\x00" in value:
        raise DevotionalEditorError(label + "含有不允許的字元", 400)
    value = value.strip()
    if required and not value:
        raise DevotionalEditorError(label + "不可空白", 400)
    if len(value) > limit:
        raise DevotionalEditorError("%s不可超過 %d 字" % (label, limit), 400)
    return value


def _uuid(value):
    if not isinstance(value, str) or not UUID_RE.match(value.strip()):
        raise DevotionalEditorError("草稿 id 格式不正確", 400)
    return str(uuid.UUID(value.strip()))


def _int(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DevotionalEditorError(label + "格式不正確", 400)
    return value


def _range_dict(item, payload=False):
    book = item.get("book_code") or item.get("book")
    key = "book_code" if payload else "book"
    return {
        key: book,
        "start_chapter": item.get("start_chapter"),
        "start_verse": item.get("start_verse"),
        "end_chapter": item.get("end_chapter"),
        "end_verse": item.get("end_verse"),
        **({"sequence_no": item.get("sequence_no")} if payload else {}),
    }


def _parse_reference(reference):
    scope, ranges, _errors = parse_scripture_reference(reference)
    if scope != "IN_SCOPE" or not ranges:
        raise DevotionalEditorError("經文範圍必須是四福音內的有效範圍", 400)
    return ranges


def _generated_source_url(ranges):
    first = ranges[0]
    book = first.book_code.lower()
    chapter = first.start_chapter
    verse = first.start_verse or 1
    return "https://bible.b827262.org/site/chapter.html?book=%s&ch=%d#v%d" % (book, chapter, verse)


def _valid_source_url(value):
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    try:
        if parsed.port == 0:
            return False
    except ValueError:
        return False
    return True


class Editor:
    def __init__(self, site_root):
        self.site_root = os.path.abspath(site_root)

    # ---------- 讀取與驗證 ----------
    def _scripture(self, ranges):
        out = []
        for item in ranges or []:
            book = item.get("book_code") or item.get("book")
            if book not in ("MAT", "MRK", "LUK", "JHN"):
                continue
            try:
                path = os.path.join(self.site_root, "data", book.lower() + ".json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                chapters = data["chapters"]
            except (OSError, ValueError, KeyError):
                raise DevotionalEditorError("讀不到經文資料", 503)
            start_ch = int(item["start_chapter"])
            end_ch = int(item["end_chapter"])
            start_v = item.get("start_verse")
            end_v = item.get("end_verse")
            for chapter in chapters:
                if not start_ch <= int(chapter["ch"]) <= end_ch:
                    continue
                for verse in chapter["verses"]:
                    if int(chapter["ch"]) == start_ch and start_v and verse.get("end", verse["v"]) < start_v:
                        continue
                    if int(chapter["ch"]) == end_ch and end_v and verse["v"] > end_v:
                        continue
                    out.append({
                        "book": book,
                        "chapter": int(chapter["ch"]),
                        "verse": verse["v"],
                        "end": verse.get("end"),
                        "text": verse["text"],
                    })
        return out

    def _clean_content(self, content):
        if not isinstance(content, dict):
            raise DevotionalEditorError("content 必須是物件", 400)
        extra = set(content) - CONTENT_KEYS
        if extra:
            raise DevotionalEditorError("不接受額外欄位：" + "、".join(sorted(extra)), 400)
        date = _strict_date(content.get("date"))
        reference = _text(content.get("reference"), "經文範圍", TEXT_LIMITS["reference"])
        ranges = _parse_reference(reference)
        title = _text(content.get("title"), "標題", TEXT_LIMITS["title"])
        summary = _text(content.get("summary"), "默想", TEXT_LIMITS["summary"])
        reflection = _text(content.get("reflection"), "反思", TEXT_LIMITS["reflection"])
        prayer = _text(content.get("prayer"), "禱告", TEXT_LIMITS["prayer"])
        raw_source = content.get("source_url")
        source_url = _text(raw_source, "來源網址", TEXT_LIMITS["source_url"], required=False)
        if source_url and not _valid_source_url(source_url):
            raise DevotionalEditorError("來源網址不合法", 400)
        if not source_url:
            source_url = _generated_source_url(ranges)
        canonical_url = normalize_url(source_url)
        if not canonical_url:
            raise DevotionalEditorError("來源網址不合法", 400)
        clean = {
            "date": date, "reference": reference, "title": title, "source_url": source_url,
            "summary": summary, "reflection": reflection, "prayer": prayer,
        }
        payload_ranges = [_range_dict({
            "sequence_no": r.sequence_no, "book_code": r.book_code,
            "start_chapter": r.start_chapter, "start_verse": r.start_verse,
            "end_chapter": r.end_chapter, "end_verse": r.end_verse,
        }, payload=True) for r in ranges]
        return clean, payload_ranges, canonical_url

    # ---------- API 操作 ----------
    def preview(self, reference):
        reference = _text(reference, "經文範圍", TEXT_LIMITS["reference"])
        ranges = _parse_reference(reference)
        range_dicts = [_range_dict(vars(r)) for r in ranges]
        return {"ranges": range_dicts, "scripture": self._scripture(range_dicts)}

    def list_entries(self, date_from, date_through):
        date_from = _strict_date(date_from, "起始日期")
        date_through = _strict_date(date_through, "結束日期")
        start = datetime.date.fromisoformat(date_from)
        end = datetime.date.fromisoformat(date_through)
        if end < start:
            raise DevotionalEditorError("起始日期不可晚於結束日期", 400)
        if (end - start).days + 1 > 366:
            raise DevotionalEditorError("日期範圍不可超過 366 日", 400)
        statement = """
SELECT jsonb_build_object(
  'entries', COALESCE((
    SELECT jsonb_agg(jsonb_build_object(
      'id', e.id, 'date', e.devotional_date, 'title', COALESCE(e.title, e.raw_reference),
      'reference', e.raw_reference, 'source_status', e.source_status,
      'theology_status', e.theology_status, 'version', admin_devotional_entry_version(e.id)
    ) ORDER BY e.devotional_date, e.id)
    FROM (
      SELECT * FROM entries
      WHERE devotional_date BETWEEN %s::date AND %s::date
        AND scope = 'IN_SCOPE' AND NOT is_template
        AND canonical_url NOT LIKE '%%example.com%%'
        AND canonical_url NOT LIKE '%%example.org%%'
        AND canonical_url NOT LIKE '%%localhost%%'
        AND canonical_url NOT LIKE '%%127.0.0.1%%'
      ORDER BY devotional_date, id LIMIT 501
    ) e
  ), '[]'::jsonb),
  'drafts', COALESCE((
    SELECT jsonb_agg(jsonb_build_object(
      'id', d.id, 'entry_id', d.entry_id,
      'date', d.payload->'content'->>'date', 'title', d.payload->'content'->>'title',
      'version', d.version,
      'updated_at', to_char(d.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
    ) ORDER BY d.updated_at DESC)
    FROM (
      SELECT * FROM admin_devotional_drafts
      WHERE status = 'DRAFT'
        AND payload->'content'->>'date' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        AND (payload->'content'->>'date')::date BETWEEN %s::date AND %s::date
      ORDER BY updated_at DESC LIMIT 501
    ) d
  ), '[]'::jsonb)
)
""" % (_q(date_from), _q(date_through), _q(date_from), _q(date_through))
        data = _json_result(_sql(statement))
        if len(data.get("entries") or []) > 500 or len(data.get("drafts") or []) > 500:
            raise DevotionalEditorError("日期範圍內筆數超過 500，請縮小範圍", 400)
        return data

    def get_entry(self, entry_id):
        entry_id = _int(entry_id, "文章 id", 1)
        statement = """
SELECT jsonb_build_object(
  'id', e.id, 'version', admin_devotional_entry_version(e.id),
  'content', jsonb_build_object(
    'date', e.devotional_date, 'reference', e.raw_reference,
    'title', COALESCE(e.title, ''), 'source_url', COALESCE(e.source_url, ''),
    'summary', COALESCE(e.summary, ''), 'reflection', COALESCE(e.reflection, ''),
    'prayer', COALESCE(e.prayer, '')
  ),
  'source_status', e.source_status, 'theology_status', e.theology_status,
  'ranges', COALESCE((
    SELECT jsonb_agg(jsonb_build_object(
      'book', r.book_code, 'start_chapter', r.start_chapter, 'start_verse', r.start_verse,
      'end_chapter', r.end_chapter, 'end_verse', r.end_verse
    ) ORDER BY r.sequence_no)
    FROM scripture_ranges r WHERE r.entry_id = e.id
  ), '[]'::jsonb)
)
FROM entries e
WHERE e.id = %d AND e.scope = 'IN_SCOPE' AND NOT e.is_template
  AND e.canonical_url NOT LIKE '%%example.com%%'
  AND e.canonical_url NOT LIKE '%%example.org%%'
  AND e.canonical_url NOT LIKE '%%localhost%%'
  AND e.canonical_url NOT LIKE '%%127.0.0.1%%'
""" % entry_id
        text = _sql(statement)
        if not text:
            raise DevotionalEditorError("找不到可編輯的禱讀內容", 404)
        data = _json_result(text)
        ranges = data.pop("ranges", [])
        return {"entry": data, "scripture": self._scripture(ranges)}

    def get_draft(self, draft_id):
        draft_id = _uuid(draft_id)
        statement = """
SELECT jsonb_build_object(
  'id', d.id, 'version', d.version, 'entry_id', d.entry_id, 'base_version', d.base_version,
  'content', d.payload->'content', 'status', d.status,
  'ranges', COALESCE(d.payload->'ranges', '[]'::jsonb)
)
FROM admin_devotional_drafts d WHERE d.id = %s::uuid
""" % _q(draft_id)
        text = _sql(statement)
        if not text:
            raise DevotionalEditorError("找不到這份草稿", 404)
        data = _json_result(text)
        ranges = data.pop("ranges", [])
        return {"draft": data, "scripture": self._scripture(ranges)}

    def save(self, body):
        if not isinstance(body, dict):
            raise DevotionalEditorError("請求內容必須是物件", 400)
        draft_id = body.get("draft_id")
        draft_id = str(uuid.uuid4()) if draft_id is None else _uuid(draft_id)
        version = _int(body.get("version", 0), "草稿版本")
        entry_id = body.get("entry_id")
        entry_id = None if entry_id is None else _int(entry_id, "文章 id", 1)
        base_version = body.get("base_version")
        if base_version is not None and (not isinstance(base_version, str) or len(base_version) > 128):
            raise DevotionalEditorError("base_version 格式不正確", 400)
        if entry_id is not None and not (base_version or "").strip():
            raise DevotionalEditorError("缺少 base_version，請重新載入文章", 409)
        content, ranges, canonical_url = self._clean_content(body.get("content"))
        payload = {"content": content, "canonical_url": canonical_url, "ranges": ranges}
        statement = "SELECT admin_devotional_draft_save(%s::uuid, %d, %s, %s, %s)::text;" % (
            _q(draft_id), version, _q(entry_id), _q(base_version), _jsonb(payload))
        data = _json_result(_sql(statement))
        stored = data.get("payload") or payload
        return {
            "draft": {
                "id": data.get("id"), "version": data.get("version"), "entry_id": data.get("entry_id"),
                "base_version": data.get("base_version"), "content": stored.get("content"),
                "status": data.get("status"),
            },
            "scripture": self._scripture(ranges),
        }

    def approve(self, body):
        if not isinstance(body, dict):
            raise DevotionalEditorError("請求內容必須是物件", 400)
        draft_id = _uuid(body.get("draft_id"))
        version = _int(body.get("version"), "草稿版本")
        reviewer = _text(body.get("reviewer"), "審核者", 120)
        if body.get("source_confirmed") is not True or body.get("theology_confirmed") is not True:
            raise DevotionalEditorError("必須勾選來源與神學兩項確認", 400)
        statement = "SELECT admin_devotional_draft_approve(%s::uuid, %d, %s, %s, %s)::text;" % (
            _q(draft_id), version, _q(reviewer), _q(True), _q(True))
        data = _json_result(_sql(statement))
        data["message"] = "已核准，等待每日排程發佈；公開檔尚未變更"
        return data
