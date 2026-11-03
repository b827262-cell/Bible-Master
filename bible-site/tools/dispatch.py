#!/usr/bin/env python3
"""Dispatch tasks to the local models through Harness headless mode, then verify the result with scripts.

  python3 bible-site/tools/dispatch.py health                 E500 / A16 / De1050 and the dsh binary
  python3 bible-site/tools/dispatch.py gen-patches            write headless overlays from the web profile's provider blocks
  python3 bible-site/tools/dispatch.py smoke [role ...]       tiny write task per role (proves model, tools, sandbox)
  python3 bible-site/tools/dispatch.py run tasks/*.md         run task files (--dry-run to only print, --allow-cloud is reserved)
  python3 bible-site/tools/dispatch.py status                 latest result per task

A task file is YAML front matter + the prompt text:
  ---
  role: e500                       # who does it first
  files: [bible-site/site/chapter.html]   # the only files the model may change
  depends: [10-app-js]             # task ids (file stem) that must have passed
  checks:                          # shell commands run from the project root; all must exit 0
    - python3 bible-site/tools/check_all.py
  ---
  prompt text ...

A role with `runner: cmd` (Command Code CLI) or `runner: codebuddy` (CodeBuddy CLI) runs that CLI in print mode instead of dsh.

Flow per task: health -> snapshot file hashes -> `dsh --profile headless --patch <overlay> --json -` (timeout) ->
scope check (only `files` changed) -> checks -> pass | retry once on the same role with the failure text | escalate to the
role's escalate_to (a local role) | needs-cloud (never calls the cloud model itself).
Results are appended to DISPATCH-REPORT.md and PROGRESS.md; raw event logs go to logs/dispatch/. Standard library + PyYAML."""
import argparse, concurrent.futures as cf, datetime, glob, hashlib, json, os, re, signal, subprocess, sys, threading, time, urllib.request

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.path.abspath(os.path.join(HERE, ".."))            # bible-site/
ROOT = os.path.abspath(os.path.join(SITE_ROOT, ".."))             # project root (cwd for dsh and checks)
CFG = yaml.safe_load(open(os.path.join(HERE, "dispatch", "roles.yml"), encoding="utf-8"))
ROLES = CFG["roles"]
DSH = os.path.expanduser(CFG["dsh_bin"])
WEB_PATCH = os.path.expanduser(CFG["web_patch"])
GEN = os.path.join(HERE, "dispatch", "generated")
LOGS = os.path.join(SITE_ROOT, "logs", "dispatch")
STATE = os.path.join(LOGS, "state.json")
REPORT = os.path.join(SITE_ROOT, "DISPATCH-REPORT.md")
IGNORE = CFG.get("ignore_changes", [])
STATE_LOCK = threading.Lock()
ROLE_LOCKS = {name: threading.Lock() for name in ROLES}           # one task per machine at a time
RUNNING = {}                                                      # task id -> files it may change (tasks running right now)
OVERLAP = {}                                                      # task id -> files of tasks that ran at the same time
RUN_LOCK = threading.Lock()


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- overlays
def provider_block(key):
    """Text of `      <key>:` and its body in the web patch (indent 6), copied verbatim."""
    out, grab = [], False
    for line in open(WEB_PATCH, encoding="utf-8").read().splitlines():
        if re.match(r"^      " + re.escape(key) + r":\s*$", line):
            grab = True
        elif grab and (re.match(r"^      \S", line) or re.match(r"^\S", line)):
            break
        if grab:
            out.append(line)
    if not out:
        raise SystemExit(f"找不到 provider {key}（{WEB_PATCH}）")
    return "\n".join(out)


def overlay_text(role):
    r = ROLES[role]
    eff = f"\n    reasoningEffort: {r['reasoning']}" if "reasoning" in r else ""
    if r.get("builtin"):                              # provider ships as its own dsh plugin (cloud), nothing to copy
        return (f"- id: agent-default-model\n  name: \"@deepseek-ai/dsh-agent-default-model\"\n  config:\n"
                f"    provider: {r['provider']}\n    model: {r['model']}{eff}\n")
    return (f"- id: llm-pi-ai\n  name: \"@deepseek-ai/dsh-llm-pi-ai\"\n  disabled: false   # the headless profile ships it disabled\n"
            f"  config:\n    providers:\n{provider_block(r['provider'])}\n"
            f"- id: agent-default-model\n  name: \"@deepseek-ai/dsh-agent-default-model\"\n  config:\n"
            f"    provider: {r['provider']}\n    model: {r['model']}{eff}\n")


