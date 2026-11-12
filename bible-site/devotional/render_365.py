#!/usr/bin/env python3
"""Verify generated drafts against PostgreSQL and prepare review artifacts."""
import collections
import hashlib
import json
from pathlib import Path

from batch_365 import BATCH_SIZE, BOOKS, DATA, OUTPUT, reading_plan
from cli import sql
from parser import parse_scripture_reference


def main():
    plan = reading_plan()
    stored = json.loads(sql("SELECT COALESCE(jsonb_agg(jsonb_build_object('date',devotional_date,'reference',raw_reference,'title',title,'summary',summary,'reflection',reflection,'prayer',prayer,'source_status',source_status,'theology_status',theology_status) ORDER BY devotional_date),'[]'::jsonb) FROM entries WHERE devotional_date BETWEEN '2026-11-21' AND '2027-11-20';"))
    if len(stored) != 365 or len({r['date'] for r in stored}) != 365:
        raise ValueError('資料庫日期或筆數不符')
    drafts, reviews = {}, {}
    for index in range(0, 365, BATCH_SIZE):
        batch = plan[index:index + BATCH_SIZE]
        folder = OUTPUT / f'{batch[0]["day"]:03d}-{batch[-1]["day"]:03d}'
        for name, target in [('drafts.json', drafts), ('review.json', reviews)]:
            data = json.loads((folder / name).read_text(encoding='utf-8'))
            if [item['day'] for item in data] != [item['day'] for item in batch]:
                raise ValueError(f'{folder}/{name} 編號不符')
            target.update({item['day']: item for item in data})
    coverage = collections.defaultdict(list)
    complete = ['# 四福音每日禱讀｜365 天待審稿', '', '2026 年 11 月 21 日至 2027 年 11 月 20 日。',
                '經文取自專案四福音和合本資料。默想、反思及禱告為 AI 原創草稿，全部待人工及神學審核。', '']
    findings = ['# 四福音禱讀｜Gemini 4 Argon Medium 初審', '',
                '審查以專案經文逐批核對。模型初審結果不代表人工或神學核准。', '']
    statuses = collections.Counter()
    for expected, row in zip(plan, stored):
        draft, review = drafts[expected['day']], reviews[expected['day']]
        if row['date'] != expected['date'] or row['reference'] != expected['reference']:
            raise ValueError(f"第 {expected['day']} 天資料庫日期或經文不符")
        if any(row[key] != draft[key] for key in ('title','summary','reflection','prayer')):
            raise ValueError(f"第 {expected['day']} 天資料庫與模型審查的草稿不同")
        if row['source_status'] != 'PENDING' or row['theology_status'] != 'PENDING':
            raise ValueError(f"第 {expected['day']} 天不是待審狀態")
        scope, ranges, errors = parse_scripture_reference(expected['reference'])
        if scope != 'IN_SCOPE' or errors or len(ranges) != 1:
            raise ValueError(f"第 {expected['day']} 天經文範圍錯誤")
        r = ranges[0]
        book = json.loads((DATA / f'{r.book_code.lower()}.json').read_text(encoding='utf-8'))
        selected = []
        for chapter in book['chapters']:
            if not r.start_chapter <= chapter['ch'] <= r.end_chapter:
                continue
            for verse in chapter['verses']:
                if chapter['ch'] == r.start_chapter and r.start_verse and verse.get('end', verse['v']) < r.start_verse:
                    continue
                if chapter['ch'] == r.end_chapter and r.end_verse and verse['v'] > r.end_verse:
                    continue
                coverage[(r.book_code, chapter['ch'])].append(verse['v'])
                label = str(verse['v']) + (f"–{verse['end']}" if verse.get('end') else '')
                selected.append(f"- {chapter['ch']}:{label} {verse['text']}")
        if not selected:
            raise ValueError(f"第 {expected['day']} 天沒有經文")
        complete += [f"## 第 {expected['day']} 天｜{row['date']}｜{row['title']}", '',
                     f"**經文範圍**：{row['reference']}", '', '**經文內容**', '', *selected, '',
                     f"**默想**：{row['summary']}", '', f"**反思**：{row['reflection']}", '', f"**全心禱告**：{row['prayer']}", '']
        statuses[review['assessment']] += 1
        if review['assessment'] == 'REVIEW':
            findings += [f"## 第 {expected['day']} 天｜{row['date']}｜{row['reference']}", '']
            findings += [f'- {issue}' for issue in review['issues']] or ['- 模型要求複核，但未提供原因。']
            findings.append('')
    for key, _ in BOOKS:
        book = json.loads((DATA / f'{key}.json').read_text(encoding='utf-8'))
        for chapter in book['chapters']:
            expected = [verse['v'] for verse in chapter['verses']]
            if coverage[(key.upper(),chapter['ch'])] != expected:
                raise ValueError(f"{key} {chapter['ch']} 節次缺漏或重複")
    findings[3:3] = [f"已審 {sum(statuses.values())} 篇，模型標記需複核 {statuses['REVIEW']} 篇，其餘 {statuses['CLEAR']} 篇未列出具體疑點。", '']
    (OUTPUT / '365-days-review-draft.md').write_text('\n'.join(complete), encoding='utf-8')
    (OUTPUT / 'argon-review-findings.md').write_text('\n'.join(findings), encoding='utf-8')
    print(f"365 篇、89 章經文逐筆覆蓋無缺漏或重複。Argon 需複核 {statuses['REVIEW']} 篇，其他 {statuses['CLEAR']} 篇。")


if __name__ == '__main__':
    main()
