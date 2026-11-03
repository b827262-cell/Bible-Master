#!/usr/bin/env python3
"""Shrink a generated collectible card image for 抽經文卡 to the upload size (see ART-BRIEF.md).

  python3 bible-site/tools/art_convert.py <input image> [-o out.jpg]

The gold frame is drawn by the image generator itself, so this script never adds a frame and never crops (cropping
would cut the frame): it keeps the aspect ratio, scales down only when the long side is over 2400 px, strips metadata
and saves a JPG of at most 3 MB (the quality steps down until it fits). Default output: <input name>-card.jpg next to it.
Upload the result in the admin (收藏卡圖片); this script never writes into site/assets itself."""
import argparse, io, os, sys

from PIL import Image, ImageOps

MAX_SIDE = 2400
MAX_BYTES = 3 * 1024 * 1024


def to_card(img):
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)                 # only ever shrinks
    return img


def encode(img):
    for q in range(92, 49, -4):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= MAX_BYTES:
            return buf.getvalue(), q
    raise SystemExit("壓到品質 50 仍超過 3 MB，請換一張圖")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    out = a.output or os.path.splitext(a.input)[0] + "-card.jpg"
    with Image.open(a.input) as src:
        size = src.size
        card = to_card(src)
        data, q = encode(card)
    open(out, "wb").write(data)
    print(f"{a.input}（{size[0]}×{size[1]}）→ {out}（{card.size[0]}×{card.size[1]}，比例不變、不加框，JPG 品質 {q}，{len(data) / 1024 / 1024:.2f} MB）")


if __name__ == "__main__":
    sys.exit(main())
