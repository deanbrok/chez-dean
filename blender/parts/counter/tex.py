"""Paints the counter part's labels into tex/sheet.png (2048x2048) and writes tex/regions.json (name -> u0,v0,u1,v1).
Run:  python3 blender/parts/counter/tex.py      (build.py only READS the results)"""
import os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tex')
EMBLEM = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'barkit', 'cat_emblem.png')
S = 2048

F_LORA_I = '/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf'
F_LORA = '/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf'
F_SERIF_B = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
F_CAL = '/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf'
F_CAL_B = '/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf'
F_CAL_I = '/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf'
F_BASK = '/usr/share/fonts/truetype/baskerville/GFSBaskerville.otf'
F_SANS_B = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
F_SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf'
F_POP_B = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
F_PENCIL = '/usr/share/texmf/fonts/opentype/public/lm/lmmonoltcond10-regular.otf'
F_JP = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'
F_JP_SANS = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

# region boxes in PIXELS (x, y, w, h), y from the top of the sheet
R = dict(
    coaster=(0, 0, 512, 512),
    note=(512, 0, 768, 576),
    matchbook=(1280, 0, 384, 448),
    menu=(1664, 0, 384, 576),
    cigar_lid=(0, 576, 768, 512),
    cigar_band=(768, 576, 768, 128),
    flags=(768, 704, 512, 128),
    plate=(1280, 704, 512, 96),
    cigar_ring=(1280, 800, 512, 160),      # the paper band on the cigar: x runs around it, the top edge is toward the head
    book=(0, 1088, 1024, 780),
    score=(1024, 1088, 1024, 640),
    keys=(768, 832, 512, 256),
    cigar_leaf=(1024, 1728, 1024, 320),    # the cigar's wrapper leaf: x runs foot -> head, y runs around it (tiles in y)
)

def F(path, size):
    try: return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', size)

def lora(size, italic=False, wght=400):
    f = F(F_LORA_I if italic else F_LORA, size)
    try: f.set_variation_by_axes([wght])
    except Exception: pass
    return f

rng = np.random.default_rng(7)

def noise2(h, w, scale, seed):
    """smooth value noise in 0..1"""
    r = np.random.default_rng(seed)
    gh, gw = max(2, int(h / scale) + 2), max(2, int(w / scale) + 2)
    g = r.random((gh, gw)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im).astype(np.float32) / 255

def fbm(h, w, scales=(64, 24, 8, 3), seed=1, weights=None):
    weights = weights or [0.5, 0.25, 0.15, 0.1]
    a = sum(wt * noise2(h, w, s, seed + i) for i, (s, wt) in enumerate(zip(scales, weights)))
    return a / sum(weights)

def paper(w, h, base=(232, 222, 196), seed=3, grain=10, stain=0.0):
    n = fbm(h, w, (90, 30, 6, 2), seed)
    a = np.ones((h, w, 3), np.float32) * np.array(base, np.float32)
    a += (n[..., None] - 0.5) * grain * 2
    if stain:
        s = fbm(h, w, (200, 80), seed + 9, [0.7, 0.3])
        a *= 1 - stain * np.clip((s[..., None] - 0.45) * 3, 0, 1) * np.array([0.05, 0.1, 0.22])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')

