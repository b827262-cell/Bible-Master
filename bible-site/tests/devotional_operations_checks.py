#!/usr/bin/env python3
"""Isolated operations checks: temp files, fake clock, no real systemctl/Git/DB."""
import copy
import datetime as dt
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('devotional_operations', Path(__file__).resolve().parents[1] / 'admin/devotional_operations.py')
ops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ops)


def condition(program):
    return ('{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 -c ' + program +
            ' ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; '
            'pid=0 ; code=(null) ; status=0/0 }')


class Systemd:
    def __init__(self, config):
        self.config = config
        self.calls = []
        self.fail = []
        self.publish = 'success'
        self.entered = None
        self.release = None
        self.timer = {'ActiveState': 'active', 'UnitFileState': 'enabled',
                      'TimersCalendar': '{ OnCalendar=2026-11-16..30 06:00:00 Asia/Taipei ; next_elapse=n/a }\n'
                                        '{ OnCalendar=2026-12-01..16 06:00:00 Asia/Taipei ; next_elapse=n/a }'}
        self.service = {'ActiveState': 'inactive', 'Job': '0', 'Result': 'success',
                        'InvocationID': 'old', 'ExecMainStatus': '0',
                        'ExecMainStartTimestampMonotonic': '100', 'ExecCondition': '',
                        'ConditionResult': 'yes'}
        self.initial_timer = copy.deepcopy(self.timer)
        self.initial_service = copy.deepcopy(self.service)

    def __call__(self, argv, timeout):
        self.calls.append((list(argv), timeout))
        assert argv[:2] == ['systemctl', '--user']
        args = argv[2:]
        for index, expected in enumerate(self.fail):
            if args == expected:
                self.fail.pop(index)
                return subprocess.CompletedProcess(argv, 1, b'', b'secret password SQL')
        output = ''
        if args[0] == 'show':
            props = [p.split('=', 1)[1] for p in args[2:]]
            source = self.timer if args[1] == ops.TIMER else self.service
            lines = []
            for prop in props:
                for item in source[prop].split('\n'):
                    lines.append(prop + '=' + item)
            output = '\n'.join(lines)
        elif args == ['daemon-reload']:
            timer = self.config / (ops.TIMER + '.d') / 'zz-admin-release.conf'
            service = self.config / (ops.SERVICE + '.d') / 'zz-admin-release.conf'
            if timer.exists():
                self.timer['TimersCalendar'] = '\n'.join('{ OnCalendar=' + line.split('=', 1)[1] + ' ; next_elapse=n/a }'
                    for line in timer.read_text().splitlines() if line.startswith('OnCalendar=') and line != 'OnCalendar=')
            else:
                self.timer['TimersCalendar'] = self.initial_timer['TimersCalendar']
            if service.exists():
                text = [line for line in service.read_text().splitlines() if line.startswith('ExecCondition=/')][0]
                program = text.split(" -c '", 1)[1][:-1]
                self.service['ExecCondition'] = condition(program)
            else:
                self.service['ExecCondition'] = self.initial_service['ExecCondition']
        elif args[0] == 'disable':
            self.timer['UnitFileState'] = 'disabled'
            if '--now' in args:
                self.timer['ActiveState'] = 'inactive'
        elif args[0] == 'enable':
            self.timer['UnitFileState'] = 'enabled-runtime' if '--runtime' in args else 'enabled'
        elif args == ['restart', ops.TIMER]:
            self.timer['ActiveState'] = 'active'
        elif args == ['stop', ops.TIMER]:
            self.timer['ActiveState'] = 'inactive'
        elif args == ['start', ops.SERVICE]:
            assert timeout == 90
            if self.entered:
                self.service['ActiveState'] = 'activating'
                self.entered.set()
                assert self.release.wait(3)
            if self.publish == 'timeout':
                self.service.update(ActiveState='activating', Job='14 ' + ops.SERVICE)
                raise subprocess.TimeoutExpired(argv, timeout, stderr='secret')
            self.service['ActiveState'] = 'inactive'
            if self.publish != 'old':
                self.service['InvocationID'] = 'new'
            if self.publish in ('success', 'failed'):
                self.service['ExecMainStartTimestampMonotonic'] = '200'
            if self.publish == 'failed':
                self.service.update(Result='exit-code', ExecMainStatus='1')
            if self.publish == 'skip':
                self.service['Result'] = 'success'  # systemd can retain old main status on condition skip
            if self.publish == 'condition-fail':
                self.service.update(Result='exec-condition', ExecMainStatus='0')
        else:
            raise AssertionError('Unexpected argv: ' + repr(args))
        return subprocess.CompletedProcess(argv, 0, output.encode(), b'')


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.config, self.state = root / 'config', root / 'state'
        self.system = Systemd(self.config)
        self.now = dt.datetime(2026, 11, 16, tzinfo=dt.timezone.utc)
        self.app = ops.Operations(self.config, self.state, self.system, lambda: self.now)

    def settings_payload(self, **updates):
        payload = dict(version=self.app.get_settings()['version'], enabled=True,
                       start_date='2026-11-20', end_date='2027-01-03', time='07:45')
        payload.update(updates)
        return payload

    def publish_payload(self):
        return dict(confirm=True, schedule_version=self.app.get_settings()['version'])

    def error(self, status, func, *args):
        with self.assertRaises(ops.OperationError) as caught:
            func(*args)
        self.assertEqual(caught.exception.status, status)
        self.assertNotIn('secret', str(caught.exception))
        return str(caught.exception)

    def test_get_read_only_stable_cross_month_actual(self):
        settings = self.app.get_settings()
        self.assertEqual((settings['start_date'], settings['end_date'], settings['time']),
                         ('2026-11-16', '2026-12-16', '06:00'))
        self.assertEqual(settings['version'], self.app.get_settings()['version'])
        self.assertFalse(self.config.exists())
        self.assertFalse(self.state.exists())
        self.assertFalse(settings['busy'])
        self.assertIsNone(settings['warning'])

    def test_date_utc_taipei_boundary(self):
        self.now = dt.datetime(2026, 11, 15, 16, tzinfo=dt.timezone.utc)
        self.assertEqual(self.app.get_settings()['today'], '2026-11-16')
        self.assertTrue(self.app.publish_now(self.publish_payload())['ok'])
        self.now = dt.datetime(2026, 11, 15, 15, 59, tzinfo=dt.timezone.utc)
        self.assertEqual(self.app.get_settings()['today'], '2026-11-15')
        self.error(409, self.app.publish_now, self.publish_payload())

    def test_parse_all_rules_and_fail_closed(self):
        for text in ('{ OnCalendar=*-*-* 06:00:00 Asia/Taipei }',
                     '{ OnCalendar=2026-11-01..03 06:00:00 Asia/Taipei } { OnCalendar=2026-11-05 06:00:00 Asia/Taipei }',
                     '{ OnCalendar=2026-11-31 06:00:00 Asia/Taipei }',
                     '{ OnCalendar=2026-11-01 06:00:00 Asia/Taipei } { OnCalendar=2026-11-02 07:00:00 Asia/Taipei }'):
            with self.subTest(text=text):
                self.system.timer['TimersCalendar'] = text
                settings = self.app.get_settings()
                self.assertIsNone(settings['start_date'])
                self.assertIsNone(settings['end_date'])
                self.assertIsNone(settings['time'])
                self.assertIsNotNone(settings['warning'])

    def test_save_cross_month_disable_enable_backup(self):
        original = self.app.get_settings()['version']
        result = self.app.save_settings(self.settings_payload(enabled=False))
        self.assertFalse(result['enabled'])
        self.assertFalse(result['busy'])
        self.assertEqual(result['end_date'], '2027-01-03')
        self.assertNotEqual(result['version'], original)
        text = self.app.paths[0].read_text()
        for expected in ('2026-11-20..30', '2026-12-01..31', '2027-01-01..03', 'Persistent=yes'):
            self.assertIn(expected, text)
        self.assertNotIn('ExecStart', self.app.paths[1].read_text())
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        self.assertTrue(self.app.save_settings(self.settings_payload())['enabled'])
        backups = list(self.state.glob('schedule-*'))
        self.assertEqual(len(backups), 2)
        self.assertTrue(any((p / '0.conf').exists() and (p / '1.conf').exists() for p in backups))
        self.assertTrue(all(ops.SERVICE not in argv or argv[2] == 'show' for argv, _ in self.system.calls))

    def test_disabled_timer_allows_publish(self):
        self.system.timer.update(UnitFileState='disabled', ActiveState='inactive')
        self.assertTrue(self.app.publish_now(self.publish_payload())['ok'])

    def test_version_conflict_no_write(self):
        payload = self.settings_payload()
        self.system.timer['UnitFileState'] = 'disabled'
        self.error(409, self.app.save_settings, payload)
        self.error(409, self.app.publish_now, dict(confirm=True, schedule_version='stale'))
        self.assertFalse(self.config.exists())
        self.assertFalse(any(argv[2] != 'show' for argv, _ in self.system.calls))

    def test_unmanaged_file_and_symlink_refused(self):
        path = self.app.paths[0]
        path.parent.mkdir(parents=True)
        path.write_text('# someone else\n')
        self.error(409, self.app.save_settings, self.settings_payload())
        self.assertEqual(path.read_text(), '# someone else\n')
        path.unlink()
        target = Path(self.tmp.name) / 'other'
        target.write_text('other')
        path.symlink_to(target)
        self.error(409, self.app.get_settings)
        self.assertEqual(target.read_text(), 'other')

    def test_custom_condition_not_dropped(self):
        for value in (condition('print("custom")'), condition('print("custom")') + ' ' + condition('print("second")')):
            self.system.service['ExecCondition'] = value
            self.error(409, self.app.save_settings, self.settings_payload())
            self.assertFalse(self.config.exists())

    def test_existing_exact_guard_recognized(self):
        path = Path(__file__).resolve().parents[1] / 'devotional/systemd/release-through-20261216.service.conf'
        line = [line for line in path.read_text().splitlines() if line.startswith('ExecCondition=/')][0]
        program = line.split(" -c '", 1)[1][:-1]
        self.system.service['ExecCondition'] = condition(program)
        self.assertTrue(self.app.save_settings(self.settings_payload())['enabled'])

    def test_rollback_command_failure_and_existing_managed_backups(self):
        self.app.save_settings(self.settings_payload())
        before = [p.read_bytes() for p in self.app.paths]
        settings = self.app.get_settings()
        self.system.fail = [['restart', ops.TIMER]]
        message = self.error(503, self.app.save_settings, self.settings_payload(time='08:30'))
        self.assertIn('已查驗還原', message)
        self.assertEqual([p.read_bytes() for p in self.app.paths], before)
        self.assertEqual(self.app.get_settings()['version'], settings['version'])

    def test_rollback_on_each_mutating_step(self):
        for failing in (['daemon-reload'], ['enable', ops.TIMER], ['restart', ops.TIMER],
                        ['disable', '--now', ops.TIMER]):
            with self.subTest(failing=failing):
                self.system.fail = [failing]
                message = self.error(503, self.app.save_settings,
                                     self.settings_payload(enabled=failing[0] != 'disable'))
                self.assertIn('已查驗還原', message)
                self.assertFalse(any(path.exists() for path in self.app.paths))
                self.assertEqual(self.system.timer, self.system.initial_timer)

    def test_runtime_enablement_is_restored(self):
        self.system.timer['UnitFileState'] = 'enabled-runtime'
        self.system.fail = [['restart', ops.TIMER]]
        self.error(503, self.app.save_settings, self.settings_payload())
        self.assertEqual(self.system.timer['UnitFileState'], 'enabled-runtime')
        self.assertIn((['systemctl', '--user', 'enable', '--runtime', ops.TIMER], 3), self.system.calls)

    def test_disabled_inactive_timer_rollback_without_previous_files(self):
        self.system.timer.update(UnitFileState='disabled', ActiveState='inactive')
        original = copy.deepcopy(self.system.timer)
        self.system.fail = [['restart', ops.TIMER]]
        self.assertIn('已查驗還原', self.error(503, self.app.save_settings, self.settings_payload()))
        self.assertEqual(self.system.timer, original)
        self.assertFalse(any(path.exists() for path in self.app.paths))

    def test_start_failure_reads_after_state_and_does_not_expose_stderr(self):
        self.system.fail = [['start', ops.SERVICE]]
        self.error(503, self.app.publish_now, self.publish_payload())
        last = self.system.calls[-1][0]
        self.assertEqual(last[2:4], ['show', ops.SERVICE])

    def test_rollback_failure_honest(self):
        self.system.fail = [['restart', ops.TIMER], ['daemon-reload']]
        message = self.error(503, self.app.save_settings, self.settings_payload())
        self.assertIn('還原未完整成功', message)
        self.assertNotIn('已查驗還原', message)

    def test_atomic_write_failure_rolls_back(self):
        original = self.app._atomic
        def fail_second(path, value):
            if path == self.app.paths[1]:
                raise OSError('secret')
            original(path, value)
        with patch.object(self.app, '_atomic', side_effect=fail_second):
            self.assertIn('已查驗還原', self.error(503, self.app.save_settings, self.settings_payload()))
        self.assertFalse(any(path.exists() for path in self.app.paths))

    def test_busy_active_and_queued_blocks_save_publish(self):
        for active, job in (('active', '0'), ('activating', '0'), ('inactive', '22 something')):
            self.system.service.update(ActiveState=active, Job=job)
            self.assertTrue(self.app.get_settings()['busy'])
            self.error(409, self.app.save_settings, self.settings_payload())
            self.error(409, self.app.publish_now, self.publish_payload())
        self.assertFalse(any(argv[2] != 'show' for argv, _ in self.system.calls))

    def test_success_requires_new_invocation_and_actual_start(self):
        for mode in ('old', 'skip', 'condition-fail', 'failed'):
            with self.subTest(mode=mode):
                self.system.service = copy.deepcopy(self.system.initial_service)
                self.system.publish = mode
                self.error(503, self.app.publish_now, self.publish_payload())
        self.system.service = copy.deepcopy(self.system.initial_service)
        self.system.publish = 'success'
        result = self.app.publish_now(self.publish_payload())
        self.assertTrue(result['ok'])
        self.assertEqual(result['outcome'], 'service_completed')
        self.assertIn('正式站更新請重新整理確認', result['message'])
        self.assertFalse(result['settings']['busy'])

    def test_timeout_preserves_inflight_rejection(self):
        self.system.publish = 'timeout'
        message = self.error(503, self.app.publish_now, self.publish_payload())
        self.assertIn('可能仍在執行', message)
        self.error(409, self.app.publish_now, self.publish_payload())
        self.assertEqual(sum(argv[2:] == ['start', ops.SERVICE] for argv, _ in self.system.calls), 1)

    def test_process_lock_rejects_concurrent_operation(self):
        self.system.entered, self.system.release = threading.Event(), threading.Event()
        payload = self.publish_payload()
        result = []
        thread = threading.Thread(target=lambda: result.append(self.app.publish_now(payload)))
        thread.start()
        try:
            self.assertTrue(self.system.entered.wait(3))
            self.error(409, self.app.publish_now, payload)
            self.error(409, self.app.save_settings, self.settings_payload())
            self.assertTrue(self.app.get_settings()['busy'])
        finally:
            self.system.release.set()
            thread.join(3)
        self.assertEqual(len(result), 1)
        self.assertFalse(ops._LOCK.locked())

    def test_injection_and_validation_no_execution(self):
        mutations = [dict(start_date='2026-11-16; touch /tmp/x'), dict(end_date='2026-2-03'),
                     dict(end_date='2029-01-01'), dict(start_date='2026-12-20', end_date='2026-11-01'),
                     dict(time='06:00\nExecStart=/bin/sh'), dict(time='24:00'), dict(enabled='true'),
                     dict(today='2026-11-16'), dict(unit='other.service'), dict(config_dir='/tmp/evil'),
                     dict(command=['git', 'push'])]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.error(400, self.app.save_settings, self.settings_payload(**mutation))
        for payload in (dict(confirm='true', schedule_version='x'), dict(confirm=True, schedule_version='x', today='2030-01-01'),
                        dict(confirm=True, schedule_version='x', command='touch /tmp/x')):
            self.error(400, self.app.publish_now, payload)
        self.assertFalse(self.config.exists())
        self.assertTrue(all(argv[2] == 'show' for argv, _ in self.system.calls))

    def test_service_error_safe_and_get_warning(self):
        self.system.fail = [['show', ops.TIMER] + ['--property=' + p for p in ops.TIMER_PROPS]]
        settings = self.app.get_settings()
        self.assertIsNone(settings['enabled'])
        self.assertIsNotNone(settings['warning'])
        self.assertNotIn('secret', settings['warning'])
        self.assertFalse(self.config.exists())

    def test_output_limit_and_missing_properties(self):
        self.app.runner = lambda argv, timeout: subprocess.CompletedProcess(argv, 0, b'x' * (ops.MAX_OUTPUT+1), b'')
        self.assertIsNotNone(self.app.get_settings()['warning'])
        self.error(503, self.app.publish_now, dict(confirm=True, schedule_version='x'))
        self.app.runner = lambda argv, timeout: subprocess.CompletedProcess(argv, 0, b'ActiveState=inactive', b'')
        self.assertIsNotNone(self.app.get_settings()['warning'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