def gen_patches():
    os.makedirs(GEN, exist_ok=True)
    for role, r in ROLES.items():
        if r.get("manual") or r.get("runner"):
            continue
        p = os.path.join(GEN, role + ".patch.yml")
        open(p, "w", encoding="utf-8").write(overlay_text(role))
        print(f"  {role}: {os.path.relpath(p, ROOT)}")


def overlay_path(role):
    p = os.path.join(GEN, role + ".patch.yml")
    if not os.path.exists(p):
        gen_patches()
    return p


# ---------------------------------------------------------------- health
def up(url, timeout=4):
    if not url:                                       # cloud roles have no local health endpoint
        return True
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def health():
    ok = True
    print(f"[{'OK' if os.access(DSH, os.X_OK) else 'FAIL'}] dsh: {DSH}")
    ok &= os.access(DSH, os.X_OK)
    for role, r in ROLES.items():
        if r.get("manual"):
            print(f"[--] {role}: 手動（不由腳本呼叫）")
            continue
        good = up(r.get("health"))
        ok &= good
        print(f"[{'OK' if good else 'FAIL'}] {role}: {r.get('health') or r.get('runner') or r['provider']}  ({r['model'].split('/')[-1]})")
    return ok


# ---------------------------------------------------------------- state / report
def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def save_result(task_id, result):
    os.makedirs(LOGS, exist_ok=True)
    with STATE_LOCK:
        st = load_state()
        st[task_id] = result
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def write_report(task, result):
    lines = [f"\n## {now()}　{task['id']}　{result['status']}", "",
             f"- 角色：{' → '.join(a['role'] for a in result['attempts'])}；檔案：{', '.join(task['files']) or '（無）'}"]
    for i, a in enumerate(result["attempts"], 1):
        lines.append(f"- 第 {i} 次（{a['role']}）：{a['verdict']}；耗時 {a['seconds']} 秒；輸入 token {a.get('input_tokens', '?')}；"
                     f"工具呼叫 {a.get('tool_calls', '?')} 次；改動 {', '.join(a['changed']) or '無'}")
        if a.get("out_of_scope"):
            lines.append(f"  - **超出範圍的改動**：{', '.join(a['out_of_scope'])}")
        for c in a.get("checks", []):
            lines.append(f"  - 檢查 `{c['cmd']}` → {'通過' if c['ok'] else '不通過'}")
        if a.get("error"):
            lines.append(f"  - 錯誤：{a['error']}")
        if a.get("final"):
            lines.append(f"  - 模型回報：{a['final'][:200]}")
    open(REPORT, "a", encoding="utf-8").write("\n".join(lines) + "\n")
    with open(os.path.join(SITE_ROOT, "PROGRESS.md"), "a", encoding="utf-8") as f:
        f.write(f"- {now()[:16]}　dispatch：{task['id']} {result['status']}（{' → '.join(a['role'] for a in result['attempts'])}）。\n")


# ---------------------------------------------------------------- snapshots
def ignored(rel):
    return any(rel.startswith(i) or i in rel for i in IGNORE)


def snapshot():
    # bible-site/ recursively plus the regular files at the project root (start.sh); symlinks are skipped so an
    # edit to start.sh is not also reported through its bible-site/start.sh link
    snap = {}
    paths = [os.path.join(ROOT, f) for f in os.listdir(ROOT)]
    for dp, dn, fs in os.walk(SITE_ROOT):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
        paths += [os.path.join(dp, f) for f in fs]
    for p in paths:
        rel = os.path.relpath(p, ROOT)
        if os.path.isfile(p) and not os.path.islink(p) and not ignored(rel):
            snap[rel] = hashlib.sha1(open(p, "rb").read()).hexdigest()
    return snap


def changed_files(before, after):
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


