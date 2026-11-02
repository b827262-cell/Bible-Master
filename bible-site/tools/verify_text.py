#!/usr/bin/env python3
"""Check scripture integrity for all four Gospels.
1) data/<key>.json matches its verified source in .verify/ verse by verse (same parse() as build_data.py).
2) No file under site/ hard-codes scripture (any 12+ character run of a verse found in a site file fails).
Exit code 0 only when everything passes."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_data import BOOKS, parse, src_path, out_path

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ok_all, refmap_all = True, {}
for b in BOOKS:
    ref = parse(open(src_path(b), encoding="utf-8").read())
    data = json.load(open(out_path(b), encoding="utf-8"))["chapters"]
    refmap = {(c["ch"], v["v"]): (v["text"], v.get("end")) for c in ref for v in c["verses"]}
    gotmap = {(c["ch"], v["v"]): (v["text"], v.get("end")) for c in data for v in c["verses"]}
    bad = [f"{k[0]}:{k[1]}" for k, t in refmap.items() if gotmap.get(k) != t]
    extra = [f"{k[0]}:{k[1]}" for k in gotmap if k not in refmap]
    good = len(refmap) - len(bad)
    print(f"經文比對 {b['name']}：{good}/{len(refmap)} 節相符" + (f"；不符 {bad[:10]}" if bad else "") + (f"；多出 {extra[:10]}" if extra else ""))
    ok_all &= not bad and not extra and len(refmap) == b["verses"] and len(ref) == b["chapters"]
    if len(refmap) != b["verses"] or len(ref) != b["chapters"]:
        print(f"不符：{b['name']} 應為 {b['chapters']} 章 {b['verses']} 節，來源是 {len(ref)} 章 {len(refmap)} 節")
    for k, (t, _) in refmap.items():
        refmap_all[(b["key"],) + k] = t

hard = []
for dp, _, fs in os.walk(os.path.join(ROOT, "site")):
    for f in fs:
        if f.endswith((".html", ".js", ".css")):
            s = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
            for k, t in refmap_all.items():
                frag = t.strip("　 ")[:12]
                if len(frag) >= 12 and frag in s:
                    hard.append(f"{f} 含 {k[0]} {k[1]}:{k[2]}")
                    break
print("寫死經文檢查：" + ("通過（site/ 沒有寫死的經文）" if not hard else f"不通過 {hard}"))
sys.exit(0 if ok_all and not hard else 1)
