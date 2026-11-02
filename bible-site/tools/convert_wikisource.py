#!/usr/bin/env python3
"""Convert a Wikisource 《聖經 (和合本)》 book page (raw wikitext, saved by hand under
.verify/download/wikisource/<key>.wiki) into the plain-text format of .verify/mark.txt:
  == 第一章 ==        chapter heading
  1　神的兒子…       verse number followed by the verse text
  〡瑪三　〡          cross-reference note lines at the end of the chapter
Only markup is translated; no text is added. Mark is the control: converting mrk.wiki must
reproduce the hand-verified mark.txt exactly (see --check).
Usage: python3 -I convert_wikisource.py <in.wiki> <out.txt>   |   --check"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY = os.path.join(HERE, "..", "..", ".verify")


def link_label(m):
    """[[target|label]] -> label, [[target]] -> target."""
    inner = m.group(1)
    return inner.split("|", 1)[1] if "|" in inner else inner


#: Wikisource marks one rare glyph with a fallback template. 路加福音 12:49 {{!|𤏲|火着}} is rendered 燒,
#: the reading of the second public source (ebible.org CUV) for the same verse.
SPECIAL = {"{{!|𤏲|火着}}": "燒"}


def inline(s):
    for k, v in SPECIAL.items():
        s = s.replace(k, v)
    s = re.sub(r"\{\{\*\|([^{}]*)\}\}", r"〈\1〉", s)          # {{*|有古卷…}} -> 〈有古卷…〉
    s = re.sub(r"\{\{udots\|([^{}]*)\}\}", r"\1", s)            # dotted (supplied) words -> plain
    s = re.sub(r"\{\{[Aa]nchor\|[^{}]*\}\}", "", s)
    s = s.replace("{{!}}", "|")
    s = re.sub(r"\[\[([^\[\]]*)\]\]", link_label, s)
    s = re.sub(r"</?sup>", "", s)
    return s


def convert(wiki):
    out = []
    for raw in wiki.splitlines():
        line = raw.strip("\r")
        if (m := re.search(r"\{\{Chapter\|\d+\|(第[^|}]+章)\}\}", line)):
            out.append(f"== {m.group(1)} ==")
        elif (m := re.match(r"((?:\{\{verse\|\d+\|\d+\}\}[ \t]*)+)(.*)$", line)):
            nums = re.findall(r"\{\{verse\|\d+\|(\d+)\}\}", m.group(1))
            label = nums[0] if len(nums) == 1 else f"{nums[0]}-{nums[-1]}"   # merged verses: "1-2"
            out.append(label + inline(m.group(2)))
        elif line.startswith(":") and out:                           # note line under a chapter
            out.append(inline(line[1:]))
    return "\n".join(out) + "\n"


def mark_lines(text):
    return [l for l in text.splitlines() if l.strip()]


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        got = mark_lines(convert(open(os.path.join(VERIFY, "download", "wikisource", "mrk.wiki"), encoding="utf-8").read()))
        want = mark_lines(open(os.path.join(VERIFY, "mark.txt"), encoding="utf-8").read())
        diff = [(i, w, g) for i, (w, g) in enumerate(zip(want, got)) if w != g]
        print(f"mark.txt {len(want)} 行，轉換結果 {len(got)} 行，不同 {len(diff) + abs(len(want) - len(got))} 行")
        for i, w, g in diff[:8]:
            print(f"  第 {i + 1} 行\n    原：{w}\n    轉：{g}")
        sys.exit(0 if not diff and len(want) == len(got) else 1)
    src, dst = sys.argv[1], sys.argv[2]
    open(dst, "w", encoding="utf-8").write(convert(open(src, encoding="utf-8").read()))
    print(f"{src} -> {dst}")
