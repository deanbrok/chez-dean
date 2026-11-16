"""Paints the nook's textures into tex/ (run once: python3 tex.py).
tex/paper.png  2048^2  manuscript pages, beer can, ink label, dictionary, eraser sleeve
tex/print.png  2048^2  noren curtain, calendar, radio front, tin / jar / bottle labels, fridge badge
All names and labels are invented. The handwriting is NOT text: pseudo-glyph strokes, column by column.
Region rectangles (pixels, top-left origin) are listed in REG and mirrored in build.py.
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tex')
EMBLEM = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'barkit', 'cat_emblem.png')
S = 2048

REG = dict(   # sheet, x0, y0, x1, y1
    ms_top=('paper', 0, 0, 1040, 1440),
    ms_done=('paper', 1040, 0, 2048, 1396),
    can=('paper', 0, 1440, 900, 1830),
    ink=('paper', 900, 1440, 1100, 1600),
    dict_cover=('paper', 1100, 1440, 1400, 1878),
    dict_spine=('paper', 1400, 1440, 1540, 1878),
    dict_edge=('paper', 1540, 1440, 1700, 1878),
    eraser=('paper', 1700, 1440, 1900, 1540),
    noren=('print', 0, 0, 1600, 716),
    calendar=('print', 1600, 0, 2048, 640),
    radio=('print', 0, 720, 800, 1220),
    tin_tea=('print', 800, 720, 1400, 920),
    tin_coffee=('print', 800, 920, 1400, 1120),
    tin_biscuit=('print', 1400, 720, 2048, 920),
    jar_a=('print', 1400, 920, 1700, 1120),
    jar_b=('print', 1700, 920, 2000, 1120),
    soy=('print', 0, 1230, 300, 1530),
    oil=('print', 300, 1230, 600, 1530),
    badge=('print', 600, 1230, 900, 1330),
)

# ------------------------------------------------------------------------------------------------ fonts
def _font(fname, size, want='JP'):
    path = None
    for d in ('/usr/share/fonts/opentype/noto', '/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/truetype/liberation',
              '/usr/share/fonts/opentype/ipafont-gothic'):
        p = os.path.join(d, fname)
        if os.path.exists(p): path = p
    if path.endswith('.ttc'):
        for i in range(10):
            try:
                f = ImageFont.truetype(path, size, index=i)
            except Exception: break
            if want in ' '.join(f.getname()): return f
    return ImageFont.truetype(path, size)

def serif_jp(s, w='Regular'): return _font('NotoSerifCJK-%s.ttc' % w, s)
def sans_jp(s, w='Regular'): return _font('NotoSansCJK-%s.ttc' % w, s)
def serif(s, bold=False): return _font('DejaVuSerif-Bold.ttf' if bold else 'DejaVuSerif.ttf', s)
def sans(s, bold=False): return _font('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf', s)
def cond(s, bold=False): return _font('DejaVuSansCondensed-Bold.ttf' if bold else 'DejaVuSansCondensed.ttf', s)

def text_c(d, xy, s, f, fill, anchor='mm'):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)

def vtext(d, x, y, s, f, fill, step):
    for i, ch in enumerate(s): d.text((x, y + i * step), ch, font=f, fill=fill, anchor='mm')

# ------------------------------------------------------------------------------------------------ helpers
def fbm(h, w, seed, octaves=5, base=4):
    rng = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((n + 1, int(n * w / h) + 2)).astype(np.float32)
        im = Image.fromarray(g).resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(im); tot += amp; amp *= 0.5
    return out / tot

def paper_base(w, h, seed, col=(236, 230, 212), age=0.0):
    n = fbm(h, w, seed, 5, 3)
    rng = np.random.default_rng(seed + 1)
    fib = rng.normal(0, 1, (h, w)).astype(np.float32)
    fib = gaussian_filter(fib, 0.8)
    a = np.ones((h, w, 3), np.float32) * np.array(col, np.float32)
    a += ((n - 0.5) * 10)[..., None] + (fib * 2.2)[..., None]
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)).astype(np.float32)
    e = np.clip(1 - edge / (0.06 * min(w, h)), 0, 1) ** 2
    a -= (e * (8 + 14 * age))[..., None] * np.array([0.8, 1.0, 1.6])
    return np.clip(a, 0, 255)

def to_img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def multiply(base_arr, layer_rgba):
    """layer_rgba: PIL RGBA ink layer. returns base * ink (alpha-weighted)"""
    l = np.asarray(layer_rgba).astype(np.float32) / 255.0
    al = l[..., 3:4]; col = l[..., :3]
    return base_arr * (1 - al + al * col)

def catmull(pts, n=10):
    pts = [pts[0]] + list(pts) + [pts[-1]]; out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = (np.array(p, float) for p in pts[i - 1:i + 3])
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(np.array(pts[-2], float))
    return out

# ------------------------------------------------------------------------------------------------ handwriting
class Hand:
    """pseudo-handwriting on an RGBA layer at SS x supersampling. Never real characters."""
    def __init__(self, w, h, ss, seed, ink=(28, 34, 66)):
        self.ss = ss; self.im = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
        self.rng = np.random.default_rng(seed); self.ink = ink

    def stroke(self, pts, w, taper=(0.55, 1.0, 0.35), alpha=235):
        r = self.rng; ss = self.ss
        sm = catmull(pts, 12) if len(pts) > 2 else [np.array(pts[0], float) + (np.array(pts[1], float) - np.array(pts[0], float)) * t for t in np.linspace(0, 1, 14)]
        n = len(sm)
        for i, p in enumerate(sm):
            t = i / max(1, n - 1)
            k = taper[0] + (taper[1] - taper[0]) * min(1, t * 4) if t < 0.25 else taper[1] + (taper[2] - taper[1]) * max(0, (t - 0.7) / 0.3)
            rr = max(0.5, w * k * 0.5 * ss)
            a = int(alpha * (0.85 + 0.15 * r.random()))
            x, y = p[0] * ss, p[1] * ss
            self.d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(*self.ink, a))

    def glyph(self, cx, cy, s, kind=None):
        """pseudo-character centred at cx, cy (px), size s (px)"""
        r = self.rng
        kind = kind or ('kana' if r.random() < 0.5 else 'kanji')
        sc = s * (1.0 + 0.12 * r.random()); w = s * 0.075 * (0.9 + 0.25 * r.random())
        ox, oy = cx + r.normal(0, s * 0.04), cy + r.normal(0, s * 0.04)
        P = lambda u, v: (ox + (u - 0.5) * sc, oy + (v - 0.5) * sc)
        J = lambda: r.normal(0, 0.03)
        if kind == 'kana':
            sc *= 0.9
            for _ in range(r.integers(2, 4)):
                k = r.choice([0, 0, 1, 2, 3, 3, 4])
                if k == 0:      # sweeping hook
                    u0 = 0.25 + 0.5 * r.random()
                    pts = [P(u0, 0.1 + J()), P(u0 + 0.05 + J(), 0.45), P(u0 - 0.15 + J(), 0.75), P(u0 + 0.2 + J(), 0.85)]
                elif k == 1:    # loop
                    pts = [P(0.3 + J(), 0.3), P(0.7, 0.35 + J()), P(0.55, 0.65 + J()), P(0.3, 0.6), P(0.45 + J(), 0.45), P(0.75 + J(), 0.85)]
                elif k == 2:    # short bar
                    v = 0.2 + 0.4 * r.random(); pts = [P(0.2 + J(), v), P(0.55, v - 0.03 + J()), P(0.8 + J(), v + 0.02)]
                elif k == 3:    # tick + tail
                    pts = [P(0.65 + J(), 0.15), P(0.55, 0.4 + J()), P(0.35 + J(), 0.7), P(0.6 + J(), 0.9)]
                else:           # wave
                    pts = [P(0.15, 0.55 + J()), P(0.35 + J(), 0.4), P(0.55, 0.62 + J()), P(0.85 + J(), 0.5)]
                self.stroke(pts, w)
        else:
            parts = [(0.0, 1.0)] if r.random() < 0.45 else [(0.0, 0.42), (0.38, 1.0)]
            for (a, b) in parts:
                n = r.integers(2, 5) if len(parts) > 1 else r.integers(3, 7)
                U = lambda t: a + (b - a) * t
                for _ in range(n):
                    k = r.choice(['h', 'h', 'v', 'v', 'l', 'rr', 'd'])
                    if k == 'h':
                        v = 0.12 + 0.76 * r.random(); u0 = 0.08 + 0.2 * r.random(); u1 = 0.72 + 0.2 * r.random()
                        pts = [P(U(u0), v + J()), P(U(u1), v - 0.03 + J())]
                    elif k == 'v':
                        u = 0.2 + 0.6 * r.random(); v0 = 0.08 + 0.2 * r.random(); v1 = 0.7 + 0.25 * r.random()
                        pts = [P(U(u) + J(), v0), P(U(u), (v0 + v1) / 2), P(U(u) + J() - 0.03, v1)]
                    elif k == 'l':
                        u = 0.45 + 0.3 * r.random(); pts = [P(U(u), 0.2 + J()), P(U(u - 0.12), 0.55), P(U(u - 0.4), 0.85 + J())]
                    elif k == 'rr':
                        pts = [P(U(0.4), 0.35 + J()), P(U(0.6), 0.6), P(U(0.92), 0.88 + J())]
                    else:
                        u, v = 0.2 + 0.6 * r.random(), 0.1 + 0.8 * r.random(); pts = [P(U(u), v), P(U(u) + 0.06, v + 0.09)]
                    self.stroke(pts, w * (0.95 if k != 'd' else 1.2))

    def punct(self, cx, cy, s, kind):
        r = self.rng
        if kind == 'maru':   # small circle at the upper right of the cell (vertical writing)
            x, y, rr = cx + s * 0.22, cy - s * 0.22, s * 0.12
            pts = [(x + rr * math.cos(a), y + rr * math.sin(a)) for a in np.linspace(-1.2, 2 * math.pi - 0.6, 9)]
            self.stroke(pts, s * 0.07, (0.8, 1.0, 0.7))
        elif kind == 'ten':
            x, y = cx + s * 0.18, cy - s * 0.25
            self.stroke([(x - s * 0.05, y - s * 0.06), (x + s * 0.06, y + s * 0.06)], s * 0.09, (0.6, 1.0, 0.5))
        elif kind == 'open':   # 「 rotated for vertical text
            x, y = cx + s * 0.1, cy + s * 0.25
            self.stroke([(x - s * 0.3, y), (x + s * 0.05, y), (x + s * 0.05, y + s * 0.2)], s * 0.07)
        elif kind == 'close':
            x, y = cx - s * 0.1, cy - s * 0.25
            self.stroke([(x - s * 0.05, y - s * 0.2), (x - s * 0.05, y), (x + s * 0.3, y)], s * 0.07)

    def strike(self, x, y0, y1, s):
        r = self.rng; pts = []
        for i, y in enumerate(np.linspace(y0, y1, 7)):
            pts.append((x + (s * 0.12 if i % 2 else -s * 0.12) + r.normal(0, s * 0.03), y))
        self.stroke(pts, s * 0.08, (0.8, 1.0, 0.8))
        self.stroke([(x + s * 0.02, y0 - s * 0.1), (x - s * 0.03, y1 + s * 0.1)], s * 0.06, (0.8, 1.0, 0.8))

    def result(self, w, h):
        im = self.im.resize((w, h), Image.LANCZOS)
        return im.filter(ImageFilter.GaussianBlur(0.35))

def genko(w, h, seed, fill, done=False, age=0.0):
    """squared manuscript paper (portrait, vertical writing, 15 columns x 25 cells). fill: list of column specs."""
    a = paper_base(w, h, seed, (237, 231, 213), age)
    pxcm = w / 26.0
    cell = 1.15 * pxcm; gap = 0.30 * pxcm; ncol, nrow = 15, 25
    gw = ncol * cell + (ncol - 1) * gap; gh = nrow * cell
    x0 = (w - gw) / 2; y0 = 3.0 * pxcm
    grid = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0)); g = ImageDraw.Draw(grid)
    gc = (176, 104, 74, 200)
    lw = max(2, int(pxcm * 0.035 * 2))
    def X(i): return (x0 + i * (cell + gap)) * 2
    for i in range(ncol):
        xa = X(i); xb = xa + cell * 2
        g.rectangle((xa, y0 * 2, xb, (y0 + gh) * 2), outline=gc, width=lw)
        for j in range(1, nrow):
            yy = (y0 + j * cell) * 2; g.line((xa, yy, xb, yy), fill=gc, width=lw)
    m = 0.22 * pxcm
    g.rectangle(((x0 - m) * 2, (y0 - m) * 2, (x0 + gw + m) * 2, (y0 + gh + m) * 2), outline=gc, width=lw * 3)
    # small printed stationer's mark (a box and a tiny cat), bottom-left margin
    bx, by = (x0 + 0.2 * pxcm) * 2, (y0 + gh + 0.9 * pxcm) * 2
    g.rectangle((bx, by, bx + 2.2 * pxcm * 2, by + 0.55 * pxcm * 2), outline=gc, width=lw)
    f = cond(int(pxcm * 0.36 * 2)); g.text((bx + 1.1 * pxcm * 2, by + 0.28 * pxcm * 2), '15 × 25', font=f, fill=gc, anchor='mm')
    grid = grid.resize((w, h), Image.LANCZOS)
    a = multiply(a, Image.composite(grid, Image.new('RGBA', (w, h), (255, 255, 255, 0)), grid))
    # ink
    H = Hand(w, h, 2, seed + 7)
    def C(col, row):   # centre of a cell; column 0 = rightmost
        i = ncol - 1 - col
        return (x0 + i * (cell + gap) + cell / 2, y0 + row * cell + cell / 2)
    for col, spec in enumerate(fill):
        if spec is None: continue
        start, stop, puncts, strikes = spec
        for row in range(start, stop):
            cx, cy = C(col, row)
            if row in puncts: H.punct(cx, cy, cell, puncts[row]); continue
            H.glyph(cx, cy, cell)
        for (ra, rb) in strikes:
            cx, ca = C(col, ra); _, cb = C(col, rb)
            H.strike(cx, ca - cell * 0.4, cb + cell * 0.4, cell)
            # replacement written small in the gap to the right of the column
            gx = cx + cell / 2 + gap / 2 + cell * 0.08
            for k in range(rb - ra + 2):
                H.glyph(gx, ca + k * cell * 0.62 - cell * 0.1, cell * 0.5)
            H.stroke([(gx - cell * 0.3, ca - cell * 0.55), (gx - cell * 0.1, ca - cell * 0.45), (gx - cell * 0.42, ca - cell * 0.3)], cell * 0.05)
    if done:   # page number, bottom margin centre
        cx = w / 2; cy = y0 + gh + 1.4 * pxcm
        H.glyph(cx - cell * 0.32, cy, cell * 0.55, 'kana'); H.glyph(cx + cell * 0.32, cy, cell * 0.55, 'kana')
    ink = H.result(w, h)
    a = multiply(a, ink)
    return a, (x0, y0, cell, gap, ncol, nrow)

def column_plan(rng, ncols, nrow, stop_at=None):
    """paragraph structure. returns list of (start, stop, {row: punct}, strikes)"""
    out = []; para_start = True
    for c in range(ncols):
        last = (stop_at is not None and c == stop_at[0])
        start = 1 if para_start else 0
        stop = stop_at[1] if last else nrow
        pun = {}
        if para_start and rng.random() < 0.35:   # dialogue
            pun[start] = 'open'
        end_para = (not last) and rng.random() < 0.3
        if end_para:
            stop = int(rng.integers(6, nrow - 3)); pun[stop - 1] = 'maru'
            if 'open' in pun.values(): pun[stop - 2] = 'close'
        for row in range(start + 2, stop - 2):
            if row not in pun and rng.random() < 0.06: pun[row] = 'ten'
            elif row not in pun and rng.random() < 0.035: pun[row] = 'maru'
        strikes = []
        if rng.random() < 0.18 and stop - start > 8:
            ra = int(rng.integers(start + 2, stop - 5)); strikes.append((ra, ra + int(rng.integers(1, 3))))
        out.append((start, stop, pun, strikes))
        para_start = end_para
        if last: break
    return out

def paint_manuscripts(sheet):
    # the top sheet: 7 columns written, the 8th stops mid-line (no punctuation: mid-sentence)
    rng = np.random.default_rng(1975)
    w, h = 1040, 1440
    plan = column_plan(rng, 15, 25, stop_at=(7, 11))
    plan[4] = (0, 25, {9: 'ten', 17: 'maru'}, [(5, 7)])        # one visible correction
    top, _ = genko(w, h, 11, plan)
    sheet.paste(to_img(top), REG['ms_top'][1:3])
    # a finished page, full, slightly handled, faint ring from the mug
    rng = np.random.default_rng(1979)
    w2, h2 = 1008, 1396
    plan = column_plan(rng, 15, 25)
    done, _ = genko(w2, h2, 23, plan, done=True, age=0.6)
    yy, xx = np.mgrid[0:h2, 0:w2]
    d = np.hypot(xx - w2 * 0.72, yy - h2 * 0.83); R = w2 * 0.135
    ring = np.exp(-((d - R) / 5.0) ** 2) * 0.55 + (d < R) * 0.06
    ring *= 0.6 + 0.4 * fbm(h2, w2, 5, 4, 4)
    done = done * (1 - ring[..., None] * np.array([0.10, 0.22, 0.42]))
    sheet.paste(to_img(done), REG['ms_done'][1:3])

# ------------------------------------------------------------------------------------------------ paper sheet extras
def reg_box(name): s, x0, y0, x1, y1 = REG[name]; return x0, y0, x1, y1

def paint_can(sheet):
    x0, y0, x1, y1 = reg_box('can'); w, h = x1 - x0, y1 - y0
    im = Image.new('RGB', (w, h), (196, 158, 74)); d = ImageDraw.Draw(im)
    n = fbm(h, w, 31, 3, 2)
    a = np.asarray(im).astype(np.float32) * (0.92 + 0.12 * n[..., None]); im = to_img(a); d = ImageDraw.Draw(im)
    green = (22, 58, 40); cream = (238, 226, 192)
    d.rectangle((0, 0, w, 34), fill=green); d.rectangle((0, h - 40, w, h), fill=green)
    d.rectangle((0, 40, w, 44), fill=green); d.rectangle((0, h - 50, w, h - 46), fill=green)
    for rep in (0, 1):      # the design twice around the can
        cx = w * (0.25 + 0.5 * rep)
        d.ellipse((cx - 70, 70, cx + 70, 210), fill=green)
        d.ellipse((cx - 62, 78, cx + 62, 202), outline=cream, width=3)
        # a pine on a hill (invented mark)
        d.polygon([(cx - 40, 175), (cx, 95), (cx + 40, 175)], fill=cream)
        d.rectangle((cx - 5, 175, cx + 5, 190), fill=cream)
        d.polygon([(cx - 55, 196), (cx, 182), (cx + 55, 196)], fill=(196, 158, 74))
        text_c(d, (cx, 248), 'KUROMORI', serif(56, True), green)
        text_c(d, (cx, 295), 'LAGER  BEER', cond(28, True), (90, 40, 20))
        text_c(d, (cx, 326), '黒森ビール', serif_jp(26, 'Bold'), green)
        vtext(d, cx + 0.25 * w - 6, 80, '生', serif_jp(34, 'Bold'), (150, 40, 25), 40)
    sheet.paste(im, (x0, y0))

def paint_ink(sheet):
    x0, y0, x1, y1 = reg_box('ink'); w, h = x1 - x0, y1 - y0
    im = Image.new('RGB', (w, h), (232, 224, 204)); d = ImageDraw.Draw(im)
    d.rectangle((6, 6, w - 7, h - 7), outline=(30, 40, 80), width=4)
    d.rectangle((14, 14, w - 15, 54), fill=(30, 40, 80))
    text_c(d, (w / 2, 34), 'SUIREN', serif(24, True), (232, 224, 204))
    text_c(d, (w / 2, 82), 'BLUE-BLACK', cond(24, True), (30, 40, 80))
    text_c(d, (w / 2, 112), 'INK', serif(26), (30, 40, 80))
    text_c(d, (w / 2, 140), '万年筆用', sans_jp(18), (30, 40, 80))
    sheet.paste(im, (x0, y0))

def paint_dictionary(sheet):
    x0, y0, x1, y1 = reg_box('dict_cover'); w, h = x1 - x0, y1 - y0
    n = fbm(h, w, 41, 5, 3)
    base = np.array((92, 22, 20), np.float32)
    a = np.ones((h, w, 3), np.float32) * base * (0.8 + 0.4 * n[..., None])
    yy, xx = np.mgrid[0:h, 0:w]
    e = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    a += (np.clip(1 - e / 18, 0, 1) ** 1.5 * 60 * (0.6 + 0.8 * n))[..., None] * np.array([1.0, 0.8, 0.7])   # rubbed corners
    im = to_img(a); d = ImageDraw.Draw(im)
    d.rectangle((24, 24, w - 25, h - 25), outline=(70, 14, 12), width=3)
    d.rectangle((32, 32, w - 33, h - 33), outline=(70, 14, 12), width=1)
    text_c(d, (w / 2, h * 0.36), '辞', serif_jp(92, 'Bold'), (70, 14, 12))
    text_c(d, (w / 2, h * 0.58), '典', serif_jp(92, 'Bold'), (70, 14, 12))
    sheet.paste(im, (x0, y0))
    # spine
    x0, y0, x1, y1 = reg_box('dict_spine'); w, h = x1 - x0, y1 - y0
    a = np.ones((h, w, 3), np.float32) * base * (0.85 + 0.4 * fbm(h, w, 42, 4, 3)[..., None])
    a[:, :8] += 30; a[:, -8:] += 30
    im = to_img(a); d = ImageDraw.Draw(im)
    gold = (196, 160, 88)
    for yy in (30, 38, h - 38, h - 30): d.line((10, yy, w - 10, yy), fill=gold, width=3)
    vtext(d, w / 2, 90, '国語辞典', serif_jp(60, 'Bold'), gold, 72)
    text_c(d, (w / 2, h - 80), '改訂', serif_jp(26), gold)
    d.ellipse((w / 2 - 14, h - 62, w / 2 + 14, h - 48), outline=gold, width=2)
    sheet.paste(im, (x0, y0))
    # fore-edge: page lines + thumb-index marks (kana index, staggered black tabs)
    x0, y0, x1, y1 = reg_box('dict_edge'); w, h = x1 - x0, y1 - y0
    rng = np.random.default_rng(43)
    rows = rng.normal(0, 1, (1, w)).astype(np.float32)
    a = np.ones((h, w, 3), np.float32) * np.array((226, 216, 190)) + (rows * 7)[..., None]
    a *= (0.88 + 0.16 * fbm(h, w, 44, 4, 3))[..., None]
    for i in range(10):
        ya = int(h * (0.04 + i * 0.094)); xa = int(w * (0.08 + (i % 5) * 0.18))
        a[ya:ya + int(h * 0.075), xa:xa + int(w * 0.12)] *= 0.18
    sheet.paste(to_img(a), (x0, y0))

def paint_eraser(sheet):
    x0, y0, x1, y1 = reg_box('eraser'); w, h = x1 - x0, y1 - y0
    im = Image.new('RGB', (w, h), (238, 238, 232)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w * 0.34, h), fill=(150, 50, 36)); d.rectangle((w * 0.66, 0, w, h), fill=(150, 50, 36))
    text_c(d, (w / 2, h * 0.38), 'PLASTIC', cond(13, True), (30, 30, 30))
    text_c(d, (w / 2, h * 0.66), 'ERASER', cond(13, True), (30, 30, 30))
    sheet.paste(im, (x0, y0))

# ------------------------------------------------------------------------------------------------ print sheet
def paint_noren(sheet):
    x0, y0, x1, y1 = reg_box('noren'); w, h = x1 - x0, y1 - y0
    n1 = fbm(h, w, 51, 5, 2); n2 = fbm(h, w, 52, 3, 6)
    rng = np.random.default_rng(53)
    warp = gaussian_filter(rng.normal(0, 1, (h, w)).astype(np.float32), 0.6)
    weave = np.repeat(rng.normal(0, 1, (1, w)).astype(np.float32), h, 0) * 0.6 + warp * 0.6
    mustard = np.array((184, 136, 52), np.float32)
    a = np.ones((h, w, 3), np.float32) * mustard
    yy, xx = np.mgrid[0:h, 0:w]
    fade = np.clip(0.18 * (1 - yy / h) + 0.12 * (n1 - 0.5), 0, 1)       # sun-faded towards the top, unevenly
    a = a * (1 - fade[..., None]) + np.array((214, 190, 140)) * fade[..., None]
    a *= (0.93 + 0.1 * n2)[..., None]; a += (weave * 5)[..., None]
    # top sleeve (wraps the rod): doubled cloth + stitch line
    sl = int(h * 0.075)
    a[:sl] *= 0.86
    for x in range(0, w, 14): a[sl + 3:sl + 5, x:x + 8] *= 0.7
    # hem at the bottom
    a[h - 14:] *= 0.88
    for x in range(0, w, 14): a[h - 20:h - 18, x:x + 8] *= 0.72
    # the cat, dyed dark brown, straddling the middle split (panel boundary at u = 0.5)
    cat = Image.open(EMBLEM).convert('RGBA'); bb = cat.getbbox(); cat = cat.crop(bb)
    ch = int(h * 0.58); cw = int(cat.width * ch / cat.height)
    cat = cat.resize((cw, ch), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
    m = np.zeros((h, w), np.float32)
    cx, cy = w // 2, int(h * 0.53)
    m[cy - ch // 2:cy - ch // 2 + ch, cx - cw // 2:cx - cw // 2 + cw] = np.asarray(cat)[..., 3] / 255.0
    m *= 0.86 + 0.14 * n2           # dye unevenness
    brown = np.array((58, 36, 20), np.float32) * (0.9 + 0.25 * n1[..., None])
    a = a * (1 - m[..., None]) + brown * m[..., None]
    # small shop name, lower right of the right-most panel, also dyed
    im = to_img(a); d = ImageDraw.Draw(im)
    vtext(d, int(w * 0.94), int(h * 0.56), "DEAN'S", serif(22, True), (70, 44, 24), 24)
    sheet.paste(im, (x0, y0))

def paint_calendar(sheet):
    x0, y0, x1, y1 = reg_box('calendar'); w, h = x1 - x0, y1 - y0
    a = paper_base(w, h, 61, (238, 232, 216), 0.5)
    im = to_img(a); d = ImageDraw.Draw(im)
    # picture: two persimmons on a branch, flat woodblock colours
    px0, py0, px1, py1 = 26, 30, w - 26, int(h * 0.44)
    d.rectangle((px0, py0, px1, py1), fill=(214, 200, 168))
    d.rectangle((px0, int(py1 - (py1 - py0) * 0.28), px1, py1), fill=(190, 172, 140))
    d.line((px0 + 10, py0 + 40, px1 - 70, py0 + 70, px1 - 30, py0 + 150), fill=(60, 40, 28), width=7)
    for (cx, cy, r) in ((w * 0.38, py0 + 140, 46), (w * 0.62, py0 + 175, 40)):
        d.ellipse((cx - r, cy - r * 0.92, cx + r, cy + r * 0.92), fill=(212, 100, 34))
        d.ellipse((cx - r * 0.55, cy - r * 0.6, cx - r * 0.1, cy - r * 0.2), fill=(232, 140, 70))
        d.polygon([(cx, cy - r * 0.95), (cx - 22, cy - r * 0.75 - 12), (cx - 4, cy - r * 0.8), (cx + 20, cy - r * 0.95 - 10)], fill=(70, 80, 40))
        d.line((cx, cy - r * 0.9, cx + 6, py0 + 70), fill=(60, 40, 28), width=3)
    d.rectangle((px0, py0, px1, py1), outline=(80, 60, 40), width=2)
    # heading
    hy = int(h * 0.50)
    text_c(d, (w * 0.30, hy), '十一月', serif_jp(54, 'Bold'), (40, 30, 26))
    text_c(d, (w * 0.75, hy - 10), '11', serif(52, True), (150, 40, 30))
    text_c(d, (w * 0.75, hy + 26), 'NOVEMBER', cond(14), (60, 50, 40))
    # grid: 7 columns, 1st = Saturday
    gy0 = int(h * 0.57); cw = (w - 40) / 7; rh = (h * 0.95 - gy0 - 26) / 5
    wd = '日月火水木金土'; fj = sans_jp(18, 'Medium'); fn = serif(24, True)
    for i, ch in enumerate(wd):
        text_c(d, (20 + cw * (i + 0.5), gy0 + 10), ch, fj, (170, 40, 30) if i == 0 else ((40, 60, 120) if i == 6 else (50, 40, 34)))
    d.line((20, gy0 + 24, w - 20, gy0 + 24), fill=(90, 80, 70), width=1)
    ring_xy = None
    for day in range(1, 31):
        k = day - 1 + 6; col, row = k % 7, k // 7
        if row > 4: row = 4               # 30th shares the last row's cell (old calendars stack 23/30)
        cx = 20 + cw * (col + 0.5); cy = gy0 + 26 + rh * (row + 0.5)
        colr = (170, 40, 30) if col == 0 else ((40, 60, 120) if col == 6 else (40, 32, 28))
        if day == 30: cx, cy = 20 + cw * 0.78, gy0 + 26 + rh * 4.72; fsz = serif(15, True)
        else: fsz = fn
        if day == 23: cy -= rh * 0.18
        text_c(d, (cx, cy), str(day), fsz, colr)
        if day == 14: ring_xy = (cx, cy)
    # one date ringed in red pencil
    rr = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0)); rd = ImageDraw.Draw(rr)
    cx, cy = ring_xy[0] * 2, ring_xy[1] * 2
    rng = np.random.default_rng(64)
    pts = [(cx + (32 + rng.normal(0, 1.5)) * 2 * math.cos(t) * 1.12, cy + (26 + rng.normal(0, 1.5)) * 2 * math.sin(t)) for t in np.linspace(-0.6, 2 * math.pi + 0.3, 40)]
    for p, q in zip(pts[:-1], pts[1:]): rd.line((*p, *q), fill=(200, 40, 32, 210), width=6)
    rr = rr.resize((w, h), Image.LANCZOS)
    im = Image.alpha_composite(im.convert('RGBA'), rr).convert('RGB'); d = ImageDraw.Draw(im)
    text_c(d, (w / 2, h - 16), '酒・米・調味料　大川商店', sans_jp(15), (90, 70, 60))
    d.ellipse((w / 2 - 7, 10, w / 2 + 7, 24), fill=(120, 110, 96))          # nail hole
    sheet.paste(im, (x0, y0))

def paint_radio(sheet):
    x0, y0, x1, y1 = reg_box('radio'); w, h = x1 - x0, y1 - y0     # 24 x 15 cm, ~33 px/cm
    im = Image.new('RGB', (w, h), (222, 212, 188)); d = ImageDraw.Draw(im)
    n = fbm(h, w, 71, 3, 3); a = np.asarray(im).astype(np.float32) * (0.95 + 0.08 * n[..., None]); im = to_img(a); d = ImageDraw.Draw(im)
    # dial window across the top
    d.rounded_rectangle((26, 22, w - 26, 148), 14, fill=(36, 30, 24), outline=(170, 160, 140), width=5)
    d.rectangle((40, 36, w - 40, 134), fill=(226, 214, 180))
    f = cond(18, True); fs = cond(13)
    for i, v in enumerate(['53', '60', '70', '80', '100', '120', '140', '160']):
        x = 100 + i * (w - 170) / 7
        d.line((x, 40, x, 58), fill=(40, 34, 30), width=2); text_c(d, (x, 72), v, f, (40, 34, 30))
    for i, v in enumerate(['76', '80', '84', '88', '90']):
        x = 100 + i * (w - 170) / 4
        d.line((x, 116, x, 132), fill=(150, 40, 30), width=2); text_c(d, (x, 100), v, f, (150, 40, 30))
    for k in range(57):
        x = 100 + k * (w - 170) / 56; d.line((x, 40, x, 48), fill=(40, 34, 30), width=1)
    text_c(d, (52, 72), 'AM', fs, (40, 34, 30)); text_c(d, (52, 100), 'FM', fs, (150, 40, 30))
    nx = 100 + 0.43 * (w - 170); d.line((nx, 36, nx, 134), fill=(200, 30, 20), width=4)
    # speaker grille: perforated chrome panel, left 62%
    gx0, gy0, gx1, gy1 = 26, 168, int(w * 0.64), h - 24
    d.rounded_rectangle((gx0, gy0, gx1, gy1), 12, fill=(150, 150, 146), outline=(205, 205, 200), width=5)
    for yy in range(gy0 + 18, gy1 - 10, 14):
        off = 7 if ((yy - gy0) // 14) % 2 else 0
        for xx in range(gx0 + 16 + off, gx1 - 10, 14): d.ellipse((xx - 3.5, yy - 3.5, xx + 3.5, yy + 3.5), fill=(30, 28, 26))
    # right panel: badge, band switch marks
    bx = int(w * 0.66)
    d.rounded_rectangle((bx + 8, gy0, w - 26, gy0 + 70), 8, fill=(170, 150, 100), outline=(110, 90, 50), width=3)
    text_c(d, ((bx + w - 18) / 2, gy0 + 35), 'KOHARU', serif(32, True), (60, 40, 20))
    text_c(d, ((bx + w - 18) / 2, gy0 + 100), '8 TRANSISTOR', cond(20, True), (60, 50, 40))
    text_c(d, ((bx + w - 18) / 2, gy0 + 128), 'SOLID STATE', cond(17), (60, 50, 40))
    d.line((bx + 20, gy0 + 152, w - 38, gy0 + 152), fill=(120, 110, 90), width=2)
    for i, s in enumerate(('OFF', 'AM', 'FM')):
        text_c(d, (bx + 52 + i * 70, gy0 + 176), s, fs, (60, 50, 40)); d.ellipse((bx + 46 + i * 70, gy0 + 192, bx + 58 + i * 70, gy0 + 204), fill=(60, 50, 40))
    d.rounded_rectangle((bx + 8, gy1 - 60, w - 26, gy1), 10, fill=(60, 52, 44))
    text_c(d, ((bx + w - 18) / 2, gy1 - 30), 'VOLUME · TONE', cond(15, True), (200, 190, 170))
    sheet.paste(im, (x0, y0))

def paint_label(sheet, name, bg, lines, border=None, deco=None):
    x0, y0, x1, y1 = reg_box(name); w, h = x1 - x0, y1 - y0
    im = Image.new('RGB', (w, h), bg); d = ImageDraw.Draw(im)
    a = np.asarray(im).astype(np.float32) * (0.93 + 0.1 * fbm(h, w, hash(name) % 1000, 3, 2)[..., None]); im = to_img(a); d = ImageDraw.Draw(im)
    if border: d.rectangle((6, 6, w - 7, h - 7), outline=border, width=4)
    if deco: deco(d, w, h)
    for (rel, s, f, c) in lines: text_c(d, (w * rel[0], h * rel[1]), s, f, c)
    sheet.paste(im, (x0, y0))

def paint_labels(sheet):
    G = (40, 80, 50); CR = (238, 228, 200); BR = (70, 40, 24); RD = (160, 40, 30)
    def tea_deco(d, w, h):
        for rep in (0.25, 0.75):
            d.ellipse((w * rep - 46, 20, w * rep + 46, h - 20), outline=CR, width=3)
    paint_label(sheet, 'tin_tea', G, [((0.25, 0.5), '緑茶', serif_jp(52, 'Bold'), CR), ((0.75, 0.5), '山園', serif_jp(48, 'Bold'), CR),
                                      ((0.5, 0.86), 'YAMAZONO', cond(18, True), CR)], CR, tea_deco)
    paint_label(sheet, 'tin_coffee', (118, 66, 34), [((0.25, 0.42), 'COFFEE', serif(40, True), CR), ((0.25, 0.72), 'KAWASE BLEND', cond(20), CR),
                                                     ((0.75, 0.42), 'COFFEE', serif(40, True), CR), ((0.75, 0.72), '珈琲', serif_jp(30, 'Bold'), CR)], CR)
    def bisc(d, w, h):
        for i in range(0, w, 40): d.rectangle((i, 0, i + 20, 24), fill=(170, 40, 34)); d.rectangle((i + 20, h - 24, i + 40, h), fill=(170, 40, 34))
    paint_label(sheet, 'tin_biscuit', (232, 214, 170), [((0.25, 0.5), 'Biscuits', serif(44, True), (120, 30, 26)), ((0.75, 0.5), 'OKAWADO', serif(40, True), (40, 60, 110))], None, bisc)
    paint_label(sheet, 'jar_a', (232, 222, 196), [((0.5, 0.5), '梅干', sans_jp(58, 'Bold'), RD)], RD)
    paint_label(sheet, 'jar_b', (240, 234, 216), [((0.5, 0.5), '砂糖', sans_jp(56, 'Medium'), (40, 40, 60))])
    paint_label(sheet, 'soy', (230, 214, 170), [((0.5, 0.22), 'マル久', sans_jp(36, 'Bold'), RD), ((0.5, 0.58), '醤油', serif_jp(70, 'Bold'), (30, 24, 20)),
                                               ((0.5, 0.88), 'こいくち', sans_jp(24), (30, 24, 20))], RD)
    paint_label(sheet, 'oil', (210, 226, 200), [((0.5, 0.3), 'サラダ油', sans_jp(40, 'Bold'), (40, 80, 40)), ((0.5, 0.7), 'SALAD OIL', cond(28, True), (40, 80, 40))], (40, 80, 40))
    paint_label(sheet, 'badge', (190, 190, 186), [((0.5, 0.5), 'FROST·ACE', serif(34, True), (60, 60, 64))], (110, 110, 110))

def main():
    os.makedirs(OUT, exist_ok=True)
    paper = Image.new('RGB', (S, S), (200, 196, 186))
    paint_manuscripts(paper); paint_can(paper); paint_ink(paper); paint_dictionary(paper); paint_eraser(paper)
    paper.save(os.path.join(OUT, 'paper.png'))
    pr = Image.new('RGB', (S, S), (180, 170, 150))
    paint_noren(pr); paint_calendar(pr); paint_radio(pr); paint_labels(pr)
    pr.save(os.path.join(OUT, 'print.png'))
    print('wrote', OUT)

if __name__ == '__main__':
    main()
