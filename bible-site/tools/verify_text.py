#!/usr/bin/env python3
"""Check scripture integrity. 1) data/mark.json matches .verify/mark.txt verse by verse.
2) No file under site/ hard-codes scripture (any 12+ character run of a verse found in a site file fails).
Exit code 0 only when everything passes."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_data import SRC, OUT, parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ref = parse(open(SRC, encoding="utf-8").read())
data = json.load(open(OUT, encoding="utf-8"))["chapters"]
ok, bad = 0, []
refmap = {(c["ch"], v["v"]): v["text"] for c in ref for v in c["verses"]}
gotmap = {(c["ch"], v["v"]): v["text"] for c in data for v in c["verses"]}
for k, t in refmap.items():
    if gotmap.get(k) == t:
        ok += 1
    else:
        bad.append(f"{k[0]}:{k[1]}")
extra = [f"{k[0]}:{k[1]}" for k in gotmap if k not in refmap]
print(f"經文比對：{ok}/{len(refmap)} 節相符" + (f"；不符 {bad[:10]}" if bad else "") + (f"；多出 {extra[:10]}" if extra else ""))

site = os.path.join(ROOT, "site")
hard = []
for dp, _, fs in os.walk(site):
    for f in fs:
        if f.endswith((".html", ".js", ".css")):
            s = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
            for k, t in refmap.items():
                frag = t.strip("　 ")[:12]
                if len(frag) >= 12 and frag in s:
                    hard.append(f"{f} 含 {k[0]}:{k[1]}")
                    break
print("寫死經文檢查：" + ("通過（site/ 沒有寫死的經文）" if not hard else f"不通過 {hard}"))
sys.exit(0 if ok == len(refmap) and not bad and not extra and not hard else 1)