# ---------------------------------------------------------------- running dsh
def run_dsh(role, prompt, timeout_min, log_path):
    """Returns dict(final, error, input_tokens, tool_calls, timed_out, seconds)."""
    cmd = [DSH, "--profile", "headless", "--patch", overlay_path(role), "--json", "-"]
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", start_new_session=True)
    timed_out = False
    try:
        out, err = proc.communicate(prompt, timeout=timeout_min * 60)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    open(log_path, "w", encoding="utf-8").write(out or "")
    info = {"final": "", "error": "", "input_tokens": 0, "tool_calls": 0, "timed_out": timed_out, "seconds": int(time.time() - t0)}
    for line in (out or "").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") == "final":
            info["final"] = e.get("text", "")
        elif e.get("type") == "tool_call":
            info["tool_calls"] += 1
        elif e.get("type") == "status":
            reason = e.get("reason") or {}
            if reason.get("kind") == "error":
                info["error"] = reason["error"].get("message", "error")
            info["input_tokens"] += (e.get("usage") or {}).get("inputTokens", 0)
    if timed_out:
        info["error"] = f"逾時（{timeout_min} 分鐘），已終止"
    elif proc.returncode not in (0, None) and not info["error"]:
        info["error"] = f"dsh 結束代碼 {proc.returncode}：{(err or '').strip()[-300:]}"
    return info


def cli_command(role, prompt):
    r = ROLES[role]
    if r["runner"] == "cmd":
        return ["cmd", "--no-auto-update", "--skip-onboarding", "--trust", "--no-session", "--yolo",
                "-m", r["model"], "--output-format", "json", "-p", prompt]
    if r["runner"] == "codebuddy":
        return ["codebuddy", "--permission-mode", "acceptEdits", "--model", r["model"],
                "--output-format", "stream-json", "-p", prompt]
    if r["runner"] == "agy":                                           # file edits auto-approved, nothing broader
        return ["agy", "--model", r["model"], "--effort", r.get("effort", "high"), "--mode", "accept-edits",
                "--output-format", "stream-json", "--print-timeout", f"{r['timeout_min']}m", "-p", prompt]
    if r["runner"] == "qoder":
        cmd = ["qodercli", "-m", r["model"], "--permission-mode", "accept_edits", "--no-session-persistence",
               "-w", ROOT, "-o", "stream-json"]
        for tool in r.get("allowed_tools", []):                        # e.g. the bailian-image MCP tool for image tasks
            cmd += ["--allowed-tools", tool]
        return cmd + ["-p", prompt]
    raise SystemExit(f"不認得的 runner：{r['runner']}（{role}）")


def run_cli(role, prompt, timeout_min, log_path):
    """Same contract as run_dsh, for roles that run an agent CLI in print mode."""
    t0 = time.time()
    proc = subprocess.Popen(cli_command(role, prompt), cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", start_new_session=True)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout_min * 60)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    open(log_path, "w", encoding="utf-8").write(out or "")
    info = {"final": "", "error": "", "input_tokens": 0, "tool_calls": 0, "timed_out": timed_out, "seconds": int(time.time() - t0)}
    for line in (out or "").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict):
            continue
        if e.get("event") == "result":                                 # agy
            res = e.get("result") or {}
            info["final"] = res.get("response") or ""
            info["input_tokens"] = (res.get("usage") or {}).get("input_tokens") or 0
            if res.get("status") != "SUCCESS":
                info["error"] = str(res.get("status") or "error")
        elif e.get("event") == "step_update":
            step = e.get("step_update") or {}
            info["tool_calls"] += 1 if step.get("tool_name") and "duration_seconds" in step else 0
        elif e.get("type") == "result":                                 # cmd / codebuddy / qoder end with one result line
            usage = e.get("usage") or {}
            info["final"] = e.get("finalText") or e.get("result") or ""
            info["input_tokens"] = usage.get("inputTokens") or usage.get("input_tokens") or 0
            if e.get("subtype") not in (None, "success") or e.get("is_error"):
                info["error"] = str(e.get("subtype") or "error")
        elif e.get("type") == "event" and (e.get("event") or {}).get("type") == "tool_completed":
            info["tool_calls"] += 1
        elif e.get("type") == "assistant":
            content = (e.get("message") or {}).get("content") or []
            info["tool_calls"] += sum(1 for c in content if isinstance(c, dict) and c.get("type") == "tool_use")
    if timed_out:
        info["error"] = f"逾時（{timeout_min} 分鐘），已終止"
    elif proc.returncode not in (0, None) and not info["error"]:
        info["error"] = f"{ROLES[role]['runner']} 結束代碼 {proc.returncode}：{(err or '').strip()[-300:]}"
    return info


