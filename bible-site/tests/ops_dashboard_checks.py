#!/usr/bin/env python3
"""Independent, offline regression for agent routing, progress and devotional status.
Run: python3 -B bible-site/tests/ops_dashboard_checks.py
All writes use TemporaryDirectory; Herdr, systemd and public HTTP are mocked.
"""
import contextlib
import datetime as dt
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

route = load('ops_test_routes', ROOT / 'tools/herdr_team.py')
progress = load('ops_test_progress', ROOT / 'tools/pm_status.py')
status = load('devotional_status', ROOT / 'admin/devotional_status.py')
server = load('ops_test_server', ROOT / 'admin/server.py')
_systemctl_show_real = status._systemctl_show
_http_get_real = status._http_get

class Offline(unittest.TestCase):
    def setUp(self):
        for target in ['subprocess.run', 'urllib.request.OpenerDirector.open']:
            p = patch(target, side_effect=AssertionError('external operation forbidden in tests'))
            p.start()
            self.addCleanup(p.stop)

class Routes(Offline):
    def test_current_roles_and_opaque_ids(self):
        for alias, expected in {'backend':'w2:p2','PM':'w2:p2','fe':'w2:p5','qa':'w2:pC',
                                'assistant':'w2:pD','codex':'w2:p1','w2:pC':'w2:pC','pD':'w2:pD'}.items():
            with self.subTest(alias=alias), patch.dict(os.environ, {'HERDR_DEFAULT_WORKSPACE':'w2'}):
                self.assertEqual(route.resolve(alias), expected)

    def test_rejected_targets_never_dispatch(self):
        for entry in [None, {'pane_id':'w2:pC','agent':'','agent_status':'unknown'},
                      {'pane_id':'w2:pC','agent':'kilo','agent_status':'unknown'},
                      {'pane_id':'w2:pC','agent':'kilo','agent_status':'blocked'}]:
            with self.subTest(entry=entry), patch.object(route,'pane_list',return_value=[] if entry is None else [entry]), \
                 patch.object(route,'agent_get',return_value={}), patch.object(route,'pane_read',return_value=''), \
                 patch.object(route,'send_prompt') as send, patch.object(route,'snapshot') as snapshot:
                result, ok = route.attempt({'pane':'w2:pC','path':'test-task.md'})
                self.assertFalse(ok)
                self.assertNotEqual(result['verdict'],'通過')
                send.assert_not_called()
                snapshot.assert_not_called()

    def test_agent_not_found_is_rejected(self):
        entry={'pane_id':'w2:pC','agent':'qa','agent_status':'idle'}
        with patch.object(route,'pane_list',return_value=[entry]), patch.object(route,'agent_get',return_value={}):
            _, reason=route.require_dispatchable('w2:pC')
            self.assertIn('agent_not_found',reason)

    def test_working_then_unknown_is_not_done(self):
        with patch.object(route,'agent_get',return_value={'state_change_seq':1}), \
             patch.object(route,'wait_for',side_effect=[('working',2),('unknown',3)]):
            self.assertEqual(route.settle('w2:pC',0.1),'unknown')

    def test_unknown_completion_never_runs_checks_or_passes(self):
        entry={'pane_id':'w2:pC','agent':'qa','agent_status':'idle'}
        task={'pane':'w2:pC','path':'fixture.md','id':'fixture','role':'qa','files':[],
              'timeout_min':1,'checks':[]}
        with patch.object(route,'require_dispatchable',return_value=(entry,None)), \
             patch.object(route,'snapshot',return_value={}), \
             patch.object(route,'send_prompt',return_value=('accepted','')), \
             patch.object(route,'settle',return_value='unknown'), \
             patch.object(route,'pane_read',return_value=''), \
             patch.object(route,'run_checks') as checks, contextlib.redirect_stdout(io.StringIO()):
            result,ok=route.attempt(task)
            self.assertFalse(ok)
            self.assertEqual(result['verdict'],'無法確認完成')
            checks.assert_not_called()

    def test_recognized_idle_agent_accepts_explicit_prompt(self):
        entry={'pane_id':'w2:pC','agent':'qa','agent_status':'idle'}
        with patch.object(route,'pane_list',return_value=[entry]), \
             patch.object(route,'agent_get',return_value=entry), \
             patch.object(route,'send_prompt',return_value=('accepted','')) as send, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(route.cmd_prompt('qa','fixture',False,1,10),0)
            send.assert_called_once_with('w2:pC','fixture',wait_ms=None)