def emblem(size, color, alpha=255):
    e = Image.open(EMBLEM).convert('RGBA')
    e = e.crop(e.getbbox())
    k = size / max(e.size)
    e = e.resize((max(1, int(e.size[0] * k)), max(1, int(e.size[1] * k))), Image.LANCZOS)
    m = e.split()[3].point(lambda v: v * alpha // 255)
    solid = Image.new('RGBA', e.size, (*color, 255)); solid.putalpha(m)
    return solid

def paste_c(dst, src, cx, cy):
    dst.alpha_composite(src, (int(cx - src.size[0] / 2), int(cy - src.size[1] / 2)))

def text_c(d, cx, y, s, font, fill, spacing=0):
    if spacing:
        ws = [d.textlength(c, font=font) for c in s]; tw = sum(ws) + spacing * (len(s) - 1)
        x = cx - tw / 2
        for c, w in zip(s, ws):
            d.text((x, y), c, font=font, fill=fill); x += w + spacing
        return
    w = d.textlength(s, font=font)
    d.text((cx - w / 2, y), s, font=font, fill=fill)

def ink_layer(size):
    return Image.new('RGBA', size, (0, 0, 0, 0))

def hand(layer, x, y, text, font, color, r, rot=0.0, jit=1.8, wobble=2.0, pressure=0.3):
    """handwriting from a font: per-glyph rotation, baseline drift, size jitter, ink density variation"""
    d0 = ImageDraw.Draw(layer)
    base = y; cx = x
    for i, ch in enumerate(text):
        if ch == ' ':
            cx += font.size * (0.27 + 0.06 * r.random()); continue
        g = Image.new('L', (font.size * 2, font.size * 2), 0)
        ImageDraw.Draw(g).text((font.size * 0.5, font.size * 0.3), ch, font=font, fill=255)
        sc = 1 + (r.random() - 0.5) * 0.10 * jit
        g = g.resize((int(g.size[0] * sc), int(g.size[1] * sc)), Image.BICUBIC)
        g = g.rotate(rot + (r.random() - 0.5) * 7 * jit, resample=Image.BICUBIC, expand=False)
        dens = 1 - pressure * r.random()
        g = g.point(lambda v, dd=dens: int(v * dd))
        col = Image.new('RGBA', g.size, (*color, 255)); col.putalpha(g)
        drift = math.sin(i * 0.35 + r.random()) * font.size * 0.03 * wobble + (r.random() - 0.5) * font.size * 0.04 * jit
        slope = -math.tan(math.radians(rot)) * (cx - x)
        layer.alpha_composite(col, (int(cx - font.size * 0.5 * sc), int(base + drift + slope - font.size * 0.3 * sc)))
        cx += d0.textlength(ch, font=font) * (0.96 + 0.06 * r.random())
    return cx

def ink_finish(layer, blur=0.6):
    a = np.asarray(layer).astype(np.float32)
    al = a[..., 3]
    h, w = al.shape
    # ink pooling: slightly darker where strokes are dense, a little feathering
    fe = np.asarray(Image.fromarray(al.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)
    al = np.clip(al * 0.92 + fe * 0.15, 0, 255)
    a[..., 3] = al
    return Image.fromarray(a.astype(np.uint8), 'RGBA').filter(ImageFilter.GaussianBlur(blur))

def warp(layer, amp=2.5, scale=40, seed=0):
    a = np.asarray(layer).astype(np.float32); h, w = a.shape[:2]
    dx = (fbm(h, w, (scale, scale / 3), seed, [0.7, 0.3]) - 0.5) * 2 * amp
    dy = (fbm(h, w, (scale, scale / 3), seed + 5, [0.7, 0.3]) - 0.5) * 2 * amp
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sx = np.clip(xx + dx, 0, w - 1.001); sy = np.clip(yy + dy, 0, h - 1.001)
    x0 = sx.astype(int); y0 = sy.astype(int); fx = (sx - x0)[..., None]; fy = (sy - y0)[..., None]
    out = (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')

def wear_edges(img, amt=0.5, seed=5, col=(250, 245, 230), width=10):
    """lighten / scuff the borders of a printed region (worn card corners and edges)"""
    a = np.asarray(img.convert('RGB')).astype(np.float32); h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy]).astype(np.float32)
    n = fbm(h, w, (40, 12, 4), seed)
    m = np.clip((width * (0.4 + n * 1.6) - dist) / width, 0, 1) * amt
    # corners rounder/worse
    cd = np.minimum.reduce([np.hypot(xx, yy), np.hypot(w - xx, yy), np.hypot(xx, h - yy), np.hypot(w - xx, h - yy)])
    m = np.clip(m + np.clip((width * 4 - cd) / (width * 4), 0, 1) * amt * 0.8 * n, 0, 1)
    a = a * (1 - m[..., None]) + np.array(col, np.float32) * m[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

# ------------------------------------------------------------------------------------------------ pieces
def p_coaster(w, h):
    # cork: speckled granules
    base = np.array([172, 128, 82], np.float32)
    n1 = fbm(h, w, (30, 10, 3, 1.5), 11, [0.3, 0.3, 0.25, 0.15])
    sp = np.random.default_rng(12).random((h, w)).astype(np.float32)
    sp = np.asarray(Image.fromarray((sp * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
    a = base * (0.72 + 0.55 * n1[..., None]) * (0.8 + 0.4 * sp[..., None])
    dark = (np.random.default_rng(13).random((h, w)) > 0.985)
    dark = np.asarray(Image.fromarray((dark * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
    a *= 1 - 0.5 * dark[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    # printed emblem (ink soaks into cork: patchy)
    ink = ink_layer((w, h))
    paste_c(ink, emblem(int(h * 0.50), (38, 20, 12), 230), w / 2, h * 0.42)
    d = ImageDraw.Draw(ink)
    text_c(d, w / 2, h * 0.71, "DEAN'S", F(F_CAL_B, int(h * 0.105)), (38, 20, 12, 230), spacing=int(w * 0.018))
    d.ellipse((w * 0.07, h * 0.07, w * 0.93, h * 0.93), outline=(38, 20, 12, 200), width=max(2, int(w * 0.008)))
    m = np.asarray(ink).astype(np.float32)
    patch = 0.62 + 0.38 * fbm(h, w, (20, 5, 2), 14)
    m[..., 3] *= patch
    im.alpha_composite(Image.fromarray(m.astype(np.uint8)))
    return im.convert('RGB')

def p_note(w, h):
    im = paper(w, h, (236, 228, 206), seed=21, grain=6).convert('RGBA')
    d = ImageDraw.Draw(im)
    # letterpress header: small emblem + DEAN'S, burnt orange
    oc = (150, 62, 24)
    paste_c(im, emblem(int(h * 0.12), oc), w * 0.5, h * 0.11)
    text_c(d, w * 0.5, h * 0.18, "D E A N ' S", F(F_CAL_B, int(h * 0.055)), (*oc, 255))
    d.line((w * 0.30, h * 0.275, w * 0.70, h * 0.275), fill=(*oc, 180), width=2)
    # handwriting, blue-black fountain pen
    r = np.random.default_rng(31)
    ink = ink_layer((w, h)); col = (22, 28, 58)
    f = lora(int(h * 0.096), italic=True, wght=430)
    hand(ink, w * 0.08, h * 0.33, "Stepped out for a minute.", f, col, r, rot=-1.5)
    hand(ink, w * 0.11, h * 0.49, "The record is yours —", f, col, r, rot=-1.0)
    hand(ink, w * 0.08, h * 0.65, "turn it over when it ends.", f, col, r, rot=-2.0)
    hand(ink, w * 0.62, h * 0.80, "— D.", lora(int(h * 0.13), italic=True, wght=520), col, r, rot=-3)
    ink = warp(ink, 3.0, 26, 33)
    im.alpha_composite(ink_finish(ink, 0.7))
    return wear_edges(im, 0.35, 22, (244, 238, 220), 8)

def p_matchbook(w, h):
    g = (28, 58, 40)
    im = Image.new('RGBA', (w, h), (*g, 255))
    a = np.asarray(im).astype(np.float32); n = fbm(h, w, (60, 15, 3), 41)
    a[..., :3] *= (0.85 + 0.3 * n[..., None]); im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im); cream = (226, 206, 160)
    # the cover front occupies the top 78 %; the bottom 22 % is the folded flap with the striker
    fh = int(h * 0.78)
    d.rectangle((w * 0.06, h * 0.04, w * 0.94, fh - h * 0.03), outline=(*cream, 255), width=3)
    paste_c(im, emblem(int(fh * 0.50), cream), w / 2, fh * 0.42)
    text_c(d, w / 2, fh * 0.70, "DEAN'S", F(F_CAL_B, int(h * 0.10)), (*cream, 255), spacing=6)
    text_c(d, w / 2, fh * 0.86, "地下一階 ・ jazz & coffee", F(F_JP_SANS, int(h * 0.04)), (*cream, 230))
    # flap + striker
    d.rectangle((0, fh, w, h), fill=(*[int(c * 0.8) for c in g], 255))
    sr = np.asarray(im).astype(np.float32)
    y0, y1 = int(fh + (h - fh) * 0.25), int(fh + (h - fh) * 0.75)
    grit = np.random.default_rng(42).random((y1 - y0, w))
    sr[y0:y1, :, :3] = (np.array([70, 48, 38]) * (0.6 + 0.7 * grit[..., None]))
    im = Image.fromarray(np.clip(sr, 0, 255).astype(np.uint8))
    return wear_edges(im, 0.35, 43, (120, 120, 100), 6)

def p_menu(w, h):
    im = paper(w, h, (234, 224, 198), seed=51, grain=7, stain=0.6).convert('RGBA')
    d = ImageDraw.Draw(im); br = (60, 34, 22); oc = (150, 62, 24)
    paste_c(im, emblem(int(h * 0.09), br), w / 2, h * 0.075)
    text_c(d, w / 2, h * 0.125, "DEAN'S", F(F_CAL_B, int(h * 0.055)), (*br, 255), spacing=5)
    text_c(d, w / 2, h * 0.19, "— COFFEE コーヒー —", F(F_JP, int(h * 0.032)), (*oc, 255))
    items = [("Blend", "ブレンド", "300"), ("Siphon", "サイフォン", "380"),
             ("Café au lait", "カフェオレ", "350"), ("Iced coffee", "アイス", "330"),
             ("Milk tea", "ミルクティ", "300"), ("Cheese toast", "チーズトースト", "250")]
    fe = F(F_CAL, int(h * 0.036)); fj = F(F_JP, int(h * 0.024))
    y = h * 0.26
    for en, jp, pr in items:
        d.text((w * 0.09, y), en, font=fe, fill=(*br, 255))
        d.text((w * 0.09, y + h * 0.042), jp, font=fj, fill=(*br, 200))
        pw = d.textlength('¥' + pr, font=fe)
        d.text((w * 0.91 - pw, y), '¥' + pr, font=fe, fill=(*br, 255))
        dl = w * 0.09 + d.textlength(en, font=fe) + 8
        xx = dl
        while xx < w * 0.91 - pw - 12:
            d.ellipse((xx, y + h * 0.03, xx + 2, y + h * 0.03 + 2), fill=(*br, 150)); xx += 9
        y += h * 0.092
    d.line((w * 0.2, h * 0.84, w * 0.8, h * 0.84), fill=(*oc, 200), width=2)
    text_c(d, w / 2, h * 0.86, "MORNING SET  till 11:00", F(F_CAL_I, int(h * 0.03)), (*oc, 255))
    text_c(d, w / 2, h * 0.905, "モーニング セット  ¥420", F(F_JP, int(h * 0.026)), (*br, 230))
    return wear_edges(im, 0.3, 52, (240, 232, 210), 6)

def arc_text(img, cx, cy, rad, text, font, fill, a_mid=90, spread=None, inside=False):
    d = ImageDraw.Draw(img)
    ws = [d.textlength(c, font=font) for c in text]; tot = sum(ws) * 1.12
    ang_tot = tot / rad
    a = math.radians(a_mid) + ang_tot / 2 if not inside else math.radians(a_mid) - ang_tot / 2
    for c, wd in zip(text, ws):
        da = wd * 1.12 / rad
        am = a - da / 2 if not inside else a + da / 2
        g = Image.new('RGBA', (font.size * 2, font.size * 2), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((font.size - wd / 2, font.size * 0.4), c, font=font, fill=fill)
        rot = math.degrees(am) - 90 if not inside else math.degrees(am) + 90
        g = g.rotate(rot, resample=Image.BICUBIC)
        x = cx + rad * math.cos(am); y = cy - rad * math.sin(am)
        img.alpha_composite(g, (int(x - font.size), int(y - font.size)))
        a = a - da if not inside else a + da

def p_cigar_lid(w, h):
    cream = (238, 222, 180); red = (128, 28, 22); gold = (186, 140, 58); dk = (50, 26, 16)
    im = paper(w, h, cream, seed=61, grain=8).convert('RGBA')
    d = ImageDraw.Draw(im)
    # borders
    d.rectangle((6, 6, w - 7, h - 7), outline=(*gold, 255), width=10)
    d.rectangle((22, 22, w - 23, h - 23), outline=(*red, 255), width=5)
    for i in range(0, w, 18):   # tiny repeating border dots
        d.ellipse((i + 6, 32, i + 12, 38), fill=(*gold, 255)); d.ellipse((i + 6, h - 38, i + 12, h - 32), fill=(*gold, 255))
    # side panels: laurel-ish stripes
    for x0 in (44, w - 44 - 150):
        d.rectangle((x0, 50, x0 + 150, h - 50), fill=(*red, 255))
        d.rectangle((x0 + 8, 58, x0 + 142, h - 58), outline=(*gold, 255), width=3)
        for k in range(9):
            yy = 80 + k * (h - 160) / 8
            d.ellipse((x0 + 55, yy - 12, x0 + 95, yy + 12), outline=(*gold, 255), width=3)
            d.line((x0 + 30, yy, x0 + 55, yy), fill=(*gold, 255), width=2); d.line((x0 + 95, yy, x0 + 120, yy), fill=(*gold, 255), width=2)
    # medallion with three clock faces
    cx, cy = w / 2, h * 0.47
    d.ellipse((cx - 150, cy - 150, cx + 150, cy + 150), fill=(*gold, 255))
    d.ellipse((cx - 138, cy - 138, cx + 138, cy + 138), fill=(*cream, 255), outline=(*red, 255), width=4)
    for k, (ox, oy, hh, mm) in enumerate([(-50, 38, 3, 40), (50, 38, 9, 10), (0, -16, 12, 0)]):
        x, y = cx + ox, cy + oy
        d.ellipse((x - 38, y - 38, x + 38, y + 38), fill=(250, 244, 226, 255), outline=(*dk, 255), width=4)
        for t in range(12):
            a = math.radians(t * 30); d.line((x + 30 * math.cos(a), y + 30 * math.sin(a), x + 35 * math.cos(a), y + 35 * math.sin(a)), fill=(*dk, 255), width=2)
        ah = math.radians(90 - (hh % 12) * 30 - mm * 0.5); am = math.radians(90 - mm * 6)
        d.line((x, y, x + 18 * math.cos(ah), y - 18 * math.sin(ah)), fill=(*dk, 255), width=4)
        d.line((x, y, x + 28 * math.cos(am), y - 28 * math.sin(am)), fill=(*dk, 255), width=2)
    arc_text(im, cx, cy + 4, 112, "TRES RELOJES", F(F_SERIF_B, 27), (*red, 255), a_mid=90)
    # ribbons
    d.rectangle((cx - 190, h - 120, cx + 190, h - 66), fill=(*red, 255), outline=(*gold, 255), width=3)
    text_c(d, cx, h - 112, "HECHO A MANO", F(F_SERIF_B, 28), (*cream, 255), spacing=2)
    text_c(d, cx, 52, "SELECTOS  No. 4", F(F_CAL_B, 30), (*dk, 255), spacing=3)
    im = Image.fromarray(np.asarray(im))
    return wear_edges(im, 0.45, 62, (226, 210, 170), 9)

def p_cigar_band(w, h):
    im = paper(w, h, (236, 220, 178), seed=71, grain=8).convert('RGBA'); d = ImageDraw.Draw(im)
    red = (128, 28, 22); gold = (186, 140, 58)
    d.rectangle((0, 0, w, 16), fill=(*gold, 255)); d.rectangle((0, h - 16, w, h), fill=(*gold, 255))
    text_c(d, w / 2, h * 0.24, "T R E S   R E L O J E S", F(F_SERIF_B, int(h * 0.36)), (*red, 255))
    text_c(d, w / 2, h * 0.62, "tabacos selectos  ·  25 unidades", F(F_CAL_I, int(h * 0.2)), (60, 30, 18, 255))
    return wear_edges(im, 0.4, 72, (220, 205, 165), 5)

def p_cigar_ring(w, h):
    """the house band (Tres Relojes, the same invented marque as the box): oxblood, gold lines, a cream medallion with one clock.
    x runs once around the cigar (the medallion sits in the middle = on top of the cigar as it lies), the top edge is toward the head."""
    ox = (112, 22, 20); gold = (198, 152, 66); gold_d = (140, 100, 38); cream = (240, 228, 196); dk = (48, 24, 14)
    a = np.ones((h, w, 3), np.float32) * np.array(ox, np.float32)
    a *= 0.94 + 0.12 * fbm(h, w, (40, 12, 3), 81)[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA'); d = ImageDraw.Draw(im)
    for (y0, y1, c) in ((0, 9, gold), (12, 14, gold), (h - 14, h - 12, gold), (h - 9, h, gold)):
        d.rectangle((0, y0, w, y1), fill=(*c, 255))
    for x in range(6, w, 12):                                   # a row of pin dots inside each gold line
        d.ellipse((x - 1.6, 19, x + 1.6, 22.2), fill=(*gold, 255)); d.ellipse((x - 1.6, h - 22.2, x + 1.6, h - 19), fill=(*gold, 255))
    cx, cy = w / 2, h / 2
    # medallion: slightly taller than the band's field, as on a real band
    rx, ry = 62, 66
    d.ellipse((cx - rx - 7, cy - ry - 7, cx + rx + 7, cy + ry + 7), fill=(*gold, 255))
    d.ellipse((cx - rx - 3, cy - ry - 3, cx + rx + 3, cy + ry + 3), fill=(*gold_d, 255))
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(*cream, 255))
    r = 40; yy = cy - 4
    d.ellipse((cx - r, yy - r, cx + r, yy + r), outline=(*dk, 255), width=3)
    for t in range(12):
        an = math.radians(t * 30); r0 = r - (9 if t % 3 == 0 else 6)
        d.line((cx + r0 * math.cos(an), yy + r0 * math.sin(an), cx + (r - 3) * math.cos(an), yy + (r - 3) * math.sin(an)), fill=(*dk, 255), width=3 if t % 3 == 0 else 2)
    for (hh, ln, wd) in ((1.9, 20, 4), (0.0, 29, 3)):             # five to two, more or less: after closing
        an = math.radians(hh * 30 - 90) if ln < 25 else math.radians(11 * 30 - 90)
        d.line((cx, yy, cx + ln * math.cos(an), yy + ln * math.sin(an)), fill=(*dk, 255), width=wd)
    d.ellipse((cx - 3.5, yy - 3.5, cx + 3.5, yy + 3.5), fill=(*ox, 255))
    text_c(d, cx, cy + 40, "No. 4", F(F_CAL_B, 17), (*ox, 255), spacing=1)
    # the name either side of the medallion, small print further round
    f = F(F_SERIF_B, 30)
    text_c(d, cx - 128, cy - 19, "TRES", f, (*gold, 255), spacing=3)
    text_c(d, cx + 136, cy - 19, "RELOJES", F(F_SERIF_B, 25), (*gold, 255), spacing=2)
    fs = F(F_CAL_I, 17)
    text_c(d, cx - 128, cy + 22, "selectos", fs, (*cream, 235)); text_c(d, cx + 136, cy + 22, "hecho a mano", fs, (*cream, 235))
    for x in (30, w - 30):
        d.polygon([(x, cy - 9), (x + 7, cy), (x, cy + 9), (x - 7, cy)], fill=(*gold, 255))
    return im

def _tile_y(n):
    """make a noise field wrap in y (the wrapper goes right round the cigar): cross-fade it with itself half a turn on"""
    h = n.shape[0]; y = np.arange(h, dtype=np.float32)[:, None]
    k = 1 - np.abs(2 * y / h - 1)
    return n * k + np.roll(n, h // 2, 0) * (1 - k)

def p_cigar_leaf(w, h):
    """a Cameroon-style wrapper leaf: reddish mid-brown, a little oily, toothy, wound on in a spiral with the cap at the head.
    x = along the cigar (0 foot tip .. 1 head), y = around it."""
    L_MM = 152.4; mm = w / L_MM                                   # px per millimetre along the cigar
    X = np.arange(w, dtype=np.float32)[None, :] + np.zeros((h, 1), np.float32); Y = np.arange(h, dtype=np.float32)[:, None] + np.zeros((1, w), np.float32)
    lo = np.array((96, 56, 31), np.float32); hi = np.array((143, 90, 51), np.float32)
    m = _tile_y(fbm(h, w, (120, 40, 12, 4), 91, [0.4, 0.3, 0.2, 0.1]))
    m = np.clip((m - 0.5) * 1.8 + 0.5, 0, 1)
    a = lo + (hi - lo) * m[..., None]
    # the leaf is wound on as one spiral strip: a seam every 30 mm of length, and a slow change of tone across the strip
    pitch = 30 * mm
    cap0 = 141.5 * mm                                             # the cap (a separate round of leaf) starts here
    ph = (Y / h - X / pitch) % 1.0
    body = (X < cap0 - 2).astype(np.float32)
    a *= (1 - 0.07 * (ph - 0.5) * body)[..., None]
    dpx = np.minimum(ph, 1 - ph) * h * 0.5                        # rough distance to the seam in px
    seam = np.exp(-(dpx / 1.3) ** 2) * body
    lip = np.exp(-np.clip(ph * h * 0.5, 0, 60) / 5.0) * body      # the overlapping edge catches a little light
    a *= (1 - 0.42 * seam)[..., None]; a *= (1 + 0.10 * lip * (1 - seam))[..., None]
    # veins: finer, steeper spirals, broken up
    r = np.random.default_rng(92)
    for j in range(7):
        pj = (55 + 60 * r.random()) * mm; off = r.random(); wv = 0.7 + 0.8 * r.random()
        pv = (Y / h - X / pj + off) % 1.0; dv = np.minimum(pv, 1 - pv) * h * 0.6
        brk = np.clip((_tile_y(noise2(h, w, 46, 200 + j)) - 0.38) * 3, 0, 1)
        v = np.exp(-(dv / wv) ** 2) * brk * body
        a *= (1 + 0.13 * v)[..., None]
        a *= (1 - 0.10 * np.exp(-((dv - 2.2 * wv) / wv) ** 2) * brk * body)[..., None]     # its shadow side
    # tooth: the tiny pale grains a Cameroon leaf is known for
    t = (r.random((h, w)) > 0.985).astype(np.float32)
    t = np.asarray(Image.fromarray((t * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32) / 255
    a *= (1 + 0.9 * _tile_y(t))[..., None]
    a *= (0.95 + 0.10 * _tile_y(noise2(h, w, 2.5, 93)))[..., None]
    # the cap: two fine lines round the head
    for xc, k in ((cap0, 0.40), (cap0 + 4.2 * mm, 0.30)):
        a *= (1 - k * np.exp(-((X - xc) / 1.4) ** 2))[..., None]
    # scorched for a few millimetres behind the burn line (17 mm from the foot); before that it is ash anyway
    burn = 17.0 * mm
    edge = burn + 0.6 * mm + (_tile_y(noise2(h, w, 9, 94)) - 0.5) * 1.8 * mm
    k = np.clip((X - edge) / (4.0 * mm), 0, 1); k = k * k * (3 - 2 * k)
    a = a * (0.16 + 0.84 * k)[..., None] + np.array((14, 10, 8), np.float32) * (1 - k)[..., None] * 0.6
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')

def p_flags(w, h):
    im = Image.new('RGBA', (w, h), (14, 12, 10, 255)); d = ImageDraw.Draw(im)
    f = F(F_SANS_B, int(h * 0.62))
    cells = ['¥', '', '7', '8', '0']
    cw = w / len(cells)
    for i, c in enumerate(cells):
        x0 = i * cw + 8
        if c:
            d.rounded_rectangle((x0, 10, x0 + cw - 16, h - 10), 6, fill=(236, 228, 210, 255))
            text_c(d, x0 + (cw - 16) / 2, h * 0.12, c, f, (20, 16, 12, 255))
    return im

def p_plate(w, h):
    im = Image.new('RGBA', (w, h), (176, 150, 92, 255)); d = ImageDraw.Draw(im)
    d.rectangle((4, 4, w - 5, h - 5), outline=(90, 70, 40, 255), width=3)
    text_c(d, w / 2, h * 0.12, "H O S H I D A", F(F_SERIF_B, int(h * 0.5)), (40, 28, 16, 255))
    a = np.asarray(im).astype(np.float32); n = fbm(h, w, (30, 8), 81)
    a[..., :3] *= 0.8 + 0.35 * n[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def p_keys(w, h):
    """keyboard plate of the register: columns of round keys with printed numbers (as a flat decal on the sloped deck)"""
    im = Image.new('RGBA', (w, h), (40, 36, 30, 255)); d = ImageDraw.Draw(im)
    cols, rows = 6, 5
    f = F(F_SANS_B, 18)
    for c in range(cols):
        for r_ in range(rows):
            x = (c + 0.5) * w / cols; y = (r_ + 0.5) * h / rows
            d.ellipse((x - 26, y - 20, x + 26, y + 20), fill=(222, 210, 182, 255), outline=(20, 18, 14, 255), width=2)
            n = [9, 8, 7, 6, 5][r_] if c < 5 else ['TL', 'NS', 'CH', 'RC', 'PD'][r_]
            lab = str(n) if c < 5 else n
            text_c(d, x, y - 11, lab if c >= 5 else str(n * [1, 10, 100, 1000, 1][c] if c < 4 else n), f, (30, 24, 18, 255))
    return im

def p_book(w, h):
    """full cover spread: back | spine | front ; a plain, well-read paperback of Norwegian Wood (typographic, no art)"""
    bw = int(w * 0.465); sw = w - 2 * bw   # back, spine, front widths
    crm = (230, 221, 198); grn = (34, 58, 44); ink = (32, 28, 24); mut = (96, 104, 92)
    im = paper(w, h, crm, seed=94, grain=7, stain=0.35).convert('RGBA'); d = ImageDraw.Draw(im)
    fx = bw + sw
    # FRONT (right): thin green frame, author, title, nothing else
    m = int(bw * 0.07)
    d.rectangle((fx + m, m, w - m, h - m), outline=(*grn, 255), width=3)
    d.rectangle((fx + m + 9, m + 9, w - m - 9, h - m - 9), outline=(*grn, 200), width=1)
    cx = fx + bw / 2
    text_c(d, cx, h * 0.15, "HARUKI MURAKAMI", lora(int(h * 0.034), wght=500), (*ink, 255), spacing=5)
    d.line((cx - bw * 0.10, h * 0.245, cx + bw * 0.10, h * 0.245), fill=(*grn, 255), width=2)
    text_c(d, cx, h * 0.33, "Norwegian", lora(int(h * 0.088), italic=True, wght=500), (*grn, 255))
    text_c(d, cx, h * 0.44, "Wood", lora(int(h * 0.088), italic=True, wght=500), (*grn, 255))
    text_c(d, cx, h * 0.80, "a novel", lora(int(h * 0.032), italic=True), (*mut, 255))
    # SPINE: deep green, cream lettering
    d.rectangle((bw, 0, bw + sw, h), fill=(*grn, 255))
    sp = Image.new('RGBA', (h, sw), (0, 0, 0, 0)); ds = ImageDraw.Draw(sp)
    ds.text((h * 0.06, sw * 0.22), "NORWEGIAN WOOD", font=lora(int(sw * 0.40), wght=600), fill=(*crm, 255))
    ds.text((h * 0.70, sw * 0.28), "MURAKAMI", font=lora(int(sw * 0.32), wght=500), fill=(*crm, 235))
    im.alpha_composite(sp.rotate(-90, expand=True), (bw, 0))
    # BACK (left): a few lines of plain blurb, the price
    fb = lora(int(h * 0.036), italic=True, wght=500); fs = lora(int(h * 0.026))
    text_c(d, bw / 2, h * 0.14, "Tokyo, the late sixties.", fb, (*grn, 255))
    words = ("A quiet student remembers the year he was caught between two young women: one who was slowly "
             "withdrawing from the world, and one who walked straight into his life. Years later, a song "
             "heard by chance brings all of it back.").split()
    y = h * 0.25; line = ''
    for wd in words:
        if d.textlength(line + ' ' + wd, font=fs) > bw * 0.70:
            text_c(d, bw / 2, y, line.strip(), fs, (*ink, 235)); y += h * 0.046; line = ''
        line += ' ' + wd
    text_c(d, bw / 2, y, line.strip(), fs, (*ink, 235))
    d.line((bw * 0.42, h * 0.78, bw * 0.58, h * 0.78), fill=(*grn, 255), width=2)
    text_c(d, bw / 2, h * 0.86, "\u00a5480", lora(int(h * 0.030), wght=500), (*mut, 255))
    # wear: cracked spine creases, whitened hinges, faint coffee ring on the back
    a = np.asarray(im).astype(np.float32)
    r = np.random.default_rng(91)
    for k in range(7):
        x = bw + sw * (0.15 + 0.7 * r.random()); y0 = r.random() * h * 0.3; y1 = h - r.random() * h * 0.3
        L = Image.new('L', (w, h), 0); ImageDraw.Draw(L).line((x, y0, x + r.normal() * 3, y1), fill=255, width=2)
        mm = np.asarray(L.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)[..., None] / 255 * 0.6
        a[..., :3] = a[..., :3] * (1 - mm) + np.array(crm) * mm
    for xe in (bw, bw + sw):                                  # hinge creases
        L = Image.new('L', (w, h), 0); ImageDraw.Draw(L).line((xe, 0, xe, h), fill=255, width=3)
        mm = np.asarray(L.filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)[..., None] / 255 * 0.45
        a[..., :3] = a[..., :3] * (1 - mm) + np.array(crm) * mm
    yy, xx = np.mgrid[0:h, 0:w]
    ring = np.abs(np.hypot(xx - bw * 0.62, yy - h * 0.86) - bw * 0.26)
    rm = np.clip(1 - ring / 5, 0, 1) * 0.30 * fbm(h, w, (30, 8), 92)
    a[..., :3] *= 1 - rm[..., None] * np.array([0.25, 0.4, 0.6])
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return wear_edges(im, 0.5, 93, (238, 230, 210), 7)

def p_score(w, h):
    im = paper(w, h, (232, 228, 210), seed=101, grain=6, stain=0.4).convert('RGBA'); d = ImageDraw.Draw(im)
    pr = (56, 92, 74)   # printed grid, faded green
    fpr = F(F_SANS_B, 16)
    text_c(d, w * 0.5, 10, "SCORE  CARD", F(F_SANS_B, 26), (*pr, 255), spacing=3)
    x0, x1, y0, y1 = 34, w - 20, 84, h - 92
    namew = 170; n_inn = 9; rows = 9
    cw = (x1 - x0 - namew - 60) / n_inn; rh = (y1 - y0 - 24) / rows
    d.rectangle((x0, y0, x1, y1), outline=(*pr, 255), width=3)
    for i in range(n_inn + 1):
        x = x0 + namew + i * cw
        d.line((x, y0, x, y1), fill=(*pr, 255), width=2)
        if i < n_inn: text_c(d, x + cw / 2, y0 + 2, str(i + 1), fpr, (*pr, 255))
    text_c(d, x1 - 30, y0 + 2, "R", fpr, (*pr, 255))
    for j in range(rows + 1):
        y = y0 + 24 + j * rh
        d.line((x0, y, x1, y), fill=(*pr, 255), width=2)
        if j < rows:
            for i in range(n_inn):   # printed diamonds
                cx = x0 + namew + i * cw + cw / 2; cy = y + rh / 2
                s = min(cw, rh) * 0.22
                d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], outline=(*pr, 110))
    # bottom runs row
    yb = y1 + 8
    d.rectangle((x0, yb, x1, yb + 40), outline=(*pr, 255), width=2); d.text((x0 + 8, yb + 10), "RUNS", font=fpr, fill=(*pr, 255))
    # pencil
    gr = (70, 70, 74); r = np.random.default_rng(103)
    pen = ink_layer((w, h)); fp = F(F_PENCIL, 30); fpb = F(F_PENCIL, 36)
    hand(pen, x0 + 150, 30, "Minato Gulls  at  Shirakawa Cranes", fp, gr, r, rot=-0.5, pressure=0.45)
    hand(pen, x1 - 170, 30, "Oct 12", fp, gr, r, pressure=0.45)
    names = ["Okabe  cf", "Tanimura 2b", "Rhee  ss", "Mori  1b", "Kessler lf", "Ando  3b", "Ishii  rf", "Fujita  c", "Noda  p"]
    plays = ["K", "6-3", "1B", "BB", "F8", "4-3", "K", "2B", "5-3", "1B", "F9", "HR", "K", "6-4-3", "BB", "1B", "F7", "K", "4-3", "1B"]
    k = 0
    for j, nm in enumerate(names):
        y = y0 + 24 + j * rh
        hand(pen, x0 + 6, y + rh * 0.22, nm, F(F_PENCIL, 24), gr, r, pressure=0.45)
        for i in range(7):   # the game stops after the 7th: nobody finished scoring it
            if (i * 9 + j) % 3 == 0 or (r.random() < 0.25):
                p = plays[k % len(plays)]; k += 1
                cx = x0 + namew + i * cw
                hand(pen, cx + cw * 0.18, y + rh * 0.2, p, F(F_PENCIL, 22), gr, r, pressure=0.5)
                if p in ('1B', '2B', 'HR', 'BB'):
                    ccx = cx + cw / 2; ccy = y + rh / 2; s = min(cw, rh) * 0.22
                    ImageDraw.Draw(pen).line([(ccx, ccy + s), (ccx + s, ccy)], fill=(*gr, 200), width=2)
                    if p == 'HR':
                        ImageDraw.Draw(pen).polygon([(ccx, ccy - s), (ccx + s, ccy), (ccx, ccy + s), (ccx - s, ccy)], fill=(*gr, 170))
    runs = ['0', '0', '1', '0', '2', '0', '1']
    for i, v in enumerate(runs):
        hand(pen, x0 + namew + i * cw + cw * 0.38, yb + 4, v, fpb, gr, r, pressure=0.4)
    hand(pen, x1 - 44, yb + 4, "4", fpb, gr, r)
    p = np.asarray(ink_finish(pen, 0.5)).astype(np.float32)
    p[..., 3] *= 0.55 + 0.45 * fbm(h, w, (6, 2), 104)   # graphite grain
    im.alpha_composite(Image.fromarray(p.astype(np.uint8)))
    return wear_edges(im, 0.25, 105, (240, 236, 220), 6)

PAINT = dict(coaster=p_coaster, note=p_note, matchbook=p_matchbook, menu=p_menu, cigar_lid=p_cigar_lid, cigar_band=p_cigar_band,
             flags=p_flags, plate=p_plate, cigar_ring=p_cigar_ring, book=p_book, score=p_score, keys=p_keys, cigar_leaf=p_cigar_leaf)

def main():
    os.makedirs(OUT, exist_ok=True)
    sheet = Image.new('RGB', (S, S), (128, 110, 90))
    regions = {}
    for k, (x, y, w, h) in R.items():
        im = PAINT[k](w, h).convert('RGB')
        sheet.paste(im, (x, y))
        # uv rect, inset half a pixel (v up)
        regions[k] = [(x + 0.5) / S, 1 - (y + h - 0.5) / S, (x + w - 0.5) / S, 1 - (y + 0.5) / S]
    sheet.save(os.path.join(OUT, 'sheet.png'))
    with open(os.path.join(OUT, 'regions.json'), 'w') as f: json.dump(regions, f, indent=1)
    print('wrote', os.path.join(OUT, 'sheet.png'))

if __name__ == '__main__':
    main()
