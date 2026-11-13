#!/usr/bin/env python3
"""派工給 Herdr pane 裡的 coding agent —— 團隊編制的 tools/dispatch.py。

  bible-site/tools/herdr_team.py status [--workspace w2]        各 pane 的 agent／狀態／角色／最後任務結果
  bible-site/tools/herdr_team.py prompt w2:p3 '文字' [--wait]    直接對一個 pane（或角色）送 prompt
  bible-site/tools/herdr_team.py run tasks/*.md [--dry-run]      依任務檔平行派工、驗範圍、跑 checks、失敗重試一次
                                                                run 另有 --ignore <路徑片段>（可重複）給範圍檢查多擋掉
                                                                別的 agent 在同一棵樹上動出來的檔案

任務檔＝YAML front matter＋prompt 正文；相比 dispatch.py，這裡多接受 `pane:`（直接指定 pane_id）：
  ---
  pane: w2:p3                            # 或 role: e500（兩者都給時以 pane 為準）
  role: e500                             # codex/cbr/review · pi/a16 · opencode/e500/pm/backend · qwen/fe/ui · kilo/de1050/qa · agy/image
  files: [bible-site/admin/admin.js]     # 該 agent 唯一准改的檔案，也是「檔案不重疊才平行」的依據
  depends: [108-admin-server-zone-art]   # 必須已通過的任務 id（檔名主檔）
  checks:                                # 從專案根執行，全部 exit 0 才算通過
    - node --check bible-site/admin/admin.js
  timeout_min: 30                        # 選填，等這個 pane 做完的上限（預設 30）
  ---
  任務說明 ...

與 dispatch.py 的差別：不啟動模型、不組 overlay —— 派工對象是已經開在 Herdr pane 裡的互動 agent。
借鏡 dispatch-herdr.sh：只送「短指令＋任務檔絕對路徑」，長文一律改走檔案，避免撞到終端 canonical line 上限。

每個任務的流程：解析 → 依 depends 與檔案不重疊派給對應 pane → 看 pane 狀態（blocked 就不送並回報）→
送 prompt → 等它回到 idle/done → snapshot 比對（改到 files 以外就判失敗）→ 跑 checks →
不通過時把錯誤寫成檔案、連同任務檔一起請它只修這些問題，重試一次 →
結果記錄到 bible-site/logs/herdr-dispatch/（state.json＋每次的 transcript），並追加到 bible-site/DISPATCH-REPORT.md。

這支腳本本身只寫上面那兩個路徑；它不 commit、不 push、不部署。需要用到的只有標準函式庫＋PyYAML。
herdr 的 `agent wait` 逾時時離開碼仍是 0，差別在 JSON 裡的 error.code，所以狀態一律從 JSON 讀。
已知手動 pane：w2:p4 是 CodeBuddy（Herdr 尚未識別 agent），w2:p8 是 Claude（總PM，負責統籌與發佈）。
w2:p4 不加 `pane run` 自動派工分支：Herdr pane list 的 agent 為空、agent_status 恆為 unknown，
無法透過 `herdr agent wait` 偵測完成或 blocked 審批狀態；在互動式 TUI 派工也有競態風險，因此維持手動派發。
實作上 MANUAL_PANES 就是這條結論的落點：`run` 遇到表裡的 pane 直接回報「這個 pane 只手動派發」（不送 prompt、不重試），
`prompt` 仍允許人工指定但會先提醒無法可靠判斷完成；`status` 則顯示這段說明而不是一句「不在團隊映射」。
離開碼：0 全部通過／1 有任務未通過／2 前置檢查失敗（找不到 herdr、任務檔或 pane）／3 目標 pane 卡在 blocked／4 等待逾時。
"""
import argparse, concurrent.futures as cf, datetime, glob, hashlib, json, os, re, shutil, subprocess, sys, threading, time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.path.abspath(os.path.join(HERE, ".."))              # bible-site/
ROOT = os.path.abspath(os.path.join(SITE_ROOT, ".."))              # 專案根（checks 與 snapshot 的基準）
LOGS = os.path.join(SITE_ROOT, "logs", "herdr-dispatch")
STATE = os.path.join(LOGS, "state.json")
REPORT = os.path.join(SITE_ROOT, "DISPATCH-REPORT.md")
HERDR = os.environ.get("HERDR_BIN", "herdr")
DEFAULT_TIMEOUT_MIN = 30                                            # 任務檔沒寫 timeout_min 時
PROMPT_INLINE_MAX = 1500                                            # 超過就改送檔案路徑
ACTIVITY_WINDOW_S = 30                                              # 送出後多久沒看到任何狀態變化就判「沒開始」
MIN_POLL_S = 0.5                                                    # herdr 立刻回傳時的最短輪詢間隔（別把 CLI 打爆）

