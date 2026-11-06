#!/usr/bin/env python3
"""Apply the human review fixes to the 365 pending drafts.

1. batch-365/manual-edits.json: hand-written replacements per day and field.
2. Mechanical rules: Traditional characters only, God addressed as 祢, prayers addressed
   to Jesus end with 阿們 (not 奉主耶穌的名), every prayer ends with 阿們, 著 not 着, reflections in the first person.
3. Reading plan boundaries (batch_365.reading_plan) no longer cut a sentence in half.

Default is a dry run that prints the changes. --write updates drafts.json; --db also updates the
pending PostgreSQL rows (text, reference and scripture range). Approvals are never touched here;
any edit leaves the entry pending, as the database triggers require.
"""
import argparse
import json
import re
from pathlib import Path

from batch_365 import BATCH_SIZE, OUTPUT, reading_plan
from cli import q, sql
from generate_draft import scripture

FIELDS = ('title', 'summary', 'reflection', 'prayer')
SIMPLIFIED = {'鉴': '鑒', '时': '時', '与': '與', '欢': '歡'}
JESUS = re.compile(r'耶穌|基督|羔羊|人子|牧人|復活的主')
QUOTE = re.compile(r'(「[^」]*」|『[^』]*』)')


def outside_quotes(text, change):
    """Apply change() only to the parts of text that are not quotations."""
    return ''.join(part if QUOTE.fullmatch(part) else change(part) for part in QUOTE.split(text))


def mechanical(draft):
    out = dict(draft)
    for key in FIELDS:
        for bad, good in SIMPLIFIED.items():
            out[key] = out[key].replace(bad, good)
        out[key] = outside_quotes(out[key], lambda s: s.replace('着', '著'))
    out['prayer'] = outside_quotes(out['prayer'], lambda s: re.sub(r'妳|你(?!們)', '祢', s))
    out['reflection'] = outside_quotes(out['reflection'], lambda s: re.sub(r'你(?!們)', '我', s))
    prayer = out['prayer']
    address = prayer.split('，', 1)[0]
    if JESUS.search(address) and prayer.endswith('奉主耶穌的名禱告，阿們。'):
        prayer = prayer[:-len('奉主耶穌的名禱告，阿們。')] + '阿們。'
    if not prayer.endswith('阿們。'):
        prayer = prayer.rstrip('。，、 ') + '。阿們。'
    out['prayer'] = prayer
    return out


def problems(draft):
    found = []
    text = ''.join(draft[k] for k in FIELDS)
    if any(ch in text for ch in SIMPLIFIED):
        found.append('簡體字')
    if re.search(r'妳|你(?!們)', QUOTE.sub('', draft['prayer'])):
        found.append('禱告以你稱呼神')
    if JESUS.search(draft['prayer'].split('，', 1)[0]) and '奉主耶穌的名' in draft['prayer']:
        found.append('向耶穌禱告卻奉耶穌的名')
    if not draft['prayer'].endswith('阿們。'):
        found.append('禱告沒有以阿們結尾')
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--write', action='store_true', help='寫回 batch-365/*/drafts.json')
    p.add_argument('--db', action='store_true', help='同時更新 PostgreSQL 待審紀錄（需 --write）')
    args = p.parse_args()
    if args.db and not args.write:
        p.error('--db 需要 --write')
    plan = reading_plan()
    edits = json.loads((OUTPUT / 'manual-edits.json').read_text(encoding='utf-8'))
    changed, remaining = [], []
    for index in range(0, 365, BATCH_SIZE):
        batch = plan[index:index + BATCH_SIZE]
        path = OUTPUT / f'{batch[0]["day"]:03d}-{batch[-1]["day"]:03d}' / 'drafts.json'
        drafts = json.loads(path.read_text(encoding='utf-8'))
        fixed = []
        for row, draft in zip(batch, drafts):
            new = dict(draft, **edits.get(str(row['day']), {}))
            new = mechanical(new)
            fixed.append(new)
            if new != draft:
                changed.append((row, draft, new))
            if problems(new):
                remaining.append((row['day'], problems(new)))
        if args.write and fixed != drafts:
            path.write_text(json.dumps(fixed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    stored = json.loads(sql("SELECT COALESCE(jsonb_agg(jsonb_build_object('date',devotional_date,'reference',raw_reference)),'[]'::jsonb) FROM entries WHERE devotional_date BETWEEN '2026-11-21' AND '2027-11-20';"))
    stored = {r['date']: r['reference'] for r in stored}
    moved = [row for row in plan if stored.get(row['date']) != row['reference']]
    print(f'草稿文字變更 {len(changed)} 篇，經文範圍變更 {len(moved)} 篇，殘留問題 {len(remaining)} 篇')
    for day, found in remaining:
        print(f'  第 {day} 天：{"、".join(found)}')
    if not args.db:
        return
    texts = {row['day']: new for row, _, new in changed}
    statements = []
    for row in plan:
        moved_here = row in moved
        if row['day'] not in texts and not moved_here:
            continue
        sets = [f'{k}={q(texts[row["day"]][k])}' for k in FIELDS] if row['day'] in texts else []
        where = f"devotional_date={q(row['date'])}::date"
        if moved_here:
            r, _ = scripture(row['reference'])
            url = f'https://bible.b827262.org/site/chapter.html?book={r.book_code.lower()}&ch={r.start_chapter}#v{r.start_verse or 1}'
            sets += [f'raw_reference={q(row["reference"])}', f'source_url={q(url)}', f'canonical_url={q(url)}']
            statements.append(f"UPDATE scripture_ranges SET start_chapter={r.start_chapter},start_verse={q(r.start_verse)},end_chapter={r.end_chapter},end_verse={q(r.end_verse)} "
                              f"WHERE sequence_no=1 AND entry_id=(SELECT id FROM entries WHERE {where});")
        statements.append(f"UPDATE entries SET {','.join(sets)} WHERE {where} AND source_status='PENDING' AND theology_status='PENDING';")
    sql('BEGIN;\n' + '\n'.join(statements) + '\nCOMMIT;')
    print(f'PostgreSQL 已更新 {sum(s.startswith("UPDATE entries") for s in statements)} 筆待審紀錄')


if __name__ == '__main__':
    main()
