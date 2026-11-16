"""Paints the lounge textures into tex/:  sheet.png (2048^2: posters, clock face, dial, photo, music, labels)
and map.jpg (the framed chart, cropped from the project's own invented map).  Run:  python3 tex.py
Region rectangles (px, x y w h, origin top-left) are written to tex/regions.json for build.py."""
import os, json, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tex')
S = 2048
TG = '/usr/share/texmf/fonts/opentype/public/tex-gyre/'
F = dict(
    chorus=TG + 'texgyrechorus-mediumitalic.otf',
    bonum=TG + 'texgyrebonum-bold.otf',
    bonum_r=TG + 'texgyrebonum-regular.otf',
    heros_cn=TG + 'texgyreheroscn-bold.otf',
    adventor=TG + 'texgyreadventor-bold.otf',
    pagella_i=TG + 'texgyrepagella-italic.otf',
    schola=TG + 'texgyreschola-bold.otf',
    jp='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
    jps='/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',
)
REG = dict(
    posterA=(0, 0, 640, 904), posterB=(640, 0, 640, 904),
    clock=(1280, 0, 768, 768), dial=(1280, 768, 384, 384), photo=(1680, 768, 288, 384),
    music0=(0, 1160, 480, 624), music1=(480, 1160, 480, 624), music2=(960, 1160, 480, 624),
    name=(1440, 1160, 608, 96), directory=(1440, 1260, 320, 436), memo=(1776, 1260, 200, 280),
    label=(1776, 1548, 256, 128), books=(0, 920, 960, 160),
)

def font(k, size, idx=0):
    return ImageFont.truetype(F[k], size, index=idx)

def cat(h):
    im = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'barkit', 'cat_emblem.png')).convert('RGBA')
    im = im.crop(im.getbbox())
    w = int(im.width * h / im.height)
    return im.resize((w, h), Image.LANCZOS)

def ctext(d, cx, y, s, f, fill, spacing=0):
    if spacing:
        ws = [d.textlength(c, font=f) for c in s]; tot = sum(ws) + spacing * (len(s) - 1); x = cx - tot / 2
        for c, w in zip(s, ws):
            d.text((x, y), c, font=f, fill=fill); x += w + spacing
    else:
        w = d.textlength(s, font=f); d.text((cx - w / 2, y), s, font=f, fill=fill)

def fbm(h, w, rng, octaves=5, base=4):
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((n + 1, int(n * w / h) + 2)).astype(np.float32)
        im = Image.fromarray(g, 'F').resize((w, h), Image.BICUBIC)
        out += np.asarray(im) * amp; tot += amp; amp *= 0.5
    return out / tot

def age(img, rng, yellow=0.35, stain=0.25, edge=0.35, fold=None):
    """yellowed paper: multiply toward nicotine, blotches, darker edges, optional fold lines"""
    a = np.asarray(img).astype(np.float32) / 255.0
    h, w = a.shape[:2]
    n = fbm(h, w, rng)
    tint = np.array([1.0, 0.90, 0.68], np.float32)
    k = yellow * (0.6 + 0.8 * n)[..., None]
    a = a * (1 - k) + a * tint * k
    # blotches
    b = np.clip((fbm(h, w, rng, 4, 3) - 0.55) * 4, 0, 1)[..., None]
    a = a * (1 - stain * b * np.array([0.25, 0.4, 0.7]))
    # edge darkening
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dd = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / (0.06 * min(h, w))
    e = np.clip(1 - dd, 0, 1) ** 2 * (0.6 + 0.6 * n)
    a = a * (1 - edge * e[..., None] * np.array([0.35, 0.5, 0.8]))
    if fold:
        for (axis, pos) in fold:
            if axis == 'h': d = np.abs(yy - pos * h)
            else: d = np.abs(xx - pos * w)
            l = np.exp(-(d / 2.0) ** 2) * 0.12 - np.exp(-((d - 3) / 2.0) ** 2) * 0.05
            a = a * (1 - l[..., None])
    # paper grain
    g = rng.normal(0, 0.012, (h, w)).astype(np.float32)[..., None]
    a = np.clip(a + g, 0, 1)
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8))

