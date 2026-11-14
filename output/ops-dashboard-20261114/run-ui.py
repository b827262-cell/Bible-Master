from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copytree
from PIL import Image
import socket,subprocess,os,sys,json,time,urllib.request,hashlib
repo=Path(__file__).resolve().parents[2];out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
with TemporaryDirectory(prefix='weekly-editor-ui-') as td:
 root=Path(td)/'bible-site';root.mkdir();copytree(repo/'bible-site/admin',root/'admin');copytree(repo/'bible-site/data',root/'data');copytree(repo/'bible-site/site/assets',root/'site/assets')
 cfg=root/'data/home-week.json';data=json.loads(cfg.read_text());data['days'][6].pop('focus',None);cfg.write_text(json.dumps(data,ensure_ascii=False))
 Image.new('RGB',(32,18),'#fdf2da').save(root/'small.png')
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 env=dict(os.environ,BIBLE_SITE_ROOT=str(root),BIBLE_ADMIN_TOKEN_FILE=str(root/'token'))
 proc=subprocess.Popen([sys.executable,str(root/'admin/server.py'),'--port',str(port),'--host','127.0.0.1'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  base=f'http://127.0.0.1:{port}'
  for i in range(50):
   try:urllib.request.urlopen(base+'/api/ping',timeout=1).read();break
   except Exception:time.sleep(.1)
  files=['server.py','index.html','admin.css','admin.js'];(out/'source-hashes.json').write_text(json.dumps({f:hashlib.sha256((root/'admin'/f).read_bytes()).hexdigest() for f in files},indent=2))
  p=subprocess.run(['node',str(Path(__file__).resolve().parent/'browser.mjs'),base,str(root),str(out)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=100);print(p.stdout,flush=True);print('EXIT',p.returncode)
 finally:
  proc.terminate();proc.wait(timeout=5)
