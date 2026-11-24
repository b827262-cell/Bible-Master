#!/usr/bin/env python3
"""禱讀發佈狀態的唯讀收集器（task 141）。

只讀取三類來源，不寫入任何檔案、不執行發佈：
  - 正式站 https://bible.b827262.org/data/devotional.json（固定 HTTPS、最多 2 MiB、timeout 3 秒）
  - 本機 <site_root>/data/devotional.json（最多 2 MiB）
  - `systemctl --user show` 固定兩個 unit 的唯讀屬性（timeout 2 秒、輸出截斷）

`collect_status(site_root, now=None)` 是唯一入口；now 只供測試注入，HTTP 端點不暴露日期或 URL 參數。
任何局部來源失敗都只讓該區塊變成 unavailable/invalid，其他區塊照常回傳。
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")
PUBLIC_URL = "https://bible.b827262.org/data/devotional.json"
PUBLIC_SOURCE = PUBLIC_URL
LOCAL_SOURCE = "本機 data/devotional.json"
MAX_BYTES = 2 * 1024 * 1024
HTTP_TIMEOUT = 3.0
SYSTEMCTL_TIMEOUT = 2.0
MAX_OUTPUT = 64 * 1024
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
USER_AGENT = "BibleMaster-AdminStatus/1.0"

TIMER_UNIT = "bible-devotional-publish.timer"
SERVICE_UNIT = "bible-devotional-publish.service"
TIMER_PROPS = ("ActiveState", "UnitFileState", "NextElapseUSecRealtime", "TimersCalendar")
SERVICE_PROPS = ("Result", "ExecMainStatus", "ExecMainStartTimestamp", "ExecMainExitTimestamp")


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _as_taipei(now=None):
    if now is None:
        return datetime.datetime.now(TAIPEI)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    return now.astimezone(TAIPEI)


def _validate_entries(obj):
    """驗證 devotional.json 的陣列；回 (state, count, latest_date, error)。"""
    if not isinstance(obj, list):
        return "invalid", None, None, "資料格式不是 JSON 陣列"
    seen = set()
    for idx, entry in enumerate(obj, 1):
        if not isinstance(entry, dict):
            return "invalid", None, None, "第 %d 筆不是 JSON 物件" % idx
        value = entry.get("devotional_date")
        if not isinstance(value, str) or not DATE_RE.match(value):
            return "invalid", None, None, "第 %d 筆缺少合法的 devotional_date" % idx
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            return "invalid", None, None, "第 %d 筆的 devotional_date 不是合法日期" % idx
        if value in seen:
            return "invalid", None, None, "devotional_date 重複：%s" % value
        seen.add(value)
    if not obj:
        return "ok", 0, None, None
    return "ok", len(obj), max(seen), None


def _parse_json_entries(raw):
    """bytes → (state, count, latest, error)；壞 JSON／編碼不報成功。"""
    if len(raw) > MAX_BYTES:
        return "invalid", None, None, "資料超過 2 MiB 上限"
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return "invalid", None, None, "資料不是合法的 UTF-8 JSON"
    return _validate_entries(obj)


def _read_local(site_root, observed_at):
    path = os.path.join(site_root, "data", "devotional.json")
    try:
        with open(path, "rb") as f:
            raw = f.read(MAX_BYTES + 1)
    except OSError:
        return {"state": "unavailable", "count": None, "latest_date": None, "observed_at": observed_at,
                "source": LOCAL_SOURCE, "error": "讀不到本機資料"}
    state, count, latest, err = _parse_json_entries(raw)
    return {"state": state, "count": count, "latest_date": latest, "observed_at": observed_at,
            "source": LOCAL_SOURCE, "error": err}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """固定來源不跟隨任何重導，避免被帶到其他主機或 scheme。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_get(url, timeout):
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with opener.open(req, timeout=timeout) as resp:
        if not resp.geturl().startswith("https://"):
            raise urllib.error.URLError("來源不是 HTTPS")
        return resp.read(MAX_BYTES + 1)


def _fetch_public(observed_at):
    try:
        raw = _http_get(PUBLIC_URL, HTTP_TIMEOUT)
    except urllib.error.HTTPError as exc:
        return {"state": "unavailable", "count": None, "latest_date": None, "observed_at": observed_at,
                "source": PUBLIC_SOURCE, "error": "正式站回應 HTTP %s" % exc.code}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"state": "unavailable", "count": None, "latest_date": None, "observed_at": observed_at,
                "source": PUBLIC_SOURCE, "error": "連線失敗或逾時"}
    state, count, latest, err = _parse_json_entries(raw)
    return {"state": state, "count": count, "latest_date": latest, "observed_at": observed_at,
            "source": PUBLIC_SOURCE, "error": err}