# ------------------------------------------------------------------------------------------------- posters
def poster_a(w, h, rng):
    """THE HOUSE TRIO, every Thursday at DEAN'S: mustard, burnt orange moon, black cat from behind"""
    S2 = 2; W, H = w * S2, h * S2
    MUST = (214, 160, 52); ORANGE = (196, 82, 34); INK = (28, 22, 20); CREAM = (238, 226, 196)
    size = (W, H)
    def L(): return Image.new('L', size, 0)
    # cream border + mustard field
    m_must = L(); ImageDraw.Draw(m_must).rectangle((40, 40, W - 40, H - 40), fill=255)
    m_moon = L(); ImageDraw.Draw(m_moon).ellipse((W * 0.18, H * 0.20, W * 0.82, H * 0.20 + W * 0.64), fill=255)
    # stripes at the bottom of the moon (60s sunset bands)
    d = ImageDraw.Draw(m_moon)
    for i in range(5):
        y = H * 0.20 + W * 0.44 + i * 22
        d.rectangle((0, y, W, y + 8 + i * 2), fill=0)
    m_cat = L(); c = cat(int(H * 0.40))
    m_cat.paste(c.split()[3], (int(W / 2 - c.width / 2), int(H * 0.29)))
    # floor line under the cat
    ImageDraw.Draw(m_cat).rectangle((W * 0.12, H * 0.29 + c.height - 6, W * 0.88, H * 0.29 + c.height + 4), fill=255)
    m_txt = L(); dt = ImageDraw.Draw(m_txt)
    ctext(dt, W / 2, 70, 'THE HOUSE', font('heros_cn', 150), 255, spacing=6)
    ctext(dt, W / 2, 210, 'TRIO', font('heros_cn', 230), 255, spacing=24)
    y = H * 0.29 + c.height + 40
    ctext(dt, W / 2, y, 'EVERY THURSDAY', font('adventor', 64), 255, spacing=10)
    ctext(dt, W / 2, y + 90, 'from 9 p.m. till the last set', font('pagella_i', 52), 255)
    m_or = L(); do = ImageDraw.Draw(m_or)
    do.rectangle((40, H - 270, W - 40, H - 40), fill=255)
    m_txt2 = L(); d2 = ImageDraw.Draw(m_txt2)
    ctext(d2, W / 2, H - 262, "DEAN'S", font('schola', 110), 255, spacing=14)
    ctext(d2, W / 2, H - 112, '毎週木曜 ・ 地下一階 ・ 入場無料', font('jp', 40), 255)
    im = Image.new('RGB', size, CREAM)
    for m, col, off in ((m_must, MUST, (0, 0)), (m_moon, ORANGE, (5, -3)), (m_cat, INK, (0, 0)), (m_txt, INK, (-3, 2)),
                        (m_or, INK, (0, 0)), (m_txt2, MUST, (4, 3))):
        if off != (0, 0):
            m2 = L(); m2.paste(m, off); m = m2
        im.paste(Image.new('RGB', size, col), (0, 0), m)
    im = im.resize((w, h), Image.LANCZOS)
    # pin holes / tape marks
    d = ImageDraw.Draw(im)
    for (x, y) in ((14, 14), (w - 16, 15)):
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(70, 55, 40))
    return age(im, rng, yellow=0.42, stain=0.3, edge=0.45, fold=[('h', 0.5), ('v', 0.5)])

