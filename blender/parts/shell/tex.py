"""Paints the shell's few image textures into tex/ (run once: python3 tex.py).
   plate.png  : small brass door plate, engraved with a downward arrow only
   fuse.png   : the little paper card on the fuse box door
"""
import os, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
os.makedirs(D, exist_ok=True)
rng = np.random.default_rng(7)


def plate():
    W, H = 256, 384
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    # brushed brass: horizontal streaks + soft tarnish blotches
    streak = rng.normal(0, 1, (H, 1)).repeat(W, 1)
    streak = (streak + np.roll(streak, 1, 0) + np.roll(streak, -1, 0)) / 3.0
    blot = rng.normal(0, 1, (H // 32, W // 32)).astype(np.float32)
    blot = np.asarray(Image.fromarray(blot, 'F').resize((W, H), Image.BICUBIC))
    base = np.array([182, 132, 62], np.float32)
    k = 1.0 + 0.05 * streak - 0.10 * np.clip(blot, 0, 3)
    # darker tarnish toward the rim, brighter rubbed centre
    d = np.minimum(np.minimum(x, W - 1 - x), np.minimum(y, H - 1 - y))
    k *= 0.78 + 0.22 * np.clip(d / 40.0, 0, 1)
    img = base[None, None, :] * k[..., None]
    # bevel: bright top-left edge, dark bottom-right edge
    e = 6
    img[d < e] *= 0.75
    img[(d < e) & ((x < e) | (y < e))] *= 1.45
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB')
    dr = ImageDraw.Draw(im)
    cx = W // 2
    ink = (36, 24, 12)
    # the arrow: shaft + head, cut deep and filled with old dark wax
    dr.rectangle([cx - 11, 92, cx + 11, 232], fill=ink)
    dr.polygon([(cx - 50, 222), (cx + 50, 222), (cx, 300)], fill=ink)
    # thin bright lip on the lower side of the cut (engraving catches light)
    dr.line([(cx + 12, 94), (cx + 12, 222)], fill=(220, 175, 95), width=2)
    dr.line([(cx + 2, 300), (cx + 52, 224)], fill=(220, 175, 95), width=2)
    # two countersunk screws with slots
    for sy in (40, H - 40):
        dr.ellipse([cx - 15, sy - 15, cx + 15, sy + 15], fill=(120, 84, 38))
        dr.ellipse([cx - 12, sy - 12, cx + 12, sy + 12], fill=(160, 115, 52))
        dr.line([(cx - 11, sy + 4), (cx + 11, sy - 4)], fill=(40, 26, 12), width=4)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    im.save(os.path.join(D, 'plate.png'))


def fuse():
    W, H = 256, 160
    a = np.full((H, W, 3), (214, 200, 165), np.float32)
    a *= (1 + 0.04 * rng.normal(0, 1, (H, W, 1))).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    a *= 1 - 0.18 * yy                           # yellowed lower part
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')
    dr = ImageDraw.Draw(im)
    dr.rectangle([6, 6, W - 7, H - 7], outline=(120, 40, 30), width=3)
    f = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 54, index=0)
    dr.text((W // 2, 62), '分電盤', fill=(40, 30, 26), font=f, anchor='mm')
    f2 = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 22, index=0)
    dr.text((W // 2, 122), '100V  30A', fill=(70, 50, 40), font=f2, anchor='mm')
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    im.save(os.path.join(D, 'fuse.png'))


if __name__ == '__main__':
    plate(); fuse()
    print('ok')