# ---------------------------------------------------------------- 團隊編制
TEAM = [
    {"pane": "w2:p1", "duty": "架構與最終審查", "roles": ["codex", "cbr", "review"]},
    {"pane": "w2:p2", "duty": "地端快速單檔開發", "roles": ["pi", "a16"]},
    {"pane": "w2:p3", "duty": "主力全端／後端開發", "roles": ["opencode", "e500", "pm", "backend"]},
    {"pane": "w2:p5", "duty": "前端 HTML/CSS/JS 主力", "roles": ["qwen", "fe", "ui"]},
    {"pane": "w2:p6", "duty": "PM 調度／前端與生圖", "roles": ["agy", "image"]},
    {"pane": "w2:p7", "duty": "腳本管理員與測試執行", "roles": ["kilo", "de1050", "qa"]},
]
ROLE_TO_PANE = {r: m["pane"] for m in TEAM for r in m["roles"]}
PANE_DUTY = {m["pane"]: m["duty"] for m in TEAM}
PANE_ROLES = {m["pane"]: m["roles"] for m in TEAM}

# 範圍檢查時忽略的檔案：本腳自己寫的報告、執行期日誌與快取，以及這台機器上別的進程常動到的東西
IGNORE = ["bible-site/logs/", "bible-site/.verify/", "bible-site/output/", "bible-site/design/", "output/", "__pycache__/", ".git/", "node_modules/"]
IGNORE_FILES = {"bible-site/DISPATCH-REPORT.md", "bible-site/PROGRESS.md", "bible-site/admin/.token", "bible-site/TEST-REPORT.md", "bible-site/FAILS.md"}
EXTRA_IGNORE = set()                                                # run --ignore 加進來的（同一棵樹上有別的 agent 時很有用）

MANUAL_PANES = {
    "w2:p4": "CodeBuddy（Herdr 未識別 agent，手動派發）",
    "w2:p8": "Claude（總PM，負責統籌與發佈）"
}

STATE_LOCK = threading.Lock()
RUN_LOCK = threading.Lock()
RUNNING = {}                                                        # 任務 id -> 該任務准改的檔案（算「同時在跑」用）
PANE_LOCKS = {m["pane"]: threading.Lock() for m in TEAM}
WARNED_DEPS = set()                                                 # 同一批任務裡提醒過的「依賴查無紀錄」

def running_others(exclude_id):
    """目前其他任務准改的檔案：它們在同樣的時間窗裡被改，不算這個任務越界。"""
    with RUN_LOCK:
        return set().union(*(v for k, v in RUNNING.items() if k != exclude_id)) if RUNNING else set()

def pane_lock(pane):
    with RUN_LOCK:
        if pane not in PANE_LOCKS:
            PANE_LOCKS[pane] = threading.Lock()
        return PANE_LOCKS[pane]

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(*lines):
    try:
        print(*lines, flush=True)
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except BrokenPipeError:
            pass
        raise SystemExit(0)


# ---------------------------------------------------------------- herdr 呼叫
def herdr_call(args, timeout=60):
    if not shutil.which(HERDR):
        raise SystemExit(f"找不到 herdr（{HERDR}）；請確認 PATH 或設定 HERDR_BIN")
    try:
        p = subprocess.run([HERDR] + list(args), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=ROOT)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"herdr {' '.join(args[:2])} 逾時（{timeout} 秒）"


def parse_json(text):
    for line in (text or "").splitlines():
        s = line.strip()
        if s.startswith("{"):
            try:
                return json.loads(s)
            except Exception:
                return None
    return None


def herdr_out(args, timeout=60):
    """回傳 (data, rc, err)。data 為 herdr 的 JSON（含 error 時 data['error'] 有 code/message）。"""
    rc, out, err = herdr_call(args, timeout)
    return parse_json(out), rc, err


