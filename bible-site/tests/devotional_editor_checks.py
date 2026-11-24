"""Independent PM integration: random isolated database; never uses production database."""
import concurrent.futures,copy,datetime,hashlib,importlib.util,json,os,pathlib,subprocess,sys,tempfile,threading,urllib.request,urllib.error,uuid
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'admin'))
DB='bible_admin_editor_check_'+uuid.uuid4().hex[:12]
HOST=os.environ.get('DEVOTIONAL_SSH_HOST','debian-toshiba')
import re
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',HOST):raise SystemExit('Invalid SSH host')
def pg(sql,db='postgres'):
 p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5',HOST,'sudo','-n','-u','postgres','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-p','5433','-d',db],input=sql,text=True,capture_output=True,timeout=20)
 if p.returncode: raise RuntimeError(p.stderr)
 return p.stdout.strip()
results=[]
def check(name,value):
 results.append({'name':name,'pass':bool(value)});print(('PASS ' if value else 'FAIL ')+name,flush=True)
 if not value:raise AssertionError(name)
made=False;httpd=None
try:
 pg('CREATE DATABASE '+DB);made=True
 for name in ('schema.sql','grants.sql','002_policy.sql','003_scripture_bounds.sql','004_title.sql','005_admin_editor.sql'):
  pg((ROOT/'devotional'/name).read_text(),DB)
 os.environ['DEVOTIONAL_DATABASE']=DB;os.environ['DEVOTIONAL_SSH_HOST']=HOST
 import devotional_editor as de
 editor=de.Editor(str(ROOT))
 def content(day='2026-11-16'):
  return dict(date=day,reference='馬太福音 4:23–5:12',title='測試主題',source_url='',summary='測試默想',reflection='測試反思',prayer='測試禱告')
 def save(c=None,**kw):return editor.save(dict(draft_id=None,version=0,entry_id=None,base_version=None,content=c or content(),**kw))
 def error(fn,status):
  try:fn()
  except de.DevotionalEditorError as exc:return exc.status==status
  return False
 p=editor.preview(content()['reference'])
 mat=json.loads((ROOT/'data/mat.json').read_text())
 expected=[v['text'] for ch in mat['chapters'] for v in ch['verses'] if (ch['ch']==4 and v.get('end',v['v'])>=23) or (ch['ch']==5 and v['v']<=12)]
 check('cross-chapter preview equals canonical JSON', [v['text'] for v in p['scripture']]==expected)
 merged=None
 for book in ('mat','mrk','luk','jhn'):
  data=json.loads((ROOT/'data'/f'{book}.json').read_text())
  for ch in data['chapters']:
   for verse in ch['verses']:
    if verse.get('end',verse['v'])>verse['v']:merged=(book,ch['ch'],verse);break
   if merged:break
  if merged:break
 if merged:
  book,ch,v=merged;label={'mat':'馬太福音','mrk':'馬可福音','luk':'路加福音','jhn':'約翰福音'}[book]
  q=editor.preview(f'{label} {ch}:{v["end"]}')['scripture']
  check('merged verse resolves original text',len(q)==1 and q[0]['text']==v['text'] and q[0]['end']==v['end'])
 for ref in ('馬太福音 29:1','馬可福音 1:999','阿摩司書 1:1','馬太福音 1:1；阿摩司書 1:1'):
  check('invalid/mixed range rejected '+ref,error(lambda:editor.preview(ref),400))
 draft=save()['draft']
 check('new draft does not create public entry',pg('SELECT count(*) FROM entries',DB)=='0')
 check('explicit human confirmations required',error(lambda:editor.approve(dict(draft_id=draft['id'],version=1,reviewer='PM fixture',source_confirmed='true',theology_confirmed=True)),400))
 def approve(d):return editor.approve(dict(draft_id=d['id'],version=d['version'],reviewer='PM fixture',source_confirmed=True,theology_confirmed=True))
 applied=approve(draft)['entry'];entry_id=applied['id']
 check('approval sets both reviews',applied['source_status']==applied['theology_status']=='APPROVED')
 check('approval audited',pg("SELECT count(*) FROM review_audit_logs WHERE new_status='APPROVED'",DB)=='2')
 before=pg('SELECT row_to_json(e) FROM entries e WHERE id='+str(entry_id),DB)
 c=content();c['title']="文字 ' \\ ";c['summary']='修訂本文'
 revision=editor.save(dict(draft_id=None,version=0,entry_id=entry_id,base_version=applied['version'],content=c))['draft']
 check('saving revision preserves whole original row',pg('SELECT row_to_json(e) FROM entries e WHERE id='+str(entry_id),DB)==before)
 check('public export retains original during review',pg('SELECT count(*) FROM v_approved_export',DB)=='1')
 check('stale draft update rejected',error(lambda:editor.save(dict(draft_id=revision['id'],version=0,entry_id=entry_id,base_version=applied['version'],content=c)),409))
 pg("UPDATE entries SET title='concurrent writer' WHERE id="+str(entry_id),DB)
 check('stale base approval rejected atomically',error(lambda:approve(revision),409))
 check('failed approval preserves draft',editor.get_draft(revision['id'])['draft']['status']=='DRAFT')
 # Concurrent creation must not produce 2 active drafts on one day.
 def attempt(_):
  try: save(content('2026-11-20'));return 200
  except de.DevotionalEditorError as e:return e.status
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: codes=list(pool.map(attempt,range(2)))
 check('concurrent same-date drafts: exactly one success',sorted(codes)==[200,409])
 check('unique-date index enforced',pg("SELECT count(*) FROM admin_devotional_drafts WHERE payload->'content'->>'date'='2026-11-20'",DB)=='1')
 # Resolve the intentional concurrent edit before testing publication eligibility.
 latest=editor.get_entry(entry_id)['entry']
 rebased=editor.save(dict(draft_id=revision['id'],version=revision['version'],entry_id=entry_id,base_version=latest['version'],content=c))['draft']
 check('explicit rebase then review applies retained draft',approve(rebased)['entry']['content']['summary']==c['summary'])
 # Exercise the real exporter against this isolated DB: future approvals stay private.
 future=save(content('2026-11-17'))['draft'];approve(future)
 with tempfile.TemporaryDirectory() as export_dir:
  exported=pathlib.Path(export_dir)/'devotional.json'
  def export(through):
   run=subprocess.run([sys.executable,'-B',str(ROOT/'devotional/cli.py'),'export','--output',str(exported),'--through',through],capture_output=True,text=True,timeout=20)
   if run.returncode:raise RuntimeError('Isolated export failed')
   return json.loads(exported.read_text())
  today_export=export('2026-11-16')
  check('real export excludes future approval and unapproved draft',len(today_export)==1 and today_export[0]['devotional_date']=='2026-11-16')
  next_export=export('2026-11-17')
  check('real export releases future only on corresponding date',sorted(x['devotional_date'] for x in next_export)==['2026-11-16','2026-11-17'])
 # Real HTTP adapter + real isolated DB. Mock only operations to ensure no real publishing/settings writes.
 with tempfile.TemporaryDirectory() as td:
  os.environ['BIBLE_SITE_ROOT']=str(ROOT);os.environ['BIBLE_ADMIN_TOKEN_FILE']=td+'/token'
  spec=importlib.util.spec_from_file_location('pm_editor_server',ROOT/'admin/server.py');srv=importlib.util.module_from_spec(spec);spec.loader.exec_module(srv)
  import devotional_operations as ops
  calls=[]
  ops.save_settings=lambda payload: calls.append(('settings',payload)) or {'saved':True}
  ops.publish_now=lambda payload: calls.append(('publish',payload)) or {'ok':True,'outcome':'service_completed'}
  srv.init_token();httpd=srv.ThreadingHTTPServer(('127.0.0.1',0),srv.AdminRequestHandler)
  threading.Thread(target=httpd.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(httpd.server_port)
  def req(path,body=None,token=True,origin=None):
   headers={'X-Bible-Admin':'1','Content-Type':'application/json','Origin':origin or base}
   if token:headers['X-Bible-Token']=srv.ADMIN_TOKEN
   r=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
   try:
    with urllib.request.urlopen(r,timeout=20) as response:return response.status,response.read()
   except urllib.error.HTTPError as exc:return exc.code,exc.read()
  check('HTTP private GET requires token',req('/api/devotional-editor/list?from=2026-11-01&through=2026-11-30',token=False)[0]==403)
  check('HTTP cross-origin POST blocked',req('/api/devotional-editor/publish',{'confirm':True},origin='https://evil.invalid')[0]==403 and calls==[])
  check('HTTP POST without token blocked',req('/api/devotional-editor/settings',{},token=False)[0]==403 and calls==[])
  check('HTTP authenticated real DB list',req('/api/devotional-editor/list?from=2026-11-01&through=2026-11-30')[0]==200)
  check('HTTP oversized JSON blocked',req('/api/devotional-editor/save',{'x':'x'*70000})[0]==413)
  for path in ('/devotional_editor.py','/devotional_operations.py','/005_admin_editor.sql','/.token'):
   check('private file not served '+path,req(path)[0]==404)
  check('standalone editor JS served',req('/devotional_editor.js')[0]==200)
  check('settings adapter calls fixed function',req('/api/devotional-editor/settings',{'fixture':True})[0]==200 and calls[-1][0]=='settings')
  check('publish adapter calls fixed function',req('/api/devotional-editor/publish',{'confirm':True,'schedule_version':'fixture'})[0]==200 and calls[-1][0]=='publish')
finally:
 if httpd:httpd.shutdown();httpd.server_close()
 if made:pg('DROP DATABASE '+DB)
 pathlib.Path(tempfile.gettempdir(),DB+'-results.json').write_text(json.dumps({'database':DB,'results':results},ensure_ascii=False,indent=2))
print(f'{len(results)}/{len(results)} passed')