# ---------------------------------------------------------------- tasks
def load_task(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"{path}: 缺少 front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    return {"id": os.path.splitext(os.path.basename(path))[0], "role": meta["role"], "files": meta.get("files", []),
            "depends": meta.get("depends", []), "checks": meta.get("checks", []), "body": m.group(2).strip()}


def build_prompt(task, role, failure=None):
    files = "、".join(task["files"]) or "（不修改任何檔案）"
    p = task["body"] + f"\n\n【範圍】只准修改這些檔案：{files}。不要修改、也不要建立其他檔案。完成後只回報你修改了哪些檔案。"
    if failure:
        p += "\n\n【上一次的結果沒有通過】請只針對下面的問題修正：\n" + failure
    return p


def run_checks(cmds):
    out = []
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=300)
            out.append({"cmd": cmd, "ok": r.returncode == 0, "output": (r.stdout + r.stderr).strip()[-1500:]})
        except subprocess.TimeoutExpired:
            out.append({"cmd": cmd, "ok": False, "output": "檢查逾時（300 秒）"})
    return out


def attempt(task, role, failure, dry):
    r = ROLES[role]
    prompt = build_prompt(task, role, failure)
    if dry:
        print(f"--- {task['id']} → {role}\n{prompt}\n")
        return {"role": role, "verdict": "dry-run", "seconds": 0, "changed": [], "checks": []}, True
    if not up(r.get("health")):
        return {"role": role, "verdict": "機器沒有回應", "seconds": 0, "changed": [], "checks": [], "error": f"{r['health']} 沒有回應"}, False
    with ROLE_LOCKS[role]:
        with RUN_LOCK:
            OVERLAP[task["id"]] = set().union(*RUNNING.values()) if RUNNING else set()
            for tid, fs in RUNNING.items():
                OVERLAP[tid] = OVERLAP.get(tid, set()) | set(task["files"])
            RUNNING[task["id"]] = set(task["files"])
        before = snapshot()
        log = os.path.join(LOGS, f"{task['id']}-{role}-{datetime.datetime.now():%H%M%S}.jsonl")
        info = (run_cli if r.get("runner") else run_dsh)(role, prompt, r["timeout_min"], log)
        after = snapshot()
        with RUN_LOCK:
            RUNNING.pop(task["id"], None)
            others = set(OVERLAP.get(task["id"], set()))                   # files owned by tasks that ran in parallel
    changed = changed_files(before, after)
    out_scope = [c for c in changed if c not in task["files"] and c not in others]
    a = {"role": role, "seconds": info["seconds"], "input_tokens": info["input_tokens"], "tool_calls": info["tool_calls"],
         "changed": changed, "out_of_scope": out_scope, "final": info["final"], "error": info["error"], "checks": []}
    if info["error"]:
        a["verdict"] = "模型執行失敗"
        return a, False
    if len(task["files"]) > r.get("max_files", 99):
        a["error"] = f"任務檔列了 {len(task['files'])} 個檔案，超過 {role} 的上限 {r['max_files']}"
    if out_scope:
        a["verdict"] = "改到範圍外的檔案"
        return a, False
    if not changed and task["files"]:
        a["verdict"] = "沒有改任何檔案"
        return a, False
    a["checks"] = run_checks(task["checks"])
    ok = all(c["ok"] for c in a["checks"])
    a["verdict"] = "通過" if ok else "檢查不通過"
    return a, ok


def failure_text(a):
    parts = []
    if a.get("error"):
        parts.append("錯誤：" + a["error"])
    if a.get("out_of_scope"):
        parts.append("你改到了不該改的檔案：" + "、".join(a["out_of_scope"]) + "（請只改指定的檔案）")
    if a["verdict"] == "沒有改任何檔案":
        parts.append("你沒有修改任何檔案，請用寫檔或編輯工具實際修改。")
    for c in a.get("checks", []):
        if not c["ok"]:
            parts.append(f"檢查 `{c['cmd']}` 不通過，輸出：\n{c['output']}")
    return "\n".join(parts)[:3000]