def _run_bounded(cmd, timeout):
    """執行固定命令；回 (stdout, error)。不經過 shell，輸出截斷，錯誤不原樣外洩。"""
    if not shutil.which(cmd[0]):
        return None, "%s 不存在" % cmd[0]
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return None, "查詢逾時"
    except OSError:
        return None, "查詢失敗"
    if proc.returncode != 0:
        return None, "查詢失敗"
    raw = proc.stdout or b""
    if len(raw) > MAX_OUTPUT:
        return None, "輸出超過上限"
    out = raw[:MAX_OUTPUT].decode("utf-8", "replace")
    return out, None


def _systemctl_show(unit, props):
    """回 (dict, error)；只讀指定 unit 的白名單屬性。
       systemd 對多條 OnCalendar 會輸出多行同名 TimersCalendar=，必須全部累積後再交給
       _parse_cutoff；其他屬性維持舊行為（同名取最後一行）。"""
    cmd = ["systemctl", "--user", "show", unit] + ["--property=" + p for p in props]
    out, err = _run_bounded(cmd, SYSTEMCTL_TIMEOUT)
    if err:
        return None, err
    values = {}
    calendars = []
    for line in (out or "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key == "TimersCalendar" and key in props:
                calendars.append(value)
            elif key in props:
                values[key] = value
    if calendars:
        values["TimersCalendar"] = " ; ".join(calendars)
    if not values:
        return None, "systemd 沒有回傳可用屬性"
    return values, None


def _parse_cutoff(calendar):
    """從 TimersCalendar 的有限 OnCalendar 取截止日；無法唯一判定回 None。
       只接受完整可辨識的有限規則；逗號列表、無限規則、混合規則或任何不合法日期一律 None。
       多條有限規則取所有截止日的 max（例如 11/30 + 12/16 → 12/16）。"""
    if not isinstance(calendar, str):
        return None
    chunks = re.findall(r"OnCalendar=([^;}\n]*)", calendar)
    if not chunks:
        return None
    candidates = set()
    for chunk in chunks:
        text = chunk.strip()
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})\.\.(\d{4})-(\d{2})-(\d{2})(?:\s|$)", text)
        if m:
            try:
                candidates.add(datetime.date(int(m.group(4)), int(m.group(5)), int(m.group(6))).isoformat())
            except ValueError:
                return None
            continue
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})\.\.(\d{2})(?:\s|$)", text)
        if m:
            try:
                candidates.add(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(4))).isoformat())
            except ValueError:
                return None
            continue
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:\s|$)", text)
        if m:
            try:
                candidates.add(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat())
            except ValueError:
                return None
            continue
        return None                                            # 未知或無限規則：不得推論截止日
    return max(candidates) if candidates else None


def _collect_schedule(timer, timer_err, now):
    if timer is None:
        return {"state": "unavailable", "enabled": None, "active": None, "next_run": None,
                "cutoff_date": None, "expired": None, "calendar": None, "error": timer_err}
    missing = [p for p in TIMER_PROPS if p not in timer]
    if missing:
        return {"state": "invalid", "enabled": None, "active": None, "next_run": None,
                "cutoff_date": None, "expired": None, "calendar": None,
                "error": "timer 缺少必要屬性：" + "、".join(missing)}
    active = timer.get("ActiveState") or None
    unit_file = timer.get("UnitFileState") or None
    enabled = None if unit_file is None else unit_file in ("enabled", "enabled-runtime")
    calendar = timer.get("TimersCalendar") or None
    cutoff = _parse_cutoff(calendar)
    expired = None if cutoff is None else (now.date().isoformat() > cutoff)
    next_run = timer.get("NextElapseUSecRealtime") or None
    if next_run in ("n/a", "0"):
        next_run = None
    return {"state": "ok", "enabled": enabled, "active": active, "next_run": next_run,
            "cutoff_date": cutoff, "expired": expired, "calendar": calendar, "error": None}


def _collect_last_run(service, service_err):
    if service is None:
        return {"state": "unknown", "started_at": None, "finished_at": None, "exit_code": None,
                "error": service_err}
    missing = [p for p in SERVICE_PROPS if p not in service]
    if missing:
        return {"state": "unknown", "started_at": None, "finished_at": None, "exit_code": None,
                "error": "service 缺少必要屬性：" + "、".join(missing)}
    started = service.get("ExecMainStartTimestamp") or None
    if started in ("", "n/a"):
        started = None
    finished = service.get("ExecMainExitTimestamp") or None
    if finished in ("", "n/a"):
        finished = None
    try:
        exit_code = int(service.get("ExecMainStatus"))
    except (TypeError, ValueError):
        exit_code = None
    if started is None:
        return {"state": "never", "started_at": None, "finished_at": finished, "exit_code": exit_code,
                "error": None}
    result = (service.get("Result") or "").strip()
    if result == "success":
        if exit_code is None:
            state = "unknown"                              # Result 說成功但狀態碼無法解析：不可報成功
        elif exit_code == 0:
            state = "success"
        else:
            state = "failed"
    elif result in ("failed", "exit-code", "signal", "core-dump", "timeout", "watchdog",
                    "oom-kill", "start-limit-hit", "resources"):
        state = "failed"
    elif result in ("exec-condition", "skipped"):
        state = "skipped"
    else:
        state = "unknown"
    return {"state": state, "started_at": started, "finished_at": finished, "exit_code": exit_code,
            "error": None}


