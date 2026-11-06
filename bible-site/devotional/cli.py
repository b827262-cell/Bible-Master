#!/usr/bin/env python3
"""Manual import and review. No remote crawling or media downloading."""
import argparse,csv,datetime,json,os,re,subprocess,sys
from pathlib import Path
from zoneinfo import ZoneInfo
from parser import normalize_url, parse_iso_date, parse_scripture_reference
HOST=os.environ.get('DEVOTIONAL_SSH_HOST','debian-toshiba')
DB=os.environ.get('DEVOTIONAL_DATABASE','bible_devotional')
if not re.fullmatch(r'[a-z][a-z0-9_]*',DB): raise SystemExit('Invalid database name')
def q(v):
    if v is None:return 'NULL'
    if isinstance(v,bool):return 'TRUE' if v else 'FALSE'
    if isinstance(v,int):return str(v)
    return "'"+str(v).replace("'","''")+"'"
def sql(statement,reader=False):
    cmd=['ssh','-o','BatchMode=yes',HOST,'sudo','-n','-u','postgres','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-p','5433','-d',DB]
    p=subprocess.run(cmd,input=('SET ROLE bible_devotional_export_reader;\n' if reader else 'SET ROLE bible_devotional_operator;\n')+statement,text=True,capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()
def sample(row,url):
    batch=row.get('import_batch_id','').lower()
    return any(x in batch for x in ('sample_','template_')) or (url and any(x in url.lower() for x in ('example.com','example.org','localhost','127.0.0.1')))
def validurl(s):
    from urllib.parse import urlsplit
    try:
        p=urlsplit(s); return bool(p.scheme in ('http','https') and p.hostname and not p.username and not p.password and p.port != 0)
    except ValueError:return False
def rows(path,kind):
    out=[];seen=set()
    with open(path,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);required={'raw_scripture_text', 'source_url' if kind=='entries' else 'media_url'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):raise ValueError('CSV 缺少必要欄位: '+', '.join(sorted(required)))
        for line,row in enumerate(reader,2):
            raw=row.get('source_url' if kind=='entries' else 'media_url','').strip()
            url=normalize_url(raw) if validurl(raw) else ''
            date=parse_iso_date(row.get('devotional_date' if kind=='entries' else 'recorded_date',''))
            scope,ranges,issues=parse_scripture_reference(row.get('raw_scripture_text',''))
            if not url:issues.append('網址不合法')
            if kind=='entries' and not date:issues.append('日期缺失或錯誤')
            if kind=='media' and row.get('recorded_date') and not date:issues.append('日期格式錯誤')
            key=(url,date) if kind=='entries' else url
            eligible=bool(url and scope != "OUT_OF_SCOPE")
            duplicate=eligible and key in seen
            if eligible:seen.add(key)
            out.append(dict(line=line,url=url,source_url=raw,date=date,reference=row.get('raw_scripture_text',''),scope=scope,ranges=[vars(x) for x in ranges],issues=issues,duplicate=duplicate,is_template=sample(row,url)))
    return out
def import_rows(records,kind):
    commands=['BEGIN;']
    for x in records:
        if x["scope"] == "OUT_OF_SCOPE" or x["duplicate"] or not x["url"]:
            continue
        if kind=='entries':
            st='NEEDS_FIX' if x['issues'] else 'PENDING'
            values=','.join(q(z) for z in [x['source_url'],x['url'],x['date'],x['reference'],x['scope'],x['is_template'],st])
            payload=q(json.dumps(x['ranges'],ensure_ascii=False))
            commands.append("WITH inserted AS (INSERT INTO entries(source_url,canonical_url,devotional_date,raw_reference,scope,is_template,source_status) VALUES ("+values+") ON CONFLICT DO NOTHING RETURNING id) INSERT INTO scripture_ranges(entry_id,sequence_no,book_code,start_chapter,start_verse,end_chapter,end_verse) SELECT inserted.id,r.sequence_no,r.book_code,r.start_chapter,r.start_verse,r.end_chapter,r.end_verse FROM inserted CROSS JOIN jsonb_to_recordset("+payload+"::jsonb) AS r(sequence_no int,book_code text,start_chapter int,start_verse int,end_chapter int,end_verse int);")
        else:
            book=x['ranges'][0]['book_code'] if len(x['ranges'])==1 else None
            commands.append('INSERT INTO media_links(canonical_url,recorded_date,raw_reference,scope,book_code,is_template) VALUES('+','.join(q(z) for z in [x['url'],x['date'],x['reference'],x['scope'],book,x['is_template']])+') ON CONFLICT DO NOTHING;')
    commands.append('COMMIT;');sql('\n'.join(commands))
def pending(from_date, to_date, flagged):
    if any(parse_iso_date(date) != date for date in (from_date, to_date)):
        raise ValueError('--from 與 --to 須為 YYYY-MM-DD')
    if from_date > to_date:
        raise ValueError('--from 不可晚於 --to')

    flagged_dates = None
    if flagged:
        report = Path(__file__).resolve().parent / 'batch-365' / 'argon-review-findings.md'
        try:
            findings = report.read_text(encoding='utf-8')
        except FileNotFoundError as exc:
            raise ValueError(f'找不到本機 Argon 審查報告：{report}') from exc
        flagged_dates = set(re.findall(r'^## 第 [0-9]+ 天｜([0-9]{4}-[0-9]{2}-[0-9]{2})｜', findings, re.MULTILINE))

    result = sql(f"""
        BEGIN READ ONLY;
        SELECT COALESCE(jsonb_agg(to_jsonb(pending) ORDER BY devotional_date, id), '[]'::jsonb)
        FROM (
            SELECT id, devotional_date, raw_reference, title, source_status, theology_status
            FROM entries
            WHERE devotional_date BETWEEN {q(from_date)}::date AND {q(to_date)}::date
              AND (source_status <> 'APPROVED' OR theology_status <> 'APPROVED')
        ) AS pending;
        COMMIT;
    """)
    writer = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
    writer.writerow(('ID', '日期', '經文範圍', '標題', '來源審核', '神學審核'))
    for entry in json.loads(result):
        if flagged_dates is None or entry['devotional_date'] in flagged_dates:
            writer.writerow([entry[key] for key in (
                'id', 'devotional_date', 'raw_reference', 'title', 'source_status', 'theology_status',
            )])


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    for c in ['dry-run','import']:
        x=sub.add_parser(c);x.add_argument('--devotional-csv');x.add_argument('--media-csv');x.add_argument('--output-report')
    x=sub.add_parser('draft');x.add_argument('id',type=int);x.add_argument('--summary',required=True);x.add_argument('--reflection',required=True);x.add_argument('--title');x.add_argument('--prayer')
    x=sub.add_parser('review');x.add_argument('id',type=int);x.add_argument('--type',choices=['source','theology'],required=True);x.add_argument('--reviewer',required=True)
    x=sub.add_parser('media-link');x.add_argument('media_id',type=int);x.add_argument('entry_id',type=int)
    x=sub.add_parser('media-review');x.add_argument('media_id',type=int);x.add_argument('--reviewer',required=True)
    x=sub.add_parser('show');x.add_argument('--date',required=True,help='日期 YYYY-MM-DD')
    x=sub.add_parser('today');x.add_argument('--date',help='指定日期 YYYY-MM-DD，預設台灣時間今天')
    x = sub.add_parser('pending', help='列出日期區間內尚未完成雙重審核的篇章')
    x.add_argument('--from', dest='from_date', required=True, help='起日 YYYY-MM-DD（含）')
    x.add_argument('--to', dest='to_date', required=True, help='迄日 YYYY-MM-DD（含）')
    x.add_argument('--flagged', action='store_true', help='只列出本機 Argon 報告標記的日期')
    x=sub.add_parser('export');x.add_argument('--output',required=True);x.add_argument('--through',help='只匯出到此日期 YYYY-MM-DD，預設台灣時間今天')
    args=p.parse_args()
    if args.cmd in ('dry-run','import'):
        report={}
        for kind,path in [('entries',args.devotional_csv),('media',args.media_csv)]:
            if path:
                report[kind]=rows(path,kind)
                if args.cmd=='import':import_rows(report[kind],kind)
        if not report:raise ValueError('請指定 CSV')
        text=json.dumps(report,ensure_ascii=False,indent=2)
        if args.output_report:Path(args.output_report).write_text(text,encoding='utf-8')
        else: print(text)
    elif args.cmd == 'pending':
        pending(args.from_date, args.to_date, args.flagged)
    elif args.cmd in ('show','today'):
        requested_date=args.date or datetime.datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
        date=parse_iso_date(requested_date)
        if not date or date != requested_date:raise ValueError('日期須為 YYYY-MM-DD')
        result=sql("SELECT COALESCE(jsonb_agg(jsonb_build_object('id',e.id,'date',e.devotional_date,'reference',e.raw_reference,'title',e.title,'source_url',e.source_url,'summary',e.summary,'reflection',e.reflection,'prayer',e.prayer,'source_status',e.source_status,'theology_status',e.theology_status,'ranges',(SELECT jsonb_agg(jsonb_build_object('book',r.book_code,'start_chapter',r.start_chapter,'start_verse',r.start_verse,'end_chapter',r.end_chapter,'end_verse',r.end_verse) ORDER BY r.sequence_no) FROM scripture_ranges r WHERE r.entry_id=e.id)) ORDER BY e.id),'[]'::jsonb) FROM entries e WHERE e.devotional_date="+q(date)+'::date;')
        items=json.loads(result)
        if not items:raise ValueError('當日沒有禱讀資料')
        for item in items:
            passages=[]
            for r in item['ranges'] or []:
                if r['book'] not in ('MAT','MRK','LUK','JHN'):continue
                data=json.loads((Path(__file__).resolve().parent.parent/'data'/f"{r['book'].lower()}.json").read_text(encoding='utf-8'))
                for chapter in data['chapters']:
                    if not r['start_chapter'] <= chapter['ch'] <= r['end_chapter']:continue
                    for verse in chapter['verses']:
                        if chapter['ch']==r['start_chapter'] and r['start_verse'] and verse.get('end',verse['v'])<r['start_verse']:continue
                        if chapter['ch']==r['end_chapter'] and r['end_verse'] and verse['v']>r['end_verse']:continue
                        passages.append({'book':r['book'],'chapter':chapter['ch'],'verse':verse['v'],'end':verse.get('end'),'text':verse['text']})
            item['scripture']=passages
        if args.cmd == 'show':
            print(json.dumps(items,ensure_ascii=False,indent=2))
        else:
            for item in items:
                print(f"\n{item['date']}　{item['title'] or item['reference']}\n{item['reference']}")
                if item['source_status'] != 'APPROVED' or item['theology_status'] != 'APPROVED':
                    print('【待人工與神學審核的草稿】')
                print('\n經文')
                for v in item['scripture']:
                    label=str(v['verse']) + (f"–{v['end']}" if v['end'] else '')
                    print(f"{v['chapter']}:{label} {v['text']}")
                for label,key in [('默想','summary'),('反思','reflection'),('禱告','prayer')]:
                    print(f"\n{label}\n{item[key] or '尚未撰寫'}")
    elif args.cmd=='draft':
        if not args.summary.strip() or not args.reflection.strip():raise ValueError('摘要和反思不可空白')
        updates=['summary='+q(args.summary),'reflection='+q(args.reflection)]
        if args.title is not None:updates.append('title='+q(args.title))
        if args.prayer is not None:updates.append('prayer='+q(args.prayer))
        result=sql('UPDATE entries SET '+','.join(updates)+' WHERE id='+q(args.id)+' RETURNING id;')
        if not result:raise ValueError('找不到紀錄')
    elif args.cmd=='review':
        if not args.reviewer.strip():raise ValueError('審核者不可空白')
        prefix=args.type
        if prefix=='source':
            result=sql("UPDATE entries SET source_status='APPROVED',source_reviewer="+q(args.reviewer)+",source_reviewed_at=now() WHERE id="+q(args.id)+" AND EXISTS(SELECT 1 FROM scripture_ranges r WHERE r.entry_id=entries.id) AND NOT EXISTS(SELECT 1 FROM scripture_ranges r WHERE r.entry_id=entries.id AND r.book_code NOT IN ('MAT','MRK','LUK','JHN')) RETURNING id; ")
        else:result=sql("UPDATE entries SET theology_status='APPROVED',theology_reviewer="+q(args.reviewer)+",theology_reviewed_at=now() WHERE id="+q(args.id)+' RETURNING id;')
        if not result:raise ValueError('找不到紀錄或缺少有效的四福音經文範圍')
    elif args.cmd=='media-link':
        result=sql('UPDATE media_links SET entry_id='+q(args.entry_id)+' WHERE id='+q(args.media_id)+' RETURNING id;')
        if not result:raise ValueError('找不到影音紀錄')
    elif args.cmd=='media-review':
        if not args.reviewer.strip():raise ValueError('審核者不可空白')
        result=sql("UPDATE media_links SET status='VERIFIED', reviewer="+q(args.reviewer)+", reviewed_at=now() WHERE id="+q(args.media_id)+' RETURNING id;')
        if not result:raise ValueError('找不到影音紀錄')
    else:
        # 每日上架：只匯出到指定日期（預設台灣時間今天）為止的已核准內容，未來日期不進公開檔
        through=args.through or datetime.datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
        if parse_iso_date(through) != through:raise ValueError('--through 須為 YYYY-MM-DD')
        data=sql("SELECT COALESCE(jsonb_agg(row_to_json(v) ORDER BY v.devotional_date,v.id),'[]'::jsonb) FROM v_approved_export v WHERE v.devotional_date<="+q(through)+"::date;",True)
        output=Path(args.output);temporary=output.with_suffix('.tmp')
        temporary.write_text(json.dumps(json.loads(data),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        temporary.replace(output)
if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError) as e:print(str(e),file=sys.stderr);sys.exit(1)
