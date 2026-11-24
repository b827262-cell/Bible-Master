#!/usr/bin/env python3
"""Checks for tools/freebuff_dispatch.py — fully mocked, never touches a real terminal.

Builds fake herdr-core / herdr-app executables plus a temporary freebuff chat store, so every
branch (discovery, ambiguity, idle check, submit, stale response, duplicate, lock, timeout,
transport failure) is exercised without consuming Freebuff quota.

Usage: python3 bible-site/tests/freebuff_dispatch_checks.py [--grep REGEX]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
TOOL = SITE_ROOT / "tools" / "freebuff_dispatch.py"
ONLY = None
results = []

FAKE = r'''#!/usr/bin/env python3
"""Fake herdr-core / herdr-app driven by world.json next to this file."""
import json, os, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.join(BASE, "world.json")
ROLE = os.path.basename(sys.argv[0])
args = sys.argv[1:]


def load():
    with open(WORLD) as fh:
        return json.load(fh)


def save(w):
    with open(WORLD, "w") as fh:
        json.dump(w, fh)


w = load()

if ROLE == "herdr-core":
    cmd = args[0] if args else ""
    if cmd == "ls":
        print(json.dumps({"terminals": [
            {"address": t["address"], "state": t.get("state", "live"), "agent": t.get("agent", "bash")}
            for t in w["terminals"]
        ]}))
    elif cmd == "get":
        addr = args[1]
        for t in w["terminals"]:
            if t["address"] == addr:
                print(json.dumps(t))
                sys.exit(0)
        print(json.dumps({"error": {"kind": "not_found"}}))
        sys.exit(1)
    elif cmd == "read":
        print(w.get("screen", ""))
    elif cmd == "send":
        addr, text = args[1], args[2]
        if w.get("send_rc", 0) != 0:
            print("send failed")
            sys.exit(w["send_rc"])
        if w.get("append_messages", True):
            now = int(time.time() * 1000)
            path = w["chat_file"]
            data = json.load(open(path)) if os.path.exists(path) else []
            data.append({"id": f"user-{now}", "variant": "user", "content": text, "blocks": []})
            data.append({
                "id": f"ai-{now + 5}-deadbeef", "variant": "ai", "content": "",
                "blocks": [{"type": "text", "content": w.get("reply", "OK")}],
                "isComplete": True, "completionTime": "2s",
            })
            with open(path, "w") as fh:
                json.dump(data, fh)
        print("sent at turn 0 (no status); it doesn't report status")
    else:
        print("{}")
        sys.exit(2)

elif ROLE == "herdr-app":
    cmd = args[0] if args else ""
    if cmd == "ls":
        tabs = []
        for tab in w["tabs"]:
            tabs.append({
                "id": tab["id"], "name": tab.get("name", "DOS Prompt"), "active": tab.get("active", False),
                "terminals": [{"terminal": tab["terminal"], "pane": tab["pane"], "app": None}],
            })
        print(json.dumps({"spaces": [{"id": "sp-fake", "name": "Fake", "active": True, "tabs": tabs}]}))
    elif cmd == "do":
        action = args[1]
        if action == "tab.select":
            tab_id = args[3]
            w["active_tab"] = tab_id
            for tab in w["tabs"]:
                tab["active"] = tab["id"] == tab_id
        elif action == "pane.focus":
            terminal = args[3]
            for tab in w["tabs"]:
                if tab["terminal"] == terminal:
                    w["focused_pane"] = tab["pane"]
        save(w)
        print(json.dumps({"ok": True}))
    elif cmd == "status":
        print(json.dumps({"focused_pane": w.get("focused_pane"), "tab": w.get("active_tab")}))
    else:
        print(json.dumps({"error": "unknown"}))
        sys.exit(2)
'''


def check(name, ok, detail=""):
    if ONLY and not re.search(ONLY, name):
        return
    results.append(ok)
    print(("通過" if ok else "不通過") + f"：{name}" + (f"（{detail}）" if detail else ""))


class Env:
    """One mocked world: fake binaries, chat store, state dir."""

    def __init__(self, root, freebuff_terminals=("t7",), extra_terminals=(), screen=None,
                 reply="OK", send_rc=0, append_messages=True, seed_chat=None):
        self.root = Path(root)
        self.bin = self.root / "bin"
        self.bin.mkdir(parents=True, exist_ok=True)
        self.chats = self.root / "chats"
        self.state = self.root / "state"
        self.state.mkdir(parents=True, exist_ok=True)
        for name in ("herdr-core", "herdr-app"):
            path = self.bin / name
            path.write_text(FAKE, encoding="utf-8")
            path.chmod(0o755)

        self.project = self.root / "project"
        self.session = self.project / "chats" / "2026-01-01T00-00-00.000Z"
        self.session.mkdir(parents=True, exist_ok=True)
        self.chat_file = self.session / "chat-messages.json"
        self.chat_file.write_text(json.dumps(seed_chat or []), encoding="utf-8")

        terminals = []
        for addr in freebuff_terminals:
            terminals.append({
                "address": addr, "state": "live", "agent": "bash",
                "foreground": {"argv": ["node", "/usr/local/bin/freebuff"], "name": "node"},
                "cwd": "/home/tester/Bible-Master",
            })
        for addr, argv in extra_terminals:
            terminals.append({
                "address": addr, "state": "live", "agent": "bash",
                "foreground": {"argv": argv, "name": argv[0]}, "cwd": "/home/tester/Bible-Master",
            })

        tabs = [{"id": f"tab-{t['address']}", "terminal": t["address"], "pane": f"pane-{t['address']}",
                 "name": "DOS Prompt", "active": False} for t in terminals]

        self.world = {
            "terminals": terminals,
            "tabs": tabs,
            "focused_pane": None,
            "active_tab": None,
            "screen": screen if screen is not None else "Enter a coding task or / for commands\n",
            "chat_file": str(self.chat_file),
            "reply": reply,
            "send_rc": send_rc,
            "append_messages": append_messages,
        }
        self.write_world()

    def write_world(self):
        (self.bin / "world.json").write_text(json.dumps(self.world), encoding="utf-8")

    def read_world(self):
        return json.loads((self.bin / "world.json").read_text(encoding="utf-8"))

    def env(self):
        e = dict(os.environ)
        e["HERDR_CORE_BIN"] = str(self.bin / "herdr-core")
        e["HERDR_APP_BIN"] = str(self.bin / "herdr-app")
        e["FREEBUFF_DISPATCH_CHAT_ROOT"] = str(self.chats)
        e["FREEBUFF_DISPATCH_STATE_DIR"] = str(self.state)
        return e

    def run(self, *args, timeout=60):
        # chat root must contain <project>/chats/... ; alias the seeded project name
        alias = self.chats / "Bible-Master"
        if not alias.exists():
            alias.parent.mkdir(parents=True, exist_ok=True)
            try:
                alias.symlink_to(self.project, target_is_directory=True)
            except OSError:
                shutil.copytree(self.project, alias)
        cmd = [sys.executable, str(TOOL), *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=self.env())

    def seed(self, messages):
        self.chat_file.write_text(json.dumps(messages), encoding="utf-8")


def scenario(name, fn):
    tmp = tempfile.mkdtemp(prefix="fbd-")
    try:
        ok, detail = fn(Path(tmp))
    except Exception as exc:  # noqa: BLE001 - a crashed scenario is a failed check
        ok, detail = False, f"例外：{exc!r}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check(name, ok, detail)


def discovery_ok(root):
    env = Env(root)
    proc = env.run("--dry-run", "--expected-terminal", "t7")
    out = proc.stdout
    return (proc.returncode == 0 and "tab-t7" in out and "pane-t7" in out, f"exit={proc.returncode}")


def ambiguity_rejected(root):
    env = Env(root, freebuff_terminals=("t7", "t9"))
    proc = env.run("--dry-run")
    return (proc.returncode == 2 and "多個 freebuff" in proc.stdout, f"exit={proc.returncode}")


def wrong_terminal_rejected(root):
    env = Env(root, extra_terminals=(("t8", ["/bin/bash"]),))
    proc = env.run("--terminal", "t8", "--dry-run")
    return (proc.returncode == 2 and "不是 freebuff" in proc.stdout, f"exit={proc.returncode}")


def missing_terminal_rejected(root):
    env = Env(root)
    proc = env.run("--terminal", "t8", "--dry-run")
    return (proc.returncode == 2, f"exit={proc.returncode}")


def idle_check_rejected(root):
    env = Env(root, screen="some draft text without the placeholder\n")
    proc = env.run("--dry-run", "--expected-terminal", "t7")
    return (proc.returncode == 2 and "輸入框不是空白" in proc.stdout, f"exit={proc.returncode}")


def busy_rejected(root):
    env = Env(root, screen="Enter a coding task or / for commands\nWorking...\n")
    proc = env.run("--dry-run", "--expected-terminal", "t7")
    return (proc.returncode == 2 and "工作中" in proc.stdout, f"exit={proc.returncode}")


def submit_ok(root):
    env = Env(root, reply="FREEBUFF_T8_OK")
    proc = env.run("--text", "Reply exactly FREEBUFF_T8_OK", "--timeout", "15",
                   "--expected-terminal", "t7", "--json")
    try:
        report = json.loads(proc.stdout)
    except ValueError:
        return False, f"非 JSON：{proc.stdout[:120]}"
    world = env.read_world()
    return (
        proc.returncode == 0
        and report["verified"] is True
        and report["submitted"] == "confirmed"
        and report["reply"] == "FREEBUFF_T8_OK"
        and report["tab_id"] == "tab-t7"
        and world["focused_pane"] == "pane-t7"
        and world["active_tab"] == "tab-t7",
        f"exit={proc.returncode} reply={report.get('reply')!r}",
    )


def stale_response_rejected(root):
    old = [
        {"id": "user-1000000000000", "variant": "user", "content": "Reply exactly FREEBUFF_T8_OK"},
        {"id": "ai-1000000000005-x", "variant": "ai", "isComplete": True,
         "blocks": [{"type": "text", "content": "STALE_OLD_REPLY"}]},
    ]
    env = Env(root, append_messages=False, seed_chat=old)
    proc = env.run("--text", "Reply exactly FREEBUFF_T8_OK", "--timeout", "4",
                   "--expected-terminal", "t7", "--json", timeout=60)
    report = json.loads(proc.stdout)
    return (
        proc.returncode == 5 and report["verified"] is False and report["reply"] is None,
        f"exit={proc.returncode} reply={report.get('reply')!r}",
    )


def duplicate_rejected(root):
    env = Env(root)
    first = env.run("--text", "same prompt", "--timeout", "15", "--expected-terminal", "t7")
    second = env.run("--text", "same prompt", "--timeout", "15", "--expected-terminal", "t7")
    return (first.returncode == 0 and second.returncode == 7, f"first={first.returncode} second={second.returncode}")


def concurrent_rejected(root):
    env = Env(root)
    (env.state / "dispatch.lock").write_text(json.dumps({
        "pid": os.getpid(), "terminal": "t7", "prompt_sha256": "x", "started_at": time.time(),
    }))
    proc = env.run("--text", "hello", "--timeout", "10", "--expected-terminal", "t7")
    return (proc.returncode == 6 and "已有派工進行中" in proc.stdout, f"exit={proc.returncode}")


def stale_lock_taken_over(root):
    env = Env(root)
    (env.state / "dispatch.lock").write_text(json.dumps({
        "pid": 999999, "terminal": "t7", "prompt_sha256": "x", "started_at": time.time() - 7200,
    }))
    proc = env.run("--text", "hello", "--timeout", "15", "--expected-terminal", "t7")
    return (proc.returncode == 0, f"exit={proc.returncode}")


def transport_failure(root):
    env = Env(root, send_rc=1)
    proc = env.run("--text", "hello", "--timeout", "10", "--expected-terminal", "t7")
    return (proc.returncode == 2 and "send 失敗" in proc.stdout, f"exit={proc.returncode}")


def timeout_unverified(root):
    env = Env(root, append_messages=False)
    proc = env.run("--text", "hello", "--timeout", "4", "--expected-terminal", "t7", "--json", timeout=60)
    report = json.loads(proc.stdout)
    return (proc.returncode == 5 and report["submitted"] == "unverified" and report["verified"] is False,
            f"exit={proc.returncode}")


def no_wait_path(root):
    env = Env(root)
    proc = env.run("--text", "hello", "--no-wait", "--expected-terminal", "t7", "--json")
    report = json.loads(proc.stdout)
    return (proc.returncode == 0 and report["submitted"] == "unverified" and report["verified"] is False,
            f"exit={proc.returncode}")


def require_expected_fails(root):
    env = Env(root)
    proc = env.run("--dry-run", "--expected-terminal", "t8", "--require-expected")
    return (proc.returncode == 2 and "要求中止" in proc.stdout, f"exit={proc.returncode}")


def default_dry_run_t7(root):
    """第 16 項：預設參數 --dry-run --json 應回報 expected_terminal=t7 且無不符。"""
    env = Env(root)
    proc = env.run("--dry-run", "--json")
    try:
        report = json.loads(proc.stdout)
    except ValueError:
        return False, f"非 JSON：{proc.stdout[:120]}"
    return (
        proc.returncode == 0
        and report.get("terminal") == "t7"
        and report.get("expected_terminal") == "t7"
        and report.get("terminal_mismatch") is False,
        f"exit={proc.returncode} expected={report.get('expected_terminal')!r} "
        f"mismatch={report.get('terminal_mismatch')!r}",
    )


def main():
    global ONLY
    if "--grep" in sys.argv:
        ONLY = sys.argv[sys.argv.index("--grep") + 1]

    scenario("探索：單一 freebuff 終端可解析出 tab 與 pane", discovery_ok)
    scenario("探索：多個 freebuff 終端視為 ambiguous 並拒絕", ambiguity_rejected)
    scenario("探索：--terminal 指到非 freebuff 終端會被拒", wrong_terminal_rejected)
    scenario("探索：--terminal 指到不存在的終端會被拒", missing_terminal_rejected)
    scenario("前置：輸入框非空白時拒絕送出", idle_check_rejected)
    scenario("前置：偵測到工作中字樣時拒絕送出", busy_rejected)
    scenario("派工：送出後以 chat store 驗證完成並回報原文", submit_ok)
    scenario("驗證：舊回覆不得當成本次結果", stale_response_rejected)
    scenario("防護：相同 prompt 在窗口內被拒", duplicate_rejected)
    scenario("防護：已有派工鎖時拒絕（併發）", concurrent_rejected)
    scenario("防護：逾時且 pid 已死的鎖可接管", stale_lock_taken_over)
    scenario("失敗：herdr-core send 失敗時回 exit 2", transport_failure)
    scenario("失敗：等不到回覆時回 unverified 且不重試", timeout_unverified)
    scenario("模式：--no-wait 只回報已送出未驗證", no_wait_path)
    scenario("模式：--require-expected 不符時中止", require_expected_fails)
    scenario("預設：預設參數 dry-run 對 t7 回報 expected_terminal=t7 且無不符", default_dry_run_t7)

    if not results:
        print("沒有執行任何檢查")
        return 2
    passed = sum(1 for r in results if r)
    print(f"\n總結：{passed}/{len(results)} 項檢查通過")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
