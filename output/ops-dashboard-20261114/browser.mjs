import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
const [base, fixture, out] = process.argv.slice(2);
fs.mkdirSync(out,{recursive:true});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const results=[]; const errors=[];
function check(name,ok,detail=''){results.push({name,ok:!!ok,detail});console.log(`${ok?'PASS':'FAIL'} ${name}${!ok?' '+detail:''}`);}
const profile=path.join(out,'profile');
const chrome=spawn('/usr/bin/google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--hide-scrollbars','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore'});
let ws;let cdp;
try {
 const active=path.join(profile,'DevToolsActivePort');
 for(let n=0;!fs.existsSync(active)&&n<100;n++) await delay(100);
 const port=Number(fs.readFileSync(active,'utf8').split('\n')[0]);
 const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 ws=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);
 await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 let id=0;const pending=new Map();
 cdp=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>{pending.delete(n);reject(Error('CDP timeout '+method))},15000);pending.set(n,{resolve,reject,timer});ws.send(JSON.stringify({id:n,method,params}));});
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown'){errors.push(m.params.exceptionDetails.text);}else if(m.method==='Page.javascriptDialogOpening'){cdp('Page.handleJavaScriptDialog',{accept:true}).catch(()=>{});}};
 const ev=async expression=>{const r=await cdp('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result?.value;};
 const until=async(expr,name)=>{for(let i=0;i<100;i++){if(await ev(expr))return;await delay(100);}throw Error('wait '+name);};
 const value=(day,field)=>ev(`document.getElementById('week-d${day}-${field}').value`);
 const set=(day,field,val,event='input')=>ev(`(()=>{const e=document.getElementById('week-d${day}-${field}');e.value=${JSON.stringify(val)};e.dispatchEvent(new Event('${event}',{bubbles:true}));})()`);
 const get=async()=>await (await fetch(base+'/api/home-week')).json();
 const raw=cfg=>JSON.stringify({enabled:cfg.enabled,days:cfg.days});
 const click=selector=>ev(`document.querySelector(${JSON.stringify(selector)}).click()`);
 const dirty=()=>ev(`(()=>{let e=new Event('beforeunload',{cancelable:true});window.dispatchEvent(e);return e.defaultPrevented;})()`);
 async function shot(name,width,selector='#home-week-settings'){
  await cdp('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
  await ev(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'start',behavior:'instant'})`);await delay(200);
  const s=await cdp('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(s.data,'base64'));
 }
 await cdp('Page.enable');await cdp('Runtime.enable');
 await cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'light'},{name:'prefers-reduced-motion',value:'reduce'}]});

 const baseline=JSON.parse(fs.readFileSync(new URL('./fixture.json', import.meta.url)));
 await cdp('Page.addScriptToEvaluateOnNewDocument',{source:`window.__devoFixture=${JSON.stringify(baseline)};window.__devoMode='normal';window.__devoCount=0;window.__devoMethods=[];{const real=window.fetch.bind(window);window.fetch=(u,o)=>{if(String(u).startsWith('/api/devotional-status')){window.__devoCount++;window.__devoMethods.push(o?.method||'GET');if(window.__devoMode==='http')return Promise.resolve(new Response('failure',{status:500}));if(window.__devoMode==='invalid')return Promise.resolve(new Response('invalid-json',{status:200}));if(window.__devoMode==='hold')return new Promise((r,j)=>{window.__devoRelease=()=>r(new Response(JSON.stringify(window.__devoFixture)));o?.signal?.addEventListener('abort',()=>j(new DOMException('Aborted','AbortError')));});return Promise.resolve(new Response(JSON.stringify(window.__devoFixture),{headers:{'Content-Type':'application/json'}}));}return real(u,o);};}`});
 await cdp('Page.navigate',{url:base+'/'});
 await until(`document.querySelector('#dev-status-release')?.textContent==='已排程'`,'ready');
 const val=async id=>await ev(`document.getElementById(${JSON.stringify(id)}).textContent`);
 const refresh=async(data=baseline,mode='normal')=>{await ev(`window.__devoFixture=${JSON.stringify(data)};window.__devoMode=${JSON.stringify(mode)};document.querySelector('#devotional-status-refresh').click()`);await until(`!document.querySelector('#devotional-status-refresh').disabled && document.querySelector('#devotional-status').getAttribute('aria-busy')==='false'`,'refresh');};
 const clone=()=>structuredClone(baseline);
 check('Public and local distinct',await val('dev-status-public-count')==='317 篇'&&await val('dev-status-local-count')==='23 篇');
 check('Dynamic cutoff, no hard-coded Nov25',await val('dev-status-schedule-cutoff')==='2026-12-02');
 check('Successful service and Taiwan observation',await val('dev-status-last-state')==='成功'&&(await val('devotional-status-observed')).includes('Asia/Taipei'));
 for(const w of [320,375,768,1440]){await cdp('Emulation.setDeviceMetricsOverride',{width:w,height:1000,deviceScaleFactor:1,mobile:false});await delay(120);check(w+' no overflow',await ev(`document.documentElement.scrollWidth<=innerWidth && document.querySelector('#devotional-status').scrollWidth<=document.querySelector('#devotional-status').clientWidth+1`));if([375,1440].includes(w)){await ev(`document.querySelector('#devotional-status').scrollIntoView({block:'start'})`);const s=await cdp('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,'dashboard-'+w+'.png'),Buffer.from(s.data,'base64'));}}
 let f=clone();f.public={...f.public,state:'unavailable',count:null,latest_date:null,error:'正式站暫時無法讀取'};f.release_state='unknown';await refresh(f);
 check('Partial failure keeps local source',await val('dev-status-public-count')==='未知'&&await val('dev-status-local-count')==='23 篇');
 f=clone();f.public={...f.public,count:0,latest_date:null};await refresh(f);check('Empty data differs from unknown',await val('dev-status-public-count')==='0 篇'&&await val('dev-status-public-latest')==='尚無資料');
 f=clone();f.schedule={state:'unavailable',enabled:null,active:null,next_run:null,cutoff_date:null,expired:null,calendar:null,error:'無法取得排程'};f.release_state='unknown';await refresh(f);check('Missing systemd stays unknown',await val('dev-status-schedule-cutoff')==='未知'&&await val('dev-status-schedule-enabled')==='未知');
 f=clone();f.last_run={...f.last_run,state:'failed',exit_code:1,error:'上次執行失敗'};f.release_state='attention';await refresh(f);check('Failed release visible',await val('dev-status-last-state')==='失敗'&&await val('dev-status-release')==='需要留意');
 f=clone();f.release_state='cutoff';f.schedule.expired=true;f.schedule.next_run=null;await refresh(f);check('Cutoff is normal stop',await val('dev-status-release')==='已依設定截止'&&(await val('dev-status-schedule-next')).includes('已截止'));
 f=clone();f.warnings=['<img src=x onerror="window.__xss=1">'];await refresh(f);check('Warning is text, no XSS',await ev(`!document.querySelector('#dev-status-warning-list img')&&!window.__xss&&document.querySelector('#dev-status-warning-list').textContent.includes('<img')`));
 await refresh(baseline,'http');check('HTTP failure clears stale success',await val('dev-status-release')==='資料未更新'&&await val('dev-status-public-count')==='未知');
 await refresh(baseline,'invalid');check('Invalid JSON clears stale success',await val('dev-status-release')==='資料未更新'&&await val('dev-status-last-state')==='未知');
 await refresh();const n=await ev('window.__devoCount');await ev(`window.__devoMode='hold';document.querySelector('#devotional-status-refresh').click();document.querySelector('#devotional-status-refresh').click()`);
 check('Busy locks duplicate refresh',await ev(`document.querySelector('#devotional-status-refresh').disabled&&window.__devoCount===${n+1}&&document.querySelector('#devotional-status').getAttribute('aria-busy')==='true'`));
 await ev('window.__devoRelease()');await until(`!document.querySelector('#devotional-status-refresh').disabled`,'release held request');
 await ev(`window.__devoMode='hold';document.querySelector('#devotional-status-refresh').click()`);await delay(12300);await until(`!document.querySelector('#devotional-status-refresh').disabled`,'abort');
 check('Timeout removes success and unlocks retry',await val('dev-status-release')==='資料未更新'&&(await val('devotional-status-observed')).includes('逾時'));
 await refresh();check('Recovery succeeds',await val('dev-status-public-count')==='317 篇'&&await val('dev-status-release')==='已排程');
 check('Read-only GET only',await ev(`window.__devoMethods.every(x=>x==='GET')`));
 check('Accessible live feedback',await ev(`document.querySelector('#devotional-status-live').getAttribute('role')==='status'&&document.querySelector('#devotional-status-live').getAttribute('aria-live')==='polite'`));

 const contrastExpr=`(()=>{const parse=s=>{const a=(s.match(/[0-9.]+/g)||[]).map(Number);return[a[0]||0,a[1]||0,a[2]||0,a.length>3?a[3]:1];};const over=(a,b)=>a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3])).concat(1);const lum=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4);}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);let fails=[],n=0,min=99;for(const e of document.querySelectorAll('#devotional-status *')){if(!e.getClientRects().length||getComputedStyle(e).visibility==='hidden'||![...e.childNodes].some(x=>x.nodeType===3&&x.textContent.trim()))continue;let chain=[],p=e;while(p){chain.push(p);p=p.parentElement;}let bg=[255,255,255,1];for(const q of chain.reverse())bg=over(parse(getComputedStyle(q).backgroundColor),bg);const fg=over(parse(getComputedStyle(e).color),bg);let a=lum(fg),b=lum(bg),r=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);n++;min=Math.min(min,r);if(r<4.5)fails.push({id:e.id,text:e.textContent.trim().slice(0,40),ratio:r,color:getComputedStyle(e).color,bg});}return{n,min,fails};})()`;
 for(const scheme of ['light','dark']){
  await cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:scheme},{name:'prefers-reduced-motion',value:'reduce'}]});
  for(const mode of ['normal','warning','error','cutoff']){
   const d=clone();if(mode==='warning'){d.release_state='attention';d.warnings=['請核對上架狀態'];d.public.state='unavailable';d.public.error='連線失敗';d.public.count=null;}
   if(mode==='error'){d.release_state='attention';d.last_run.state='failed';d.last_run.error='執行失敗';d.local.state='invalid';}
   if(mode==='cutoff'){d.release_state='cutoff';d.schedule.expired=true;d.schedule.next_run=null;}
   await refresh(d);await delay(80);const result=await ev(contrastExpr);check(scheme+' '+mode+' text contrast >=4.5',result.n>10&&result.fails.length===0,JSON.stringify(result));
  }
 }
 await cdp('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'light'},{name:'prefers-reduced-motion',value:'reduce'}]});await refresh();
 check('No JS exceptions',errors.length===0,JSON.stringify(errors));
} catch(e){check('test execution',false,e.stack||String(e));}
finally{if(ws)ws.close();chrome.kill('SIGTERM');await delay(300);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));}
console.log('TOTAL',results.filter(r=>r.ok).length,'/',results.length);process.exitCode=results.every(r=>r.ok)?0:1;