class Progress(Offline):
    def fixture(self, root):
        shutil.copytree(ROOT/'data',root/'data')
        (root/'site').mkdir()
        for f in progress.SITE_FILES:
            (root/'site'/f).write_text('fixture',encoding='utf-8')
        for name in ['REVIEW.md','CHANGELOG.md']:
            (root/name).write_text('nonempty',encoding='utf-8')
        (root/'FAILS.md').write_text('全部通過',encoding='utf-8')
        (root/'PROGRESS.md').write_text('before-sentinel\n<!-- pm:auto:start -->\nold\n<!-- pm:auto:end -->\nafter-sentinel',encoding='utf-8')

    def run_case(self, case):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.fixture(root)
            if case=='missing':(root/'data/mrk.json').unlink()
            if case=='broken':(root/'data/mrk.json').write_text('{invalid',encoding='utf-8')
            if case in ['null_verse','short','wrong_type']:
                p=root/'data/mrk.json';obj=json.loads(p.read_text())
                if case=='null_verse':obj['chapters'][0]['verses'][0]=None
                elif case=='short':obj['chapters'][0]['verses'].pop()
                else:obj=[]
                p.write_text(json.dumps(obj),encoding='utf-8')
            if case=='missing_page':(root/'site/devotional.html').unlink()
            if case=='cached_failure':(root/'FAILS.md').write_text('不通過',encoding='utf-8')
            with patch.object(progress,'ROOT',str(root)),patch.object(sys,'argv',['pm_status.py','--no-checks']), \
                 patch.object(progress,'last_check_all',side_effect=AssertionError('must not run checks')),contextlib.redirect_stdout(io.StringIO()):
                code=progress.main()
            text=(root/'PROGRESS.md').read_text()
            self.assertTrue(text.startswith('before-sentinel\n'))
            self.assertTrue(text.endswith('\nafter-sentinel'))
            self.assertIn('3776',text)
            if case in ['missing','broken','null_verse','short','wrong_type']:
                self.assertIn('四福音JSON驗證：驗證失敗',text)
            return code,text

    def test_valid_current_site(self):
        code,text=self.run_case('valid');self.assertEqual(code,0);self.assertNotIn('mark.json',text)

    def test_invalid_data_and_missing_site_are_not_complete(self):
        for case in ['missing','broken','null_verse','short','wrong_type','missing_page','cached_failure']:
            with self.subTest(case=case):
                code,_=self.run_case(case);self.assertNotEqual(code,0)

