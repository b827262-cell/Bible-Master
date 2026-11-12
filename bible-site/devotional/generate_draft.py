#!/usr/bin/env python3
"""Generate one scripture-grounded draft for human review using AGY."""
import argparse
import json
import re
import subprocess
from pathlib import Path

from cli import q, sql
from parser import parse_iso_date, parse_scripture_reference

DATA = Path(__file__).resolve().parent.parent / 'data'


def scripture(reference):
    scope, ranges, errors = parse_scripture_reference(reference)
    if scope != 'IN_SCOPE' or errors or len(ranges) != 1:
        raise ValueError('請指定一段有效的四福音經文')
    r = ranges[0]
    book = json.loads((DATA / f'{r.book_code.lower()}.json').read_text(encoding='utf-8'))
    verses = []
    for chapter in book['chapters']:
        if not r.start_chapter <= chapter['ch'] <= r.end_chapter:
            continue
        for verse in chapter['verses']:
            if chapter['ch'] == r.start_chapter and r.start_verse and verse.get('end', verse['v']) < r.start_verse:
                continue
            if chapter['ch'] == r.end_chapter and r.end_verse and verse['v'] > r.end_verse:
                continue
            verses.append(f"{chapter['ch']}:{verse['v']} {verse['text']}")
    if not verses or len(verses) > 40:
        raise ValueError('每篇須選擇 1 至 40 節經文')
    return r, '\n'.join(verses)


def generate(reference, passage):
    prompt = ('依以下四福音經文創作繁體中文禱讀草稿。只根據此經文撰寫，'
              '不引用其他靈修文章，不憑記憶重寫經文。請輸出 JSON 物件，'
              '只含 title、summary、reflection、prayer 四個非空字串。'
              'summary 約 60–120 字，reflection 是一個問題，prayer 是一段禱告。'
              '不要使用工具，不寫檔，不標示已審核。\n經文範圍：' + reference + '\n' + passage)
    process = subprocess.run(
        ['agy', '--model', 'gemini-4-argon-medium', '--effort', 'medium', '--mode', 'plan',
         '--output-format', 'json', '--print-timeout', '3m', '-p', prompt],
        capture_output=True, text=True, timeout=200, check=True,
    )
    result = json.loads(process.stdout)
    if result.get('status') != 'SUCCESS':
        raise ValueError('模型未成功產生草稿')
    response = result.get('response', '').strip()
    response = re.sub(r'^```(?:json)?\s*|\s*```$', '', response, flags=re.I)
    draft = json.loads(response)
    if not isinstance(draft, dict) or set(draft) != {'title', 'summary', 'reflection', 'prayer'}:
        raise ValueError('模型輸出的欄位不正確')
    if any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in draft.values()):
        raise ValueError('模型輸出含空白或過長內容')
    return {key: value.strip() for key, value in draft.items()}


def save(date, reference, r, draft):
    url = f'https://bible.b827262.org/site/chapter.html?book={r.book_code.lower()}&ch={r.start_chapter}#v{r.start_verse or 1}'
    values = [url, url, date, reference, 'IN_SCOPE', False,
              draft['title'], draft['summary'], draft['reflection'], draft['prayer']]
    range_values = [1, r.book_code, r.start_chapter, r.start_verse, r.end_chapter, r.end_verse]
    statement = ('BEGIN; SELECT pg_advisory_xact_lock(hashtextextended(\'bible-devotional-daily\',0)); '
                 'WITH new_entry AS (INSERT INTO entries(source_url,canonical_url,devotional_date,'
                 'raw_reference,scope,is_template,title,summary,reflection,prayer) SELECT '
                 + ','.join(q(value) for value in values)
                 + ' WHERE NOT EXISTS (SELECT 1 FROM entries WHERE devotional_date=' + q(date) + '::date)'
                 + ' ON CONFLICT DO NOTHING RETURNING id) '
                 'INSERT INTO scripture_ranges(entry_id,sequence_no,book_code,start_chapter,start_verse,end_chapter,end_verse) '
                 'SELECT id,' + ','.join(q(value) for value in range_values) + ' FROM new_entry RETURNING entry_id; COMMIT;')
    saved = sql(statement)
    if not saved:
        raise ValueError('該日期已有資料，未覆蓋既有草稿')
    return int(saved)


def main():
    parser = argparse.ArgumentParser(description='依專案四福音經文產生待人工審核的禱讀草稿')
    parser.add_argument('--date', required=True, help='YYYY-MM-DD')
    parser.add_argument('--reference', required=True, help='例如 馬太福音 5:1–12')
    parser.add_argument('--save', action='store_true', help='將草稿寫入 PostgreSQL 待審核')
    args = parser.parse_args()
    if parse_iso_date(args.date) != args.date:
        raise ValueError('日期須為 YYYY-MM-DD')
    r, passage = scripture(args.reference)
    if args.save and sql('SELECT count(*) FROM entries WHERE devotional_date=' + q(args.date) + '::date;') != '0':
        raise ValueError('該日期已有資料，未呼叫模型或覆蓋既有草稿')
    draft = generate(args.reference, passage)
    result = {'date': args.date, 'reference': args.reference, 'draft': draft,
              'source_status': 'PENDING', 'theology_status': 'PENDING'}
    if args.save:
        result['id'] = save(args.date, args.reference, r, draft)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc))