def poster_b(w, h, rng):
    """AFTER HOURS SESSION — late Saturday, an invented quartet; cream, bottle green, oxblood, interlocking half-moons"""
    S2 = 2; W, H = w * S2, h * S2; size = (W, H)
    CREAM = (234, 222, 192); GREEN = (36, 84, 60); OX = (128, 34, 30); INK = (30, 26, 22); OCH = (200, 140, 50)
    def L(): return Image.new('L', size, 0)
    m_g = L(); dg = ImageDraw.Draw(m_g)
    m_o = L(); do = ImageDraw.Draw(m_o)
    # a column of alternating half-discs (like piano hammers / records), the 60s modernist grid
    r = W * 0.16; x0 = W * 0.22
    for i in range(4):
        cy = H * 0.12 + i * r * 1.25
        dg.pieslice((x0 - r, cy - r, x0 + r, cy + r), 90, 270, fill=255)
        do.pieslice((x0 - r + r * 0.25, cy - r, x0 + r + r * 0.25, cy + r), 270, 90, fill=255)
    # big bar
    do.rectangle((W * 0.50, H * 0.10, W * 0.56, H * 0.62), fill=255)
    dg.rectangle((W * 0.62, H * 0.10, W * 0.90, H * 0.14), fill=255)
    m_och = L(); ImageDraw.Draw(m_och).ellipse((W * 0.62, H * 0.17, W * 0.90, H * 0.17 + W * 0.28), fill=255)
    m_t = L(); dt = ImageDraw.Draw(m_t)
    ft = font('heros_cn', 120)
    for i, wd in enumerate(['AFTER', 'HOURS', 'SESSION']):
        dt.text((W * 0.60, H * 0.36 + i * 120), wd, font=ft, fill=255)
    dt.text((W * 0.07, H * 0.66), 'the hollow reed', font=font('pagella_i', 92), fill=255)
    dt.text((W * 0.07, H * 0.66 + 100), 'QUARTET', font=font('adventor', 96), fill=255)
    dt.text((W * 0.07, H * 0.66 + 230), 'saturdays  ·  11 p.m.  ·  late', font=font('adventor', 46), fill=255)
    dt.text((W * 0.07, H * 0.66 + 300), '土曜深夜  ジャズ・セッション', font=font('jp', 50), fill=255)
    m_bar = L(); ImageDraw.Draw(m_bar).rectangle((0, H - 150, W, H), fill=255)
    m_t2 = L(); d2 = ImageDraw.Draw(m_t2)
    d2.text((W * 0.07, H - 128), "DEAN'S", font=font('schola', 92), fill=255)
    c = cat(118); m_t2.paste(c.split()[3], (int(W * 0.86 - c.width / 2), H - 136))
    im = Image.new('RGB', size, CREAM)
    for m, col, off in ((m_g, GREEN, (0, 0)), (m_o, OX, (4, 4)), (m_och, OCH, (-3, 2)), (m_t, INK, (0, 0)), (m_bar, GREEN, (0, 0)), (m_t2, CREAM, (3, -2))):
        if off != (0, 0):
            m2 = L(); m2.paste(m, off); m = m2
        im.paste(Image.new('RGB', size, col), (0, 0), m)
    im = im.resize((w, h), Image.LANCZOS)
    return age(im, rng, yellow=0.5, stain=0.35, edge=0.5, fold=[('h', 0.33), ('h', 0.66)])

