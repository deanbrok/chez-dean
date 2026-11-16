"""Paints the hifi textures (run once:  python3 blender/parts/hifi/tex.py).
   tex/close.png  2048x1024 : left half = LP sleeve cover "After Hours" (The House Trio), right half = centre label
   tex/sheet.png  2048x2048 : small printed parts (panels, dials, badges, strobe ring...)
   tex/regions.json         : uv rects (u0, v0, u1, v1) of every region in sheet.png (+ layout fractions)
All names, logos and designs are invented."""
import os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
F = dict(
    black='/usr/share/fonts/opentype/inter/Inter-Black.otf',
    bold='/usr/share/fonts/opentype/inter/Inter-Bold.otf',
    semi='/usr/share/fonts/opentype/inter/Inter-SemiBold.otf',
    med='/usr/share/fonts/opentype/inter/Inter-Medium.otf',
    reg='/usr/share/fonts/opentype/inter/Inter-Regular.otf',
    serifb='/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf',
    serif='/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf',
    serifi='/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf',
    jp='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
    jps='/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',
    mono='/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
)
RNG = np.random.default_rng(7)

def font(k, s): return ImageFont.truetype(F[k], int(s))

def text_img(txt, k, size, fill, squeeze=1.0, track=0):
    """render text to its own RGBA image (optionally condensed / letter-spaced)"""
    f = font(k, size)
    if track:
        ws = [f.getbbox(c)[2] - f.getbbox(c)[0] if c != ' ' else size * 0.3 for c in txt]
        W = int(sum(ws) + track * (len(txt) - 1) + size)
    else:
        b = f.getbbox(txt); W = int(b[2] + size // 2)
    H = int(size * 1.4)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if track:
        x = 0
        for c, w in zip(txt, ws):
            if c != ' ': d.text((x - f.getbbox(c)[0], 0), c, font=f, fill=fill)
            x += w + track
    else:
        d.text((0, 0), txt, font=f, fill=fill)
    im = im.crop(im.getbbox())
    if squeeze != 1.0: im = im.resize((max(1, int(im.width * squeeze)), im.height), Image.LANCZOS)
    return im

def paste(dst, im, x, y, anchor='lt'):
    """anchor: l/c/r + t/m/b"""
    if anchor[0] == 'c': x -= im.width // 2
    elif anchor[0] == 'r': x -= im.width
    if anchor[1] == 'm': y -= im.height // 2
    elif anchor[1] == 'b': y -= im.height
    dst.alpha_composite(im, (int(x), int(y)))

def T(dst, txt, x, y, k, size, fill, anchor='lt', squeeze=1.0, track=0):
    im = text_img(txt, k, size, fill, squeeze, track); paste(dst, im, x, y, anchor); return im

def brushed(w, h, col, streak=0.06, seed=0, vertical=False):
    r = np.random.default_rng(seed)
    if vertical: w, h = h, w
    rows = r.normal(0, 1, (h, 1)) * 0.6 + r.normal(0, 1, (h, w // 8 + 2)).repeat(8, 1)[:, :w] * 0.4
    k = np.ones(31) / 31
    rows = np.apply_along_axis(lambda a: np.convolve(a, k, mode='same'), 1, rows)
    a = np.array(col, np.float32)[None, None, :] * (1 + streak * rows[..., None])
    if vertical: a = a.transpose(1, 0, 2)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')

def grain(im, amt=6, seed=1):
    a = np.asarray(im).astype(np.float32)
    n = np.random.default_rng(seed).normal(0, amt, a.shape[:2])[..., None]
    a[..., :3] = np.clip(a[..., :3] + n, 0, 255)
    return Image.fromarray(a.astype(np.uint8))

# ======================================================================================== sleeve
def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A += [[-x, -y, -1, 0, 0, 0, u * x, u * y, u], [0, 0, 0, -x, -y, -1, v * x, v * y, v]]
    _, _, Vt = np.linalg.svd(np.array(A, float)); Hm = Vt[-1].reshape(3, 3)
    return Hm / Hm[2, 2]

def keyboard_photo(W, H):
    """grey 'photograph': piano keys receding into the dark under one lamp"""
    im = Image.new('L', (W, H), 8); d = ImageDraw.Draw(im)
    nk = 22
    Hm = homography([(0, 0), (nk, 0), (nk, 6), (0, 6)],
                    [(-0.25 * W, 0.98 * H), (0.98 * W, 0.08 * H), (1.25 * W, 0.42 * H), (0.12 * W, 1.55 * H)])
    def P(x, y):
        p = Hm @ np.array([x, y, 1.0]); return (p[0] / p[2], p[1] / p[2])
    for i in range(nk):
        poly = [P(i + 0.04, 0), P(i + 0.96, 0), P(i + 0.96, 6), P(i + 0.04, 6)]
        d.polygon(poly, fill=200)
        d.polygon([P(i + 0.04, 0), P(i + 0.96, 0), P(i + 0.96, -0.25), P(i + 0.04, -0.25)], fill=120)   # front lip
    for i in range(nk):
        if i % 7 in (0, 1, 3, 4, 5):
            x = i + 0.68
            d.polygon([P(x, 2.2), P(x + 0.62, 2.2), P(x + 0.62, 6), P(x, 6)], fill=14)
            d.polygon([P(x + 0.06, 2.2), P(x + 0.56, 2.2), P(x + 0.56, 2.45), P(x + 0.06, 2.45)], fill=70)
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32) / 255
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    lamp = np.exp(-(((xx - 0.38 * W) / (0.55 * W)) ** 2 + ((yy - 0.62 * H) / (0.50 * H)) ** 2))
    a = a * (0.08 + 1.05 * lamp)
    a += 0.06 * np.exp(-(((xx - 0.85 * W) / (0.2 * W)) ** 2 + ((yy - 0.15 * H) / (0.2 * H)) ** 2))   # haze of smoke
    a += RNG.normal(0, 0.025, a.shape)
    return np.clip(a, 0, 1)

def halftone(g, cell=7.0, ang=45):
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    u = (xx * c - yy * s) / cell; v = (xx * s + yy * c) / cell
    fu = u - np.floor(u) - 0.5; fv = v - np.floor(v) - 0.5
    dist = np.sqrt(fu * fu + fv * fv)
    dark = 1 - g
    rad = np.sqrt(np.clip(dark, 0, 1)) * 0.62
    return np.clip((rad - dist) * 6 + 0.5, 0, 1)        # 1 = ink

def sleeve(S=1024):
    cream = (226, 214, 186)
    im = Image.new('RGBA', (S, S), cream + (255,))
    # photo block, duotone halftone: burnt orange paper, black ink
    x0, y0, x1, y1 = 118, 40, S - 40, 610
    g = keyboard_photo(x1 - x0, y1 - y0)
    ink = halftone(g, 6.5)
    orange = np.array((196, 92, 30), np.float32); blk = np.array((24, 19, 17), np.float32)
    ph = orange[None, None] * (1 - ink[..., None]) + blk[None, None] * ink[..., None]
    im.paste(Image.fromarray(ph.astype(np.uint8)), (x0, y0))
    # type
    T(im, 'AFTER HOURS', x0, 642, 'black', 182, (22, 18, 16, 255), squeeze=0.62)
    T(im, 'THE HOUSE TRIO', x0 + 4, 848, 'bold', 50, (178, 76, 24, 255), track=14)
    for i in range(3):
        d = ImageDraw.Draw(im); cx = S - 70 - i * 34; d.ellipse((cx - 11, 862, cx + 11, 884), fill=(22, 18, 16, 255))
    d = ImageDraw.Draw(im)
    d.line((x0, 925, S - 40, 925), fill=(22, 18, 16, 255), width=3)
    T(im, 'LOW LAMP', x0, 945, 'black', 30, (22, 18, 16, 255), track=4)
    # lamp glyph
    lx = x0 + 230; d.polygon([(lx, 948), (lx + 26, 948), (lx + 34, 968), (lx - 8, 968)], fill=(178, 76, 24, 255))
    d.ellipse((lx + 7, 970, lx + 19, 982), fill=(178, 76, 24, 255))
    T(im, 'STEREO   LL-4011', S - 40, 950, 'semi', 26, (22, 18, 16, 255), anchor='rt', track=3)
    T(im, 'piano · bass · drums', x0, 990, 'serifi', 24, (70, 58, 48, 255))
    # 'STEREO' tab on the photo
    d.rectangle((S - 190, 62, S - 62, 104), fill=cream + (255,))
    T(im, 'STEREO', S - 126, 83, 'black', 26, (178, 76, 24, 255), anchor='cm', track=3)
    # Japanese obi strip down the left edge
    d.rectangle((0, 0, 92, S), fill=(238, 232, 218, 255))
    d.rectangle((0, 0, 92, 150), fill=(160, 32, 26, 255))
    T(im, 'JAZZ', 46, 30, 'black', 28, (240, 232, 214, 255), anchor='ct')
    T(im, '名盤', 46, 80, 'jp', 40, (240, 232, 214, 255), anchor='ct')
    y = 175
    for ch in 'アフター・アワーズ':
        if ch == 'ー':
            d.line((46, y + 6, 46, y + 38), fill=(22, 18, 16, 255), width=5); y += 46; continue
        T(im, ch, 46, y, 'jp', 40, (22, 18, 16, 255), anchor='ct'); y += 46
    y += 20
    for ch in 'ザ・ハウス・トリオ':
        T(im, ch, 46, y, 'jp', 26, (90, 30, 24, 255), anchor='ct'); y += 31
    T(im, '¥2,300', 46, S - 60, 'bold', 22, (22, 18, 16, 255), anchor='ct')
    d.line((92, 0, 92, S), fill=(170, 160, 140, 255), width=2)
    # wear: paper grain, ring wear, softened corners, faint yellowing
    a = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    rr = np.sqrt((xx - S * 0.55) ** 2 + (yy - S * 0.50) ** 2)
    ring = np.exp(-((rr - S * 0.445) / 9) ** 2) * 0.10 + np.exp(-((rr - S * 0.05) / 30) ** 2) * 0.06
    edge = np.minimum.reduce([xx, yy, S - 1 - xx, S - 1 - yy])
    wear = np.clip(1 - edge / 10, 0, 1) * 0.35
    n = RNG.normal(0, 1, (S // 4, S // 4)); n = np.asarray(Image.fromarray(n.astype(np.float32), 'F').resize((S, S), Image.BICUBIC))
    a[..., :3] = a[..., :3] * (1 - ring[..., None] * 0) + (255 - a[..., :3]) * (ring + wear)[..., None] * 0.55
    a[..., :3] *= (1 + 0.025 * n)[..., None]
    a[..., 2] *= 0.96
    im = grain(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), 5, 3)
    return im

def label(S=1024):
    cream = (232, 220, 192); ink = (26, 20, 18); orange = (190, 84, 26)
    im = Image.new('RGBA', (S, S), (0, 0, 0, 255)); d = ImageDraw.Draw(im)
    c = S // 2
    d.ellipse((0, 0, S - 1, S - 1), fill=cream + (255,))
    d.ellipse((24, 24, S - 25, S - 25), outline=orange + (255,), width=16)
    d.ellipse((52, 52, S - 53, S - 53), outline=orange + (255,), width=3)
    lay = Image.new('RGBA', (S, S), (0, 0, 0, 0)); L = ImageDraw.Draw(lay)
    # top: label logo
    lx = c - 20
    L.polygon([(lx - 6, 120), (lx + 46, 120), (lx + 62, 160), (lx - 22, 160)], fill=orange + (255,))
    L.ellipse((lx + 8, 164, lx + 32, 188), fill=orange + (255,))
    T(lay, 'LOW LAMP', c, 200, 'black', 54, ink + (255,), anchor='ct', track=10)
    T(lay, 'RECORDS · TOKYO', c, 268, 'semi', 26, ink + (255,), anchor='ct', track=6)
    T(lay, 'STEREO', 150, c - 30, 'bold', 30, ink + (255,), anchor='lm', track=3)
    T(lay, '33 1/3', S - 150, c - 30, 'bold', 32, ink + (255,), anchor='rm')
    T(lay, 'LL-4011-A', 150, c + 22, 'med', 24, ink + (255,), anchor='lm')
    T(lay, 'SIDE 1', S - 150, c + 22, 'black', 26, orange + (255,), anchor='rm', track=3)
    T(lay, 'AFTER HOURS', c, c + 92, 'black', 76, ink + (255,), anchor='ct', squeeze=0.8)
    T(lay, 'THE HOUSE TRIO', c, c + 186, 'bold', 34, orange + (255,), anchor='ct', track=8)
    for i, t in enumerate(['1. BASEMENT LIGHT  6:41', '2. NINE STEPS DOWN  5:12', '3. RAIN ON CEDAR STREET  7:03']):
        T(lay, t, c, c + 250 + i * 40, 'med', 26, ink + (255,), anchor='ct')
    T(lay, 'MADE IN JAPAN  ·  ALL RIGHTS RESERVED', c, S - 118, 'reg', 18, ink + (255,), anchor='ct', track=2)
    # printed slightly off-centre and turned, as real labels often are
    lay = lay.rotate(-2.2, resample=Image.BICUBIC, center=(c, c), translate=(5, -3))
    im.alpha_composite(lay)
    d = ImageDraw.Draw(im)
    d.ellipse((c - 40, c - 40, c + 40, c + 40), fill=(12, 10, 10, 255))       # spindle hole
    d.ellipse((c - 100, c - 100, c + 100, c + 100), outline=(205, 192, 165, 255), width=2)   # pressing ring
    im = grain(im, 4, 5)
    a = np.asarray(im).copy(); yy, xx = np.mgrid[0:S, 0:S]
    a[((xx - c) ** 2 + (yy - c) ** 2) > (c - 1) ** 2] = (10, 9, 9, 255)
    return Image.fromarray(a)

# ======================================================================================== sheet
def vu(w, h, db=None, rest=False):
    im = Image.new('RGBA', (w, h), (244, 214, 150, 255)); d = ImageDraw.Draw(im)
    a = np.asarray(im).astype(np.float32); yy, xx = np.mgrid[0:h, 0:w]
    glow = np.exp(-(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.75) / (h * 0.8)) ** 2))
    a[..., :3] *= (0.62 + 0.38 * glow)[..., None]
    im = Image.fromarray(a.astype(np.uint8)); d = ImageDraw.Draw(im)
    cx, cy, R = w / 2, h * 1.12, h * 0.80
    def ang(v): return math.radians(-48 + 96 * (v / 1.413))
    def pt(t, r): return (cx + r * math.sin(t), cy - r * math.cos(t))
    # arcs
    for v0, v1, col, wd in ((0.0, 1.0, (30, 24, 20), 3), (1.0, 1.413, (200, 30, 20), 7)):
        pts = [pt(ang(v0 + (v1 - v0) * i / 30), R) for i in range(31)]
        d.line(pts, fill=col + (255,), width=wd)
    for db_ in (-20, -10, -7, -5, -3, -1, 0, 1, 2, 3):
        v = 10 ** (db_ / 20); t = ang(v); red = db_ >= 0
        col = (200, 30, 20, 255) if red else (30, 24, 20, 255)
        d.line([pt(t, R), pt(t, R + h * 0.09)], fill=col, width=3)
        lab = str(abs(db_)) if db_ != 0 else '0'
        T(im, lab, *pt(t, R + h * 0.17), 'bold', h * 0.085, col, anchor='cm')
    for pc in (0, 20, 40, 60, 80, 100):
        t = ang(pc / 100); d.line([pt(t, R - 5), pt(t, R - h * 0.06)], fill=(30, 24, 20, 255), width=2)
    T(im, 'VU', cx, h * 0.66, 'black', h * 0.20, (30, 24, 20, 255), anchor='cm')
    T(im, '−', w * 0.10, h * 0.16, 'bold', h * 0.14, (30, 24, 20, 255), anchor='cm')
    T(im, '+', w * 0.90, h * 0.16, 'bold', h * 0.14, (200, 30, 20, 255), anchor='cm')
    T(im, 'OKABE', cx, h * 0.85, 'semi', h * 0.07, (70, 56, 44, 255), anchor='cm', track=3)
    t = math.radians(-53) if rest else ang(10 ** (db / 20))
    d.line([pt(t, h * 0.42), pt(t, R + h * 0.12)], fill=(16, 12, 10, 255), width=4)
    d.rectangle((0, h * 0.93, w, h), fill=(40, 30, 22, 255))   # needle-pivot shroud
    return im

def tuner(w, h):
    im = Image.new('RGBA', (w, h), (22, 15, 10, 255)); d = ImageDraw.Draw(im)
    cream = (250, 214, 150, 255)
    T(im, 'FM', 12, h * 0.25, 'bold', h * 0.2, cream, anchor='lm')
    T(im, 'AM', 12, h * 0.75, 'bold', h * 0.2, cream, anchor='lm')
    x0, x1 = 100, w - 30
    for i, f in enumerate(range(88, 110, 2)):
        x = x0 + (x1 - x0) * i / 10
        T(im, str(f), x, h * 0.25, 'semi', h * 0.2, cream, anchor='cm')
    for i in range(51):
        x = x0 + (x1 - x0) * i / 50; d.line((x, h * 0.44, x, h * (0.56 if i % 5 else 0.6)), fill=cream, width=2)
    for i, f in enumerate([530, 600, 700, 800, 1000, 1200, 1400, 1600]):
        x = x0 + (x1 - x0) * i / 7
        T(im, str(f), x, h * 0.76, 'semi', h * 0.18, cream, anchor='cm')
    px = x0 + (x1 - x0) * (89.4 - 88) / 20
    d.rectangle((px - 3, 4, px + 3, h - 4), fill=(235, 50, 25, 255))
    return im

def engraved(im, txt, x, y, k, size, anchor='lt', track=0, col=(28, 26, 24, 255)):
    hi = text_img(txt, k, size, (255, 255, 255, 110), track=track)
    paste(im, hi, x + 1, y + 1, anchor)
    return T(im, txt, x, y, k, size, col, anchor, track=track)

def knob_scale(im, cx, cy, r, n=11, col=(28, 26, 24, 255), w=2):
    d = ImageDraw.Draw(im)
    for i in range(n):
        t = math.radians(-135 + 270 * i / (n - 1))
        d.line((cx + r * math.sin(t), cy - r * math.cos(t), cx + (r + 8) * math.sin(t), cy - (r + 8) * math.cos(t)), fill=col, width=w)

AMP_KNOBS = [0.42, 0.58, 0.74]; AMP_TOGGLE = 0.87; AMP_PILOT = 0.94

def amp_front(w, h):
    im = brushed(w, h, (178, 176, 168), 0.07, 11)
    engraved(im, 'OKABE', 40, h * 0.30, 'serifb', h * 0.36, 'lm', track=4)
    engraved(im, 'LABORATORY', 42, h * 0.62, 'semi', h * 0.11, 'lm', track=7)
    engraved(im, 'STEREO POWER AMPLIFIER   TYPE 50', 42, h * 0.84, 'med', h * 0.085, 'lm', track=3)
    for u, lab in zip(AMP_KNOBS, ['INPUT', 'VOLUME L', 'VOLUME R']):
        engraved(im, lab, u * w, h * 0.09, 'semi', h * 0.085, 'ct', track=2)
        knob_scale(im, u * w, h * 0.55, h * 0.33)
    engraved(im, 'POWER', AMP_TOGGLE * w, h * 0.09, 'semi', h * 0.085, 'ct', track=2)
    engraved(im, 'ON', AMP_TOGGLE * w, h * 0.30, 'semi', h * 0.075, 'ct')
    engraved(im, 'OFF', AMP_TOGGLE * w, h * 0.82, 'semi', h * 0.075, 'ct')
    d = ImageDraw.Draw(im)
    d.rectangle((2, 2, w - 3, h - 3), outline=(120, 118, 112, 255), width=3)
    return grain(im, 3, 12)

PRE = dict(jack=(0.035, 0.35), vu1=(0.07, 0.17, 0.22, 0.83), vu2=(0.235, 0.17, 0.385, 0.83),
           tuner=(0.42, 0.56, 0.82, 0.88), knobs=[0.46, 0.56, 0.66, 0.76], knob_v=0.27, tune=(0.905, 0.5))

def pre_front(w, h):
    im = brushed(w, h, (196, 184, 158), 0.06, 13); d = ImageDraw.Draw(im)
    for k in ('vu1', 'vu2', 'tuner'):
        u0, v0, u1, v1 = PRE[k]
        d.rectangle((u0 * w - 6, (1 - v1) * h - 6, u1 * w + 6, (1 - v0) * h + 6), fill=(30, 26, 22, 255))
    engraved(im, 'PHONES', PRE['jack'][0] * w, (1 - 0.72) * h, 'semi', h * 0.075, 'ct', track=1)
    for u, lab in zip(PRE['knobs'], ['BASS', 'TREBLE', 'BALANCE', 'SELECTOR']):
        engraved(im, lab, u * w, (1 - 0.48) * h, 'semi', h * 0.07, 'ct', track=1)
        knob_scale(im, u * w, (1 - PRE['knob_v']) * h, h * 0.13, 9, w=2)
    engraved(im, 'OKABE  PR-2', 0.905 * w, h * 0.06, 'serifb', h * 0.12, 'ct', track=2)
    engraved(im, 'TUNING', 0.905 * w, h * 0.84, 'semi', h * 0.07, 'ct', track=2)
    engraved(im, 'FM STEREO', 0.62 * w, h * 0.02, 'semi', h * 0.065, 'ct', track=3)
    d.rectangle((2, 2, w - 3, h - 3), outline=(130, 120, 100, 255), width=3)
    return grain(im, 3, 14)

REEL = dict(vu1=(0.03, 0.40, 0.20, 0.86), vu2=(0.22, 0.40, 0.39, 0.86), counter=(0.43, 0.60, 0.555, 0.80), reset=(0.585, 0.70),
            levers=[0.66, 0.765, 0.87], lever_v=0.64, knobs=[0.08, 0.20, 0.32], knob_v=0.18, speed=(0.47, 0.18),
            power=(0.93, 0.18), pilot=(0.93, 0.42), phones=(0.80, 0.18))

def reel_lower(w, h):
    im = brushed(w, h, (40, 38, 36), 0.10, 21); d = ImageDraw.Draw(im)
    wh = (226, 222, 210, 255)
    for k in ('vu1', 'vu2', 'counter'):
        u0, v0, u1, v1 = REEL[k]
        d.rectangle((u0 * w - 4, (1 - v1) * h - 4, u1 * w + 4, (1 - v0) * h + 4), fill=(12, 11, 10, 255), outline=(150, 148, 140, 255), width=2)
    T(im, 'TAPE COUNTER', (REEL['counter'][0] + REEL['counter'][2]) / 2 * w, (1 - 0.88) * h, 'semi', h * 0.05, wh, 'ct', track=2)
    T(im, 'RESET', REEL['reset'][0] * w, (1 - 0.56) * h, 'semi', h * 0.045, wh, 'ct')
    for u, lab in zip(REEL['levers'], ['MODE', 'PLAY', 'REC']):
        T(im, lab, u * w, (1 - 0.92) * h, 'semi', h * 0.05, wh if lab != 'REC' else (230, 70, 50, 255), 'ct', track=1)
        d.rectangle((u * w - 8, (1 - 0.86) * h, u * w + 8, (1 - 0.45) * h), fill=(10, 10, 10, 255))
    for u, lab in zip(REEL['knobs'], ['LINE', 'MIC', 'OUTPUT']):
        T(im, lab, u * w, (1 - 0.34) * h, 'semi', h * 0.05, wh, 'ct', track=1)
        knob_scale(im, u * w, (1 - REEL['knob_v']) * h, h * 0.10, 11, col=wh)
    T(im, 'SPEED', REEL['speed'][0] * w, (1 - 0.34) * h, 'semi', h * 0.05, wh, 'ct', track=1)
    T(im, '9.5', REEL['speed'][0] * w - 46, (1 - 0.18) * h, 'semi', h * 0.045, wh, 'rm')
    T(im, '19', REEL['speed'][0] * w + 46, (1 - 0.18) * h, 'semi', h * 0.045, wh, 'lm')
    T(im, 'POWER', REEL['power'][0] * w, (1 - 0.34) * h, 'semi', h * 0.05, wh, 'ct', track=1)
    T(im, 'SHIRANE', 0.62 * w, (1 - 0.30) * h, 'serifb', h * 0.12, wh, 'lm', track=3)
    T(im, 'TR-7  3-HEAD', 0.62 * w, (1 - 0.14) * h, 'semi', h * 0.05, wh, 'lm', track=2)
    d.rectangle((1, 1, w - 2, h - 2), outline=(90, 88, 84, 255), width=2)
    return grain(im, 3, 22)

def counter(w, h):
    im = Image.new('RGBA', (w, h), (10, 10, 10, 255))
    n = 4; cw = w / n
    for i, ch in enumerate('0347'):
        cell = Image.new('RGBA', (int(cw - 6), h - 8), (232, 228, 216, 255)); a = np.asarray(cell).astype(np.float32)
        yy = np.linspace(-1, 1, a.shape[0])[:, None]; a[..., :3] *= (1 - 0.55 * yy ** 2)[..., None]
        cell = Image.fromarray(a.astype(np.uint8)); T(cell, ch, cell.width / 2, cell.height / 2, 'bold', h * 0.62, (16, 14, 12, 255), 'cm')
        im.alpha_composite(cell, (int(i * cw + 3), 4))
    return im

SPK_KNOBS = [0.66, 0.86]

def spk_plate(w, h):
    im = brushed(w, h, (170, 166, 156), 0.07, 31)
    engraved(im, 'HAZAMA', 26, h * 0.34, 'serifb', h * 0.30, 'lm', track=5)
    engraved(im, 'STUDIO MONITOR  M-15', 28, h * 0.66, 'semi', h * 0.085, 'lm', track=2)
    engraved(im, 'ACOUSTIC WORKS · KAWASAKI', 28, h * 0.84, 'med', h * 0.06, 'lm', track=2)
    for u, lab in zip(SPK_KNOBS, ['MID', 'HIGH']):
        engraved(im, lab, u * w, h * 0.06, 'semi', h * 0.08, 'ct', track=2)
        knob_scale(im, u * w, h * 0.55, h * 0.22, 7)
        engraved(im, '−', u * w - h * 0.30, h * 0.80, 'med', h * 0.06, 'cm')
        engraved(im, '+', u * w + h * 0.30, h * 0.80, 'med', h * 0.06, 'cm')
    d = ImageDraw.Draw(im); d.rectangle((2, 2, w - 3, h - 3), outline=(110, 108, 100, 255), width=3)
    for x, y in ((12, 12), (w - 13, 12), (12, h - 13), (w - 13, h - 13)):
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(120, 116, 108, 255), outline=(70, 68, 64, 255))
    return grain(im, 3, 32)