class Status(Offline):
    def setUp(self):
        super().setUp()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'data').mkdir()
        self.local=[{'devotional_date':'2026-11-13'}]
        self.public=self.local+[{'devotional_date':'2026-11-14'}]
        self.write_local(self.local)
        self.timer={'ActiveState':'active','UnitFileState':'enabled','NextElapseUSecRealtime':'Sun 2026-11-15 06:00:00 CST',
                    'TimersCalendar':'{ OnCalendar=2026-11-14..25 06:00:00 Asia/Taipei ; next_elapse=n/a }'}
        self.service={'Result':'success','ExecMainStatus':'0','ExecMainStartTimestamp':'Sat 2026-11-14 06:00:20 CST',
                      'ExecMainExitTimestamp':'Sat 2026-11-14 06:00:21 CST'}
        http_patch=patch.object(status,'_http_get',return_value=json.dumps(self.public).encode())
        self.http=http_patch.start();self.addCleanup(http_patch.stop)
        show_patch=patch.object(status,'_systemctl_show',side_effect=self.mock_show)
        self.show=show_patch.start();self.addCleanup(show_patch.stop)

    def mock_show(self,unit,props):
        self.assertIn(unit,[status.TIMER_UNIT,status.SERVICE_UNIT])
        return (dict(self.timer) if unit==status.TIMER_UNIT else dict(self.service)),None

    def write_local(self,value):
        (self.root/'data/devotional.json').write_text(json.dumps(value),encoding='utf-8')

    def collect(self,now=None):
        return status.collect_status(str(self.root),now=now or dt.datetime(2026,11,14,8,tzinfo=dt.timezone.utc))

    def test_sources_separate_and_input_unchanged(self):
        p=self.root/'data/devotional.json';before=p.read_bytes();d=self.collect()
        self.assertEqual((d['public']['count'],d['local']['count']),(2,1))
        self.assertEqual(d['release_state'],'scheduled');self.assertEqual(p.read_bytes(),before)
        self.assertNotIn('summary',json.dumps(d));self.assertEqual(d['timezone'],'Asia/Taipei')

    def test_empty_is_valid(self):
        self.http.return_value=b'[]';self.write_local([]);d=self.collect()
        self.assertEqual(d['public']['state'],'ok');self.assertEqual(d['public']['count'],0)
        self.assertIsNone(d['public']['latest_date'])

    def test_payload_size_boundary(self):
        self.http.return_value=b'[]'+b' '*(status.MAX_BYTES-2)
        self.assertEqual(self.collect()['public']['state'],'ok')
        self.http.return_value+=b' '
        result=self.collect()['public']
        self.assertEqual(result['state'],'invalid')
        self.assertIsNone(result['count'])

    def test_malformed_public_is_invalid_not_zero(self):
        values=[b'broken',b'{}',b'null',b'[null]',b'[{"devotional_date":"2026-02-30"}]',
                b'[{"devotional_date":"20261114"}]',json.dumps(self.public+self.public).encode(),b' '*(status.MAX_BYTES+1)]
        for raw in values:
            with self.subTest(raw_length=len(raw)):
                self.http.return_value=raw;d=self.collect()
                self.assertEqual(d['public']['state'],'invalid');self.assertIsNone(d['public']['count'])
                self.assertEqual(d['local']['count'],1)

    def test_http_failure_keeps_schedule_and_hides_raw_error(self):
        for exc in [TimeoutError('SECRET-TOKEN'),urllib.error.URLError('SECRET-TOKEN'),
                    urllib.error.HTTPError(status.PUBLIC_URL,403,'SECRET-TOKEN',{},None)]:
            with self.subTest(error=type(exc).__name__):
                self.http.side_effect=exc;d=self.collect()
                self.assertEqual(d['public']['state'],'unavailable');self.assertEqual(d['schedule']['state'],'ok')
                self.assertEqual(d['release_state'],'unknown');self.assertNotIn('SECRET-TOKEN',json.dumps(d))

    def test_local_invalid_or_missing(self):
        self.write_local({});self.assertEqual(self.collect()['local']['state'],'invalid')
        (self.root/'data/devotional.json').unlink();self.assertEqual(self.collect()['local']['state'],'unavailable')

    def test_no_systemd_is_unknown_not_failed(self):
        self.show.side_effect=None;self.show.return_value=(None,'查詢失敗');d=self.collect()
        self.assertEqual(d['schedule']['state'],'unavailable');self.assertEqual(d['last_run']['state'],'unknown')

    def test_last_run_failed_never_and_invalid_status(self):
        self.service['Result']='exit-code';self.service['ExecMainStatus']='1'
        self.assertEqual(self.collect()['release_state'],'attention')
        self.service['ExecMainStartTimestamp']='';self.assertEqual(self.collect()['last_run']['state'],'never')
        self.service.update(Result='success',ExecMainStatus='not-an-int',ExecMainStartTimestamp='nonempty')
        self.assertEqual(self.collect()['last_run']['state'],'unknown')

    def test_taipei_cutoff_boundary(self):
        before=self.collect(dt.datetime(2026,11,25,15,59,59,tzinfo=dt.timezone.utc))
        after=self.collect(dt.datetime(2026,11,25,16,0,tzinfo=dt.timezone.utc))
        self.assertFalse(before['schedule']['expired']);self.assertTrue(after['schedule']['expired'])
        self.assertEqual(after['release_state'],'cutoff')

    def test_cutoff_changes_with_loaded_calendar(self):
        self.timer['TimersCalendar']='{ OnCalendar=2026-12-01..20 06:00:00 Asia/Taipei ; next_elapse=n/a }'
        self.assertEqual(self.collect()['schedule']['cutoff_date'],'2026-12-20')
        for text in ['{ OnCalendar=2026-11-14,20 06:00:00 Asia/Taipei }',
                     '{ OnCalendar=*-*-* 06:00:00 Asia/Taipei }',
                     '{ OnCalendar=2026-11-14..25 06:00:00 Asia/Taipei } { OnCalendar=*-*-* 06:00:00 Asia/Taipei }']:
            self.timer['TimersCalendar']=text
            with self.subTest(calendar=text):self.assertIsNone(self.collect()['schedule']['cutoff_date'])

    def test_finite_month_rules_have_the_latest_cutoff(self):
        november='{ OnCalendar=2026-11-16..30 06:00:00 Asia/Taipei ; next_elapse=n/a }'
        december='{ OnCalendar=2026-12-01..16 06:00:00 Asia/Taipei ; next_elapse=n/a }'
        for calendar in [november+' '+december,december+' '+november]:
            with self.subTest(calendar=calendar):
                self.timer['TimersCalendar']=calendar
                self.assertEqual(self.collect()['schedule']['cutoff_date'],'2026-12-16')
        self.timer['TimersCalendar']=november+' '+december+' { OnCalendar=*-*-* 06:00:00 Asia/Taipei }'
        self.assertIsNone(self.collect()['schedule']['cutoff_date'])

    def test_cross_month_taipei_cutoff_boundary(self):
        self.timer['TimersCalendar']=('{ OnCalendar=2026-11-16..30 06:00:00 Asia/Taipei } '
                                      '{ OnCalendar=2026-12-01..16 06:00:00 Asia/Taipei }')
        before=self.collect(dt.datetime(2026,12,16,15,59,59,tzinfo=dt.timezone.utc))
        after=self.collect(dt.datetime(2026,12,16,16,0,tzinfo=dt.timezone.utc))
        self.assertIs(before['schedule']['expired'],False)
        self.assertIs(after['schedule']['expired'],True)
        self.assertEqual(after['release_state'],'cutoff')

    def test_systemctl_preserves_multiple_calendar_property_lines(self):
        raw=('ActiveState=active\nUnitFileState=enabled\n'
             'NextElapseUSecRealtime=Tue 2026-11-17 06:00:00 CST\n'
             'TimersCalendar={ OnCalendar=2026-12-01..16 06:00:00 Asia/Taipei }\n'
             'TimersCalendar={ OnCalendar=2026-11-16..30 06:00:00 Asia/Taipei }\n')
        with patch.object(status,'_run_bounded',return_value=(raw,None)):
            values,error=_systemctl_show_real(status.TIMER_UNIT,status.TIMER_PROPS)
        self.assertIsNone(error)
        self.assertEqual(values['TimersCalendar'].count('OnCalendar='),2)
        schedule=status._collect_schedule(values,None,dt.datetime(2026,11,16,tzinfo=status.TAIPEI))
        self.assertEqual(schedule['cutoff_date'],'2026-12-16')

    def test_systemctl_commands_timeout_and_oversize(self):
        with patch.object(status.shutil,'which',return_value='/usr/bin/systemctl'), \
             patch.object(status.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'x'*(status.MAX_OUTPUT+1),b'')) as run:
            self.assertIsNone(_systemctl_show_real(status.TIMER_UNIT,status.TIMER_PROPS)[0])
            kwargs=run.call_args.kwargs;self.assertLessEqual(kwargs['timeout'],2)
            self.assertNotIn('shell',kwargs);self.assertEqual(kwargs['env']['LC_ALL'],'C')
            self.assertEqual(run.call_args.args[0][:4],['systemctl','--user','show',status.TIMER_UNIT])
        with patch.object(status.shutil,'which',return_value='/usr/bin/systemctl'), \
             patch.object(status.subprocess,'run',side_effect=subprocess.TimeoutExpired('systemctl',2)):
            self.assertIsNone(_systemctl_show_real(status.TIMER_UNIT,status.TIMER_PROPS)[0])

    def test_http_fixed_source_timeout_and_read_limit(self):
        with patch.object(status.urllib.request,'build_opener') as factory:
            response=factory.return_value.open.return_value.__enter__.return_value
            response.geturl.return_value=status.PUBLIC_URL
            response.read.return_value=b'[]'
            self.assertEqual(_http_get_real(status.PUBLIC_URL,status.HTTP_TIMEOUT),b'[]')
            response.read.assert_called_once_with(status.MAX_BYTES+1)
            call=factory.return_value.open.call_args
            self.assertEqual(call.args[0].full_url,status.PUBLIC_URL)
            self.assertLessEqual(call.kwargs['timeout'],3)

    def test_redirects_are_rejected(self):
        self.assertIsNone(status._NoRedirect().redirect_request(None,None,302,'',{},'http://attacker.invalid/'))

    def test_api_integration_read_only_and_static_privacy(self):
        with patch.object(server,'SITE_ROOT',str(self.root)),patch.object(server.AdminRequestHandler,'log_message',lambda *a:None):
            httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.AdminRequestHandler)
            thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
            def request(path,method='GET'):
                conn=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=5)
                try:
                    conn.request(method,path);response=conn.getresponse();return response.status,response.read()
                finally:conn.close()
            try:
                before=(self.root/'data/devotional.json').read_bytes()
                code,body=request('/api/devotional-status');self.assertEqual(code,200)
                self.assertEqual(json.loads(body)['public']['count'],2)
                for path in ['/devotional_status.py','/admin/devotional_status.py']:
                    self.assertEqual(request(path)[0],404)
                self.assertEqual(request('/api/devotional-status','POST')[0],403)
                with patch.object(status,'collect_status',side_effect=RuntimeError('SECRET-TOKEN')):
                    code,body=request('/api/devotional-status')
                    self.assertEqual(code,200);self.assertEqual(json.loads(body)['release_state'],'unknown')
                    self.assertNotIn(b'SECRET-TOKEN',body)
                self.assertEqual((self.root/'data/devotional.json').read_bytes(),before)
            finally:httpd.shutdown();httpd.server_close();thread.join(timeout=2)

if __name__=='__main__':unittest.main(verbosity=2)