# ------------------------------------------------------------------------------------------------- clock face
def clock_face(n, rng):
    S2 = 2; N = n * S2; c = N / 2
    im = Image.new('RGB', (N, N), (232, 220, 192)); d = ImageDraw.Draw(im)
    R = N / 2
    d.ellipse((0, 0, N - 1, N - 1), fill=(226, 213, 182))
    # minute track: double ring + ticks
    for rr, wdt in ((R * 0.90, 4), (R * 0.82, 3)):
        d.ellipse((c - rr, c - rr, c + rr, c + rr), outline=(30, 26, 22), width=wdt)
    for i in range(60):
        a = math.radians(i * 6)
        r0, r1 = (R * 0.80, R * 0.92) if i % 5 == 0 else (R * 0.82, R * 0.90)
        wdt = 9 if i % 5 == 0 else 3
        d.line((c + r0 * math.sin(a), c - r0 * math.cos(a), c + r1 * math.sin(a), c - r1 * math.cos(a)), fill=(30, 26, 22), width=wdt)
    f = font('bonum', int(N * 0.115))
    for i in range(1, 13):
        a = math.radians(i * 30); r = R * 0.66
        s = str(i); x = c + r * math.sin(a); y = c - r * math.cos(a)
        bb = d.textbbox((0, 0), s, font=f)
        d.text((x - (bb[2] + bb[0]) / 2, y - (bb[3] + bb[1]) / 2), s, font=f, fill=(28, 24, 20))
    ctext(d, c, c - R * 0.40, 'ARDLEY', font('bonum_r', int(N * 0.045)), (40, 34, 28), spacing=8)
    ctext(d, c, c + R * 0.28, 'YOKOHAMA', font('bonum_r', int(N * 0.030)), (60, 50, 40), spacing=6)
    ctext(d, c, c + R * 0.36, '8 DAY', font('bonum_r', int(N * 0.026)), (60, 50, 40), spacing=4)
    # winding holes
    for dx in (-R * 0.22, R * 0.22):
        x, y, r = c + dx, c + R * 0.12, R * 0.045
        d.ellipse((x - r * 1.5, y - r * 1.5, x + r * 1.5, y + r * 1.5), fill=(180, 150, 90))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(20, 16, 12))
    im = im.resize((n, n), Image.LANCZOS)
    # age: radial yellowing toward the rim, one hairline crack
    a = np.asarray(im).astype(np.float32) / 255
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); rr = np.hypot(xx - n / 2, yy - n / 2) / (n / 2)
    nn = fbm(n, n, rng)
    k = np.clip(0.15 + 0.5 * rr ** 3, 0, 1) * (0.6 + 0.8 * nn)
    a = a * (1 - 0.35 * k[..., None] * np.array([0.1, 0.3, 0.7]))
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    pts = [(n * 0.71, n * 0.22)]
    for i in range(9):
        x, y = pts[-1]; pts.append((x + rng.uniform(4, 11), y + rng.uniform(-3, 9)))
    d.line(pts, fill=(150, 132, 104), width=1)
    return im

# ------------------------------------------------------------------------------------------------- phone dial
def dial(n):
    S2 = 4; N = n * S2; c = N / 2; R = N / 2
    PINK = (214, 128, 116); PL = (226, 150, 138)
    im = Image.new('RGB', (N, N), PINK); d = ImageDraw.Draw(im)
    # number card (white ring) under the finger wheel
    d.ellipse((c - R * 0.97, c - R * 0.97, c + R * 0.97, c + R * 0.97), fill=(150, 76, 68))
    d.ellipse((c - R * 0.93, c - R * 0.93, c + R * 0.93, c + R * 0.93), fill=PL)       # finger wheel plate
    f = font('heros_cn', int(N * 0.085))
    nums = '1234567890'
    for i, s in enumerate(nums):
        a = math.radians(60 - 30 * i); r = R * 0.68
        x, y = c + r * math.sin(a), c - r * math.cos(a); hr = R * 0.17
        d.ellipse((x - hr - 6, y - hr - 6, x + hr + 6, y + hr + 6), fill=(120, 58, 52))    # hole shadow rim
        d.ellipse((x - hr, y - hr, x + hr, y + hr), fill=(246, 242, 232))               # the white card seen through the hole
        bb = d.textbbox((0, 0), s, font=f)
        d.text((x - (bb[2] + bb[0]) / 2, y - (bb[3] + bb[1]) / 2 + hr * 0.1), s, font=f, fill=(20, 18, 18))
        d.arc((x - hr, y - hr, x + hr, y + hr), 200, 340, fill=(150, 140, 130), width=8)   # inner shade at top of hole
    # centre card
    rc = R * 0.34
    d.ellipse((c - rc - 10, c - rc - 10, c + rc + 10, c + rc + 10), fill=(190, 186, 176))
    d.ellipse((c - rc, c - rc, c + rc, c + rc), fill=(244, 238, 222))
    ctext(d, c, c - rc * 0.62, '電話', font('jp', int(rc * 0.42)), (150, 40, 34))
    ctext(d, c, c + rc * 0.05, '10円', font('jp', int(rc * 0.36)), (30, 28, 26))
    d.line((c - rc * 0.6, c + rc * 0.02, c + rc * 0.6, c + rc * 0.02), fill=(150, 40, 34), width=4)
    return im.resize((n, n), Image.LANCZOS)