def np_plate(w, h):
    a = np.asarray(brushed(w, h, (176, 132, 62), 0.10, 41)).astype(np.float32)
    im = Image.fromarray(a.astype(np.uint8))
    engraved(im, 'NOW PLAYING', w / 2, h / 2, 'serifb', h * 0.50, 'cm', track=6, col=(40, 26, 12, 255))
    d = ImageDraw.Draw(im); d.rectangle((3, 3, w - 4, h - 4), outline=(110, 76, 30, 255), width=3)
    for x in (14, w - 15): d.ellipse((x - 6, h / 2 - 6, x + 6, h / 2 + 6), fill=(130, 96, 44, 255), outline=(70, 48, 20, 255))
    return grain(im, 4, 42)

def tt_badge(w, h):
    im = brushed(w, h, (186, 184, 178), 0.05, 51)
    T(im, 'HAYASE', 14, h / 2, 'black', h * 0.55, (24, 22, 20, 255), 'lm', track=6)
    T(im, 'BD-3   BELT DRIVE   2-SPEED', w - 14, h / 2, 'semi', h * 0.26, (40, 38, 34, 255), 'rm', track=3)
    return im

def speed_top(s):
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=(22, 21, 20, 255)); d.ellipse((8, 8, s - 9, s - 9), outline=(70, 68, 64, 255), width=2)
    d.rectangle((s / 2 - 3, 10, s / 2 + 3, s / 2), fill=(236, 230, 214, 255))
    T(im, '33', s * 0.28, s * 0.66, 'bold', s * 0.17, (236, 230, 214, 255), 'cm')
    T(im, '45', s * 0.72, s * 0.66, 'bold', s * 0.17, (236, 230, 214, 255), 'cm')
    return im

