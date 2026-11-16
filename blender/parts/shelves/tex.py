"""Painted textures for the `shelves` part (numpy + PIL).  Run:  python3 blender/parts/shelves/tex.py
Writes  tex/spines.png  (atlas `shelves`: LP spines, box sets, book spines, side covers, bottle labels, tags)
        tex/covers.png  (atlas `shelves_b`: the six interactive sleeves, four ledgers, four bottle-keep labels + tags)
Importing this module only defines the sheet layouts (pixel rects) that build.py reads; painting happens under __main__.
Everything is invented: label "Mezzotint Records", artists, titles, whisky names.
"""
import os, math, random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tex')
SHEET_A = os.path.join(OUT, 'spines.png')
SHEET_B = os.path.join(OUT, 'covers.png')
W = 2048

# ------------------------------------------------------------------ layouts (pixel rects x0, y0, x1, y1; y down)
N_LP = 384
def LP(i):
    if i < 256: return (i * 8, 0, i * 8 + 8, 512)
    i -= 256; return (i * 8, 512, i * 8 + 8, 1024)
N_BOX = 32
def BOX(j): return (1024 + j * 32, 512, 1024 + j * 32 + 32, 1024)
N_BOOK = 30
def BOOK(j): return (j * 64, 1024, j * 64 + 64, 1536)
WHITE = (1920, 1024, 1928, 1536)
EDGE = (1932, 1030, 1964, 1090)        # sleeve card edge (tops of LP rows)
PAGES = (1932, 1100, 1964, 1160)       # book page edges
DARK = (1932, 1170, 1964, 1230)        # near-black (box interiors etc.)
KRAFT = (1932, 1240, 1964, 1300)       # cardboard
CLOTH = (1932, 1310, 1964, 1370)       # folded cloth (ochre check)
SINGLES = (1932, 1380, 1964, 1530)     # 7-inch box front label strip
def TAG(i): return (1968, 1024 + i * 64, 2048, 1024 + i * 64 + 56)     # 8 small keep-bottle tags 80x56
N_SIDE = 8
def SIDE(i): return (i * 256, 1536, i * 256 + 256, 1792)
N_LAB = 16
def LAB(i): return (i * 128, 1792, i * 128 + 128, 2048)

