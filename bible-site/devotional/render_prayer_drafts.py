#!/usr/bin/env python3
"""Render review drafts with scripture from the project's Gospel data."""
import argparse
import json
import re
from pathlib import Path

from parser import parse_scripture_reference

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / 'data'
SOURCES = ('prayer-reading-draft.md', 'prayer-reading-week-2.md')


def render():
    output = ['# 四福音每日禱讀｜兩週審核稿', '',
              '經文取自專案四福音資料。默想、反思與禱告為原創草稿，待人工及神學審核。', '']
    total = 0
    for name in SOURCES:
        source = (ROOT / name).read_text(encoding='utf-8')
        sections = re.split(r'^## (第[一二三四五六七八九十]+天)｜(.+)$', source, flags=re.M)[1:]
        if len(sections) % 3:
            raise ValueError(f'{name} 的段落格式不完整')
        for day, title, body in zip(sections[::3], sections[1::3], sections[2::3]):
            fields = {}
            for key in ('經文', '默想', '反思', '禱告'):
                match = re.search(r'^' + key + r'：(.*)$', body, re.M)
                if not match:
                    raise ValueError(f'{day} 缺少{key}')
                fields[key] = match.group(1).strip()
            scope, ranges, errors = parse_scripture_reference(fields['經文'])
            if scope != 'IN_SCOPE' or errors or not ranges:
                raise ValueError(f'{day} 經文範圍無效：{errors}')
            verses = []
            for passage in ranges:
                book = json.loads((DATA / f'{passage.book_code.lower()}.json').read_text(encoding='utf-8'))
                for chapter in book['chapters']:
                    if not passage.start_chapter <= chapter['ch'] <= passage.end_chapter:
                        continue
                    for verse in chapter['verses']:
                        if chapter['ch'] == passage.start_chapter and passage.start_verse and verse.get('end', verse['v']) < passage.start_verse:
                            continue
                        if chapter['ch'] == passage.end_chapter and passage.end_verse and verse['v'] > passage.end_verse:
                            continue
                        label = str(verse['v'])
                        if verse.get('end'):
                            label += f"–{verse['end']}"
                        verses.append(f"{chapter['ch']}:{label} {verse['text']}")
            if not verses:
                raise ValueError(f'{day} 沒有找到經文')
            output += [f'## {day}｜{title}', '', f"**經文範圍**：{fields['經文']}", '',
                       '**經文內容**', '', *[f'- {v}' for v in verses], '',
                       f"**默想**：{fields['默想']}", '', f"**反思**：{fields['反思']}", '',
                       f"**全心禱告**：{fields['禱告']}", '']
            total += 1
    if total != 14:
        raise ValueError(f'預期 14 篇，實際 {total} 篇')
    return '\n'.join(output)


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    args.output.write_text(render(), encoding='utf-8')
