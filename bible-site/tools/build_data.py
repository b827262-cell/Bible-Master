#!/usr/bin/env python3
"""Build data/mark.json from the verified Union Version text (.verify/mark.txt). No model involved.
Each verse keeps its text exactly as in mark.txt (only the leading verse number is removed);
the cross-reference note lines at the end of each chapter go into "notes"."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", ".verify", "mark.txt")
OUT = os.path.join(HERE, "..", "data", "mark.json")
NUM = "一二三四五六七八九十"


def cn(s):
    """Chinese chapter numeral (一 … 十六) to int."""
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + NUM.index(s[1]) + 1
    return NUM.index(s) + 1


def parse(text):
    chapters, cur = [], None
    for line in text.splitlines():
        m = re.match(r"== 第(.+?)章 ==$", line)
        if m:
            cur = {"ch": cn(m.group(1)), "verses": [], "notes": []}
            chapters.append(cur)
        elif cur is None or not line.strip():
            continue
        elif (v := re.match(r"(\d+)(.*)$", line)):
            cur["verses"].append({"v": int(v.group(1)), "text": v.group(2)})
        else:
            cur["notes"].append(line)
    return chapters


if __name__ == "__main__":
    chapters = parse(open(SRC, encoding="utf-8").read())
    data = {"book": "馬可福音", "version": "和合本", "chapters": chapters}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(chapters)} chapters, {sum(len(c['verses']) for c in chapters)} verses -> data/mark.json")