# ------------------------------------------------------------------------------------------------- photograph
def photo(w, h, rng):
    """indistinct: two figures on a pale shore, overexposed sky, all soft"""
    a = np.zeros((h, w, 3), np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) / np.array([h, w], np.float32)[:, None, None]
    sky = np.array([0.86, 0.80, 0.66]); sea = np.array([0.52, 0.48, 0.40]); sand = np.array([0.74, 0.66, 0.52])
    hz = 0.46 + 0.01 * np.sin(xx * 6)
    a[:] = sky
    a[yy > hz] = sea
    shore = 0.62 + 0.05 * np.sin(xx * 3 + 1)
    a[yy > shore] = sand
    im = Image.fromarray((a * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for (cx, s) in ((0.40, 1.0), (0.55, 0.88)):
        x = cx * w; y = 0.66 * h; hh = 0.30 * h * s
        d.ellipse((x - 0.035 * w * s, y - hh, x + 0.035 * w * s, y - hh + 0.07 * w * s), fill=(60, 50, 42))
        d.polygon([(x - 0.06 * w * s, y - hh + 0.07 * w * s), (x + 0.06 * w * s, y - hh + 0.07 * w * s), (x + 0.05 * w * s, y), (x - 0.05 * w * s, y)], fill=(55, 46, 40))
    im = im.filter(ImageFilter.GaussianBlur(w * 0.022))
    a = np.asarray(im).astype(np.float32) / 255
    r = np.hypot(xx - 0.5, yy - 0.5)
    a = a * (1 - 0.6 * np.clip(r - 0.25, 0, 1)[..., None] ** 1.2)
    a = a * np.array([1.0, 0.92, 0.76])            # sepia
    a = np.clip(a + rng.normal(0, 0.02, a.shape[:2])[..., None], 0, 1)
    im = Image.fromarray((a * 255).astype(np.uint8))
    out = Image.new('RGB', (w, h), (236, 228, 208)); out.paste(im.resize((w - 28, h - 28)), (14, 14))   # white border print
    return out

# ------------------------------------------------------------------------------------------------- hand-copied music
def music(w, h, rng, title=None):
    S2 = 2; W, H = w * S2, h * S2
    im = Image.new('RGB', (W, H), (232, 222, 196)); d = ImageDraw.Draw(im)
    INK = (34, 32, 52); STAFF = (120, 100, 90)
    m = W * 0.07; top = H * 0.12 if title else H * 0.06
    if title:
        ctext(d, W / 2, H * 0.025, title, font('chorus', int(H * 0.042)), INK)
        d.text((W * 0.70, H * 0.075), '— for the late set', font=font('chorus', int(H * 0.022)), fill=INK)
    nst = 9; gap = (H * 0.95 - top) / nst; sp = gap * 0.085
    fch = font('chorus', int(sp * 2.6))
    for s in range(nst):
        y0 = top + s * gap + gap * 0.3
        for i in range(5):
            y = y0 + i * sp + rng.uniform(-0.6, 0.6)
            d.line((m, y, W - m, y + rng.uniform(-1.5, 1.5)), fill=STAFF, width=2)
        # clef-ish hand mark and a key signature
        cx = m + sp * 0.8
        d.arc((cx - sp, y0 + sp * 1.2, cx + sp, y0 + sp * 3.4), 30, 330, fill=INK, width=4)
        d.line((cx + sp * 0.2, y0 - sp * 0.8, cx - sp * 0.2, y0 + sp * 5), fill=INK, width=4)
        for k in range(2):
            kx = cx + sp * 1.6 + k * sp * 0.9; ky = y0 + sp * (1.0 + k * 1.5)
            d.line((kx, ky - sp * 1.6, kx, ky + sp * 0.5), fill=INK, width=3)
            d.arc((kx - sp * 0.1, ky - sp * 0.4, kx + sp * 0.8, ky + sp * 0.5), 270, 110, fill=INK, width=3)
        # bars
        nb = 4; bx0 = cx + sp * 4; bw = (W - m - bx0) / nb
        for b in range(nb + 1):
            x = bx0 + b * bw
            d.line((x, y0, x + rng.uniform(-1, 1), y0 + 4 * sp), fill=INK, width=3)
        for b in range(nb):
            # chord symbol above the bar (invented sequence, not a real tune)
            if rng.random() < 0.8:
                root = rng.choice('CDEFGAB') + rng.choice(['', '', 'b'])
                q = rng.choice(['m7', '7', 'maj7', 'm7b5', '6', '9', ''])
                d.text((bx0 + b * bw + sp * 0.5, y0 - sp * 3.2), root + q, font=fch, fill=INK)
            nn = rng.choice([2, 3, 4, 4, 6, 8])
            xs = [bx0 + b * bw + bw * (0.12 + 0.8 * j / nn) for j in range(nn)]
            prev = None
            for j, x in enumerate(xs):
                st = rng.randint(-2, 9)
                y = y0 + 4 * sp - st * sp / 2
                x += rng.uniform(-2, 2)
                filled = nn > 2 or rng.random() < 0.5
                rx, ry = sp * 0.62, sp * 0.45
                d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=INK if filled else None, outline=INK, width=3)
                if st < 0 and st % 2 == 0 or st <= -2:
                    d.line((x - rx * 1.6, y0 + 4 * sp + sp, x + rx * 1.6, y0 + 4 * sp + sp), fill=INK, width=2)
                up = st < 4
                sx = x + rx * 0.9 if up else x - rx * 0.9
                ey = y - sp * 3.3 if up else y + sp * 3.3
                d.line((sx, y, sx, ey), fill=INK, width=3)
                if nn >= 6 and j % 2 == 1 and prev:
                    d.line((prev[0], prev[1], sx, ey), fill=INK, width=6)
                prev = (sx, ey)
                if rng.random() < 0.08:
                    d.text((x - sp * 2, y - sp * 1.6), 'b', font=fch, fill=INK)
    im = im.resize((w, h), Image.LANCZOS)
    return age(im, np.random.default_rng(int(rng.random() * 1000)), yellow=0.25, stain=0.12, edge=0.25)

# ------------------------------------------------------------------------------------------------- small labels
def nameboard(w, h):
    """white = gold leaf, black = wood (used as a mask)"""
    S2 = 4; W, H = w * S2, h * S2
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    ctext(d, W / 2, H * 0.02, 'Amagasa', font('chorus', int(H * 0.70)), 255)
    ctext(d, W / 2, H * 0.78, 'TOKYO', font('bonum_r', int(H * 0.15)), 255, spacing=int(H * 0.08))
    d.line((W * 0.36, H * 0.86, W * 0.44, H * 0.86), fill=255, width=4); d.line((W * 0.56, H * 0.86, W * 0.64, H * 0.86), fill=255, width=4)
    return im.resize((w, h), Image.LANCZOS).convert('RGB')

def directory(w, h, rng):
    S2 = 2; W, H = w * S2, h * S2
    im = Image.new('RGB', (W, H), (206, 160, 60)); d = ImageDraw.Draw(im)
    d.rectangle((0, H * 0.30, W, H * 0.52), fill=(40, 34, 30))
    ctext(d, W / 2, H * 0.08, '東京都区部', font('jps', int(W * 0.10)), (40, 34, 30))
    ctext(d, W / 2, H * 0.325, '電話番号簿', font('jps', int(W * 0.14)), (220, 180, 80))
    ctext(d, W / 2, H * 0.58, '五十音別 ・ 昭和五十三年版', font('jp', int(W * 0.055)), (40, 34, 30))
    for i in range(3):
        d.line((W * 0.1, H * (0.72 + i * 0.04), W * 0.9, H * (0.72 + i * 0.04)), fill=(150, 100, 40), width=3)
    im = im.resize((w, h), Image.LANCZOS)
    return age(im, rng, yellow=0.2, stain=0.4, edge=0.6)

def memo(w, h, rng):
    S2 = 2; W, H = w * S2, h * S2
    im = Image.new('RGB', (W, H), (238, 232, 212)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, H * 0.06), fill=(150, 60, 50))
    for i in range(10):
        y = H * (0.16 + i * 0.085); d.line((W * 0.05, y, W * 0.95, y), fill=(150, 170, 190), width=2)
    f = font('chorus', int(H * 0.075))
    d.text((W * 0.10, H * 0.17), 'K. —', font=f, fill=(40, 40, 70))
    d.text((W * 0.16, H * 0.26), 'call back after 3', font=f, fill=(40, 40, 70))
    d.line((W * 0.15, H * 0.42, W * 0.70, H * 0.40), fill=(40, 40, 70), width=3)
    # pencil doodle: a little spiral
    pts = [(W * 0.7 + math.cos(t) * t * 3, H * 0.65 + math.sin(t) * t * 3) for t in np.linspace(0, 14, 80)]
    d.line(pts, fill=(90, 90, 95), width=2)
    return age(im.resize((w, h), Image.LANCZOS), rng, yellow=0.15, stain=0.1, edge=0.2)

