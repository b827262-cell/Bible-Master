#!/usr/bin/env python3
"""freebuff 靜態探測腳本 — 唯讀診斷，完全不送任何按鍵給終端。

檢查三件事：
1. freebuff CLI 是否安裝與版本號（freebuff --version）。
2. 定位實際執行的原生 binary（launcher.js 會把下載的執行檔放在
   ~/.config/manicode/ 下），並唯讀掃描字串 isPlainEnterKey
   判斷上游 Enter 修正是否已落地。
3. 呼叫 herdr-core ls --json（唯讀），列出 label name=freebuff 或執行
   node .../freebuff 的終端的 address / identity / status。
   在 herdr 原生支援 freebuff 之前，status 預期為 null。

本腳本絕不對任何終端執行 send / keys / read 等互動指令。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# 上游修正符號：若 binary 內含此字串，代表 Enter 問題已修復
FIX_SYMBOL = b"isPlainEnterKey"
LAUNCHER_PATH = Path.home() / ".local" / "lib" / "node_modules" / "freebuff" / "launcher.js"
CONFIG_DIR_DEFAULT = Path.home() / ".config" / "manicode"
BINARY_CANDIDATES = [CONFIG_DIR_DEFAULT / "freebuff"]
BINARY_NAME_PATTERN = re.compile(r"freebuff", re.IGNORECASE)


def probe_cli() -> dict:
    """檢查 freebuff CLI 安裝與版本。"""
    path = shutil.which("freebuff")
    result = {"installed": path is not None, "path": path, "version": None, "error": None}
    if not path:
        return result
    try:
        out = subprocess.run(
            ["freebuff", "--version"],
            capture_output=True, text=True, timeout=30,
        )
        text = (out.stdout + out.stderr).strip()
        if out.returncode == 0:
            result["version"] = text.splitlines()[0].strip() if text else None
        else:
            result["error"] = f"exit {out.returncode}: {text[:200]}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)
    return result


def parse_launcher_binary_name():
    """解析 launcher.js 找出 config 目錄與 binary 名稱（唯讀）。"""
    name = None
    config_dir = str(CONFIG_DIR_DEFAULT)
    try:
        src = LAUNCHER_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return name, config_dir, False
    # launcher.js: binaryPath = path.join(configDir, binaryName)
    m_cfg = re.search(
        r"path\.join\(\s*homeDir,\s*['\"]\.config['\"],\s*['\"]([\w.-]+)['\"]", src
    )
    if m_cfg:
        config_dir = os.path.join(str(Path.home()), ".config", m_cfg.group(1))
    m_name = re.search(r"binaryPath:\s*path\.join\(\s*configDir,\s*(\w+)\)", src)
    if m_name:
        var = m_name.group(1)
        m_val = re.search(
            r"const\s+" + re.escape(var) + r"\s*=\s*['\"]([^'\"]+)['\"]", src
        )
        if m_val:
            name = m_val.group(1)
    return name, config_dir, True


def probe_binary() -> dict:
    """定位原生 binary，唯讀檢查是否包含上游修正符號。"""
    name, config_dir, launcher_found = parse_launcher_binary_name()
    candidates = []
    if name:
        candidates.append(Path(config_dir) / name)
    candidates.extend(BINARY_CANDIDATES)

    binary = None
    for cand in candidates:
        try:
            if cand.is_file() and os.access(cand, os.R_OK | os.X_OK):
                binary = cand
                break
        except OSError:
            continue

    result = {
        "launcher": str(LAUNCHER_PATH) if LAUNCHER_PATH.is_file() else None,
        "launcher_parsed": launcher_found,
        "config_dir": config_dir,
        "binary": str(binary) if binary else None,
        "binary_size": binary.stat().st_size if binary else None,
        "fix_symbol_present": None,
        "error": None,
    }
    if binary is None:
        result["error"] = "找不到 freebuff 原生 binary"
        return result

    # 唯讀分塊掃描（處理跨塊界字串）
    try:
        found = False
        tail = b""
        with open(binary, "rb") as fh:
            while True:
                chunk = fh.read(8 * 1024 * 1024)
                if not chunk:
                    break
                if FIX_SYMBOL in tail + chunk:
                    found = True
                    break
                tail = chunk[-len(FIX_SYMBOL):]
        result["fix_symbol_present"] = found
    except OSError as exc:
        result["error"] = f"讀取 binary 失敗: {exc}"
    return result


FREEBUFF_KEYWORD = "freebuff"


def probe_terminals_top(data) -> list:
    """頂層 ls 資料先比對（agent / where 含 freebuff）。"""
    terminals = data.get("terminals", []) if isinstance(data, dict) else []
    matches = []
    for term in terminals:
        agent = str(term.get("agent", ""))
        if agent.lower() == FREEBUFF_KEYWORD or re.search(
            rf"node\s+\S*{FREEBUFF_KEYWORD}", str(term.get("where", "")), re.IGNORECASE
        ):
            matches.append({
                "address": term.get("address"),
                "identity": term.get("identity"),
                "status": term.get("status"),
                "agent": agent,
                "where": term.get("where"),
                "state": term.get("state"),
                "matched_by": "ls(agent/where)",
                "detail": None,
            })
    return terminals, matches


def probe_terminal_detail(address) -> dict:
    """唯讀呼叫 herdr-core get <address> --json，判斷該終端是否為 freebuff。

    頂層 ls 的 argv 可能只是 /bin/bash（freebuff 由互動 bash 啟動），
    因此需查 detail：foreground.argv、labels（如 name=freebuff）或 title。
    """
    try:
        out = subprocess.run(
            ["herdr-core", "get", str(address), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            return None
        detail = json.loads(out.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    if not isinstance(detail, dict):
        return None

    reasons = []
    labels = detail.get("labels") or {}
    label_name = str(labels.get("name") or "")
    if label_name.lower() == FREEBUFF_KEYWORD:
        reasons.append(f"labels.name={label_name}")
    fg_argv = (detail.get("foreground") or {}).get("argv") or []
    fg_str = " ".join(str(a) for a in fg_argv)
    if FREEBUFF_KEYWORD.lower() in fg_str.lower():
        reasons.append(f"foreground.argv={fg_argv}")
    title = str(detail.get("title") or "")
    if FREEBUFF_KEYWORD.lower() in title.lower():
        reasons.append(f"title 含 freebuff")
    if not reasons:
        return None
    return {
        "address": detail.get("address") or address,
        "identity": detail.get("identity"),
        "status": detail.get("status"),
        "agent": str((detail.get("foreground") or {}).get("name") or detail.get("argv") or ""),
        "where": labels.get("where"),
        "state": detail.get("state"),
        "matched_by": "; ".join(reasons),
        "detail": {
            "foreground_argv": fg_argv,
            "labels": {k: v for k, v in labels.items() if k in ("name", "where", "herdr.tab", "herdr.space")},
            "title": title,
        },
    }


def probe_herdr() -> dict:
    """呼叫 herdr-core ls --json（唯讀），找出 freebuff 相關終端。

    頂層 ls 的 argv 顯示的是啟動器（如 /bin/bash），freebuff 由互動 bash
    啟動時不易分辨，因此對每個 live 終端再以 herdr-core get <address>
    --json 唯讀複查 foreground.argv / labels / title。全程不送按鍵。
    """
    result = {"available": True, "matches": [], "note": None, "error": None}
    if not shutil.which("herdr-core"):
        result["available"] = False
        result["error"] = "herdr-core 不在 PATH 中"
        return result
    try:
        out = subprocess.run(
            ["herdr-core", "ls", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            result["error"] = f"exit {out.returncode}: {(out.stdout + out.stderr)[:200]}"
            return result
        data = json.loads(out.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)
        return result

    terminals, matches = probe_terminals_top(data)

    # 頂層 ls 的 argv 可能只是啟動 shell；對其餘 live 終端唯讀複查 detail
    seen = {m["address"] for m in matches}
    for term in terminals:
        address = term.get("address")
        if not address or address in seen or term.get("state") != "live":
            continue
        detail_match = probe_terminal_detail(address)
        if detail_match:
            matches.append(detail_match)
            seen.add(address)

    result["matches"] = matches
    if not matches:
        result["note"] = (
            "沒有 label name=freebuff 或執行 node ...(freebuff) 的終端；"
            "herdr 原生支援 freebuff 前，status 亦為 null。"
        )
    return result


def summarize(data: dict) -> str:
    """繁體中文摘要輸出。"""
    lines = ["== freebuff 靜態探測（唯讀，未送任何按鍵） =="]
    cli = data["cli"]
    if cli["installed"]:
        ver = cli["version"] or "（無法取得版本）"
        lines.append(f"1. CLI 已安裝：{cli['path']}，版本 {ver}")
        if cli["error"]:
            lines.append(f"   但版本查詢有警告：{cli['error']}")
    else:
        lines.append("1. CLI 未安裝（PATH 中找不到 freebuff）")

    bin_ = data["binary"]
    if bin_["binary"]:
        sym = bin_["fix_symbol_present"]
        if sym is True:
            verdict = "已包含 → Enter 問題修復已落地 ✅"
        elif sym is False:
            verdict = "未包含 → Enter 問題修復尚未落地（仍需人工留意 Enter 行為）❌"
        else:
            verdict = "無法判斷（掃描失敗）"
        size_mb = bin_["binary_size"] / (1024 * 1024) if bin_["binary_size"] else 0
        lines.append(
            f"2. 原生 binary：{bin_['binary']}（{size_mb:.1f} MB，"
            f"launcher.js 指向 config 目錄 {bin_['config_dir']}）"
        )
        lines.append(f"   修正符號 isPlainEnterKey：{verdict}")
        if bin_["error"]:
            lines.append(f"   警告：{bin_['error']}")
    else:
        lines.append(f"2. 找不到原生 binary（{bin_['error']}）")

    her = data["herdr"]
    if not her["available"]:
        lines.append(f"3. herdr-core 不可用：{her['error']}")
    elif her["error"]:
        lines.append(f"3. herdr-core ls 失敗：{her['error']}")
    elif her["matches"]:
        lines.append(f"3. 發現 {len(her['matches'])} 個 freebuff 終端：")
        for m in her["matches"]:
            lines.append(
                f"   - address={m['address']} identity={m['identity']} "
                f"status={m['status']} agent={m['agent']} state={m['state']}"
            )
            lines.append(f"     命中依據：{m.get('matched_by', '')}")
            det = m.get("detail")
            if det:
                lbls = det.get("labels") or {}
                lines.append(
                    f"     foreground.argv={det.get('foreground_argv')} "
                    f"labels.name={lbls.get('name')} "
                    f"herdr.tab={lbls.get('herdr.tab')}"
                )
    else:
        lines.append("3. 未發現 freebuff 終端。" + (her["note"] or ""))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="freebuff 唯讀靜態探測（不送任何按鍵）")
    parser.add_argument("--json", action="store_true", help="以 JSON 輸出")
    args = parser.parse_args()

    data = {"cli": probe_cli(), "binary": probe_binary(), "herdr": probe_herdr()}
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(summarize(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