def agent_get(pane):
    data, _, _ = herdr_out(["agent", "get", pane])
    return ((data or {}).get("result") or {}).get("agent") or {}


def pane_list(workspace):
    data, rc, err = herdr_out(["pane", "list", "--workspace", workspace])
    if data is None:
        raise SystemExit(f"herdr pane list --workspace {workspace} 失敗：{(err or '').strip()[-200:] or '沒有 JSON 輸出'}"
                         f"（herdr 可能沒在跑：herdr status）")
    if data.get("error"):
        raise SystemExit(f"herdr pane list 回報：{data['error']}")
    return ((data.get("result") or {}).get("panes")) or []


def pane_read(pane, lines=40):
    _, out, err = herdr_call(["pane", "read", pane, "--source", "recent-unwrapped", "--lines", str(lines)])
    return (out or err or "").rstrip()


# ---------------------------------------------------------------- 目標解析與狀態
def roles_for_pane(pane):
    return PANE_ROLES.get(pane, [])


def resolve(target):
    """pane_id（w2:p3，也允許只寫 p3）或角色名 → pane_id。"""
    t = str(target).strip().lower().replace(" ", "")
    ws = os.environ.get("HERDR_DEFAULT_WORKSPACE", "w2")
    if re.fullmatch(r"w\d+:p\d+", t):
        return t
    if re.fullmatch(r"p\d+", t):
        return ws + ":" + t
    if t in ROLE_TO_PANE:
        return ROLE_TO_PANE[t]
    raise SystemExit(f"不認得的目標：{target}（可以用 pane_id 如 w2:p3，或角色：" + "、".join(sorted(ROLE_TO_PANE)) + "）")


def last_result(pane):
    rows = [v for v in load_state().values() if v.get("pane") == pane]
    if not rows:
        return "（本腳本尚未派工過）"
    v = max(rows, key=lambda r: r.get("at", ""))
    return f"{v.get('task', '?')} → {v.get('status', '?')}（{v.get('at', '')[:16]}）"


def cmd_status(workspace):
    panes = pane_list(workspace)
    if not panes:
        log(f"workspace {workspace} 裡沒有任何 pane")
        return 0
    log(f"workspace {workspace}｜herdr 派工團隊 pane 狀態")
    for p in sorted(panes, key=lambda x: x.get("pane_id") or ""):
        pid = p.get("pane_id", "?")
        roles = "、".join(roles_for_pane(pid))
        agent, state = p.get("agent") or "-", p.get("agent_status") or "-"
        duty = PANE_DUTY.get(pid, "")
        flag = ""
        if pid in MANUAL_PANES:
            flag = f"｜{MANUAL_PANES[pid]}"
        elif not roles:
            flag = "｜不在團隊映射（如需派工請先加進 TEAM 或 MANUAL_PANES）"
        log(f"  {pid}  agent={agent:10} status={state:8} 角色={roles or '-':26} 職務={duty or '-':20} "
            f"最後={last_result(pid)}{flag}")
        if state == "blocked":
            log(f"       ⚠ {pid} 卡在審批／提問，需要人工處理才能再派工")
    log("提示：herdr pane read <pane> --source recent-unwrapped --lines 40 可看畫面尾端；"
        "run 會自動略過 blocked 的 pane 並回報。")
    return 0