def run_task(task, dry=False):
    attempts, role, tries, failure, status = [], task["role"], 0, None, "失敗"
    visited = set()
    while True:
        a, ok = attempt(task, role, failure, dry)
        attempts.append(a)
        if dry:
            return {"status": "dry-run", "attempts": attempts}
        if ok:
            status = "通過"
            break
        failure = failure_text(a)
        tries += 1
        if tries < 2 and a["verdict"] != "機器沒有回應":
            continue                                  # one retry on the same role, with the failure text
        visited.add(role)
        nxt = ROLES[role].get("escalate_to")
        if not nxt or nxt in visited:
            break
        if ROLES[nxt].get("manual"):
            status = "需要雲端（貓聽）"
            break
        role, tries = nxt, 0                          # escalate to the next local role
    result = {"status": status, "at": now(), "attempts": attempts}
    save_result(task["id"], result)
    write_report(task, result)
    return result


def run_many(paths, dry):
    tasks = [load_task(p) for p in paths]
    by_id = {t["id"]: t for t in tasks}
    results, running = {}, {}                          # id -> status | id -> future
    st = load_state()
    pending = list(tasks)
    with cf.ThreadPoolExecutor(max_workers=max(1, len(ROLES))) as pool:
        while pending or running:
            for tid, fut in list(running.items()):
                if fut.done():
                    results[tid] = fut.result()["status"]
                    print(f"[{now()[11:]}] {tid}: {results[tid]}")
                    del running[tid]
            busy_roles = {by_id[t]["role"] for t in running}
            busy_files = {f for t in running for f in by_id[t]["files"]}
            for t in list(pending):
                deps_ok = all(results.get(d) in ("通過", "dry-run") or (d not in by_id and st.get(d, {}).get("status") == "通過") for d in t["depends"])
                dep_bad = any(results.get(d) not in (None, "通過", "dry-run") for d in t["depends"])
                if dep_bad:
                    results[t["id"]] = "跳過（依賴未通過）"
                    print(f"[{now()[11:]}] {t['id']}: 跳過（依賴未通過）")
                    pending.remove(t)
                elif deps_ok and t["role"] not in busy_roles and not (set(t["files"]) & busy_files):
                    print(f"[{now()[11:]}] 開始 {t['id']} → {t['role']}")
                    running[t["id"]] = pool.submit(run_task, t, dry)
                    busy_roles.add(t["role"])
                    busy_files |= set(t["files"])
                    pending.remove(t)
            time.sleep(1)
    return results


def status():
    st = load_state()
    for tid, r in sorted(st.items()):
        print(f"{tid:28} {r['status']:14} {r.get('at', '')}  {' → '.join(a['role'] for a in r['attempts'])}")
    if not st:
        print("還沒有任何紀錄")


def smoke(roles):
    ok_all = True
    for role in roles or [r for r, v in ROLES.items() if not v.get("manual")]:
        rel = f"bible-site/tmp-dispatch-smoke-{role}.txt"
        task = {"id": f"smoke-{role}", "role": role, "files": [rel], "depends": [], "checks": [f"grep -q ok {rel}"],
                "body": f"在 {rel} 寫入一行文字 ok。"}
        a, ok = attempt(task, role, None, False)
        if os.path.exists(os.path.join(ROOT, rel)):
            os.remove(os.path.join(ROOT, rel))
        ok_all &= ok
        print(f"[{'OK' if ok else 'FAIL'}] {role}: {a['verdict']}；{a['seconds']} 秒；輸入 {a.get('input_tokens')} token；工具 {a.get('tool_calls')} 次"
              + (f"；{a['error']}" if a.get("error") else ""))
    return ok_all


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["health", "gen-patches", "smoke", "run", "status"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-cloud", action="store_true", help="reserved: cloud escalation is manual in this version")
    a = ap.parse_args()
    if a.cmd == "health":
        sys.exit(0 if health() else 1)
    elif a.cmd == "gen-patches":
        gen_patches()
    elif a.cmd == "smoke":
        sys.exit(0 if smoke(a.args) else 1)
    elif a.cmd == "status":
        status()
    else:
        files = sorted(p for g in a.args for p in glob.glob(g))
        if not files:
            sys.exit("沒有符合的任務檔")
        res = run_many(files, a.dry_run)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        sys.exit(0 if all(v in ("通過", "dry-run") for v in res.values()) else 1)
