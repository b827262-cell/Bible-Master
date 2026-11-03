#!/usr/bin/env python3
"""Turn a generated picture into a classic gold-foil collectible card image for 抽經文卡 (see ART-BRIEF.md).

  python3 bible-site/tools/art_convert.py <input image> [-o out.jpg]

Makes one 1000 × 1400 JPG (classic trading-card ratio 5:7, 63 × 88 mm) of at most 3 MB: the picture is center-cropped
into the card and framed with a 24 px gold-foil border (diagonal gold gradient, a dark-gold line on the outside and
around the picture). The frame is part of the file, so the page, the 下載經文圖 download and the composite 下載圖片 all
show the same framed card from one file. Metadata is stripped; the quality steps down until the file fits.
Default output: <input name>-card.jpg next to it. Upload the result in the admin (收藏卡圖片); this script never writes
into site/assets itself."""
import argparse, io, os, sys

from PIL import Image, ImageDraw, ImageOps

W, H = 1000, 1400
FRAME = 24
MAX_BYTES = 3 * 1024 * 1024
# same gold stops the site used for its CSS frame: dark gold → bright → gold → highlight → gold → bright → dark gold
GOLD = [(0, (0x8a, 0x62, 0x16)), (0.18, (0xf7, 0xe0, 0x8a)), (0.34, (0xc9, 0x96, 0x2b)), (0.5, (0xff, 0xf3, 0xc4)),
        (0.66, (0xb5, 0x82, 0x1f)), (0.82, (0xf2, 0xd3, 0x6b)), (1, (0x7d, 0x55, 0x12))]


def gold_at(t):
    for (t0, c0), (t1, c1) in zip(GOLD, GOLD[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return GOLD[-1][1]


def gold_foil():
    """W × H diagonal gold gradient: a 1-pixel strip mapped along x + y."""
    n = W + H
    strip = Image.new("RGB", (n, 1))
    strip.putdata([gold_at(i / (n - 1)) for i in range(n)])
    return strip.transform((W, H), Image.AFFINE, (1, 1, 0, 0, 0, 0), resample=Image.NEAREST)


def to_card(img):
    picture = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (W - 2 * FRAME, H - 2 * FRAME), Image.LANCZOS)
    card = gold_foil()
    card.paste(picture, (FRAME, FRAME))
    d = ImageDraw.Draw(card)
    d.rectangle((0, 0, W - 1, H - 1), outline=(0x6b, 0x4a, 0x12), width=2)                       # outer pressed line
    d.rectangle((FRAME - 3, FRAME - 3, W - FRAME + 2, H - FRAME + 2), outline=(0x7d, 0x55, 0x12), width=3)   # around the picture
    d.rectangle((6, 6, W - 7, H - 7), outline=(0xff, 0xec, 0xaa), width=1)                         # thin highlight inside the edge
    return card


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
        data, q = encode(to_card(src))
    open(out, "wb").write(data)
    print(f"{a.input}（{size[0]}×{size[1]}）→ {out}（{W}×{H}，5:7，燙金框 {FRAME}px，JPG 品質 {q}，{len(data) / 1024 / 1024:.2f} MB）")


if __name__ == "__main__":
    sys.exit(main())