def label(w, h):
    S2 = 4; W, H = w * S2, h * S2
    im = Image.new('RGB', (W, H), (236, 230, 212)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, H * 0.40), fill=(160, 42, 36))
    ctext(d, W / 2, H * 0.02, 'でんわ', font('jp', int(H * 0.32)), (240, 232, 214))
    ctext(d, W / 2, H * 0.46, '10円玉をお入れください', font('jp', int(H * 0.15)), (40, 34, 30))
    ctext(d, W / 2, H * 0.70, '市内 3分 10円', font('jp', int(H * 0.15)), (40, 34, 30))
    return im.resize((w, h), Image.LANCZOS)

def books(w, h, rng):
    """cover/spine strip for the music books on the piano: four cloth covers side by side (each w/4)"""
    im = Image.new('RGB', (w, h)); d = ImageDraw.Draw(im)
    cols = [(52, 80, 58), (112, 36, 32), (196, 176, 136), (176, 124, 46)]
    titles = ['ÉTUDES', 'STANDARDS', 'SONATINEN', 'FAKE  BOOK']
    q = w // 4
    for i, (c, t) in enumerate(zip(cols, titles)):
        d.rectangle((i * q, 0, (i + 1) * q, h), fill=c)
        ink = (220, 200, 150) if i != 2 else (60, 40, 30)
        d.rectangle((i * q + 14, 14, (i + 1) * q - 14, h - 14), outline=ink, width=2)
        ctext(d, i * q + q / 2, h * 0.32, t, font('bonum', int(h * 0.20)), ink)
    return age(im, rng, yellow=0.2, stain=0.2, edge=0.3)