def FRONT(i): return ((i % 3) * 640, (i // 3) * 640, (i % 3) * 640 + 640, (i // 3) * 640 + 640)
def SPINE(i): return (1920 + i * 20, 0, 1920 + i * 20 + 20, 640)
def BSPINE(j): return (1920 + j * 32, 640, 1920 + j * 32 + 32, 992)
B_EDGE = (1920, 996, 1980, 1056)
B_PAGES = (1984, 996, 2044, 1056)
B_INNER = (1920, 1060, 1980, 1120)     # sleeve opening (dark)
def BACK(i): return (i * 320, 1280, i * 320 + 320, 1600)
def BCOVER(j): return (j * 224, 1600, j * 224 + 224, 1908)
def BLABEL(j): return (896 + j * 256, 1600, 896 + j * 256 + 256, 1900)
def BTAG(j): return (1920, 1600 + j * 72, 2048, 1600 + j * 72 + 64)
B_GLASS_CAP = (1920, 1900, 1980, 1960)

def uv(rect, inset=0.5):
    """pixel rect -> (u0, v0, u1, v1) with v up (Blender)"""
    x0, y0, x1, y1 = rect
    return ((x0 + inset) / W, 1 - (y1 - inset) / W, (x1 - inset) / W, 1 - (y0 + inset) / W)

# ------------------------------------------------------------------ binding content
POSTS = ['First Pressing', 'Side B Is Where the Truth Is', 'A Map of Small Hours', 'Standards, Slightly Wrong',
         'The Quiet Refactor', 'Rain on B1']
CATS = ['MZ-7101', 'MZ-7102', 'MZ-7103', 'MZ-7104', 'MZ-7105', 'MZ-7106']
LEDGERS = ['FICTION', 'MAPS & TRAVEL', 'CRAFT', 'LISTENING']

if __name__ == '__main__':
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

    os.makedirs(OUT, exist_ok=True)
    R = random.Random(1977)
    TG = '/usr/share/texmf/fonts/opentype/public/tex-gyre/'
    F = dict(
        cn=TG + 'texgyreheroscn-bold.otf', cnr=TG + 'texgyreheroscn-regular.otf', cni=TG + 'texgyreheroscn-bolditalic.otf',
        hb=TG + 'texgyreheros-bold.otf', hr=TG + 'texgyreheros-regular.otf',
        av=TG + 'texgyreadventor-bold.otf', avr=TG + 'texgyreadventor-regular.otf',
        bo=TG + 'texgyrebonum-bold.otf', bor=TG + 'texgyrebonum-regular.otf', boi=TG + 'texgyrebonum-italic.otf',
        sc=TG + 'texgyreschola-regular.otf', scb=TG + 'texgyreschola-bold.otf', sci=TG + 'texgyreschola-italic.otf',
        te=TG + 'texgyretermes-regular.otf', tei=TG + 'texgyretermes-italic.otf', teb=TG + 'texgyretermes-bold.otf',
        cu=TG + 'texgyrecursor-regular.otf', cub=TG + 'texgyrecursor-bold.otf',
        ch=TG + 'texgyrechorus-mediumitalic.otf',
        jp='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', jps='/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',
        jpr='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
    )
    _fc = {}
    def font(k, s):
        key = (k, int(s))
        if key not in _fc:
            _fc[key] = ImageFont.truetype(F[k], max(4, int(s)), index=0) if F[k].endswith('.ttc') else ImageFont.truetype(F[k], max(4, int(s)))
        return _fc[key]

    CREAM = (232, 221, 196); INK = (26, 22, 20)

    def noise2(w, h, octs=5, seed=0, base=4):
        rng = np.random.default_rng(seed)
        out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
        for o in range(octs):
            n = base * 2 ** o
            g = rng.random((n + 1, n + 1)).astype(np.float32)
            out += np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC)) * amp; tot += amp; amp *= 0.5
        out /= tot
        return (out - out.min()) / (out.max() - out.min() + 1e-6)

    def grain(im, amt=5, seed=1):
        a = np.asarray(im).astype(np.float32)
        n = np.random.default_rng(seed).normal(0, amt, a.shape[:2])[..., None]
        return Image.fromarray(np.clip(a + n, 0, 255).astype(np.uint8))

    def wear(im, amt=0.10, seed=3, edge=0.025, ring=False):
        """paper ageing: blotches, edge wear, optional ring wear from the disc inside"""
        w, h = im.size
        a = np.asarray(im.convert('RGB')).astype(np.float32) / 255
        n = noise2(w, h, 4, seed, 3)[..., None]
        a = a * (1 - amt * 0.7 * n) + amt * 0.22 * n * np.array([0.95, 0.8, 0.55])
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]).astype(np.float32)
        e = np.clip(1 - d / (edge * w), 0, 1)[..., None] * noise2(w, h, 3, seed + 1, 24)[..., None]
        a = a * (1 - e * 0.55) + e * 0.55 * np.array([0.86, 0.82, 0.74])
        if ring:
            r = np.hypot(xx - w / 2, yy - h / 2) / (w / 2)
            band = np.exp(-((r - 0.93) / 0.025) ** 2) * (noise2(w, h, 3, seed + 7, 8) > 0.45)
            band = band[..., None] * 0.22
            a = a * (1 - band) + band * np.array([0.85, 0.82, 0.76])
        return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))

    def vtext(img, text, fnt, fill, cx, y0, y1=None, rot=-90, align='center', track=0):
        """write text along a vertical strip (reads top->bottom with rot=-90). cx = centre column, y0..y1 = span."""
        bb = fnt.getbbox(text)
        tw, th = bb[2] - bb[0] + 4 + track * len(text), bb[3] - bb[1] + 4
        t = Image.new('L', (tw, th), 0); dd = ImageDraw.Draw(t)
        if track:
            x = 2
            for ch in text:
                dd.text((x - bb[0], 2 - bb[1]), ch, font=fnt, fill=255); x += fnt.getlength(ch) + track
        else:
            dd.text((2 - bb[0], 2 - bb[1]), text, font=fnt, fill=255)
        t = t.rotate(rot, expand=True)
        if y1 is not None and t.size[1] > (y1 - y0):
            t = t.resize((t.size[0], max(1, y1 - y0)), Image.LANCZOS)
        if align == 'center' and y1 is not None: yy = y0 + ((y1 - y0) - t.size[1]) // 2
        elif align == 'end' and y1 is not None: yy = y1 - t.size[1]
        else: yy = y0
        img.paste(Image.new('RGB', t.size, fill), (int(cx - t.size[0] / 2), int(yy)), t)
        return yy + t.size[1]

    def vjp(img, text, fnt, fill, cx, y0, step=None):
        """Japanese vertical text: one glyph under another"""
        d = ImageDraw.Draw(img); y = y0
        for ch in text:
            if ch == 'ー':
                bb = fnt.getbbox('｜'); d.text((cx, y), '｜', font=fnt, fill=fill, anchor='mt')
            else:
                d.text((cx, y), ch, font=fnt, fill=fill, anchor='mt')
            y += step or fnt.size * 1.02
        return y

    def htext(d, xy, text, fnt, fill, anchor='la', track=0):
        if not track:
            d.text(xy, text, font=fnt, fill=fill, anchor=anchor); return
        L = sum(fnt.getlength(c) + track for c in text) - track
        x, y = xy
        if anchor[0] == 'm': x -= L / 2
        elif anchor[0] == 'r': x -= L
        for c in text:
            d.text((x, y), c, font=fnt, fill=fill, anchor='l' + anchor[1]); x += fnt.getlength(c) + track

    def fit(text, key, maxw, start):
        s = start
        while s > 6 and font(key, s).getlength(text) > maxw: s -= 1
        return font(key, s)

    # ---------------------------------------------------------- invented words
    SYL = ['ka', 'ri', 'no', 'mo', 'sa', 'to', 'ha', 'ra', 'ki', 'yu', 'mi', 'na', 'ta', 'se', 'ko', 'shi', 'ma', 're']
    FIRST = ['Ottoline', 'Kaz', 'Pell', 'Juno', 'Ryo', 'Ines', 'Abel', 'Mabry', 'Tomas', 'Hollis', 'Wendell', 'Sachi', 'Corin',
             'Ezra', 'Lyle', 'Odile', 'Nils', 'Rufus', 'Emiko', 'Dacre', 'Vesna', 'Toru', 'Bram', 'Celia', 'Haldor', 'Mika']
    LAST = ['Brask', 'Mirelle', 'Okafor', 'Sarrat', 'Tamuro', 'Vey', 'Lindqvist', 'Ashdown', 'Orrin', 'Kessel', 'Fairley',
            'Hoshida', 'Penhale', 'Quarles', 'Rondell', 'Sabatier', 'Tilney', 'Umberg', 'Varga', 'Wyck', 'Yanase', 'Zell', 'Morrow']
    GRP = ['Trio', 'Quartet', 'Quintet', 'Sextet', 'Orchestra', 'Ensemble', 'Group', '', '', '']
    W1 = ['Night', 'Lantern', 'Copper', 'Slow', 'Harbour', 'Paper', 'Velvet', 'Late', 'Second', 'Narrow', 'Iron', 'Linen',
          'Amber', 'Winter', 'Tobacco', 'Low', 'Small', 'Quiet', 'Empty', 'Blue', 'Green', 'Ochre', 'Distant', 'Folded']
    W2 = ['Streets', 'Hours', 'Rooms', 'Tide', 'Ballads', 'Steps', 'Signals', 'Corners', 'Weather', 'Stairs', 'Letters',
          'Lights', 'Rain', 'Mirrors', 'Bridges', 'Suite', 'Sketches', 'Platform', 'Canal', 'Echoes', 'Landing']
    LABELS = ['MZ', 'LTN', 'CPR', 'OKR', 'HSK', 'BRT', 'SV', 'NJ', 'TKY', 'RVR']
    KATA = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン'
    def kname(n=None):
        n = n or R.randint(3, 6)
        return ''.join(R.choice(KATA) for _ in range(n))
    def artist(): return R.choice(FIRST) + ' ' + R.choice(LAST) + ((' ' + R.choice(GRP)) if R.random() < 0.6 else '')
    def title(): return R.choice(W1) + ' ' + R.choice(W2)
    def catno(): return '%s-%d' % (R.choice(LABELS), R.randint(1000, 9999))

    PAL = [((228, 218, 196), 3), ((214, 202, 176), 3), ((22, 20, 20), 16), ((52, 46, 42), 6), ((84, 74, 64), 4),
           ((166, 40, 30), 7), ((200, 86, 36), 6), ((206, 156, 50), 6), ((110, 30, 34), 4), ((28, 50, 92), 6),
           ((36, 90, 100), 4), ((62, 86, 56), 4), ((96, 62, 40), 5), ((128, 122, 112), 4), ((186, 132, 120), 2),
           ((70, 120, 150), 2), ((222, 188, 70), 2), ((30, 60, 48), 3), ((140, 96, 50), 3)]
    def pick_col(rr=R):
        t = rr.uniform(0, sum(w for _, w in PAL))
        for c, w in PAL:
            t -= w
            if t <= 0: return tuple(max(0, min(255, int(v + rr.uniform(-10, 10)))) for v in c)
        return PAL[0][0]
    def lum(c): return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    def contrast(c):
        return INK if lum(c) > 120 else R.choice([CREAM, CREAM, (232, 196, 80), (226, 130, 60), (210, 210, 200)])

    # ---------------------------------------------------------- LP spines (painted at 4x: 32 x 2048, downsampled to 8 x 512)
    def lp_spine():
        S = 4; w, h = 8 * S, 512 * S
        c = pick_col(); im = Image.new('RGB', (w, h), c); d = ImageDraw.Draw(im)
        kind = R.choices(['west', 'obi', 'band', 'plain'], [5, 3, 2, 1])[0]
        if kind == 'obi':
            oc = R.choice([(226, 218, 196), (214, 40, 30), (214, 40, 30), (232, 190, 40), (20, 20, 22), (20, 20, 22), (40, 80, 150)])
            d.rectangle([0, 0, w, h], fill=oc)
            tc = (200, 30, 26) if lum(oc) > 150 and R.random() < 0.5 else contrast(oc)
            f = font('jp', 19)
            y = vjp(im, kname(R.randint(4, 7)), f, tc, w // 2, R.randint(40, 120), step=21)
            vjp(im, '・' + kname(R.randint(3, 5)), font('jp', 15), tc, w // 2, y + 20, step=17)
            d.rectangle([3, h - 150, w - 4, h - 120], fill=tc)
            vtext(im, '¥2,%d00' % R.randint(0, 8), font('cn', 14), tc, w // 2, h - 110, h - 30)
            vtext(im, catno(), font('cnr', 12), tc, w // 2, 6, 34 if R.random() < 0.5 else 30)
        else:
            tc = contrast(c)
            if kind == 'band':
                c2 = pick_col(); y0 = R.randint(0, h // 2); d.rectangle([0, y0, w, y0 + R.randint(200, 900)], fill=c2)
            if kind != 'plain':
                txt = (artist() + '   ' + title()).upper() if R.random() < 0.7 else title().upper()
                fk = R.choice(['cn', 'cn', 'hb', 'av', 'bo', 'scb'])
                y0 = R.randint(60, 260); y1 = h - R.randint(260, 600)
                vtext(im, txt, fit(txt, fk, y1 - y0, 22), tc, w // 2, y0, y1, align=R.choice(['center', 'start']))
            vtext(im, catno(), font('cnr', 13), tc, w // 2, h - 200, h - 60)
            if R.random() < 0.5:
                bc = R.choice([(200, 40, 30), CREAM, (20, 20, 20), (230, 180, 50), (30, 60, 120)])
                yb = R.randint(10, 40); d.rectangle([5, yb, w - 6, yb + R.randint(20, 40)], fill=bc)
        im = im.resize((8, 512), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32)
        a[:, 0] *= 0.72; a[:, -1] *= 0.8                     # edge shading between sleeves
        a *= R.uniform(0.86, 1.06)
        return a

    def box_spine():
        S = 2; w, h = 32 * S, 512 * S
        c = R.choice([(70, 24, 24), (24, 30, 46), (24, 50, 40), (30, 28, 26), (150, 110, 60), (120, 50, 28), (206, 196, 172)])
        im = Image.new('RGB', (w, h), c); d = ImageDraw.Draw(im)
        g = (204, 164, 82) if lum(c) < 120 else INK
        for yy in (40, 52, h - 60, h - 48):
            d.rectangle([6, yy, w - 7, yy + 3], fill=g)
        d.rectangle([8, 110, w - 9, 340], outline=g, width=2)
        vtext(im, title().upper(), fit('X' * 14, 'bo', 210, 30), g, w // 2, 120, 330)
        vtext(im, artist().upper(), font('cn', 22), g, w // 2, 420, h - 200)
        d.ellipse([w // 2 - 10, h - 160, w // 2 + 10, h - 140], outline=g, width=2)
        vtext(im, '%d LP' % R.choice([3, 4, 5]), font('cn', 18), g, w // 2, h - 130, h - 80)
        im = im.resize((32, 512), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32)
        a[:, :2] *= 0.75; a[:, -2:] *= 0.8
        return a

    def book_spine(j):
        S = 2; w, h = 64 * S, 512 * S
        kind = R.choice(['cloth', 'cloth', 'cloth', 'paper', 'pocket', 'jp', 'jp'])
        g = (206, 168, 84)
        if kind == 'cloth':
            c = R.choice([(92, 26, 26), (30, 58, 44), (26, 38, 70), (150, 112, 62), (36, 32, 30), (112, 70, 38), (60, 22, 30), (38, 70, 80)])
            im = Image.new('RGB', (w, h), c); d = ImageDraw.Draw(im)
            for yy in (50, 64, 900, 914):
                d.rectangle([6, yy, w - 7, yy + 4], fill=g)
            if R.random() < 0.6:
                lc = R.choice([(20, 18, 18), (100, 26, 26), (226, 214, 186)])
                d.rectangle([12, 120, w - 13, 520], fill=lc); d.rectangle([12, 120, w - 13, 520], outline=g, width=2)
                tc = g if lc[0] < 150 else INK
            else: tc = g
            vtext(im, (R.choice(W1) + ' ' + R.choice(W2)).upper(), fit('X' * 13, 'teb', 380, 40), tc, w // 2, 130, 510)
            vtext(im, R.choice(LAST).upper(), font('te', 26), g, w // 2, 600, 820)
        elif kind == 'paper':
            c = R.choice([(226, 214, 186), (214, 200, 170), (236, 230, 214), (200, 190, 170), (180, 190, 176)])
            im = Image.new('RGB', (w, h), c); d = ImageDraw.Draw(im)
            tc = R.choice([INK, (150, 30, 30), (30, 50, 100)])
            vtext(im, title(), fit('X' * 16, 'sci', 600, 44), tc, w // 2, 80, 700)
            vtext(im, R.choice(FIRST) + ' ' + R.choice(LAST), font('sc', 28), tc, w // 2, 740, 940)
            d.rectangle([20, 960, w - 21, 990], fill=tc)
        elif kind == 'pocket':
            c = R.choice([(214, 104, 34), (40, 104, 78), (40, 66, 124), (164, 40, 56), (224, 180, 50)])
            im = Image.new('RGB', (w, h), c); d = ImageDraw.Draw(im)
            d.rectangle([0, 260, w, 760], fill=(236, 226, 200))
            vtext(im, title().upper(), fit('X' * 14, 'cn', 460, 46), INK, w // 2, 280, 740)
            d.ellipse([w // 2 - 18, 860, w // 2 + 18, 896], fill=(236, 226, 200))
        else:   # Japanese paperback (bunko) with vertical title
            c = R.choice([(232, 226, 210), (220, 206, 180), (200, 70, 50), (60, 70, 90), (236, 214, 150)])
            im = Image.new('RGB', (w, h), c); d = ImageDraw.Draw(im)
            tc = INK if lum(c) > 120 else CREAM
            y = vjp(im, ''.join(R.choice('夜窓雨月坂橋港灯紙路影海冬町音庭') for _ in range(R.randint(2, 4))), font('jps', 40), tc, w // 2, 70, step=46)
            vjp(im, kname(R.randint(3, 5)), font('jpr', 26), tc, w // 2, max(y + 60, 520), step=29)
            d.rectangle([14, 930, w - 15, 980], fill=(180, 40, 30) if R.random() < 0.5 else tc)
        im = im.resize((64, 512), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32)
        a[:, :2] *= 0.7; a[:, -2:] *= 0.75
        a *= (0.9 + 0.12 * noise2(64, 512, 3, 100 + j, 8))[..., None]
        return a

    def side_cover(i):
        """generic cover faces of sleeves seen side-on (ends of groups, leaning sleeves)"""
        rr = random.Random(50 + i)
        S = 512; c = pick_col(rr); im = Image.new('RGB', (S, S), c); d = ImageDraw.Draw(im)
        k = i % 4
        c2 = pick_col(rr); c3 = pick_col(rr)
        if k == 0:
            d.ellipse([S * 0.2, S * 0.25, S * 0.95, S], fill=c2); d.ellipse([S * 0.5, S * 0.55, S * 0.65, S * 0.7], fill=c3)
        elif k == 1:
            for n in range(6): d.rectangle([0, n * S / 6, S * rr.uniform(0.3, 1), n * S / 6 + S / 14], fill=c2 if n % 2 else c3)
        elif k == 2:
            d.polygon([(0, S), (S, S * 0.3), (S, S)], fill=c2); d.rectangle([S * 0.08, S * 0.08, S * 0.5, S * 0.2], fill=c3)
        else:
            for n in range(12): d.ellipse([S * 0.5 - n * 20, S * 0.5 - n * 20, S * 0.5 + n * 20, S * 0.5 + n * 20], outline=c2, width=6)
        htext(d, (30, 30), title().upper(), font('cn', 44), contrast(c))
        return wear(im.resize((256, 256), Image.LANCZOS), 0.14, 60 + i, ring=True)

    # ---------------------------------------------------------- bottle labels (house + keep)
    WHISKY = [('KASUMIDAI', 'PURE MALT', 'jp'), ('OLD LANTERN', 'FINE BLENDED', 'serif'), ('ROWAN & PIKE', 'HIGHLAND STYLE', 'serif'),
              ('TSURUGI', 'BLENDED WHISKY', 'jp'), ('ASHGROVE', 'SINGLE MALT · 12', 'serif'), ('HAYAMI', 'RESERVE', 'jp'),
              ('MORVEN CROSS', 'OLD SCOTCH STYLE', 'serif'), ('BELL & ANCHOR', 'NAVY RUM', 'serif'), ('MIDORI-NO-MORI', 'DRY GIN', 'jp'),
              ('KOGANE', 'UME LIQUEUR', 'jp'), ('SAINT OLAVE', 'FINE BRANDY', 'serif'), ('DUNRAITH', '8 YEARS OLD', 'serif'),
              ('HOSHIZORA', 'SHOCHU', 'jp'), ('CAPTAIN ORRERY', 'SPICED', 'serif'), ('KIRISAME', 'WHISKY', 'jp'), ('VELLAN', 'VERMOUTH ROSSO', 'serif')]
    JPN = ['霞台', '古灯', '', '剣', '', '早見', '', '', '緑の森', '黄金', '', '', '星空', '', '霧雨', '']

    def label(i, w=128, h=256, big=None):
        name, sub, kind = WHISKY[i % len(WHISKY)]
        rr = random.Random(300 + i)
        S = 4; W_, H_ = w * S, h * S
        bg = rr.choice([(232, 220, 190), (226, 210, 170), (20, 22, 24), (120, 28, 26), (236, 230, 214), (30, 52, 40), (210, 180, 110)])
        im = Image.new('RGB', (W_, H_), bg); d = ImageDraw.Draw(im)
        fg = INK if lum(bg) > 120 else (222, 190, 110)
        acc = rr.choice([(160, 30, 26), (190, 140, 50), (30, 50, 90)])
        m = W_ * 0.06
        d.rectangle([m, m, W_ - m, H_ - m], outline=fg, width=max(2, S))
        d.rectangle([m * 1.6, m * 1.6, W_ - m * 1.6, H_ - m * 1.6], outline=fg, width=max(1, S // 2))
        cx = W_ / 2
        if kind == 'jp' and JPN[i % 16]:
            jp = JPN[i % 16]
            y = H_ * 0.12
            f = font('jps', min(W_ * 0.32, H_ * 0.5 / max(1, len(jp))))
            for ch in jp:
                d.text((cx, y), ch, font=f, fill=fg, anchor='mt'); y += f.size * 1.05
            d.text((cx, y + H_ * 0.03), name, font=fit(name, 'cn', W_ * 0.78, W_ * 0.14), fill=acc if lum(bg) > 120 else fg, anchor='mt')
            d.text((cx, H_ * 0.86), sub, font=fit(sub, 'cnr', W_ * 0.75, W_ * 0.08), fill=fg, anchor='mm')
        else:
            d.text((cx, H_ * 0.15), 'EST. 19%d' % rr.randint(20, 60), font=font('tei', W_ * 0.07), fill=fg, anchor='mm')
            d.ellipse([cx - W_ * 0.18, H_ * 0.22, cx + W_ * 0.18, H_ * 0.22 + W_ * 0.36], outline=acc, width=S * 2)
            d.text((cx, H_ * 0.22 + W_ * 0.18), name[0], font=font('teb', W_ * 0.22), fill=acc, anchor='mm')
            parts = name.split(' ')
            y = H_ * 0.48
            for p in parts:
                f = fit(p, 'teb', W_ * 0.8, W_ * 0.2); d.text((cx, y), p, font=f, fill=fg, anchor='mt'); y += f.size * 1.1
            d.text((cx, y + H_ * 0.03), sub, font=fit(sub, 'te', W_ * 0.76, W_ * 0.08), fill=fg, anchor='mt')
            d.text((cx, H_ * 0.88), '43% vol · 760 ml', font=font('te', W_ * 0.06), fill=fg, anchor='mm')
        im = wear(im.resize((w, h), Image.LANCZOS), 0.16, 400 + i, 0.04)
        return im

    CAT = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'barkit', 'cat_emblem.png')).convert('RGBA')
    def cat_emblem(size, col):
        m = CAT.split()[3].resize((size, size), Image.LANCZOS)
        return Image.new('RGB', (size, size), col), m

    def keep_tag(text, w, h, seed, small=None):
        """paper neck tag of the bar's bottle keep: DEAN'S + cat emblem printed, number/name handwritten in ink"""
        S = 4; W_, H_ = w * S, h * S
        rr = random.Random(seed)
        im = Image.new('RGB', (W_, H_), rr.choice([(236, 226, 200), (230, 218, 186), (240, 232, 212)])); d = ImageDraw.Draw(im)
        d.ellipse([W_ * 0.05, H_ * 0.40, W_ * 0.05 + H_ * 0.2, H_ * 0.60], fill=(120, 100, 80))   # eyelet
        d.ellipse([W_ * 0.05 + H_ * 0.05, H_ * 0.45, W_ * 0.05 + H_ * 0.15, H_ * 0.55], fill=(40, 30, 24))
        es = int(H_ * 0.30)
        col, m = cat_emblem(es, (120, 40, 30)); im.paste(col, (int(W_ * 0.84 - es / 2), int(H_ * 0.06)), m)
        d.text((W_ * 0.84, H_ * 0.40), "DEAN'S", font=font('teb', H_ * 0.11), fill=(120, 40, 30), anchor='mt')
        d.line([W_ * 0.22, H_ * 0.78, W_ * 0.70, H_ * 0.78], fill=(150, 130, 110), width=S)
        ink = (24, 28, 52)
        f = fit(text, 'ch', W_ * 0.5, H_ * 0.62)
        d.text((W_ * 0.46, H_ * 0.44), text, font=f, fill=ink, anchor='mm')
        if small:
            d.text((W_ * 0.46, H_ * 0.88), small, font=font('ch', H_ * 0.15), fill=ink, anchor='mm')
        return wear(im.resize((w, h), Image.LANCZOS), 0.18, seed, 0.05)

    # ---------------------------------------------------------- the six covers (painted at 1280, downsampled to 640)
    S = 1280
    def mz_mark(d, x, y, col, s=1.0, anchor='la'):
        f = font('cn', 30 * s)
        d.text((x, y), 'MEZZOTINT', font=f, fill=col, anchor=anchor)

    def credits(d, cat, col, y=S - 70):
        d.text((60, y), 'MEZZOTINT RECORDS', font=font('cn', 30), fill=col, anchor='lm')
        d.text((S - 60, y), 'STEREO  ' + cat, font=font('cnr', 30), fill=col, anchor='rm')

    def cover0():   # First Pressing: mustard, a huge black disc rising off the right edge
        bg = (214, 160, 48); im = Image.new('RGB', (S, S), bg); d = ImageDraw.Draw(im)
        cx, cy, r = 900, 930, 460
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 18, 18))
        for k in range(1, 40):
            rr = r - 12 - k * 9
            if rr < 200: break
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(34, 31, 30) if k % 3 else (12, 11, 11), width=2)
        d.ellipse([cx - 190, cy - 190, cx + 190, cy + 190], fill=(176, 40, 30))
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=bg)
        d.text((cx, cy - 100), 'SIDE ONE', font=font('cn', 34), fill=CREAM, anchor='mm')
        d.text((cx, cy + 110), CATS[0], font=font('cnr', 30), fill=CREAM, anchor='mm')
        d.text((70, 80), 'FIRST', font=font('cn', 200), fill=INK, anchor='lt')
        d.text((70, 275), 'PRESSING', font=font('cn', 200), fill=INK, anchor='lt')
        d.rectangle([76, 510, 300, 522], fill=(176, 40, 30))
        d.text((76, 548), 'the Pell Okafor', font=font('boi', 46), fill=INK, anchor='lt')
        d.text((76, 604), 'Quartet', font=font('boi', 46), fill=INK, anchor='lt')
        credits(d, CATS[0], INK)
        return im

    def cover1():   # Side B Is Where the Truth Is: oxblood over cream, split on a diagonal, a giant serif B
        im = Image.new('RGB', (S, S), (232, 221, 196)); d = ImageDraw.Draw(im)
        d.polygon([(0, 0), (S, 0), (S, S * 0.38), (0, S * 0.72)], fill=(112, 28, 30))
        d.text((S * 0.60, S * 0.56), 'B', font=font('bo', 980), fill=INK, anchor='mm')
        d.ellipse([S * 0.18, S * 0.80, S * 0.24, S * 0.86], fill=(200, 86, 36))
        f = font('cn', 84)
        d.text((70, 80), 'SIDE B IS WHERE', font=f, fill=CREAM, anchor='lt')
        d.text((70, 172), 'THE TRUTH IS', font=f, fill=CREAM, anchor='lt')
        d.text((72, 290), 'Juno Sarrat · piano, alone', font=font('boi', 44), fill=(232, 190, 120), anchor='lt')
        credits(d, CATS[1], INK)
        return im

    def cover2():   # A Map of Small Hours: bottle green, ochre graticule, a dotted route between clock-arc stations
        bg = (24, 62, 50); im = Image.new('RGB', (S, S), bg); d = ImageDraw.Draw(im)
        oc = (204, 160, 70)
        for k in range(0, S, 96):
            d.line([(k, 300), (k, S - 140)], fill=(44, 86, 68), width=2)
        for k in range(300, S - 140, 96):
            d.line([(0, k), (S, k)], fill=(44, 86, 68), width=2)
        for k, (x, y) in enumerate([(220, 1000), (420, 760), (700, 860), (900, 560), (1080, 700)]):
            d.arc([x - 70, y - 70, x + 70, y + 70], -90, -90 + 30 * (k + 1) * 2, fill=oc, width=10)
            d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=CREAM)
            d.text((x + 24, y + 40), '%d:%02d' % (k + 1, (k * 17) % 60), font=font('cnr', 30), fill=oc, anchor='lt')
        pts = [(220, 1000), (420, 760), (700, 860), (900, 560), (1080, 700)]
        for (a, b) in zip(pts, pts[1:]):
            n = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 28)
            for t in range(1, n):
                x = a[0] + (b[0] - a[0]) * t / n; y = a[1] + (b[1] - a[1]) * t / n
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=CREAM)
        d.polygon([(1150, 400), (1170, 340), (1190, 400)], fill=oc); d.text((1170, 420), 'N', font=font('teb', 40), fill=oc, anchor='mt')
        d.text((70, 70), 'A Map of', font=font('tei', 120), fill=CREAM, anchor='lt')
        d.text((66, 170), 'SMALL HOURS', font=font('teb', 150), fill=oc, anchor='lt')
        credits(d, CATS[2], CREAM)
        return im

    def cover3():   # Standards, Slightly Wrong: cream with a strict grid of black squares; one is turned and red
        im = Image.new('RGB', (S, S), (232, 221, 196)); d = ImageDraw.Draw(im)
        n, s0, g = 5, 150, 38
        x0, y0 = 300, 300
        for j in range(n):
            for i in range(n):
                x = x0 + i * (s0 + g); y = y0 + j * (s0 + g)
                if (i, j) == (3, 1):
                    c = (x + s0 / 2 + 14, y + s0 / 2 + 9); a = math.radians(11)
                    pts = [(c[0] + (u * math.cos(a) - v * math.sin(a)), c[1] + (u * math.sin(a) + v * math.cos(a)))
                           for u, v in ((-s0 / 2, -s0 / 2), (s0 / 2, -s0 / 2), (s0 / 2, s0 / 2), (-s0 / 2, s0 / 2))]
                    d.polygon(pts, fill=(200, 72, 30))
                else:
                    d.rectangle([x, y, x + s0, y + s0], fill=INK)
        d.text((70, 70), 'STANDARDS,', font=font('av', 120), fill=INK, anchor='lt')
        d.text((300, 1240 - 130), 'slightly wrong', font=font('avr', 76), fill=(200, 72, 30), anchor='lt')
        d.text((70, 210), 'THE HOLLIS–UME QUARTET', font=font('cn', 40), fill=INK, anchor='lt')
        d.text((S - 60, 210), CATS[3], font=font('cnr', 34), fill=INK, anchor='rt')
        d.text((70, S - 60), 'MEZZOTINT', font=font('cn', 34), fill=INK, anchor='lm')
        return im

    def cover4():   # The Quiet Refactor: burnt orange, duotone bars rearranged into order
        bg = (196, 84, 34); im = Image.new('RGB', (S, S), bg); d = ImageDraw.Draw(im)
        rr = random.Random(44)
        dark = (70, 26, 18); light = (236, 170, 110)
        ws = [rr.randint(160, 900) for _ in range(10)]
        for k, w in enumerate(ws):
            y = 360 + k * 70
            d.rectangle([80, y, 80 + w, y + 46], fill=dark)
        for k, w in enumerate(sorted(ws)):
            y = 360 + k * 70
            d.rectangle([1200 - w * 0.12 - 60, y, 1200, y + 46], fill=light)
        d.text((80, 90), 'the quiet', font=font('hr', 120), fill=CREAM, anchor='lt')
        d.text((78, 200), 'refactor', font=font('hb', 140), fill=INK, anchor='lt')
        d.text((S - 60, 110), 'Toru Yanase Trio', font=font('cnr', 40), fill=CREAM, anchor='rt')
        credits(d, CATS[4], CREAM)
        return im

    def cover5():   # Rain on B1: near-black slate, cream rain, a single lit doorway marked B1
        bg = (30, 32, 34); im = Image.new('RGB', (S, S), bg); d = ImageDraw.Draw(im)
        rr = random.Random(55)
        for _ in range(420):
            x = rr.uniform(0, S); y = rr.uniform(0, S * 0.9); L = rr.uniform(30, 120)
            d.line([(x, y), (x - L * 0.12, y + L)], fill=(120, 124, 120) if rr.random() < 0.7 else CREAM, width=rr.choice([2, 3]))
        d.rectangle([760, 620, 960, 1100], fill=(226, 170, 60))
        d.rectangle([760, 1100, 960, 1112], fill=(140, 90, 30))
        d.text((860, 700), 'B1', font=font('cn', 120), fill=(30, 32, 34), anchor='mm')
        d.text((70, 80), 'RAIN', font=font('cn', 300), fill=CREAM, anchor='lt')
        d.text((76, 390), 'on B1', font=font('boi', 130), fill=(226, 170, 60), anchor='lt')
        d.text((80, 560), 'Ottoline Brask & Kaz Mirelle', font=font('cnr', 40), fill=CREAM, anchor='lt')
        credits(d, CATS[5], CREAM)
        return im

    COVERS = [cover0, cover1, cover2, cover3, cover4, cover5]
    SPCOL = [((214, 160, 48), INK), ((112, 28, 30), CREAM), ((24, 62, 50), (204, 160, 70)), ((232, 221, 196), INK),
             ((196, 84, 34), CREAM), ((30, 32, 34), CREAM)]

    def back_cover(i):
        bg = (232, 224, 204); im = Image.new('RGB', (640, 640), bg); d = ImageDraw.Draw(im)
        rr = random.Random(700 + i)
        d.text((30, 30), POSTS[i].upper(), font=fit(POSTS[i].upper(), 'cn', 580, 40), fill=INK)
        d.line([30, 80, 610, 80], fill=INK, width=2)
        d.text((30, 96), 'SIDE A', font=font('cn', 18), fill=INK); d.text((330, 96), 'SIDE B', font=font('cn', 18), fill=INK)
        for s, x in ((0, 30), (1, 330)):
            for k in range(4):
                d.text((x, 124 + k * 22), '%d. %s  %d:%02d' % (k + 1, title(), rr.randint(3, 9), rr.randint(0, 59)), font=font('cnr', 15), fill=INK)
        for col in range(3):
            for ln in range(34):
                w = rr.randint(120, 180) if ln % 9 != 8 else rr.randint(40, 120)
                d.rectangle([30 + col * 200, 232 + ln * 11, 30 + col * 200 + w, 232 + ln * 11 + 4], fill=(120, 112, 100))
        d.text((30, 610), 'MEZZOTINT RECORDS · TOKYO', font=font('cn', 16), fill=INK, anchor='lm')
        d.text((610, 610), CATS[i] + '  STEREO', font=font('cnr', 16), fill=INK, anchor='rm')
        return wear(im.resize((320, 320), Image.LANCZOS), 0.12, 710 + i, 0.03)

    def sleeve_spine(i):
        bg, fg = SPCOL[i]; w, h = 80, 2560
        im = Image.new('RGB', (w, h), bg)
        vtext(im, CATS[i], font('cnr', 40), fg, w // 2, 60, 360)
        vtext(im, POSTS[i].upper(), fit(POSTS[i].upper(), 'cn', 1700, 58), fg, w // 2, 460, 2200)
        vtext(im, 'MEZZOTINT', font('cn', 40), fg, w // 2, 2260, 2500)
        im = im.resize((20, 640), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32); a[:, 0] *= 0.8; a[:, -1] *= 0.85
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    # ---------------------------------------------------------- ledgers (interactive books)
    LCOL = [(36, 34, 32), (30, 58, 44), (150, 112, 70), (92, 26, 26)]
    def cloth(w, h, c, seed):
        a = np.ones((h, w, 3), np.float32) * np.array(c, np.float32)
        rng = np.random.default_rng(seed)
        weave = (np.sin(np.arange(w) * 2.6)[None, :] * np.sin(np.arange(h) * 2.6)[:, None]) * 6
        a += weave[..., None] + rng.normal(0, 4, (h, w))[..., None]
        a *= (0.88 + 0.2 * noise2(w, h, 4, seed, 4))[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    def ledger_spine(j):
        w, h = 128, 1408
        im = cloth(w, h, LCOL[j], 900 + j); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, w, 90], fill=tuple(int(v * 0.6) for v in LCOL[j])); d.rectangle([0, h - 90, w, h], fill=tuple(int(v * 0.6) for v in LCOL[j]))
        lab = (236, 226, 200)
        d.rectangle([14, 200, w - 15, 1200], fill=lab); d.rectangle([20, 206, w - 21, 1194], outline=(150, 60, 40), width=3)
        vtext(im, LEDGERS[j], fit(LEDGERS[j], 'cub', 900, 70), (30, 30, 50), w // 2, 230, 1170)
        im = im.resize((32, 352), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32); a[:, 0] *= 0.75; a[:, -1] *= 0.8
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    def ledger_cover(j):
        w, h = 448, 616
        im = cloth(w, h, LCOL[j], 950 + j); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 40, h], fill=tuple(int(v * 0.7) for v in LCOL[j]))          # quarter binding
        lab = (236, 226, 200)
        d.rectangle([110, 150, 390, 330], fill=lab); d.rectangle([118, 158, 382, 322], outline=(150, 60, 40), width=3)
        d.text((250, 215), LEDGERS[j], font=fit(LEDGERS[j], 'cub', 240, 46), fill=(30, 30, 50), anchor='mm')
        d.text((250, 285), 'vol. %d' % (j + 1), font=font('ch', 40), fill=(30, 30, 50), anchor='mm')
        if j == 1:
            for r in (40, 60):
                d.ellipse([250 - r, 470 - r, 250 + r, 470 + r], outline=(220, 200, 150), width=3)
            d.polygon([(250, 400), (262, 470), (250, 540), (238, 470)], fill=(220, 200, 150))
        if j == 3:
            d.ellipse([200, 420, 300, 520], fill=(20, 18, 18)); d.ellipse([236, 456, 264, 484], fill=(200, 86, 36))
        if j == 2:
            for k in range(14): d.line([60, 380 + k * 14, 60, 388 + k * 14], fill=(236, 226, 200), width=3)   # stitching
        return wear(im.resize((224, 308), Image.LANCZOS), 0.12, 960 + j, 0.04)

    # ================================================================== SHEET A
    A = np.zeros((W, W, 3), np.float32) + np.array([40, 30, 24], np.float32)
    def put(a, rect):
        x0, y0, x1, y1 = rect
        a_ = np.asarray(a).astype(np.float32) if not isinstance(a, np.ndarray) else a
        if a_.shape[0] != y1 - y0 or a_.shape[1] != x1 - x0:
            a_ = np.asarray(Image.fromarray(np.clip(a_, 0, 255).astype(np.uint8)).resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)
        A[y0:y1, x0:x1] = a_
    LUM = []
    for i in range(N_LP):
        a_ = lp_spine(); put(a_, LP(i)); LUM.append(round(float((a_ * [0.2126, 0.7152, 0.0722]).sum(-1).mean()), 1))
    import json
    json.dump(dict(lp_lum=LUM), open(os.path.join(OUT, 'meta.json'), 'w'))
    for j in range(N_BOX): put(box_spine(), BOX(j))
    for j in range(N_BOOK): put(book_spine(j), BOOK(j))
    A[WHITE[1]:WHITE[3], WHITE[0]:WHITE[2]] = 238
    A[EDGE[1]:EDGE[3], EDGE[0]:EDGE[2]] = (150, 138, 118)
    A[PAGES[1]:PAGES[3], PAGES[0]:PAGES[2]] = (214, 200, 170)
    A[DARK[1]:DARK[3], DARK[0]:DARK[2]] = (22, 18, 16)
    A[KRAFT[1]:KRAFT[3], KRAFT[0]:KRAFT[2]] = (150, 112, 70)
    ck = np.zeros((CLOTH[3] - CLOTH[1], CLOTH[2] - CLOTH[0], 3), np.float32) + (176, 130, 50)
    yy, xx = np.mgrid[0:ck.shape[0], 0:ck.shape[1]]
    ck[((xx // 6) % 2 == 0)] *= 0.8; ck[((yy // 6) % 2 == 0)] *= 0.85; ck[(xx % 6 == 0) | (yy % 6 == 0)] = (120, 40, 30)
    A[CLOTH[1]:CLOTH[3], CLOTH[0]:CLOTH[2]] = ck
    sg = Image.new('RGB', (SINGLES[2] - SINGLES[0], SINGLES[3] - SINGLES[1]), (236, 226, 200)); d = ImageDraw.Draw(sg)
    d.text((16, 40), '45', font=font('cn', 22), fill=(160, 40, 30), anchor='mm'); d.text((16, 100), 'rpm', font=font('cnr', 10), fill=INK, anchor='mm')
    put(sg, SINGLES)
    tagnames = ['佐藤', '森', 'K.', '山口', 'Mr. O', '小林', 'T.', 'Hal']
    for i in range(8): put(keep_tag(tagnames[i], 80, 56, 1200 + i, small="'7%d" % (5 + i % 5)), TAG(i))
    for i in range(N_SIDE): put(side_cover(i), SIDE(i))
    for i in range(N_LAB): put(label(i), LAB(i))
    # global wear: scuffed tops/bottoms of LP strips
    n = noise2(W, 1024, 5, 11, 32)
    yy = np.mgrid[0:1024, 0:W][0]
    for ya in (0, 512):
        t = (yy - ya).astype(np.float32)
        e = np.clip(1 - np.minimum(t, 511 - t) / 10.0, 0, 1); e[(yy < ya) | (yy >= ya + 512)] = 0
        k = (e * (0.2 + 0.8 * n))[..., None] * 0.5
        A[0:1024] = A[0:1024] * (1 - k) + k * np.array([206, 198, 182])
    A[0:1024] *= (0.92 + 0.14 * noise2(W, 1024, 4, 12, 64))[..., None]
    A[WHITE[1]:WHITE[3], WHITE[0]:WHITE[2]] = 238            # keep the white one perfectly blank
    im = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
    im.save(SHEET_A)

    # ================================================================== SHEET B
    B = Image.new('RGB', (W, W), (40, 30, 24))
    for i, f in enumerate(COVERS):
        c = f()
        c = wear(c.resize((640, 640), Image.LANCZOS), 0.10, 800 + i, 0.02, ring=(i in (0, 2, 5)))
        B.paste(grain(c, 2.5, 810 + i), FRONT(i)[:2])
        B.paste(back_cover(i), BACK(i)[:2])
        B.paste(sleeve_spine(i), SPINE(i)[:2])
    for j in range(4):
        B.paste(ledger_spine(j), BSPINE(j)[:2])
        B.paste(ledger_cover(j), BCOVER(j)[:2])
        lab = label([0, 4, 11, 5][j], 128, 150)
        B.paste(lab.resize((256, 300), Image.LANCZOS), BLABEL(j)[:2])
        B.paste(keep_tag('No. %d' % (j + 1), 128, 64, 1300 + j, small=['Mr. Watanabe', 'the writer', 'Ms. Ikeda', '— ?'][j]), BTAG(j)[:2])
    d = ImageDraw.Draw(B)
    d.rectangle(B_EDGE, fill=(150, 138, 118)); d.rectangle(B_PAGES, fill=(222, 210, 182)); d.rectangle(B_INNER, fill=(18, 16, 14))
    d.rectangle(B_GLASS_CAP, fill=(60, 40, 30))
    B.save(SHEET_B)
    print('wrote', SHEET_A, SHEET_B)
