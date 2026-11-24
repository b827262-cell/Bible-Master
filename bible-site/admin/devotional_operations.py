"""Fixed-unit devotional schedule operations. HTTP input never controls execution paths.

Only zz-admin-release.conf drop-ins are owned here. Construction injection is for
isolated tests; the HTTP adapter uses the three module-level functions below.
"""
import calendar
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import tempfile
import threading
import time as monotime
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo('Asia/Taipei')
TIMER = 'bible-devotional-publish.timer'
SERVICE = 'bible-devotional-publish.service'
MARKER = '# Managed by Bible-Master devotional admin v1'
MAX_OUTPUT = 65536
_LOCK = threading.Lock()
TIMER_PROPS = ('ActiveState', 'UnitFileState', 'TimersCalendar')
SERVICE_PROPS = ('ActiveState', 'Job', 'Result', 'InvocationID', 'ExecMainStatus',
                 'ExecMainStartTimestampMonotonic', 'ExecCondition', 'ConditionResult')


class OperationError(Exception):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.message, self.status = message, status


def _run(argv, timeout):
    """Bound stdout while reading, discard stderr, and never invoke a shell."""
    env = dict(os.environ, LC_ALL='C', LANG='C')
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               env=env, shell=False)
    output = bytearray()
    deadline = monotime.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - monotime.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, timeout)
                for key, _ in selector.select(min(remaining, .25)):
                    chunk = os.read(key.fd, min(4096, MAX_OUTPUT + 1 - len(output)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    output.extend(chunk)
                    if len(output) > MAX_OUTPUT:
                        raise OperationError('系統回應超過安全上限')
            remaining = deadline - monotime.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            code = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(argv, code, bytes(output), b'')
    finally:
        if process.poll() is None:
            # Killing systemctl's client does not cancel a systemd service job.
            process.kill()
            process.wait()
        process.stdout.close()


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise OperationError('日期須為 YYYY-MM-DD', 400)
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise OperationError('日期不正確', 400) from None


def _schedule(calendars):
    """Accept only complete, finite, contiguous daily rules with a common time."""
    chunks = re.findall(r'OnCalendar=([^;}\n]*)', calendars or '')
    if not chunks:
        return None, None, None
    days, times = set(), set()
    for chunk in chunks:
        match = re.fullmatch(r'\s*(\d{4})-(\d{2})-(\d{2})(?:\.\.(\d{2}))? '
                             r'(\d{2}):(\d{2}):00 Asia/Taipei\s*', chunk)
        if not match:
            return None, None, None
        y, m, first = map(int, match.group(1, 2, 3))
        last = int(match.group(4) or first)
        hour, minute = map(int, match.group(5, 6))
        try:
            if first > last or hour > 23 or minute > 59:
                raise ValueError()
            for day in range(first, last + 1):
                days.add(dt.date(y, m, day))
        except ValueError:
            return None, None, None
        times.add('%02d:%02d' % (hour, minute))
    if len(times) != 1 or not days:
        return None, None, None
    start, end = min(days), max(days)
    if (end - start).days + 1 != len(days):
        return None, None, None
    return start.isoformat(), end.isoformat(), times.pop()


def _busy(service):
    job = service.get('Job', '').strip()
    return (service.get('ActiveState') not in ('inactive', 'failed') or
            job not in ('', '0', '0 /'))


def _condition_code(start, end):
    # Every inserted component is a validated date integer, never user text.
    return ('import datetime, sys; from zoneinfo import ZoneInfo; '
            'd = datetime.datetime.now(ZoneInfo("Asia/Taipei")).date(); '
            'sys.exit(0 if datetime.date(%d, %d, %d) <= d <= '
            'datetime.date(%d, %d, %d) else 1)' %
            (start.year, start.month, start.day, end.year, end.month, end.day))


def _known_condition(serialized):
    """Recognize exact known guard programs, including systemd's show wrapper.

    Comparing full argv prevents an unrelated custom condition containing a date
    or marker from being silently discarded.
    """
    if not serialized.strip():
        return True
    programs = []
    for cutoff in ((2026, 11, 25), (2026, 12, 16)):
        y, m, d = cutoff
        label = '%04d-%02d-%02d' % cutoff
        programs.append('import datetime, sys; from zoneinfo import ZoneInfo; '
                        'd = datetime.datetime.now(ZoneInfo("Asia/Taipei")).date(); '
                        'print(f"devotional release skipped: Taipei date {d} is after ' + label +
                        '", file=sys.stderr) if d > datetime.date(%d, %d, %d) else None; '
                        'sys.exit(0 if d <= datetime.date(%d, %d, %d) else 1)' % (y,m,d,y,m,d))
    # Current admin guards have strictly numerical, canonical date constructors.
    pattern = (r'import datetime, sys; from zoneinfo import ZoneInfo; '
               r'd = datetime.datetime.now\(ZoneInfo\("Asia/Taipei"\)\).date\(\); '
               r'sys.exit\(0 if datetime.date\((\d{1,4}), (\d{1,2}), (\d{1,2})\) <= d <= '
               r'datetime.date\((\d{1,4}), (\d{1,2}), (\d{1,2})\) else 1\)')
    # A single ExecCondition object only; embedded shell / second argv fail closed.
    wrapped = re.fullmatch(r'\{ path=/usr/bin/python3 ; argv\[\]=/usr/bin/python3 -c (.*?) ; '
                           r'ignore_errors=no ; start_time=\[[^\]]*\] ; stop_time=\[[^\]]*\] ; '
                           r'pid=\d+ ; code=[^;{}]* ; status=[^;{}]* \}', serialized.strip())
    if not wrapped:
        return False
    program = wrapped.group(1)
    if program in programs:
        return True
    match = re.fullmatch(pattern, program)
    if not match:
        return False
    try:
        values = list(map(int, match.groups()))
        return _condition_code(dt.date(*values[:3]), dt.date(*values[3:])) == program
    except ValueError:
        return False


class Operations:
    def __init__(self, config_dir=None, state_dir=None, runner=None, clock=None):
        self.config_dir = Path(config_dir) if config_dir is not None else Path.home() / '.config/systemd/user'
        self.state_dir = Path(state_dir) if state_dir is not None else Path.home() / '.local/state/bible-master/devotional-admin'
        self.runner = runner or _run
        self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self.paths = [self.config_dir / (unit + '.d') / 'zz-admin-release.conf'
                      for unit in (TIMER, SERVICE)]

    def _command(self, args, timeout=3):
        try:
            result = self.runner(['systemctl', '--user'] + args, timeout=timeout)
            raw = result.stdout or b''
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8', 'replace')
            if len(raw.encode('utf-8')) > MAX_OUTPUT:
                raise OperationError('系統回應超過安全上限')
            if result.returncode:
                raise OperationError('系統服務操作失敗，請重新讀取狀態')
            return raw
        except subprocess.TimeoutExpired:
            raise OperationError('操作逾時，服務可能仍在執行；請重新讀取狀態', 503) from None
        except (OSError, ValueError):
            raise OperationError('無法連線到系統服務', 503) from None

    def _show(self, unit, props):
        output = self._command(['show', unit] + ['--property=' + prop for prop in props])
        result = {}
        for line in output.splitlines():
            key, sep, value = line.partition('=')
            if sep and key in props:
                if key in ('TimersCalendar', 'ExecCondition') and key in result:
                    result[key] += '\n' + value
                else:
                    result[key] = value
        if any(prop not in result for prop in props):
            raise OperationError('系統服務狀態不完整，請稍後重試')
        return result

    def _files(self):
        values = []
        for path in self.paths:
            if path.is_symlink():
                raise OperationError('管理設定不可使用符號連結', 409)
            try:
                with path.open('rb') as handle:
                    content = handle.read(MAX_OUTPUT + 1)
                if len(content) > MAX_OUTPUT:
                    raise OperationError('管理設定超過安全上限', 409)
                values.append(content)
            except FileNotFoundError:
                values.append(None)
            except OSError:
                raise OperationError('無法讀取管理設定') from None
        return values

    def _snapshot(self, strict=False, ignore_lock=False):
        warning = []
        timer, service = {}, {}
        for unit, props in ((TIMER, TIMER_PROPS), (SERVICE, SERVICE_PROPS)):
            try:
                value = self._show(unit, props)
                if unit == TIMER:
                    timer = value
                else:
                    service = value
            except OperationError:
                if strict:
                    raise
                warning.append('無法取得排程或上架服務狀態')
        files = self._files()
        start, end, hour = _schedule(timer.get('TimersCalendar'))
        if start is None:
            warning.append('無法確認有限且連續的每日排程，請檢查設定')
        now = self.clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.timezone.utc)
        # Stable queries retain the same version; loaded service changes invalidate it.
        digest = {'timer': timer, 'service': service,
                  'files': [value.hex() if value is not None else None for value in files]}
        version = hashlib.sha256(json.dumps(digest, sort_keys=True).encode()).hexdigest()
        settings = {'version': version,
                    'enabled': (timer['UnitFileState'] in ('enabled', 'enabled-runtime')) if timer else None,
                    'start_date': start, 'end_date': end, 'time': hour,
                    'timezone': 'Asia/Taipei', 'today': now.astimezone(TAIPEI).date().isoformat(),
                    'busy': _busy(service) or (_LOCK.locked() and not ignore_lock),
                    'service': {'active': service.get('ActiveState'), 'result': service.get('Result')},
                    'warning': '；'.join(dict.fromkeys(warning)) or None}
        return settings, timer, service, files

    def get_settings(self):
        return self._snapshot()[0]

    @staticmethod
    def _atomic(path, content):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.admin-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _backup(self, files):
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.state_dir.is_symlink() or self.state_dir.stat().st_mode & 0o077:
            raise OperationError('備份目錄必須為私人目錄')
        backup = Path(tempfile.mkdtemp(prefix='schedule-', dir=self.state_dir))
        for index, value in enumerate(files):
            if value is not None:
                self._atomic(backup / ('%d.conf' % index), value)
        self._atomic(backup / 'manifest.json', json.dumps({'present': [v is not None for v in files]}).encode())

    def _restore_timer(self, timer):
        state = timer['UnitFileState']
        # Remove newly introduced persistent/runtime enablement before restoring.
        self._command(['disable', TIMER])
        if state == 'enabled-runtime':
            self._command(['enable', '--runtime', TIMER])
        elif state == 'enabled':
            self._command(['enable', TIMER])
        if timer['ActiveState'] == 'active':
            self._command(['restart', TIMER])
        else:
            self._command(['stop', TIMER])

    def save_settings(self, payload):
        if not isinstance(payload, dict) or set(payload) != {'version', 'enabled', 'start_date', 'end_date', 'time'}:
            raise OperationError('設定欄位不正確', 400)
        if type(payload['enabled']) is not bool:
            raise OperationError('啟用設定須為布林值', 400)
        if not isinstance(payload['version'], str):
            raise OperationError('缺少設定版本', 400)
        start, end = _date(payload['start_date']), _date(payload['end_date'])
        if start > end or (end - start).days + 1 > 730:
            raise OperationError('排程範圍須依序且不超過 730 日', 400)
        hour = payload['time']
        if not isinstance(hour, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', hour):
            raise OperationError('時間須為 HH:MM', 400)
        if not _LOCK.acquire(blocking=False):
            raise OperationError('已有設定或上架操作進行中', 409)
        try:
            settings, timer, service, files = self._snapshot(strict=True, ignore_lock=True)
            if settings['version'] != payload['version']:
                raise OperationError('設定已變更，請重新讀取', 409)
            if _busy(service):
                raise OperationError('上架服務執行中，暫時無法修改設定', 409)
            if timer['UnitFileState'] not in ('enabled', 'enabled-runtime', 'disabled') or timer['ActiveState'] not in ('active', 'inactive'):
                raise OperationError('目前計時器狀態無法安全還原，請先檢查', 409)
            for value in files:
                if value is not None and not value.startswith((MARKER + '\n').encode()):
                    raise OperationError('同名設定並非本程式管理，拒絕覆寫', 409)
            if not _known_condition(service['ExecCondition']):
                raise OperationError('偵測到自訂 ExecCondition，請先人工確認日期護欄', 409)
            lines = [MARKER, '[Timer]', 'OnCalendar=']
            cursor = start
            while cursor <= end:
                last = min(end, dt.date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1]))
                lines.append('OnCalendar=%04d-%02d-%02d..%02d %s:00 Asia/Taipei' %
                             (cursor.year, cursor.month, cursor.day, last.day, hour))
                if last == end:
                    break
                cursor = last + dt.timedelta(days=1)
            lines.append('Persistent=yes')
            timer_text = '\n'.join(lines) + '\n'
            service_text = (MARKER + '\n[Service]\nExecCondition=\nExecCondition=/usr/bin/python3 -c \'' +
                            _condition_code(start, end) + "'\n")
            self._backup(files)
            try:
                for path, text in zip(self.paths, (timer_text, service_text)):
                    self._atomic(path, text.encode())
                self._command(['daemon-reload'])
                if payload['enabled']:
                    self._command(['enable', TIMER])
                    self._command(['restart', TIMER])
                else:
                    self._command(['disable', '--now', TIMER])
                actual, actual_timer, actual_service, _ = self._snapshot(strict=True, ignore_lock=True)
                expected_active = 'active' if payload['enabled'] else 'inactive'
                if (actual['enabled'] != payload['enabled'] or actual_timer['ActiveState'] != expected_active or
                        (actual['start_date'], actual['end_date'], actual['time']) !=
                        (start.isoformat(), end.isoformat(), hour) or
                        not _known_condition(actual_service['ExecCondition']) or
                        _condition_code(start, end) not in actual_service['ExecCondition']):
                    raise OperationError('重新查驗設定未生效')
                return actual
            except Exception:
                failures = []
                for path, content in zip(self.paths, files):
                    try:
                        if content is None:
                            path.unlink(missing_ok=True)
                        else:
                            self._atomic(path, content)
                    except Exception:
                        failures.append('檔案')
                try:
                    self._command(['daemon-reload'])
                    self._restore_timer(timer)
                    restored = self._snapshot(strict=True, ignore_lock=True)
                    if restored[1] != timer or restored[3] != files:
                        raise OperationError('還原查驗失敗')
                except Exception:
                    failures.append('服務狀態')
                if failures:
                    raise OperationError('儲存失敗，且還原未完整成功；請人工檢查設定與計時器狀態') from None
                raise OperationError('儲存失敗，已查驗還原原設定與計時器狀態') from None
        finally:
            _LOCK.release()

    def publish_now(self, payload):
        if (not isinstance(payload, dict) or set(payload) != {'confirm', 'schedule_version'} or
                payload.get('confirm') is not True or not isinstance(payload.get('schedule_version'), str)):
            raise OperationError('上架需要明確確認與設定版本', 400)
        if not _LOCK.acquire(blocking=False):
            raise OperationError('已有設定或上架操作進行中', 409)
        try:
            settings, _, before, _ = self._snapshot(strict=True, ignore_lock=True)
            if payload['schedule_version'] != settings['version']:
                raise OperationError('設定已變更，請重新讀取後再上架', 409)
            if _busy(before):
                raise OperationError('上架服務仍在執行，請勿重複送出', 409)
            if not settings['start_date'] or not settings['start_date'] <= settings['today'] <= settings['end_date']:
                raise OperationError('今天不在有效上架日期範圍內', 409)
            start_error = None
            try:
                self._command(['start', SERVICE], timeout=90)
            except OperationError as exc:
                start_error = exc
            # Even a failed/timed-out client can leave a running systemd job.
            try:
                after = self._show(SERVICE, SERVICE_PROPS)
            except OperationError:
                if start_error is not None:
                    raise start_error
                raise
            if start_error is not None:
                if _busy(after):
                    raise OperationError('操作未完成，服務可能仍在執行；請重新讀取狀態，勿重複上架', 503)
                raise start_error
            if _busy(after):
                raise OperationError('服務可能仍在執行；請重新讀取狀態，勿重複上架', 503)
            if not after['InvocationID'] or after['InvocationID'] == before['InvocationID']:
                raise OperationError('未確認新的上架執行，可能已被日期條件略過', 503)
            try:
                new_start = int(after['ExecMainStartTimestampMonotonic'])
                old_start = int(before['ExecMainStartTimestampMonotonic'] or '0')
            except ValueError:
                new_start = old_start = 0
            if (after['Result'] in ('exec-condition', 'skipped') or after['ConditionResult'] == 'no' or
                    new_start <= old_start or new_start == 0):
                raise OperationError('上架未執行或已被條件略過，請檢查日期與服務狀態', 503)
            if after['Result'] != 'success' or after['ExecMainStatus'] != '0':
                raise OperationError('上架服務執行失敗，請檢查服務狀態', 503)
            return {'ok': True, 'outcome': 'service_completed',
                    'message': '上架服務完成，正式站更新請重新整理確認',
                    'settings': self._snapshot(strict=True, ignore_lock=True)[0]}
        finally:
            _LOCK.release()


_DEFAULT = Operations()


def get_settings():
    return _DEFAULT.get_settings()


def save_settings(payload):
    return _DEFAULT.save_settings(payload)


def publish_now(payload):
    return _DEFAULT.publish_now(payload)
