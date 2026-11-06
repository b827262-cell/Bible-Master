#!/usr/bin/env python3
"""Generate and independently review 365 consecutive, pending devotional drafts."""
import argparse
import concurrent.futures
import datetime
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from cli import q, sql
from generate_draft import DATA, save, scripture

START = datetime.date(2026, 11, 21)
OUTPUT = Path(__file__).resolve().parent / 'batch-365'
BOOKS = [('mat', '馬太福音'), ('mrk', '馬可福音'), ('luk', '路加福音'), ('jhn', '約翰福音')]
BATCH_SIZE = 8
# 人工審查：這幾天的默想需要下一節才完整（可 14:52、路 17:10、路 24:43），段落多帶一節
EXTEND = {161, 242, 278}


def reading_plan():
    chapters = []
    for key, name in BOOKS:
        book = json.loads((DATA / f'{key}.json').read_text(encoding='utf-8'))
        for chapter in book['chapters']:
            chapters.append({'name': name, 'chapter': chapter['ch'], 'verses': chapter['verses'], 'parts': 1})
    while sum(ch['parts'] for ch in chapters) < 365:
        eligible = [ch for ch in chapters if ch['parts'] < len(ch['verses'])]
        chosen = max(eligible, key=lambda ch: len(ch['verses']) / ch['parts'])
        chosen['parts'] += 1
    result = []
    for ch in chapters:
        verses, count = ch['verses'], ch['parts']
        cuts = [len(verses) * index // count for index in range(count + 1)]
        for index in range(1, count):
            day = len(result) + index
            # 不在句子中間斷開：段落最後一節以「、」結尾時，把後面的節併入，直到句子結束
            while cuts[index] < cuts[index + 1] - 1 and (
                    re.sub(r'〈[^〉]*〉$', '', verses[cuts[index] - 1]['text']).endswith('、')
                    or (day in EXTEND and cuts[index] == len(verses) * index // count)):
                cuts[index] += 1
            if cuts[index] - len(verses) * index // count > 3:
                cuts[index] = len(verses) * index // count  # 家譜等整段長句，保留原切點
        for index in range(count):
            start, end = cuts[index], cuts[index + 1]
            first, last = verses[start], verses[end - 1]
            first_num = first['v']
            last_num = last.get('end', last['v'])
            segment = f'{first_num}' if first_num == last_num else f'{first_num}–{last_num}'
            ref = f"{ch['name']} {ch['chapter']}:{segment}"
            _, text = scripture(ref)
            result.append({'day': len(result) + 1, 'date': (START + datetime.timedelta(days=len(result))).isoformat(), 'reference': ref, 'scripture': text})
    assert len(result) == 365
    return result


def model(prompt):
    proc = subprocess.run(['agy', '--model', 'gemini-4-argon-medium', '--effort', 'medium', '--mode', 'plan',
                           '--output-format', 'json', '--print-timeout', '5m', '-p', prompt],
                          capture_output=True, text=True, timeout=310, check=True)
    envelope = json.loads(proc.stdout)
    if envelope.get('status') != 'SUCCESS':
        raise ValueError('AGY 無法完成任務')
    response = envelope.get('response', '').strip()
    response = re.sub(r'^```(?:json)?\s*|\s*```$', '', response, flags=re.I)
    return json.loads(response)


def generated(plan, batch):
    inputs = [{'day': row['day'], 'reference': row['reference'], 'scripture': row['scripture']} for row in batch]
    prompt = ('以繁體中文為以下每段四福音經文撰寫原創禱讀。只依所附經文，不使用工具、不可改檔、不要引用其他靈修文章。'
              '每篇給主題、約兩至三句默想、一句反思問題及約兩至三句禱告。不得重寫或引用長篇經文，'
              '避免將個人經歷當成普遍命令，與經文不同的應用不可假稱經文原話。'
              '僅輸出 JSON 陣列，按輸入順序逐篇回傳 day、title、summary、reflection、prayer，全部為非空字串，day 為整數。\n'
              + json.dumps(inputs, ensure_ascii=False))
    data = model(prompt)
    if not isinstance(data, list) or len(data) != len(batch):
        raise ValueError('生成數量不符')
    for item, expected in zip(data, batch):
        if not isinstance(item, dict) or set(item) != {'day', 'title', 'summary', 'reflection', 'prayer'} or item['day'] != expected['day']:
            raise ValueError('生成欄位或編號不符')
        if any(not isinstance(item[k], str) or not item[k].strip() or len(item[k]) > 2000 for k in ('title','summary','reflection','prayer')):
            raise ValueError('生成內容空白或過長')
    return data


def review(batch, drafts):
    inputs = [{'day': row['day'], 'reference': row['reference'], 'scripture': row['scripture'], 'draft': draft} for row, draft in zip(batch, drafts)]
    prompt = ('你是四福音禱讀內容的獨立文字審查者。逐篇對照給定經文，檢查默想、反思、禱告是否有不符合經文、'
              '過度推論、教義敏感或不當承諾，以及用字明顯錯誤。請勿使用工具或改檔。'
              '僅輸出 JSON 陣列，每項只含 day（整數）、assessment（CLEAR 或 REVIEW）、issues（繁體中文文字陣列）。'
              '有任何不確定或神學分歧標為 REVIEW 並指出位置與原因。沒有問題時 issues 為空。'
              '機器審查不等於人工或神學核准。\n' + json.dumps(inputs, ensure_ascii=False))
    result = model(prompt)
    if not isinstance(result, list) or len(result) != len(batch):
        raise ValueError('審查數量不符')
    for row, expected in zip(result, batch):
        if not isinstance(row, dict) or set(row) != {'day','assessment','issues'} or row['day'] != expected['day'] or row['assessment'] not in ('CLEAR','REVIEW') or not isinstance(row['issues'], list) or any(not isinstance(x, str) for x in row['issues']):
            raise ValueError('審查格式或編號錯誤')
        if row['assessment'] == 'CLEAR' and row['issues']:
            raise ValueError('審查狀態與問題不一致')
    return result


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def run_batch(plan, index, mode):
    batch = plan[index:index+BATCH_SIZE]
    path = OUTPUT / f'{batch[0]["day"]:03d}-{batch[-1]["day"]:03d}'
    draft_path, review_path = path / 'drafts.json', path / 'review.json'
    if mode == 'generate':
        if draft_path.exists():
            drafts = json.loads(draft_path.read_text())
        else:
            drafts = generated(plan, batch)
            atomic_json(draft_path, drafts)
        for row, draft in zip(batch, drafts):
            exists = sql('SELECT count(*) FROM entries WHERE devotional_date='+q(row['date'])+'::date;')
            if exists != '0':
                current = json.loads(sql("SELECT COALESCE(jsonb_agg(jsonb_build_object('reference',raw_reference,'title',title,'summary',summary,'reflection',reflection,'prayer',prayer)),'[]'::jsonb) FROM entries WHERE devotional_date="+q(row['date'])+'::date;'))
                comparable = {k: draft[k] for k in ('title','summary','reflection','prayer')}
                if len(current) != 1 or current[0].get('reference') != row['reference'] or any(current[0].get(k) != v for k, v in comparable.items()):
                    raise ValueError(f"{row['date']} 已有不同紀錄，停止以免覆蓋")
                continue
            parsed, _ = scripture(row['reference'])
            save(row['date'], row['reference'], parsed, draft)
        return f'第 {batch[0]["day"]}–{batch[-1]["day"]} 天草稿已存入待審'
    if not draft_path.exists():
        raise ValueError('缺少草稿')
    drafts = json.loads(draft_path.read_text())
    if not review_path.exists():
        atomic_json(review_path, review(batch, drafts))
    return f'第 {batch[0]["day"]}–{batch[-1]["day"]} 天 AGY 審查完成'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['plan','generate','review'])
    p.add_argument('--workers', type=int, choices=[1,2], default=1)
    p.add_argument('--through', type=int, default=365, help='處理至指定天數')
    args = p.parse_args()
    plan = reading_plan()
    if args.mode == 'plan':
        print(json.dumps([{k:v for k,v in row.items() if k != 'scripture'} for row in plan], ensure_ascii=False, indent=2))
        return
    if not 1 <= args.through <= 365:
        p.error('--through 須介於 1 和 365')
    indexes = list(range(0, args.through, BATCH_SIZE))
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_batch, plan, i, args.mode): i for i in indexes}
        for future in concurrent.futures.as_completed(futures):
            try:
                print(future.result(), flush=True)
            except Exception as exc:
                index = futures[future]
                failures.append(index + 1)
                print(f'第 {index+1} 天起處理失敗：{exc}', file=sys.stderr, flush=True)
    if failures:
        raise SystemExit(f'未完成批次：{failures}。可重跑相同命令繼續。')


if __name__ == '__main__':
    main()