# ---------------------------------------------------------------- 送 prompt
def write_text_file(name, text):
    os.makedirs(LOGS, exist_ok=True)
    p = os.path.join(LOGS, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return os.path.abspath(p)


def dispatch_message(task, failure=None):
    """給 pane 的短指令：請它自己讀任務檔，並把範圍釘死。"""
    files = "、".join(task["files"]) or "（這個任務不修改任何檔案）"
    msg = (f"[派工] 請完整讀取 {task['path']}，照其內容執行。"
           f"【範圍】只准修改：{files}；不得修改或新增其他檔案，不要 commit／push／部署。"
           f"完成後執行任務檔 checks 段落裡的指令，並只回報：改了哪些檔案、checks 結果、未通過的原因。")
    if failure:
        fp = write_text_file(f"{task['id']}-failure-{datetime.datetime.now():%H%M%S}.md", failure)
        msg += f"\n【上一次的結果沒有通過】請只針對 {fp} 裡的問題修正後重做，仍然只准動上面列出的檔案。"
    return msg


def send_prompt(pane, text, wait_ms=None):
    """herdr agent prompt → (code, 訊息)。code：accepted／blocked／stalled／timeout／error。"""
    args = ["agent", "prompt", pane, text]
    if wait_ms:
        args += ["--wait", "--timeout", str(int(wait_ms))]
    rc, out, err = herdr_call(args, timeout=max(60, (wait_ms or 0) / 1000 + 60))
    d = parse_json(out) or {}
    note = (out or err or "").strip()[-400:]
    if d.get("error"):
        code = (d["error"].get("code") or "error")
        return ("blocked" if code == "agent_blocked" else "stalled" if code == "agent_prompt_stalled" else
                "timeout" if code == "timeout" else "error"), note
    if rc != 0:
        return "error", note
    return "accepted", note


def wait_for(pane, timeout_ms):
    """herdr agent wait 同時是事件來源與節流；回傳 (狀態, state_change_seq)。
       注意：pane 本來就處在 until 裡的狀態時 herdr 會立刻回傳，所以這裡補一個最短間隔，
       否則 settle() 會把 agent wait 打成密閉迴圈（兩秒內幾十對子程序）。"""
    began = time.time()
    _, out, _ = herdr_call(["agent", "wait", pane, "--until", "idle", "--until", "working", "--until",
                            "blocked", "--until", "done", "--timeout", str(int(timeout_ms))],
                           timeout=timeout_ms / 1000 + 30)
    d = parse_json(out) or {}
    if d.get("error"):
        return (d["error"].get("code") or "timeout"), None
    a = (d.get("result") or {}).get("agent") or {}
    gap = time.time() - began
    if gap < MIN_POLL_S:
        time.sleep(MIN_POLL_S - gap)
    return a.get("agent_status") or "unknown", a.get("state_change_seq")


def settle(pane, budget_min, prefix=""):
    """送出後等這個 pane 真的動過、再回到 idle/done。回傳 idle／done／blocked／timeout／quiet。"""
    a0 = agent_get(pane)
    if (a0.get("agent_status") or "") == "blocked":
        return "blocked"
    seq0 = a0.get("state_change_seq")
    started = time.time()
    deadline = started + budget_min * 60
    moved = False
    while True:
        left_ms = int((deadline - time.time()) * 1000)
        if left_ms <= 0:
            return "timeout"
        st, seq = wait_for(pane, min(5000, left_ms))       # 一次呼叫就拿到狀態與序號
        if st == "blocked":
            return "blocked"
        if (seq is not None and seq != seq0) or st == "working":
            moved = True
        if moved and st in ("idle", "done", "unknown"):
            return st
        if not moved and time.time() - started > ACTIVITY_WINDOW_S:
            if prefix:
                log(f"{prefix} {ACTIVITY_WINDOW_S} 秒內沒有觀察到狀態變化，視為 agent 沒有開始工作")
            return "quiet"


# ---------------------------------------------------------------- 快照與範圍
def ignored(rel):
    return any(i in rel for i in IGNORE) or any(i in rel for i in EXTRA_IGNORE) or rel in IGNORE_FILES


def snapshot():
    snap = {}
    paths = [os.path.join(ROOT, f) for f in os.listdir(ROOT)]
    for dp, dn, fs in os.walk(SITE_ROOT):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
        paths += [os.path.join(dp, f) for f in fs]
    for p in paths:
        rel = os.path.relpath(p, ROOT)
        if os.path.isfile(p) and not os.path.islink(p) and not ignored(rel):
            try:
                snap[rel] = hashlib.sha1(open(p, "rb").read()).hexdigest()
            except Exception:
                snap[rel] = "unreadable"
    return snap


def changed_files(before, after):
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


# ---------------------------------------------------------------- 任務檔
def load_task(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"{path}: 缺少 YAML front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    target = meta.get("pane") or meta.get("role")
    if not target:
        raise SystemExit(f"{os.path.basename(path)}: front matter 要有 pane（例 w2:p3）或 role（team 內的角色）")
    pane = resolve(target)
    return {"id": os.path.splitext(os.path.basename(path))[0],
            "path": os.path.abspath(path),
            "pane": pane,
            "role": str(meta.get("role") or "") or "、".join(roles_for_pane(pane)),
            "files": list(meta.get("files") or []),
            "depends": list(meta.get("depends") or []),
            "checks": list(meta.get("checks") or []),
            "timeout_min": int(meta.get("timeout_min") or DEFAULT_TIMEOUT_MIN),
            "body": m.group(2).strip()}


def run_checks(cmds):
    out = []
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=300)
            out.append({"cmd": cmd, "ok": r.returncode == 0, "output": (r.stdout + r.stderr).strip()[-1500:]})
        except subprocess.TimeoutExpired:
            out.append({"cmd": cmd, "ok": False, "output": "檢查逾時（300 秒）"})
    return out


def failure_text(a):
    parts = []
    if a.get("error"):
        parts.append("錯誤：" + a["error"])
    if a.get("out_of_scope"):
        parts.append("你改到了範圍外的檔案：" + "、".join(a["out_of_scope"]) + "（請把它們還原，只動准改的檔案）")
    if a["verdict"] == "沒有改任何檔案":
        parts.append("工作樹沒有看到任何檔案變化，請實際用編輯工具修改指定的檔案。")
    for c in a.get("checks", []):
        if not c["ok"]:
            parts.append(f"檢查 `{c['cmd']}` 不通過，輸出：\n{c['output']}")
    return "\n".join(parts)[:3000]


def attempt(task, failure=None, dry=False, baseline=None):
    pane = task["pane"]
    if dry:
        log(f"--- {task['id']} → {pane}（{task['role']}）\n{dispatch_message(task, failure)}\n")
        return {"pane": pane, "verdict": "dry-run", "seconds": 0, "changed": [], "checks": [], "agent_state": "-"}, True

    info = agent_get(pane)
    if not info.get("pane_id"):
        # MANUAL_PANES 裡的 w2:p4 之類：herdr 回 agent_not_found，agent wait 也等不到 idle/done/blocked，
        # 依任務 112 的評估結論不假裝能自動派工；其他查無 agent 的 pane 仍是原本的訊息。
        if pane in MANUAL_PANES:
            return {"pane": pane, "verdict": "這個 pane 只手動派發", "seconds": 0, "changed": [], "checks": [],
                    "agent_state": "unknown",
                    "error": f"{pane} 是 {MANUAL_PANES[pane]}：Herdr 認不到它的 agent（agent get 回 agent_not_found，"
                             f"pane list 的 agent_status 恆為 unknown），`herdr agent wait` 等不到完成也等不到 blocked。"
                             f"請人工把任務檔 {task['path']} 的內容貼進該 pane；這支腳本不自動派工，也不重試。"}, False
        return {"pane": pane, "verdict": "找不到 agent", "seconds": 0, "changed": [], "checks": [],
                "agent_state": "-", "error": f"{pane} 上沒有可派工的 agent（用 status 檢視線上 pane）"}, False
    if info.get("agent_status") == "blocked":
        return {"pane": pane, "verdict": "pane 卡在審批", "seconds": 0, "changed": [], "checks": [],
                "agent_state": "blocked",
                "error": f"{pane} 目前是 blocked，未送出任何輸入。畫面尾端：\n{pane_read(pane, 20)}"}, False

    t0 = time.time()
    with pane_lock(pane):
        with RUN_LOCK:
            RUNNING[task["id"]] = set(task["files"])
        others = running_others(task["id"])
        before = snapshot()
        msg = dispatch_message(task, failure)
        if len(msg.encode("utf-8")) > PROMPT_INLINE_MAX:      # 長文走檔案，pane 只收短指令
            pf = write_text_file(f"{task['id']}-prompt-{datetime.datetime.now():%H%M%S}.md", msg)
            code, note = send_prompt(pane, f"[派工] 請完整讀取 {pf} 並照其內容執行（任務檔：{task['path']}）。")
            log(f"[{now()[11:]}] {task['id']} → {pane}：指令太長，改送 {os.path.relpath(pf, ROOT)}")
        else:
            code, note = send_prompt(pane, msg)
            log(f"[{now()[11:]}] {task['id']} → {pane}（{task['role']}）：prompt {code}")
        state = settle(pane, task["timeout_min"], prefix=f"  {task['id']}")
        after = snapshot()
        with RUN_LOCK:
            RUNNING.pop(task["id"], None)
        others |= running_others(task["id"])                  # 也包括這個任務跑的過程中才開始的任務

    changed = changed_files(before, after)
    # 越界一律以「派工前的模樣」判定：動了准改以外的檔案才算越界，把它還原回原狀不算，
    # 第一次越界後放著不動、第二次才去動別檔的情況也一樣抓得到
    ref = baseline if baseline is not None else before
    out_scope = sorted(k for k in set(ref) | set(after)
                       if k not in task["files"] and k not in others and ref.get(k) != after.get(k))
    tail = pane_read(pane, 40)
    a = {"pane": pane, "seconds": int(time.time() - t0), "changed": changed, "out_of_scope": out_scope,
         "agent_state": state, "prompt": code, "error": "", "checks": [], "transcript_tail": tail[-2000:]}
    if code == "blocked":
        a["verdict"], a["error"] = "pane 卡在審批", f"herdr 拒收（agent_blocked）：{note}"
        return a, False
    if code in ("error", "timeout"):
        a["verdict"], a["error"] = "prompt 未受理", f"{code}：{note}"
        return a, False
    if state == "blocked":
        a["verdict"], a["error"] = "pane 卡在審批", f"等待過程中變成 blocked，需要人工處理。畫面尾端：\n{tail[-800:]}"
        return a, False
    if state == "timeout":
        a["verdict"], a["error"] = "等待逾時", f"{task['timeout_min']} 分鐘內沒等到 idle/done（目前 {agent_get(pane).get('agent_status')}）"
        return a, False
    if state == "quiet":
        a["error"] = f"送出後 {ACTIVITY_WINDOW_S} 秒內沒觀察到 agent 開始工作，仍依檔案變化與 checks 判定"
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


def run_task(task, dry=False):
    attempts, retried, failure, status = [], False, None, "失敗"
    baseline = snapshot() if not dry else None          # 派工前的模樣：重試時「還原越界檔案」不該再被判越界
    while True:
        a, ok = attempt(task, failure, dry, baseline)
        attempts.append(a)
        if dry:
            return {"status": "dry-run", "pane": task["pane"], "task": task["id"], "attempts": attempts}
        if ok:
            status = "通過"
            break
        failure = failure_text(a)
        if not retried and a["verdict"] in ("檢查不通過", "沒有改任何檔案", "改到範圍外的檔案"):
            retried = True
            log(f"[{now()[11:]}] {task['id']}：{a['verdict']}，帶著錯誤說明重試一次")
            continue
        if a["verdict"] in ("pane 卡在審批", "找不到 agent", "prompt 未受理", "等待逾時", "這個 pane 只手動派發"):
            status = a["verdict"]
        break
    result = {"status": status, "at": now(), "pane": task["pane"], "task": task["id"], "role": task["role"],
              "files": task["files"],
              "attempts": [{k: v for k, v in a.items() if k != "transcript_tail"} for a in attempts]}
    save_result(task["id"], result, attempts)
    write_report(task, result, attempts)
    return result


# ---------------------------------------------------------------- 記錄
def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def save_result(task_id, result, attempts):
    os.makedirs(LOGS, exist_ok=True)
    with STATE_LOCK:
        st = load_state()
        st[task_id] = result
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for i, a in enumerate(attempts, 1):
        p = os.path.join(LOGS, f"{task_id}-{i}-{a.get('pane', '').replace(':', '_')}.log")
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"# task={task_id} pane={a.get('pane')} verdict={a.get('verdict')} "
                    f"agent_state={a.get('agent_state')} prompt={a.get('prompt')}\n")
            f.write(f"# seconds={a.get('seconds')} changed={a.get('changed')}\n"
                    f"# out_of_scope={a.get('out_of_scope')}\n")
            for c in a.get("checks", []):
                f.write(f"# check `{c['cmd']}` → {'通過' if c['ok'] else '不通過'}\n{c['output']}\n")
            if a.get("error"):
                f.write("# error: " + a["error"] + "\n")
            f.write("# ---- herdr pane read --source recent-unwrapped --lines 40 ----\n")
            f.write(a.get("transcript_tail", "") + "\n")