def dial_top(s):
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=(24, 22, 20, 255))
    c = s / 2
    for i in range(13):
        t = math.radians(-120 + 240 * i / 12); r0 = s * (0.36 if i % 4 else 0.30)
        d.line((c + r0 * math.sin(t), c - r0 * math.cos(t), c + s * 0.46 * math.sin(t), c - s * 0.46 * math.cos(t)), fill=(230, 226, 214, 255), width=2)
    d.line((c, c, c + s * 0.25 * math.sin(0.5), c - s * 0.25 * math.cos(0.5)), fill=(220, 60, 40, 255), width=3)
    return im

def cw_scale(w, h):
    im = brushed(w, h, (150, 148, 144), 0.05, 61); d = ImageDraw.Draw(im)
    for i in range(41):
        x = 8 + (w - 16) * i / 40
        d.line((x, 0, x, h * (0.55 if i % 10 == 0 else 0.3)), fill=(20, 20, 20, 255), width=2)
        if i % 10 == 0: T(im, str(i // 10), x, h * 0.78, 'bold', h * 0.36, (20, 20, 20, 255), 'cm')
    return im

def strobe(w, h):
    im = brushed(w, h, (200, 200, 196), 0.05, 71); d = ImageDraw.Draw(im)
    rows = [45, 54, 40, 36]; rh = h / (len(rows) + 0.6)
    for i, n in enumerate(rows):
        y0 = rh * (0.3 + i) + rh * 0.22; y1 = y0 + rh * 0.5
        for j in range(n):
            x = w * j / n; d.rectangle((x + 2, y0, x + w / n * 0.38, y1), fill=(40, 40, 40, 255))
    d.line((0, 1, w, 1), fill=(120, 120, 116, 255), width=2); d.line((0, h - 2, w, h - 2), fill=(120, 120, 116, 255), width=2)
    return im

def pack(items, W=2048, pad=6):
    """simple shelf packer: items name -> image; returns positions"""
    pos = {}; x = y = 0; rowh = 0
    for k, im in sorted(items.items(), key=lambda kv: -kv[1].height):
        if x + im.width > W: x = 0; y += rowh + pad; rowh = 0
        pos[k] = (x, y); x += im.width + pad; rowh = max(rowh, im.height)
    assert y + rowh <= W, 'sheet overflow'
    return pos

def main():
    os.makedirs(D, exist_ok=True)
    close = Image.new('RGBA', (2048, 1024), (0, 0, 0, 255))
    close.paste(sleeve(1024), (0, 0)); close.paste(label(1024), (1024, 0))
    close.convert('RGB').save(os.path.join(D, 'close.png'))
    items = dict(
        strobe=strobe(1536, 112), amp_front=amp_front(1400, 200), pre_front=pre_front(1400, 204),
        reel_lower=reel_lower(1000, 326), counter=counter(240, 80), spk_plate=spk_plate(600, 220),
        np_plate=np_plate(420, 110), tt_badge=tt_badge(616, 80), speed_top=speed_top(160), dial_top=dial_top(128),
        cw_scale=cw_scale(512, 48), vu_a=vu(400, 240, -5), vu_b=vu(400, 240, -3.2), vu_rest=vu(400, 240, rest=True),
        tuner=tuner(1000, 120),
    )
    pos = pack(items)
    sheet = Image.new('RGBA', (2048, 2048), (128, 128, 128, 255))
    reg = {}
    for k, im in items.items():
        x, y = pos[k]; sheet.alpha_composite(im, (x, y))
        # inset half a texel; uv v counts from the bottom of the image
        reg[k] = ((x + 0.5) / 2048, 1 - (y + im.height - 0.5) / 2048, (x + im.width - 0.5) / 2048, 1 - (y + 0.5) / 2048)
    sheet.convert('RGB').save(os.path.join(D, 'sheet.png'))
    meta = dict(regions=reg, amp=dict(knobs=AMP_KNOBS, toggle=AMP_TOGGLE, pilot=AMP_PILOT), pre=PRE, reel=REEL, spk=dict(knobs=SPK_KNOBS))
    json.dump(meta, open(os.path.join(D, 'regions.json'), 'w'), indent=1)
    print('wrote', D)

if __name__ == '__main__':
    main()
