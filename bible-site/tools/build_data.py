#!/usr/bin/env python3
"""Build data/<key>.json for the four Gospels from the verified Union Version texts in .verify/
(mark.txt is hand-verified; mat/luk/jhn.txt are converted from Wikisource by convert_wikisource.py and
cross-checked against ebible.org). No model involved.
Each verse keeps its text exactly as in the source (only the leading verse number is removed);
the cross-reference note lines at the end of each chapter go into "notes".
A source line "1-2<text>" (two verses printed as one in the source) becomes {"v": 1, "end": 2, "text": ...}.
A few rare Simplified glyphs (NORMALIZE) are mapped to Traditional so the output is fully Traditional."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY = os.path.join(HERE, "..", "..", ".verify")
DATA = os.path.join(HERE, "..", "data")
NUM = "一二三四五六七八九十"
NORMALIZE = {"脚": "腳", "叙": "敘", "况": "況", "册": "冊"}

#: key, name, source file, expected chapters / verses (source numbering: Luke 1:1-2 and 2:34-35 are printed
#: as single verses, John 7:53 is folded into 8:1, so Luke is 1149 and John 878 instead of 1151 and 879).
BOOKS = [
    {"key": "mat", "name": "馬太福音", "src": "mat.txt", "chapters": 28, "verses": 1071},
    {"key": "mrk", "name": "馬可福音", "src": "mark.txt", "chapters": 16, "verses": 678},
    {"key": "luk", "name": "路加福音", "src": "luk.txt", "chapters": 24, "verses": 1149},
    {"key": "jhn", "name": "約翰福音", "src": "jhn.txt", "chapters": 21, "verses": 878},
]


def src_path(book):
    return os.path.join(VERIFY, book["src"])


def out_path(book):
    return os.path.join(DATA, book["key"] + ".json")


def cn(s):
    """Chinese chapter numeral (一 … 二十八) to int."""
    if "十" not in s:
        return NUM.index(s) + 1
    tens, units = s.split("十")
    return (NUM.index(tens) + 1 if tens else 1) * 10 + (NUM.index(units) + 1 if units else 0)


def parse(text):
    chapters, cur = [], None
    for line in text.splitlines():
        m = re.match(r"== 第(.+?)章 ==$", line)
        if m:
            cur = {"ch": cn(m.group(1)), "verses": [], "notes": []}
            chapters.append(cur)
        elif cur is None or not line.strip():
            continue
        elif (v := re.match(r"(\d+)(?:-(\d+))?(.*)$", line)):
            t = v.group(3)
            for src, dst in NORMALIZE.items():
                t = t.replace(src, dst)
            verse = {"v": int(v.group(1)), "text": t}
            if v.group(2):
                verse["end"] = int(v.group(2))
            cur["verses"].append(verse)
        else:
            cur["notes"].append(line)
    return chapters


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    for b in BOOKS:
        chapters = parse(open(src_path(b), encoding="utf-8").read())
        data = {"key": b["key"], "book": b["name"], "version": "和合本", "chapters": chapters}
        json.dump(data, open(out_path(b), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{b['name']}: {len(chapters)} chapters, {sum(len(c['verses']) for c in chapters)} verses -> data/{b['key']}.json")