def main():
    rng = np.random.default_rng(11); random.seed(5)
    sheet = Image.new('RGB', (S, S), (128, 128, 128))
    def put(k, im):
        x, y, w, h = REG[k]; assert im.size == (w, h), (k, im.size); sheet.paste(im, (x, y))
    put('posterA', poster_a(*REG['posterA'][2:], rng))
    put('posterB', poster_b(*REG['posterB'][2:], rng))
    put('clock', clock_face(REG['clock'][2], rng))
    put('dial', dial(REG['dial'][2]))
    put('photo', photo(*REG['photo'][2:], rng))
    put('music0', music(*REG['music0'][2:], random.Random(1), title='Blue Hour, Basement  (D.)'))
    put('music1', music(*REG['music1'][2:], random.Random(2)))
    put('music2', music(*REG['music2'][2:], random.Random(3)))
    put('name', nameboard(*REG['name'][2:]))
    put('directory', directory(*REG['directory'][2:], rng))
    put('memo', memo(*REG['memo'][2:], rng))
    put('label', label(*REG['label'][2:]))
    put('books', books(*REG['books'][2:], rng))
    sheet.save(os.path.join(OUT, 'sheet.png'))
    # the chart: centre-crop to the frame window aspect (0.41 x 0.28)
    m = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'map_2k.jpg')).convert('RGB')
    asp = 0.41 / 0.28; W = int(m.height * asp); x0 = (m.width - W) // 2
    m = m.crop((x0, 0, x0 + W, m.height))
    m.save(os.path.join(OUT, 'map.jpg'), quality=92)
    json.dump(dict(size=S, regions=REG), open(os.path.join(OUT, 'regions.json'), 'w'), indent=1)
    print('wrote sheet.png, map.jpg', m.size)

if __name__ == '__main__':
    main()