def write_report(task, result, attempts):
    pane = result["pane"]
    lines = [f"\n## {result['at']}　{task['id']}　{result['status']}（herdr_team）", "",
             f"- pane：{pane}（{'、'.join(roles_for_pane(pane)) or result['role']}｜{PANE_DUTY.get(pane, '-')}）；"
             f"檔案：{', '.join(task['files']) or '（無）'}"]
    for i, a in enumerate(attempts, 1):
        lines.append(f"- 第 {i} 次（{a.get('pane')}）：{a.get('verdict')}；耗時 {a.get('seconds', 0)} 秒；"
                     f"pane 狀態 {a.get('agent_state', '-')}；改動 {', '.join(a.get('changed', [])) or '無'}")
        if a.get("out_of_scope"):
            lines.append(f"  - **超出範圍的改動**：{', '.join(a['out_of_scope'])}")
        for c in a.get("checks", []):
            lines.append(f"  - 檢查 `{c['cmd']}` → {'通過' if c['ok'] else '不通過'}")
        if a.get("error"):
            lines.append(f"  - 錯誤：{a['error'][:600]}")
    with open(REPORT, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- 平行派工
def dep_state(dep, by_id, results, st):
    """依賴的處境：ok（已通過）／wait（這批裡還在跑）／bad（失敗或跳過）／unknown（不在這批也沒有紀錄）。"""
    if dep in by_id:
        r = results.get(dep)
        if r in ("通過", "dry-run"):
            return "ok"
        if r is None:
            return "wait"
        return "bad"
    return "ok" if st.get(dep, {}).get("status") == "通過" else "unknown"


def run_many(paths, dry=False):
    tasks = [load_task(p) for p in paths]
    by_id = {t["id"]: t for t in tasks}
    results, running, pending = {}, {}, list(tasks)
    st = load_state()
    with cf.ThreadPoolExecutor(max_workers=max(1, len({t["pane"] for t in tasks}))) as pool:
        while pending or running:
            for tid, fut in list(running.items()):
                if fut.done():
                    try:
                        results[tid] = fut.result()["status"]
                    except Exception as e:
                        results[tid] = f"腳本錯誤（{e}）"
                    st = load_state()
                    log(f"[{now()[11:]}] {tid}: {results[tid]}")
                    del running[tid]
            busy_panes = {by_id[tid]["pane"] for tid in running}
            busy_files = {f for tid in running for f in by_id[tid]["files"]}
            for t in list(pending):
                states = {d: dep_state(d, by_id, results, st) for d in t["depends"]}
                if "bad" in states.values():
                    results[t["id"]] = "跳過（依賴未通過）"
                    log(f"[{now()[11:]}] {t['id']}: 跳過（依賴 {('、'.join(d for d, s in states.items() if s == 'bad'))} 未通過）")
                    pending.remove(t)
                    continue
                if "wait" in states.values():
                    continue                                          # 依賴還在跑，這一輪先擱著
                for d in (x for x, s in states.items() if s == "unknown"):
                    if d not in WARNED_DEPS:
                        WARNED_DEPS.add(d)
                        log(f"提醒：{t['id']} 的依賴 {d} 沒有通過紀錄（不在本批、state.json 也沒有），照常派工")
                if t["pane"] in busy_panes or (set(t["files"]) & busy_files):
                    continue                                          # 同一 pane 一次一個；檔案重疊不平行
                log(f"[{now()[11:]}] 開始 {t['id']} → {t['pane']}（{'、'.join(roles_for_pane(t['pane'])) or t['role'] or MANUAL_PANES.get(t['pane'], '不在團隊映射')}）")
                running[t["id"]] = pool.submit(run_task, t, dry)
                busy_panes.add(t["pane"])
                busy_files |= set(t["files"])
                pending.remove(t)
            if pending and not running:
                for t in pending:
                    results[t["id"]] = "跳過（同一批的依賴沒有跑起來）"
                    log(f"[{now()[11:]}] {t['id']}: 跳過（依賴 {('、'.join(t['depends']))} 在這批裡沒有辦法完成）")
                pending = []
            time.sleep(2)
    return results


# ---------------------------------------------------------------- 子命令
def cmd_prompt(target, text, wait, timeout_min, lines):
    pane = resolve(target)
    info = agent_get(pane)
    manual = MANUAL_PANES.get(pane, "")
    if not info.get("pane_id"):
        if manual:      # w2:p4 這類：herdr 本來就認不到它的 agent，不是腳本壞了
            log(f"target : {pane}  （{manual}）")
            log("Herdr 對這個 pane 回 agent_not_found（沒有 agent 狀態可追蹤），所以不代送文字、也不做完成偵測；"
                "請人工在該 TUI 貼上下來的指令，或改用 TEAM 裡的 pane。")
            return 2
        log(f"{pane} 上查無 agent。目前線上 agent：")
        data, _, _ = herdr_out(["agent", "list"])
        for a in ((data or {}).get("result") or {}).get("agents", []):
            log(f"  {a.get('pane_id'):8} {a.get('name') or a.get('agent') or '-':12} {a.get('agent_status'):9} {a.get('cwd')}")
        return 2
    log(f"target : {pane}  agent={info.get('agent') or '-'}  status={info.get('agent_status') or '-'}  "
        f"cwd={info.get('cwd') or '-'}")
    log(f"角色   : {'、'.join(roles_for_pane(pane)) or (manual or '（不在團隊映射）')}  職務：{PANE_DUTY.get(pane, '-')}")
    if manual:
        log(f"提醒   : {pane} 在手動／總PM 編制（{manual}），不在 TEAM 的角色表裡；"
            f"herdr 追蹤得到它的狀態，所以任務檔直接指定這個 pane 時仍會派工，但完成與否請自己到該 pane 核對。")
    if info.get("agent_status") == "blocked":
        log("pane 卡在審批／提問對話，未送出任何輸入。畫面尾端：")
        for line in pane_read(pane, 20).splitlines():
            log("  | " + line)
        return 3
    if len(text.encode("utf-8")) > PROMPT_INLINE_MAX:
        pf = write_text_file(f"manual-{pane.replace(':', '_')}-{datetime.datetime.now():%H%M%S}.md", text)
        log(f"指令超過 {PROMPT_INLINE_MAX} bytes，改送檔案：{pf}")
        text = f"[派工] 請完整讀取 {pf} 並照其內容執行。"
    code, note = send_prompt(pane, text, wait_ms=int(timeout_min * 60 * 1000) if wait else None)
    log(f"prompt : {code}")
    if code == "blocked":
        log(note)
        return 3
    if code in ("error", "stalled"):
        log(note)
    if not wait:
        return 0 if code == "accepted" else 4
    state = settle(pane, timeout_min)
    log(f"settle : {state}")
    log("-" * 72)
    log(pane_read(pane, lines))
    log("-" * 72)
    return 0 if state in ("idle", "done", "quiet") else 4


def main():
    ap = argparse.ArgumentParser(description="Herdr 團隊派工（status / prompt / run）",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="各 pane 的 agent、狀態、角色與最後任務結果")
    s.add_argument("--workspace", default=os.environ.get("HERDR_DEFAULT_WORKSPACE", "w2"))

    p = sub.add_parser("prompt", help="直接對某個 pane 或角色送 prompt")
    p.add_argument("target", help="pane_id（w2:p3）或角色名（e500）")
    p.add_argument("text", help="指令文字")
    p.add_argument("--wait", action="store_true", help="等它回到 idle/done，並印出回覆摘要")
    p.add_argument("--timeout-min", type=float, default=20, dest="timeout_min")
    p.add_argument("--lines", type=int, default=40, help="回覆摘要列數（預設 40）")

    r = sub.add_parser("run", help="依任務檔平行派工並驗證")
    r.add_argument("tasks", nargs="+", help="任務檔（可用 glob）")
    r.add_argument("--dry-run", action="store_true", help="只印出將送出的指令，不碰 herdr")
    r.add_argument("--ignore", action="append", default=[], dest="extra_ignore",
                   help="範圍檢查時一筆忽略的檔案路徑片段（可重複；同棵樹上有別的 agent 在動時很好用）")

    a = ap.parse_args()
    if a.cmd == "status":
        sys.exit(cmd_status(a.workspace))
    elif a.cmd == "prompt":
        sys.exit(cmd_prompt(a.target, a.text, a.wait, a.timeout_min, a.lines))
    else:
        EXTRA_IGNORE.update(a.extra_ignore)
        files = sorted({p for g in a.tasks for p in glob.glob(g if os.path.isabs(g) else os.path.join(ROOT, g))})
        if not files:
            sys.exit("沒有符合的任務檔")
        res = run_many(files, a.dry_run)
        log(json.dumps(res, ensure_ascii=False, indent=1))
        sys.exit(0 if all(v in ("通過", "dry-run") for v in res.values()) else 1)


if __name__ == "__main__":
    main()
