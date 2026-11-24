#!/usr/bin/env python3
"""freebuff 派工工具 —— 已驗證流程的正式版（Herdr Core + Herdr App + Freebuff CLI）。

  python3 bible-site/tools/freebuff_dispatch.py --dry-run
  python3 bible-site/tools/freebuff_dispatch.py --terminal t8 --text "Reply exactly FREEBUFF_T8_OK" --timeout 60
  python3 bible-site/tools/freebuff_dispatch.py --file tasks/x.md --no-wait --json

流程（順序不可顛倒，2026-11-24 實測）：

  1. 解析 terminal —— `herdr-core ls --json` 掃 live 終端，再用 `herdr-core get`
     比對 foreground.argv 的 basename 是否為 freebuff。多個符合一律視為 ambiguous
     並拒絕派工；`--terminal` 可指定，指定錯也會被拒。
  2. 解析 tab/pane —— `herdr-app ls` 反查該 terminal 所在 tab 的 id 與 pane id。
     tab id、pane id 一律動態取得，不寫死。
  3. 解析 chat store —— 用 terminal 的 cwd 對應 `~/.config/manicode/projects/<cwd 名>/chats/*`，
     取最新 session；對不到就拒絕派工（先確認能驗證，再花額度）。
  4. 閒置檢查 —— `herdr-core read --lines 0` 必須看到輸入框 placeholder 且無工作中字樣。
  5. 對焦 —— `herdr-app do tab.select --id <tab>` → `pane.focus --terminal <t>`，
     再以 `herdr-app status` 核對 focused_pane。只下 agent.focus 會被還原。
  6. 送出 —— `herdr-core send <t> <text>`（貼上＋Enter，會自動提交）。
     不要再補按 Enter；send 的 exit 0 也不等於已提交。
  7. 完成判定 —— 讀 freebuff 自己的 chat store，要求：
       a. 出現內容等於本次 prompt 的 user 訊息；
       b. 其後出現 isComplete 的 assistant 訊息；
       c. 兩者時間都晚於本次派工。
     **不使用** hc wait / turn / status（hc 未註冊 freebuff：turn 恆 0、status 恆 null）。

防護：
  * 併發：STATE_DIR/dispatch.lock（O_EXCL，含 pid 與時間，逾時可接管）。
  * 重複：STATE_DIR/last.json 記錄上次 prompt 雜湊，短時間內相同 prompt 直接拒絕（--force 可覆寫）。
  * 逾時不自動重試（原 prompt 可能已送出），只回報 unverified。

本工具只讀、只送一個 prompt；不 commit、不 push、不改 freebuff binary、不注入 pty。
回覆內容原樣輸出，**不代為宣告驗收通過** —— 由 PM／CodeBuddy 依內容人工核對。

離開碼：0 完成且驗證通過／2 前置條件不成立／3 對焦失敗／4 等待逾時／
        5 已送出但無法確認完成／6 有其他派工進行中／7 重複送出被拒
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERDR_CORE = os.environ.get("HERDR_CORE_BIN", "herdr-core")
HERDR_APP = os.environ.get("HERDR_APP_BIN", "herdr-app")
CHAT_ROOT = Path(
    os.environ.get("FREEBUFF_DISPATCH_CHAT_ROOT", str(Path.home() / ".config" / "manicode" / "projects"))
)
STATE_DIR = Path(
    os.environ.get("FREEBUFF_DISPATCH_STATE_DIR", str(Path.home() / ".cache" / "freebuff-dispatch"))
)
DEFAULT_EXPECTED_TERMINAL = "t8"
PLACEHOLDER_RE = re.compile(r"enter a coding task", re.IGNORECASE)
BUSY_RE = re.compile(r"esc to stop|esc to interrupt|working\.\.\.|thinking", re.IGNORECASE)
FREEBUFF_RE = re.compile(r"^freebuff(\.exe)?$", re.IGNORECASE)


class Fail(Exception):
    """帶離開碼的失敗。"""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------- 基礎工具


def run(argv, timeout=30):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise Fail(2, f"找不到指令：{argv[0]}")
    except subprocess.TimeoutExpired:
        raise Fail(2, f"指令逾時：{' '.join(argv)}")
    return proc.returncode, proc.stdout, proc.stderr


def run_json(argv, timeout=30):
    code, out, err = run(argv, timeout)
    if code != 0:
        raise Fail(2, f"{' '.join(argv)} 失敗（exit {code}）：{(out + err).strip()[:300]}")
    try:
        return json.loads(out)
    except ValueError:
        raise Fail(2, f"{' '.join(argv)} 輸出不是 JSON：{out[:300]}")


def normalize(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def msg_time(entry):
    """freebuff 訊息 id 內含 epoch 毫秒（ai-<ms>-hash / user-<ms>）。"""
    match = re.match(r"(?:ai|user)-(\d{13})", str(entry.get("id", "")))
    if not match:
        return None
    return datetime.datetime.fromtimestamp(int(match.group(1)) / 1000)


def fmt_time(stamp):
    return stamp.strftime("%F %T.%f")[:-3] if stamp else None


def message_text(entry):
    blocks = entry.get("blocks") or []
    parts = [str(b.get("content", "")) for b in blocks if b.get("type") == "text"]
    return "\n".join(parts) if parts else str(entry.get("content", ""))


# ---------------------------------------------------------------- 探索


def foreground_is_freebuff(detail):
    argv = [str(a) for a in ((detail.get("foreground") or {}).get("argv") or [])]
    return any(FREEBUFF_RE.match(Path(a).name) for a in argv)


def resolve_terminal(explicit):
    """回傳 (address, detail)；多個符合視為 ambiguous，不猜。"""
    if explicit:
        try:
            detail = run_json([HERDR_CORE, "get", explicit, "--json"])
        except Fail:
            raise Fail(2, f"找不到 terminal {explicit}")
        if not foreground_is_freebuff(detail):
            fg = (detail.get("foreground") or {}).get("argv")
            raise Fail(2, f"{explicit} 的前景程序不是 freebuff（argv={fg}）")
        return explicit, detail

    listing = run_json([HERDR_CORE, "ls", "--json"])
    matches = []
    for term in listing.get("terminals", []):
        address = term.get("address")
        if not address or term.get("state") != "live":
            continue
        try:
            detail = run_json([HERDR_CORE, "get", address, "--json"])
        except Fail:
            continue
        if foreground_is_freebuff(detail):
            matches.append((address, detail))
    if not matches:
        raise Fail(2, "找不到執行 freebuff 的 live 終端（可用 --terminal 指定）")
    if len(matches) > 1:
        names = ", ".join(f"{a}({ ' '.join((d.get('foreground') or {}).get('argv') or []) })" for a, d in matches)
        raise Fail(2, f"偵測到多個 freebuff 終端，拒絕猜測：{names}")
    return matches[0]


def resolve_pane(terminal):
    listing = run_json([HERDR_APP, "ls"])
    for space in listing.get("spaces", []):
        for tab in space.get("tabs", []):
            for item in tab.get("terminals", []):
                if item.get("terminal") == terminal:
                    return {
                        "space": space.get("id"),
                        "tab": tab.get("id"),
                        "tab_name": tab.get("name"),
                        "tab_active": tab.get("active"),
                        "pane": item.get("pane"),
                    }
    raise Fail(2, f"herdr-app 找不到 terminal {terminal}（視窗未開或已關閉？）")


def resolve_chat_store(cwd, warnings):
    """用 cwd 對應 project 目錄，取最新 session；對不到就拒絕（先能驗證再花額度）。"""
    if not CHAT_ROOT.is_dir():
        raise Fail(2, f"找不到 freebuff chat store：{CHAT_ROOT}")
    project_dir = CHAT_ROOT / Path(cwd).name
    candidates = sorted(
        project_dir.glob("chats/*/chat-messages.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if project_dir.is_dir() else []
    if candidates:
        return candidates[0], project_dir.name

    recent = []
    for path in CHAT_ROOT.glob("*/chats/*/chat-messages.json"):
        try:
            if time.time() - path.stat().st_mtime < 86400:
                recent.append(path)
        except OSError:
            continue
    if len(recent) == 1:
        warnings.append(f"cwd 對不到 project 目錄，改用唯一近期 session：{recent[0].parent.parent.parent.name}")
        return recent[0], recent[0].parent.parent.parent.name
    raise Fail(
        2,
        f"無法唯一識別 chat store（cwd={cwd}，候選 {len(recent)} 個）；拒絕在無法驗證的情況下送出",
    )


# ---------------------------------------------------------------- 前置檢查


def read_screen(terminal):
    code, out, err = run([HERDR_CORE, "read", "--lines", "0", terminal])
    if code != 0:
        raise Fail(2, f"讀取 {terminal} 畫面失敗：{(out + err).strip()[:300]}")
    return out


def check_idle(screen):
    if not PLACEHOLDER_RE.search(screen):
        raise Fail(2, "輸入框不是空白狀態（可能有草稿或正在工作中），拒絕送出")
    if BUSY_RE.search(screen):
        raise Fail(2, "偵測到工作中字樣（working/thinking/esc to stop），拒絕送出")


def focus(terminal, pane_info):
    run_json([HERDR_APP, "do", "tab.select", "--id", pane_info["tab"]])
    run_json([HERDR_APP, "do", "pane.focus", "--terminal", terminal])
    time.sleep(0.8)
    status = run_json([HERDR_APP, "status"])
    if status.get("focused_pane") != pane_info["pane"]:
        raise Fail(
            3,
            f"對焦失敗：focused_pane={status.get('focused_pane')}，預期 {pane_info['pane']}",
        )


# ---------------------------------------------------------------- 併發／重複防護


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return False
    return True


def acquire_lock(terminal, prompt, ttl):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock = STATE_DIR / "dispatch.lock"
    payload = json.dumps(
        {
            "pid": os.getpid(),
            "terminal": terminal,
            "prompt_sha256": sha256(prompt),
            "started_at": time.time(),
        }
    )
    for attempt in (0, 1):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                info = json.loads(lock.read_text())
            except (OSError, ValueError):
                info = {}
            age = time.time() - float(info.get("started_at") or 0)
            if _pid_alive(info.get("pid")) and age < ttl:
                raise Fail(6, f"已有派工進行中（pid={info.get('pid')}，{age:.0f}s）：{lock}")
            if attempt == 0:
                try:
                    lock.unlink()
                except OSError:
                    pass
                continue
            raise Fail(6, f"無法取得派工鎖：{lock}")
        else:
            with os.fdopen(fd, "w") as fh:
                fh.write(payload)
            return lock
    raise Fail(6, f"無法取得派工鎖：{lock}")


def release_lock(lock):
    try:
        lock.unlink()
    except OSError:
        pass


def check_duplicate(prompt, terminal, window, force):
    if force:
        return None
    state = STATE_DIR / "last.json"
    if not state.is_file():
        return None
    try:
        info = json.loads(state.read_text())
    except (OSError, ValueError):
        return None
    same = info.get("prompt_sha256") == sha256(prompt) and info.get("terminal") == terminal
    age = time.time() - float(info.get("sent_at") or 0)
    if same and age < window:
        raise Fail(7, f"相同 prompt 已在 {age:.0f}s 前送給 {terminal}；如確定要再送請加 --force")
    return None


def record_dispatch(prompt, terminal):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "last.json").write_text(
        json.dumps({"prompt_sha256": sha256(prompt), "terminal": terminal, "sent_at": time.time()})
    )


# ---------------------------------------------------------------- 完成驗證


def load_chat(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, list) else None


def wait_for_completion(chat_file, before_ids, prompt, dispatched_at, timeout):
    """等「本次」prompt 的 user 訊息與其後的 assistant 完成訊息；不回傳舊回覆。"""
    deadline = time.time() + timeout
    target = normalize(prompt)
    while time.time() < deadline:
        data = load_chat(chat_file)
        if data:
            fresh = [m for m in data if m.get("id") not in before_ids]
            user = next(
                (
                    m
                    for m in fresh
                    if m.get("variant") == "user" and normalize(message_text(m)) == target
                ),
                None,
            )
            if user:
                user_time = msg_time(user)
                if user_time and user_time < dispatched_at:
                    user = None  # 舊訊息，不採計
            if user:
                user_index = data.index(user)
                for entry in data[user_index + 1:]:
                    if entry.get("variant") != "ai" or not entry.get("isComplete"):
                        continue
                    stamp = msg_time(entry)
                    if stamp and stamp < dispatched_at:
                        continue
                    return {
                        "reply": message_text(entry).strip(),
                        "reply_at": fmt_time(stamp),
                        "completion_time": entry.get("completionTime"),
                        "user_message_id": user.get("id"),
                        "user_message_at": fmt_time(user_time),
                        "assistant_message_id": entry.get("id"),
                        "chat_file": str(chat_file),
                    }
        time.sleep(1.5)
    return None


# ---------------------------------------------------------------- 主流程


def dispatch(args):
    warnings = []
    terminal, detail = resolve_terminal(args.terminal)
    pane_info = resolve_pane(terminal)
    cwd = detail.get("cwd") or ""
    chat_file, project = resolve_chat_store(cwd, warnings)
    screen = read_screen(terminal)
    check_idle(screen)

    expected = args.expected_terminal
    mismatch = bool(expected) and terminal != expected
    if mismatch:
        warnings.append(f"預期 terminal {expected}，實際偵測到 {terminal}")
        if args.require_expected:
            raise Fail(2, f"預期 {expected}，實際 {terminal}，--require-expected 要求中止")

    report = {
        "task": args.task,
        "terminal": terminal,
        "expected_terminal": expected,
        "terminal_mismatch": mismatch,
        "foreground_process": (detail.get("foreground") or {}).get("argv"),
        "cwd": cwd,
        "chat_store": str(chat_file),
        "project": project,
        "tab_id": pane_info["tab"],
        "tab_name": pane_info["tab_name"],
        "pane_id": pane_info["pane"],
        "tab_was_active": pane_info["tab_active"],
        "prompt": args.text,
        "prompt_sha256": sha256(args.text or ""),
        "transport_ok": False,
        "submitted": None,
        "completed": None,
        "verified": False,
        "reply": None,
        "reply_at": None,
        "completion_time": None,
        "sent_at": None,
        "completion_source": "freebuff chat store（非 hc wait/turn/status）",
        "acceptance": "manual（本工具不代為宣告驗收通過）",
        "warnings": warnings,
    }

    if args.dry_run:
        report["dry_run"] = True
        return 0, report

    check_duplicate(args.text, terminal, args.dup_window, args.force)
    lock = acquire_lock(terminal, args.text, args.lock_ttl)
    try:
        focus(terminal, pane_info)
        report["focus_verified"] = True

        before = load_chat(chat_file) or []
        before_ids = {m.get("id") for m in before}

        dispatched_at = datetime.datetime.now()
        report["sent_at"] = fmt_time(dispatched_at)
        code, out, err = run([HERDR_CORE, "send", terminal, args.text], timeout=60)
        report["send_output"] = (out + err).strip()
        if code != 0:
            raise Fail(2, f"{HERDR_CORE} send 失敗（exit {code}）：{report['send_output'][:300]}")
        report["transport_ok"] = True
        record_dispatch(args.text, terminal)

        if args.no_wait:
            report["submitted"] = "unverified"
            report["warnings"].append("--no-wait：未驗證回覆，需人工確認")
            return 0, report

        result = wait_for_completion(chat_file, before_ids, args.text, dispatched_at, args.timeout)
        if result:
            report.update(result)
            report["submitted"] = "confirmed"
            report["completed"] = True
            report["verified"] = True
            return 0, report
        report["submitted"] = "unverified"
        report["completed"] = False
        report["warnings"].append("逾時未取得本次回覆；不自動重試（原 prompt 可能已送出）")
        return 5, report
    finally:
        release_lock(lock)


def summarize(report, exit_code):
    lines = ["== freebuff 派工 =="]
    lines.append(f"terminal       : {report['terminal']}" + ("  ⚠ 與預期不同" if report.get("terminal_mismatch") else ""))
    lines.append(f"前景程序       : {report.get('foreground_process')}")
    lines.append(f"tab（動態取得） : {report['tab_id']}  ({report.get('tab_name')})")
    lines.append(f"pane           : {report['pane_id']}  原 active={report.get('tab_was_active')}")
    lines.append(f"chat store     : {report.get('chat_store')}")
    if report.get("dry_run"):
        lines.append("dry-run        : 前置檢查通過，未送任何按鍵")
    else:
        lines.append("送出方式       : herdr-core send（貼上＋Enter，未額外按 Enter）")
        lines.append(f"送出時間       : {report.get('sent_at')}")
        if report.get("reply") is not None:
            lines.append(f"回覆時間       : {report.get('reply_at')}（UI 標示 {report.get('completion_time')}）")
            lines.append(f"完成判定來源   : {report.get('completion_source')}")
            lines.append("--- 模型回覆（原文）---")
            lines.append(report["reply"])
            lines.append("-----------------------")
        elif exit_code == 5:
            lines.append("回覆           : 逾時未取得本次回覆（unverified，不重試）")
        else:
            lines.append(f"提交狀態       : {report.get('submitted')}")
    for warn in report.get("warnings") or []:
        lines.append(f"警告           : {warn}")
    lines.append(f"驗收           : {report.get('acceptance')}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="對 freebuff 派工：動態解析 terminal/tab → tab.select → pane.focus → herdr-core send"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="要送出的 prompt 文字")
    group.add_argument("--file", help="從檔案讀 prompt")
    group.add_argument("--dry-run", action="store_true", help="只檢查前置條件，不送任何按鍵")
    parser.add_argument("--terminal", help="指定 freebuff 終端（預設自動偵測；多個符合會拒絕）")
    parser.add_argument("--expected-terminal", default=DEFAULT_EXPECTED_TERMINAL,
                        help=f"預期終端，僅用於比對與警告（預設 {DEFAULT_EXPECTED_TERMINAL}）")
    parser.add_argument("--require-expected", action="store_true", help="終端與預期不符時直接失敗")
    parser.add_argument("--no-wait", action="store_true", help="送出後立刻返回，不等回覆")
    parser.add_argument("--timeout", type=int, default=180, help="等回覆的秒數（預設 180）")
    parser.add_argument("--dup-window", type=int, default=300, help="相同 prompt 的封鎖秒數（預設 300）")
    parser.add_argument("--lock-ttl", type=int, default=600, help="派工鎖的逾時秒數（預設 600）")
    parser.add_argument("--force", action="store_true", help="略過重複送出檢查")
    parser.add_argument("--task", default="", help="任務代號，寫進報告")
    parser.add_argument("--json", action="store_true", help="以 JSON 輸出")
    args = parser.parse_args()

    if args.file:
        try:
            args.text = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"讀取 {args.file} 失敗：{exc}", file=sys.stderr)
            return 2
    if not args.dry_run and not normalize(getattr(args, "text", "")):
        print("prompt 不可為空", file=sys.stderr)
        return 2

    try:
        exit_code, report = dispatch(args)
    except Fail as exc:
        if args.json:
            print(json.dumps({"error": exc.message, "exit_code": exc.code}, ensure_ascii=False, indent=2))
        else:
            print(f"失敗：{exc.message}")
        return exc.code

    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else summarize(report, exit_code))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