def _release_state(public, local, schedule, last_run):
    if schedule.get("expired") is True:
        return "cutoff"
    if last_run.get("state") == "failed":
        return "attention"
    # scheduled 需要正式站與本機資料都可用；任一 partial failure 只保留 schedule 區塊，整體誠實 unknown
    if public.get("state") != "ok" or local.get("state") != "ok":
        return "unknown"
    if (schedule.get("state") == "ok" and schedule.get("active") in ("active", "activating")
            and schedule.get("cutoff_date") and last_run.get("state") in ("success", "never", "skipped")):
        return "scheduled"
    return "unknown"


def _warnings(public, local, schedule, last_run):
    out = []
    if public.get("state") == "unavailable":
        out.append("無法取得正式站禱讀資料")
    elif public.get("state") == "invalid":
        out.append("正式站禱讀資料格式不正確")
    if local.get("state") == "unavailable":
        out.append("讀不到本機禱讀資料")
    elif local.get("state") == "invalid":
        out.append("本機禱讀資料格式不正確")
    if schedule.get("expired") is True:
        out.append("已超過截止日 %s，排程正常停止" % schedule.get("cutoff_date"))
    elif schedule.get("state") == "ok" and not schedule.get("cutoff_date"):
        out.append("無法從 OnCalendar 判定截止日")
    if last_run.get("state") == "failed":
        out.append("上次發佈執行失敗")
    return out


def fallback_status(observed_at=None, err="狀態收集失敗"):
    """收集器本身意外失敗時的最小契約；呼叫端仍可回 200。"""
    if observed_at is None:
        observed_at = _iso(_as_taipei())
    empty = {"state": "unavailable", "count": None, "latest_date": None, "observed_at": observed_at,
             "source": PUBLIC_SOURCE, "error": err}
    return {"observed_at": observed_at, "timezone": "Asia/Taipei",
            "public": empty,
            "local": {"state": "unavailable", "count": None, "latest_date": None, "observed_at": observed_at,
                      "source": LOCAL_SOURCE, "error": err},
            "schedule": {"state": "unavailable", "enabled": None, "active": None, "next_run": None,
                         "cutoff_date": None, "expired": None, "calendar": None, "error": err},
            "last_run": {"state": "unknown", "started_at": None, "finished_at": None, "exit_code": None,
                         "error": err},
            "release_state": "unknown", "warnings": ["狀態收集失敗"]}


def collect_status(site_root, now=None):
    """回傳固定契約的唯讀狀態；任何單一來源失敗都不影響其他區塊。"""
    base = _as_taipei(now)
    observed_at = _iso(base)
    try:
        public = _fetch_public(observed_at)
    except Exception:
        public = {"state": "unavailable", "count": None, "latest_date": None, "observed_at": observed_at,
                  "source": PUBLIC_SOURCE, "error": "正式站資料收集失敗"}
    try:
        local = _read_local(site_root, observed_at)
    except Exception:
        local = {"state": "unavailable", "count": None, "latest_date": None, "observed_at": observed_at,
                 "source": LOCAL_SOURCE, "error": "本機資料收集失敗"}
    try:
        timer, timer_err = _systemctl_show(TIMER_UNIT, TIMER_PROPS)
        service, service_err = _systemctl_show(SERVICE_UNIT, SERVICE_PROPS)
        schedule = _collect_schedule(timer, timer_err, base)
        last_run = _collect_last_run(service, service_err)
    except Exception:
        schedule = {"state": "unavailable", "enabled": None, "active": None, "next_run": None,
                    "cutoff_date": None, "expired": None, "calendar": None, "error": "排程狀態收集失敗"}
        last_run = {"state": "unknown", "started_at": None, "finished_at": None, "exit_code": None,
                    "error": "上次執行狀態收集失敗"}
    return {
        "observed_at": observed_at,
        "timezone": "Asia/Taipei",
        "public": public,
        "local": local,
        "schedule": schedule,
        "last_run": last_run,
        "release_state": _release_state(public, local, schedule, last_run),
        "warnings": _warnings(public, local, schedule, last_run),
    }
