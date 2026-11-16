"""COUNTER part: the mahogany bar counter, foot rail, four stools, four pendants, the brass counter lamp and the still life
on the counter (whisky, the second drink, ashtray + cigar, the owner's note, matchbook, cigar box, paperback, peanuts...),
plus the cash register end (right) and the coffee end (left).  Painted labels: tex.py -> tex/sheet.png + tex/regions.json"""
import os, json, math, random
import bmesh
from mathutils import Vector, Matrix
from barkit import kit, mats, layout
from barkit.kit import T, Rx, Ry, Rz

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = os.path.join(HERE, 'tex', 'sheet.png')
C = layout.COUNTER
Z = C['top_z']
SL = layout.STILL_LIFE
IA = layout.INTERACTIVE

def S(sx, sy, sz):
    return Matrix.Diagonal((sx, sy, sz, 1.0))

# =========================================================================================== geometry helpers
def lathe_bm(prof, segs=24, mi=None):
    bm = bmesh.new(); rings = []
    for (r, z) in prof:
        if r < 1e-7: rings.append([bm.verts.new((0, 0, z))])
        else: rings.append([bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), z)) for j in range(segs)])
    for i in range(len(prof) - 1):
        A, B = rings[i], rings[i + 1]
        if len(A) == 1 and len(B) == 1: continue
        for j in range(segs):
            j2 = (j + 1) % segs
            if len(A) == 1: f = bm.faces.new((A[0], B[j2], B[j]))
            elif len(B) == 1: f = bm.faces.new((A[j], A[j2], B[0]))
            else: f = bm.faces.new((A[j], A[j2], B[j2], B[j]))
            if mi: f.material_index = mi[i]
    return bm, rings

def lathe(name, prof, mat, segs=24, mi=None, smooth=True, sharp=35, edit=None):
    bm, rings = lathe_bm(prof, segs, mi)
    if edit: edit(bm, rings)
    return kit.finish(name, bm, mat, smooth=smooth, sharp=sharp)

def ring_pts(R, z, n=24, cx=0.0, cy=0.0):
    return [(cx + R * math.cos(2 * math.pi * k / n), cy + R * math.sin(2 * math.pi * k / n), z) for k in range(n + 1)]

def torus(name, R, r, z, mat, n=24, segs=6, cx=0.0, cy=0.0):
    return kit.tube(name, ring_pts(R, z, n, cx, cy), r, mat, segs=segs, caps=False)

def uvmap(rect, s, t):
    u0, v0, u1, v1 = rect
    return (u0 + (u1 - u0) * s, v0 + (v1 - v0) * t)

def slab(name, w, h, t, mats_, rect=None, nx=1, ny=1, bend=None, bottom=False, top_mi=0, side_mi=1):
    """panel x in [-w/2, w/2], y in [0, h], z in [0, t]; top face (+z) carries the image region `rect`; bend(x, y) -> dz"""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('uv_tex')
    f = bend or (lambda x, y: 0.0)
    xs = [-w / 2 + w * i / nx for i in range(nx + 1)]; ys = [h * j / ny for j in range(ny + 1)]
    Tg = [[bm.verts.new((x, y, t + f(x, y))) for y in ys] for x in xs]
    Bg = [[bm.verts.new((x, y, f(x, y))) for y in ys] for x in xs]
    for i in range(nx):
        for j in range(ny):
            fc = bm.faces.new((Tg[i][j], Tg[i + 1][j], Tg[i + 1][j + 1], Tg[i][j + 1])); fc.material_index = top_mi
            if rect:
                for lp, (a, b) in zip(fc.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    lp[uvl].uv = uvmap(rect, a / nx, b / ny)
            if bottom:
                fb = bm.faces.new((Bg[i][j + 1], Bg[i + 1][j + 1], Bg[i + 1][j], Bg[i][j])); fb.material_index = side_mi
    per = [(i, 0) for i in range(nx)] + [(nx, j) for j in range(ny)] + [(i, ny) for i in range(nx, 0, -1)] + [(0, j) for j in range(ny, 0, -1)]
    for k in range(len(per)):
        a = per[k]; b = per[(k + 1) % len(per)]
        fs = bm.faces.new((Bg[a[0]][a[1]], Bg[b[0]][b[1]], Tg[b[0]][b[1]], Tg[a[0]][a[1]])); fs.material_index = side_mi
    return kit.finish(name, bm, mats_)

def disc(name, r, z0, z1, mats_, rect=None, segs=24, top_mi=0, side_mi=1, rot=0.0):
    """round disc with an image on top (rect = region); centred on the local origin"""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('uv_tex')
    top = []; bot = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        top.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z1))); bot.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z0)))
    ft = bm.faces.new(top); ft.material_index = top_mi
    if rect:
        for lp in ft.loops:
            x, y = lp.vert.co.x / r, lp.vert.co.y / r
            ca, sa = math.cos(rot), math.sin(rot)
            x, y = x * ca - y * sa, x * sa + y * ca
            lp[uvl].uv = uvmap(rect, 0.5 + 0.5 * x, 0.5 + 0.5 * y)
    for k in range(segs):
        k2 = (k + 1) % segs
        fs = bm.faces.new((bot[k], bot[k2], top[k2], top[k])); fs.material_index = side_mi
    return kit.finish(name, bm, mats_, smooth=False)

def prism_x(name, poly_yz, x0, x1, mats_, cap_mi=0, side_mi=0, skip_bottom=True):
    """polygon in the YZ plane (CCW seen from +X) extruded along X"""
    bm = bmesh.new()
    A = [bm.verts.new((x0, y, z)) for (y, z) in poly_yz]; B = [bm.verts.new((x1, y, z)) for (y, z) in poly_yz]
    fb = bm.faces.new(B); fb.material_index = cap_mi
    fa = bm.faces.new(list(reversed(A))); fa.material_index = cap_mi
    n = len(poly_yz)
    for k in range(n):
        k2 = (k + 1) % n
        (ya, za), (yb, zb) = poly_yz[k], poly_yz[k2]
        if skip_bottom and abs(za - zb) < 1e-9 and za <= min(p[1] for p in poly_yz) + 1e-9: continue
        f = bm.faces.new((A[k], A[k2], B[k2], B[k])); f.material_index = side_mi
    bm.normal_update()
    for f in bm.faces:   # make sure caps/sides point outward
        c = f.calc_center_median(); cen = Vector(((x0 + x1) / 2, sum(p[0] for p in poly_yz) / n, sum(p[1] for p in poly_yz) / n))
        if f.normal.dot(c - cen) < 0: f.normal_flip()
    return kit.finish(name, bm, mats_)

def flat_poly(name, pts, z0, z1, mat):
    """2D outline (CCW) extruded in Z, no bottom"""
    bm = bmesh.new()
    top = [bm.verts.new((x, y, z1)) for x, y in pts]; bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    bm.faces.new(top)
    n = len(pts)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((bot[k], bot[k2], top[k2], top[k]))
    return kit.finish(name, bm, mat)

# =========================================================================================== materials
def bulb(name, col, strength, night_only=True):
    """emissive bulb that does NOT block the real point light sitting inside it"""
    m = mats.emissive(name, col, strength, night_only)
    if not m.get('counter_sfix'):
        nt = m.node_tree; out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        tr = mats.N(nt, 'ShaderNodeBsdfTransparent'); lp = mats.N(nt, 'ShaderNodeLightPath'); mx = mats.N(nt, 'ShaderNodeMixShader')
        mats.L(nt, lp.outputs['Is Shadow Ray'], mx.inputs[0]); mats.L(nt, b.outputs[0], mx.inputs[1]); mats.L(nt, tr.outputs[0], mx.inputs[2])
        mats.L(nt, mx.outputs[0], out.inputs[0]); m['counter_sfix'] = 1
    return m

RINGS = [(0.29, -0.885, 0.036, 0.0016, 0.55), (-0.175, -0.70, 0.040, 0.0020, 0.5), (0.52, -0.33, 0.037, 0.0016, 0.6),
         (0.05, -0.47, 0.034, 0.0014, 0.4), (-1.05, -0.84, 0.038, 0.0020, 0.7), (1.25, -0.70, 0.036, 0.0018, 0.7),
         (0.60, -0.84, 0.031, 0.0014, 0.45), (-0.62, -0.86, 0.037, 0.0016, 0.5), (0.315, -0.862, 0.035, 0.0012, 0.3)]

def mahogany(name, rough=0.2, coat=1.0, scale=2.4, rings=None, cols=None):
    if name in mats._M: return mats._M[name]
    cols = cols or ((0.030, 0.008, 0.005), (0.10, 0.030, 0.015), (0.19, 0.068, 0.032))
    m = mats.wood(name, axis='X', cols=cols, rough=rough, rvar=0.08, scale=scale, bmp=0.04, coat=coat)
    nt = m.node_tree; N, L, M = mats.N, mats.L, mats.math_
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Coat Roughness'].default_value = 0.05
    if not rings: return m
    tc = N(nt, 'ShaderNodeTexCoord')
    flat0 = N(nt, 'ShaderNodeVectorMath', operation='MULTIPLY'); L(nt, tc.outputs['Object'], flat0.inputs[0]); flat0.inputs[1].default_value = (1, 1, 0)
    wob = N(nt, 'ShaderNodeTexNoise'); wob.inputs['Scale'].default_value = 60; wob.inputs['Detail'].default_value = 2; L(nt, tc.outputs['Object'], wob.inputs['Vector'])
    wv = N(nt, 'ShaderNodeVectorMath', operation='MULTIPLY_ADD'); L(nt, wob.outputs['Color'], wv.inputs[0]); wv.inputs[1].default_value = (0.004, 0.004, 0)
    wv.inputs[2].default_value = (-0.002, -0.002, 0)
    flat = N(nt, 'ShaderNodeVectorMath', operation='ADD'); L(nt, flat0.outputs[0], flat.inputs[0]); L(nt, wv.outputs[0], flat.inputs[1])
    acc = None
    for (cx, cy, r, w, st) in rings:
        dn = N(nt, 'ShaderNodeVectorMath', operation='DISTANCE'); L(nt, flat.outputs[0], dn.inputs[0]); dn.inputs[1].default_value = (cx, cy, 0)
        e = M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', dn.outputs['Value'], r))
        k = M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', 1.0, M(nt, 'DIVIDE', e, w), clamp=True), st)
        acc = k if acc is None else M(nt, 'MAXIMUM', acc, k)
    brk = mats.ramp(nt, mats.noise(nt, tc.outputs['Object'], 34, 4, 0.6), [(0.42, (0.0, 0.0, 0.0)), (0.62, (1, 1, 1))])
    acc = M(nt, 'MULTIPLY', acc, brk)
    old = b.inputs['Base Color'].links[0].from_socket
    L(nt, mats.mixc(nt, old, (0.12, 0.06, 0.035), M(nt, 'MULTIPLY', acc, 0.45), 'MIX'), b.inputs['Base Color'])
    oldr = b.inputs['Roughness'].links[0].from_socket
    L(nt, M(nt, 'ADD', oldr, M(nt, 'MULTIPLY', acc, 0.3), clamp=True), b.inputs['Roughness'])
    L(nt, M(nt, 'SUBTRACT', coat, M(nt, 'MULTIPLY', acc, 0.55), clamp=True), b.inputs['Coat Weight'])
    return m

def oxblood(name, col=(0.075, 0.012, 0.010)):
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    N, L, Mm = mats.N, mats.L, mats.math_
    v = mats.coords(nt)
    vor = N(nt, 'ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 300; L(nt, v, vor.inputs['Vector'])
    n1 = mats.noise(nt, v, 7, 5, 0.65)
    L(nt, mats.ramp(nt, n1, [(0.35, tuple(c * 0.6 for c in col)), (0.75, tuple(c * 1.6 for c in col))]), b.inputs['Base Color'])
    L(nt, Mm(nt, 'ADD', 0.40, Mm(nt, 'MULTIPLY', n1, 0.22)), b.inputs['Roughness'])
    mats.setp(b, coat=0.25, coat_rough=0.35)
    mats.bump(nt, b, Mm(nt, 'ADD', vor.outputs[0], Mm(nt, 'MULTIPLY', n1, 0.6)), 0.25, 0.0008)
    return m

def MATS():
    M = {}
    M['top'] = mahogany('counter_mahogany_top', rough=0.22, coat=1.0, rings=RINGS)
    M['panel'] = mahogany('counter_mahogany_panel', rough=0.32, coat=0.45, scale=2.0)
    M['panel_z'] = mats.wood('counter_mahogany_stile', axis='Z', cols=((0.030, 0.008, 0.005), (0.10, 0.030, 0.015), (0.19, 0.068, 0.032)),
                             rough=0.32, rvar=0.08, scale=2.0, bmp=0.04, coat=0.45)
    M['kick'] = mats.noisy('counter_kick', (0.012, 0.006, 0.004), (0.03, 0.016, 0.01), rough=0.45, scale=30)
    M['brass'] = mats.metal('counter_brass', (0.80, 0.56, 0.26), rough=0.22, patina=0.35)
    M['brass_old'] = mats.metal('counter_brass_old', (0.66, 0.45, 0.20), rough=0.32, patina=0.5)
    M['chrome'] = mats.metal('counter_chrome', (0.78, 0.78, 0.80), rough=0.14, patina=0.15)
    M['steel'] = mats.metal('counter_steel', (0.55, 0.55, 0.57), rough=0.32, patina=0.25)
    M['leather'] = oxblood('counter_leather')
    M['enamel'] = mats.plain('counter_enamel_green', (0.018, 0.065, 0.040), rough=0.22, coat=0.8, coat_rough=0.05)
    M['shade_in'] = mats.plain('counter_shade_cream', (0.40, 0.34, 0.23), rough=0.45)
    M['cord'] = mats.noisy('counter_cord', (0.035, 0.022, 0.015), (0.08, 0.055, 0.035), rough=0.85, scale=900, sc3=(1, 1, 0.2))
    M['bulb'] = bulb('counter_bulb', (1.0, 0.74, 0.46), 30, True)
    M['lampbulb'] = bulb('counter_lampbulb', (1.0, 0.70, 0.40), 22, True)
    M['paper'] = mats.shade_paper('counter_shade_paper', (0.93, 0.70, 0.42))
    M['glass'] = mats.glass('counter_glass', (0.98, 0.99, 0.98), rough=0.0)
    M['mist'] = mats.glass('counter_glass_mist', (0.94, 0.96, 0.97), rough=0.28)
    M['whisky'] = mats.glass('counter_whisky', (1.0, 0.68, 0.30), shadow=(1.0, 0.65, 0.3), ior=1.34)
    M['highball'] = mats.glass('counter_highball', (1.0, 0.93, 0.74), shadow=(1.0, 0.85, 0.55), ior=1.34)
    M['ice'] = mats.glass('counter_ice', (0.97, 0.985, 1.0), rough=0.16, ior=1.31)
    M['coffee'] = mats.glass('counter_coffee', (0.16, 0.06, 0.02), shadow=(0.3, 0.15, 0.05), ior=1.33)
    M['labels'] = mats.image('counter_labels', SHEET, rough=0.6)
    M['labels_gloss'] = mats.image('counter_labels_gloss', SHEET, rough=0.32)
    M['card'] = mats.plain('counter_card', (0.74, 0.70, 0.60), rough=0.7)
    M['pages'] = mats.noisy('counter_pages', (0.62, 0.54, 0.38), (0.74, 0.67, 0.50), rough=0.8, scale=200, sc3=(1, 1, 1))
    M['cork'] = mats.noisy('counter_cork', (0.30, 0.18, 0.09), (0.50, 0.33, 0.18), rough=0.85, scale=500)
    M['cedar'] = mats.wood('counter_cedar', axis='X', cols=((0.17, 0.06, 0.025), (0.30, 0.12, 0.05), (0.42, 0.19, 0.09)), rough=0.6, scale=2.5)
    M['gold_paper'] = mats.plain('counter_gold_paper', (0.55, 0.38, 0.12), rough=0.35, metal_=0.6)
    M['leaf'] = mats.noisy('counter_leaf', (0.085, 0.038, 0.016), (0.19, 0.095, 0.042), rough=0.6, scale=90, bmp=0.12)
    M['ash'] = mats.noisy('counter_ash', (0.24, 0.21, 0.18), (0.56, 0.51, 0.45), rough=0.95, scale=160, bmp=0.3)
    M['ember'] = mats.emissive('counter_ember', (1.0, 0.30, 0.05), 9, night_only=False)
    M['band'] = mats.plain('counter_cigar_band', (0.36, 0.04, 0.03), rough=0.35)
    M['porcelain'] = mats.plain('counter_porcelain', (0.86, 0.83, 0.76), rough=0.1, coat=0.4)
    M['cobalt'] = mats.plain('counter_cobalt', (0.04, 0.09, 0.32), rough=0.12)
    M['cup'] = mats.plain('counter_cup', (0.80, 0.74, 0.60), rough=0.12, coat=0.4)
    M['cupline'] = mats.plain('counter_cupline', (0.10, 0.22, 0.13), rough=0.15)
    M['peanut'] = mats.noisy('counter_peanut', (0.40, 0.21, 0.09), (0.66, 0.42, 0.20), rough=0.5, scale=70, bmp=0.15)
    M['coin'] = mats.metal('counter_coin', (0.74, 0.73, 0.70), rough=0.28, patina=0.4, scale=60)
    M['coin5'] = mats.metal('counter_coin_brass', (0.78, 0.58, 0.28), rough=0.3, patina=0.4, scale=60)
    M['water'] = mats.plain('counter_water', (0.17, 0.12, 0.09), rough=0.12, coat=1.0, coat_rough=0.02)
    M['black'] = mats.plain('counter_black', (0.012, 0.011, 0.01), rough=0.3)
    M['rubber'] = mats.plain('counter_rubber', (0.03, 0.025, 0.022), rough=0.6)
    M['tape'] = mats.plain('counter_tape', (0.70, 0.64, 0.46), rough=0.3)
    M['pencil'] = mats.plain('counter_pencil_paint', (0.55, 0.30, 0.04), rough=0.35)
    M['pwood'] = mats.plain('counter_pencil_wood', (0.62, 0.45, 0.28), rough=0.7)
    M['graphite'] = mats.plain('counter_graphite', (0.05, 0.05, 0.055), rough=0.3, metal_=0.4)
    M['regbody'] = mats.metal('counter_register', (0.22, 0.14, 0.075), rough=0.34, patina=0.55, scale=30)
    M['green'] = mats.plain('counter_matchgreen', (0.03, 0.08, 0.05), rough=0.6)
    M['menuwood'] = mats.wood('counter_menuwood', axis='X', rough=0.45)
    return M

# =========================================================================================== the counter
def build_counter(M):
    x0, x1 = -2.22, 2.22
    prof = [(-0.25, Z)]
    yf, rr = C['top_y0'], 0.026
    for k in range(7):                         # soft bull-nose on the customer edge
        t = math.radians(90 * k / 6)
        prof.append((yf + rr - rr * math.sin(t), Z - rr + rr * math.cos(t)))
    r2 = 0.016
    for k in range(1, 5):
        t = math.radians(90 * k / 4)
        prof.append((yf + r2 - r2 * math.cos(t), Z - rr - r2 * math.sin(t) + 0.0))
    zb = prof[-1][1]
    def section(name, xa, xb, cap_a, cap_b):
        bm = bmesh.new()
        A = [bm.verts.new((xa, y, z)) for y, z in prof]; B = [bm.verts.new((xb, y, z)) for y, z in prof]
        for i in range(len(prof) - 1):
            bm.faces.new((A[i], A[i + 1], B[i + 1], B[i]))
        poly = prof + [(-0.25, zb)]
        if cap_a: bm.faces.new([A[i] for i in range(len(prof))] + [bm.verts.new((xa, -0.25, zb))])
        if cap_b: bm.faces.new([B[i] for i in range(len(prof))] + [bm.verts.new((xb, -0.25, zb))])
        bm.normal_update()
        for f in bm.faces:
            c = f.calc_center_median(); ref = Vector((c.x, -0.62, Z - 0.03))
            if abs(f.normal.x) > 0.9: ref = Vector(((xa + xb) / 2, c.y, c.z))
            if f.normal.dot(c - ref) < 0: f.normal_flip()
        return kit.finish(name, bm, M['top'], smooth=True, sharp=40)
    with kit.props(td=1.25): section('top_mid', -0.95, 0.95, False, False)
    with kit.props(td=0.5):
        section('top_left', x0, -0.95, True, False); section('top_right', 0.95, x1, False, True)
    # ---- the panelled front
    y0 = C['body_y0']; yb = C['body_y1']; ztop = zb
    with kit.props(td=0.32):
        kit.box('kick', -2.19, 2.19, y0 + 0.015, yb, 0.0, 0.09, M['kick'], only=['-y', '-x', '+x', '+z'])
        kit.box('board', -2.2, 2.2, y0, yb, 0.09, ztop, M['panel'], only=['-y', '-x', '+x'])
        n = 8; st = 0.07; bw = (4.4 - (n + 1) * st) / n
        for i in range(n + 1):
            xs = -2.2 + i * (bw + st)
            kit.box('stile%d' % i, xs, xs + st, y0 - 0.018, y0, 0.09, ztop - 0.005, M['panel_z'], skip='+y', bevel=0.004, segs=1)
        kit.box('rail_bot', -2.2, 2.2, y0 - 0.016, y0, 0.09, 0.19, M['panel'], skip='+y -z', bevel=0.004, segs=1)
        kit.box('rail_top', -2.2, 2.2, y0 - 0.016, y0, ztop - 0.10, ztop - 0.005, M['panel'], skip='+y', bevel=0.004, segs=1)
        kit.box('shoe', -2.21, 2.21, y0 - 0.026, y0, 0.075, 0.095, M['panel'], skip='+y -z', bevel=0.005, segs=2)
        for i in range(n):
            xs = -2.2 + st + i * (bw + st) + 0.012
            kit.box('field%d' % i, xs, xs + bw - 0.024, y0 - 0.012, y0, 0.202, ztop - 0.117, M['panel'], skip='+y', bevel=0.012, segs=1)
        # counter ends: one raised panel each
        for sx in (-1, 1):
            xe = 2.2 * sx
            kit.box('end_frame%d' % sx, min(xe, xe + 0.016 * sx), max(xe, xe + 0.016 * sx), y0 - 0.018, yb, 0.09, ztop - 0.005, M['panel_z'],
                    only=['+x' if sx > 0 else '-x', '-y'], bevel=0.004, segs=1)
            kit.box('end_field%d' % sx, min(xe, xe + 0.026 * sx), max(xe, xe + 0.026 * sx), y0 + 0.06, yb - 0.06, 0.20, ztop - 0.12, M['panel'],
                    only=['+x' if sx > 0 else '-x', '-y', '+y', '+z', '-z'], bevel=0.008, segs=1)
    # ---- brass foot rail on brackets
    with kit.props(td=0.55):
        zr, yr, xr = 0.21, -0.99, 2.10
        pts = [(-xr, y0 - 0.018, zr), (-xr, -0.94, zr), (-xr + 0.012, -0.972, zr), (-xr + 0.04, yr, zr),
               (xr - 0.04, yr, zr), (xr - 0.012, -0.972, zr), (xr, -0.94, zr), (xr, y0 - 0.018, zr)]
        kit.tube('footrail', pts, 0.024, M['brass'], segs=16, caps=False)
        for sx in (-1, 1):
            kit.cyl('rail_flange%d' % sx, 0, 0, 0, 0.012, 0.038, M['brass'], segs=16, cap='t')
            kit.OBJS[-1].data.transform(T(sx * xr, y0 - 0.018, zr) @ Rx(90))
        for bx in (-1.45, -0.5, 0.5, 1.45):
            kit.tube('rail_arm%.2f' % bx, [(bx, y0 - 0.02, zr - 0.035), (bx, -0.90, zr - 0.035), (bx, -0.975, zr - 0.012)], 0.010, M['brass'], segs=8)
            with kit.xform(T(bx, yr, zr) @ Ry(90)):
                torus('rail_saddle%.2f' % bx, 0.0265, 0.006, 0.0, M['brass'], n=14, segs=4)
                kit.cyl('rail_saddle_b%.2f' % bx, 0, 0, -0.012, 0.012, 0.0262, M['brass'], segs=14, cap='')
            with kit.xform(T(bx, y0 - 0.02, zr - 0.035) @ Rx(90)):
                kit.cyl('rail_rose%.2f' % bx, 0, 0, 0, 0.008, 0.026, M['brass'], segs=14, cap='t')

def build_stools(M):
    with kit.props(td=0.35):
        for i, (x, y) in enumerate(layout.STOOLS):
            with kit.xform(T(x, y, 0) @ Rz(37 * i + 11)):
                lathe('stool_base%d' % i, [(0.215, 0), (0.215, 0.008), (0.20, 0.015), (0.06, 0.034), (0.034, 0.042), (0.025, 0.046)], M['steel'], segs=20)
                kit.cyl('stool_col%d' % i, 0, 0, 0.044, 0.665, 0.024, M['chrome'], segs=16, cap='')
                torus('stool_ring%d' % i, 0.165, 0.011, 0.30, M['chrome'], n=20, segs=5)
                for k in range(3):
                    a = 2 * math.pi * k / 3
                    kit.tube('stool_spoke%d_%d' % (i, k), [(0.022 * math.cos(a), 0.022 * math.sin(a), 0.30), (0.158 * math.cos(a), 0.158 * math.sin(a), 0.30)], 0.007, M['chrome'], segs=6)
                kit.cyl('stool_collar%d' % i, 0, 0, 0.28, 0.32, 0.03, M['chrome'], segs=16, cap='t')
                kit.cyl('stool_plate%d' % i, 0, 0, 0.660, 0.684, 0.10, M['steel'], r1=0.12, segs=16, cap='b')
                crease = [(0.4 + 1.7 * i) % 6.28, (2.3 + 1.1 * i) % 6.28, (4.4 + 0.7 * i) % 6.28]
                def edit(bm, rings, crease=crease):
                    for v in bm.verts:
                        r = math.hypot(v.co.x, v.co.y)
                        if v.co.z < 0.74 or r < 1e-6: continue
                        a = math.atan2(v.co.y, v.co.x)
                        dz = -0.005 * (1 - (r / 0.18) ** 2)                      # sat-in hollow
                        for c in crease:
                            da = math.atan2(math.sin(a - c), math.cos(a - c))
                            dz -= 0.0022 * math.exp(-(da * r / 0.018) ** 2) * min(1, max(0, (r - 0.06) / 0.08))
                        v.co.z += dz
                lathe('stool_seat%d' % i, [(0.11, 0.684), (0.172, 0.687), (0.183, 0.712), (0.180, 0.740), (0.160, 0.758),
                                           (0.11, 0.765), (0.05, 0.767), (0, 0.768)], M['leather'], segs=26, edit=edit)
                torus('stool_piping%d' % i, 0.1825, 0.0042, 0.737, M['leather'], n=22, segs=4)

PEND_LIFT = 0.16

def pendant_shade_prof():
    return [(0.165, 1.72), (0.158, 1.745), (0.137, 1.790), (0.100, 1.843), (0.068, 1.884), (0.049, 1.911), (0.034, 1.930), (0.020, 1.937)]

def build_pendants(M):
    with kit.props(td=0.6):
        for i, (x, y) in enumerate(layout.PENDANTS):
            with kit.xform(T(x, y, PEND_LIFT)):      # assembler: raised so the shades clear the stool's view of the back bar
                p = pendant_shade_prof()
                lathe('pend_out%d' % i, p, M['enamel'], segs=24)
                inner = [(r - 0.0018, z + 0.0006) for r, z in reversed(p)]
                lathe('pend_in%d' % i, inner, M['shade_in'], segs=24)
                torus('pend_rim%d' % i, 0.1645, 0.0028, 1.7205, M['enamel'], n=24, segs=4)
                kit.cyl('pend_socket%d' % i, 0, 0, 1.836, 1.905, 0.019, M['brass_old'], segs=14, cap='b')
                lathe('pend_bulb%d' % i, [(0, 1.766), (0.014, 1.769), (0.026, 1.779), (0.0325, 1.797), (0.030, 1.813), (0.021, 1.826), (0.0145, 1.834),
                                          (0.0135, 1.842)], M['bulb'], segs=12)
                kit.cyl('pend_cap%d' % i, 0, 0, 1.935, 1.962, 0.022, M['brass_old'], r1=0.012, segs=14, cap='t')
                kit.cyl('pend_cord%d' % i, 0, 0, 1.962, layout.ROOM['z1'] - 0.035 - PEND_LIFT, 0.0042, M['cord'], segs=6, cap='')
                kit.cyl('pend_canopy%d' % i, 0, 0, layout.ROOM['z1'] - 0.05 - PEND_LIFT, layout.ROOM['z1'] - PEND_LIFT, 0.032, M['brass_old'], r1=0.042, segs=16, cap='b')

def build_counter_lamp(M):
    lx, ly = layout.COUNTER_LAMP
    zb = 1.28   # bulb centre (binding)
    with kit.props(td=2.0), kit.xform(T(lx, ly, Z)):
        h = zb - Z
        lathe('lamp_base', [(0.066, 0.0), (0.067, 0.004), (0.064, 0.009), (0.058, 0.012), (0.056, 0.016), (0.048, 0.021), (0.032, 0.027),
                            (0.022, 0.031), (0.016, 0.036), (0.013, 0.042)], M['brass'], segs=32)
        lathe('lamp_stem', [(0.013, 0.042), (0.0115, 0.050), (0.0135, 0.058), (0.0105, 0.068), (0.0085, 0.08), (0.0080, 0.150), (0.0105, 0.156),
                            (0.0112, 0.162), (0.0095, 0.168), (0.0085, h - 0.065)], M['brass'], segs=20)
        lathe('lamp_socket', [(0.0085, h - 0.065), (0.0155, h - 0.060), (0.0160, h - 0.030), (0.0130, h - 0.024), (0.0, h - 0.024)], M['brass_old'], segs=20)
        lathe('lamp_bulb', [(0.0100, h - 0.024), (0.0105, h - 0.016), (0.0175, h - 0.008), (0.0205, h + 0.004), (0.0185, h + 0.016),
                            (0.0110, h + 0.026), (0, h + 0.029)], M['lampbulb'], segs=16)
        # harp (two arms) + finial
        for s in (-1, 1):
            kit.tube('lamp_harp%d' % s, [(0.015 * s, 0, h - 0.045), (0.05 * s, 0, h - 0.035), (0.050 * s, 0, h + 0.02), (0.012 * s, 0, h + 0.07)], 0.0016, M['brass'], segs=6)
        lathe('lamp_finial', [(0.0, h + 0.068), (0.010, h + 0.069), (0.012, h + 0.076), (0.007, h + 0.083), (0.004, h + 0.088), (0, h + 0.092)], M['brass'], segs=14)
        # pleated paper shade around the bulb
        zs0, zs1 = h - 0.068, h + 0.066
        r0, r1, np_ = 0.098, 0.060, 36
        bm = bmesh.new(); rows = []
        for (zz, rr) in ((zs0, r0), ((zs0 + zs1) / 2, (r0 + r1) / 2 + 0.003), (zs1, r1)):
            row = []
            for k in range(2 * np_):
                a = 2 * math.pi * k / (2 * np_)
                rk = rr + (0.0055 if k % 2 == 0 else -0.0015) * (rr / r0)
                row.append(bm.verts.new((rk * math.cos(a), rk * math.sin(a), zz)))
            rows.append(row)
        for i in range(2):
            for k in range(2 * np_):
                k2 = (k + 1) % (2 * np_)
                bm.faces.new((rows[i][k], rows[i][k2], rows[i + 1][k2], rows[i + 1][k]))
        kit.finish('lamp_shade', bm, M['paper'], smooth=False)
        torus('lamp_trim_b', r0 + 0.004, 0.0022, zs0, M['brass_old'], n=36, segs=4)
        torus('lamp_trim_t', r1 + 0.003, 0.0018, zs1, M['brass_old'], n=28, segs=4)
        # pull chain
        kit.tube('lamp_chain', [(0.016, 0.0, h - 0.042), (0.019, -0.002, h - 0.075), (0.020, -0.003, h - 0.095)], 0.0009, M['brass'], segs=4)
        lathe('lamp_chainbead', [(0, h - 0.108), (0.0035, h - 0.104), (0.0040, h - 0.099), (0.0025, h - 0.095), (0, h - 0.094)], M['brass'], segs=8)
        kit.OBJS[-1].data.transform(T(0.020, -0.003, 0))

# =========================================================================================== still life
def coaster(name, x, y, R, M, rot=0.0, r=0.047):
    with kit.xform(T(x, y, Z)):
        disc(name, r, 0.0, 0.0042, [M['labels'], M['cork']], R['coaster'], segs=32, rot=rot)

def build_whisky(M, R):
    x, y = SL['whisky_glass']
    with kit.props(td=2.6):
        coaster('whisky_coaster', x, y, R, M, rot=0.35)
        z0 = Z + 0.0042
        with kit.xform(T(x, y, z0)):
            prof = [(0, 0.0025), (0.028, 0.0), (0.036, 0.0006), (0.0400, 0.0035), (0.0415, 0.011), (0.0415, 0.056), (0.0408, 0.059),
                    (0.0398, 0.0615), (0.0412, 0.064), (0.0428, 0.0885), (0.0422, 0.0905), (0.0400, 0.0905), (0.0386, 0.0885),
                    (0.0366, 0.026), (0.0335, 0.0195), (0.024, 0.0178), (0, 0.0172)]
            def facet(bm, rings, n=10):
                for idx in (4, 5):
                    for v in rings[idx]:
                        a = math.atan2(v.co.y, v.co.x) % (2 * math.pi)
                        step = 2 * math.pi / n
                        ac = math.floor(a / step) * step + step / 2
                        R0 = 0.0415 * math.cos(step / 2) / math.cos(a - ac)
                        v.co.x, v.co.y = R0 * math.cos(a), R0 * math.sin(a)
            lathe('whisky_glass', prof, M['glass'], segs=40, sharp=22, edit=facet)
            lathe('whisky_liquid', [(0, 0.0178), (0.024, 0.0180), (0.0332, 0.0197), (0.0360, 0.026), (0.0368, 0.046), (0.030, 0.0462), (0, 0.0463)],
                  M['whisky'], segs=32)
            for k, (px, py, pz, rx, ry, rz, s) in enumerate([(0.008, 0.007, 0.0505, 14, -9, 31, 0.0265), (-0.011, -0.008, 0.0455, -22, 16, -14, 0.025)]):
                with kit.xform(T(px, py, pz) @ Rz(rz) @ Ry(ry) @ Rx(rx)):
                    kit.box('whisky_ice%d' % k, -s / 2, s / 2, -s / 2, s / 2, -s / 2, s / 2, M['ice'], bevel=0.0045, segs=2)

def build_second(M, R):
    x, y = SL['second_drink']
    with kit.props(td=2.0):
        coaster('second_coaster', x, y, R, M, rot=-0.9)
        z0 = Z + 0.0042
        with kit.xform(T(x, y, z0)):
            hl = 0.072   # liquid line: half finished
            prof = [(0, 0.0012), (0.027, 0.0), (0.0302, 0.002), (0.0312, 0.012), (0.0314, hl), (0.0318, 0.136), (0.0310, 0.1375), (0.0298, 0.1372),
                    (0.0294, 0.136), (0.0292, 0.014), (0.026, 0.0118), (0, 0.0112)]
            mi = [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]       # misted (condensation) below the liquid line
            lathe('second_glass', prof, [M['glass'], M['mist']], segs=32, mi=mi)
            lathe('second_liquid', [(0, 0.0118), (0.025, 0.0120), (0.0288, 0.0145), (0.0289, hl - 0.002), (0.020, hl - 0.0015), (0, hl - 0.0015)],
                  M['highball'], segs=28)
            for k, (px, py, pz, rx, ry, rz) in enumerate([(0.004, -0.005, 0.030, 8, -4, 20), (-0.006, 0.006, 0.056, -10, 12, -25),
                                                          (0.005, 0.003, 0.083, 18, -6, 48), (-0.003, -0.006, 0.108, -6, 9, 5)]):
                s = 0.0235
                with kit.xform(T(px, py, pz) @ Rz(rz) @ Ry(ry) @ Rx(rx)):
                    kit.box('second_ice%d' % k, -s / 2, s / 2, -s / 2, s / 2, -s / 2, s / 2, M['ice'], bevel=0.0028, segs=2)
            kit.tube('second_stirrer', [(-0.013, -0.011, 0.016), (0.021, 0.021, 0.137), (0.036, 0.035, 0.19)], 0.0019, M['black'], segs=6)
        # a faint wet ring where the glass stood before it was moved onto the coaster
        cx, cy = x - 0.075, y - 0.062
        with kit.xform(T(cx, cy, Z + 0.0002)):
            bm = bmesh.new(); n = 40; a0, a1 = 0.6, 0.6 + 2 * math.pi * 0.86
            outer = []; inner = []
            for k in range(n + 1):
                a = a0 + (a1 - a0) * k / n
                w = 0.0026 * (0.5 + 0.5 * math.sin(k * 0.7) ** 2) * min(1, k / 4, (n - k) / 4 + 0.2)
                outer.append(bm.verts.new((0.0322 * math.cos(a), 0.0322 * math.sin(a), 0))); inner.append(bm.verts.new(((0.0322 - w - 0.0004) * math.cos(a), (0.0322 - w - 0.0004) * math.sin(a), 0)))
            for k in range(n): bm.faces.new((inner[k], outer[k], outer[k + 1], inner[k + 1]))
            kit.finish('wet_ring', bm, M['water'])
        # coins left beside it
        with kit.props(td=1.8):
            for k, (cxo, cyo, zz, r, mat) in enumerate([(-0.095, -0.13, 0, 0.0113, 'coin'), (-0.093, -0.128, 0.0018, 0.0113, 'coin'),
                                                        (-0.062, -0.142, 0, 0.0105, 'coin'), (-0.118, -0.112, 0, 0.0110, 'coin5')]):
                kit.cyl('coin%d' % k, x + cxo, y + cyo, Z + zz, Z + zz + 0.0017, r, M[mat], segs=18, cap='t')

def build_ashtray(M):
    x, y = SL['ashtray']
    with kit.props(td=2.4), kit.xform(T(x, y, Z)):
        prof = [(0.058, 0.0), (0.0625, 0.004), (0.0635, 0.020), (0.0615, 0.0255), (0.0565, 0.0262), (0.0505, 0.0258), (0.047, 0.022),
                (0.044, 0.011), (0.036, 0.0068), (0.0, 0.0062)]
        notches = [math.radians(a) for a in (-55, 65, 185)]
        def notch(bm, rings):
            for idx in range(1, 8):
                for v in rings[idx]:
                    a = math.atan2(v.co.y, v.co.x); w = 0
                    for c in notches:
                        da = abs(math.atan2(math.sin(a - c), math.cos(a - c))) * 0.06
                        w = max(w, max(0.0, 1 - (da / 0.0105) ** 2))
                    f = min(1, max(0, (v.co.z - 0.010) / 0.014))
                    v.co.z -= 0.0095 * w * f
        lathe('ashtray', prof, M['brass'], segs=64, edit=notch, sharp=50)
        # cigar resting in the notch at -55 deg, lit end over the middle
        u = Vector((math.cos(notches[0]), math.sin(notches[0]), 0))
        def P(s, zz): return Vector((0, 0, 0)) + u * s + Vector((0, 0, zz))
        rc = 0.0088
        s_tip, s_ember, s_end, L = -0.024, -0.002, 0.118, 0.142
        zn = 0.0262 - 0.0095 + rc; zt = zn - 0.0035          # body rests in the notch (s=0.06), nearly level so the ember shows
        slope = (zn - zt) / (0.06 - s_tip)
        zz = lambda s: zt + (s - s_tip) * slope
        ash = [P(s_tip + 0.0005, zz(s_tip)), P(s_tip + 0.004, zz(s_tip + 0.004)), P(s_tip + 0.010, zz(s_tip + 0.010)), P(s_ember - 0.006, zz(s_ember - 0.006)), P(s_ember, zz(s_ember))]
        kit.tube('cigar_ash', ash, rc, M['ash'], segs=12, radii=[rc * 0.70, rc * 0.93, rc * 1.03, rc * 0.97, rc * 0.92])
        kit.tube('cigar_ember', [P(s_ember - 0.0006, zz(s_ember - 0.0006)), P(s_ember + 0.0028, zz(s_ember + 0.0028))], rc, M['ember'], segs=12, radii=[rc * 0.93, rc * 0.99])
        body = [P(s, zz(s)) for s in (s_ember + 0.0025, 0.03, 0.06, 0.09, 0.105)]
        kit.tube('cigar_body', body, rc, M['leaf'], segs=14)
        kit.tube('cigar_band', [P(0.105, zz(0.105)), P(0.117, zz(0.117))], rc * 1.04, M['band'], segs=14)
        kit.tube('cigar_head', [P(0.117, zz(0.117)), P(0.128, zz(0.128)), P(0.133, zz(0.133)), P(0.136, zz(0.136))], rc, M['leaf'], segs=14,
                 radii=[rc, rc * 0.97, rc * 0.8, rc * 0.45])
        # a little loose ash in the dish
        with kit.xform(T(-0.012, 0.014, 0.0072) @ S(1.6, 1.1, 0.35)):
            lathe('loose_ash', [(0, -0.001), (0.006, 0.0), (0.009, 0.006), (0.005, 0.011), (0, 0.012)], M['ash'], segs=8)
        with kit.xform(T(0.010, 0.020, 0.0068) @ S(1.0, 0.7, 0.3)):
            lathe('loose_ash2', [(0, -0.001), (0.004, 0.0), (0.006, 0.004), (0.003, 0.008), (0, 0.009)], M['ash'], segs=7)

def build_note(M, R):
    pid, o, sz = IA['note']
    with kit.interactive('note', origin=o, td=3.6), kit.xform(T(o[0], o[1], o[2]) @ Rz(-4)):
        hgt, foot, w = 0.068, 0.026, 0.100
        L = math.hypot(hgt, foot)
        a = math.degrees(math.atan2(hgt, foot))
        bend = lambda xx, yy: 0.0012 * math.sin(math.pi * yy / L) * (1 - (2 * xx / w) ** 2 * 0.3)
        # front panel (faces -Y): foot at y=-foot, rises to the ridge at y=0
        with kit.xform(T(0, -foot, 0) @ Rx(a)):
            slab('note_front', w, L, 0.0005, [M['labels'], M['card']], R['note'], nx=2, ny=4, bend=lambda xx, yy: -bend(xx, yy))
        with kit.xform(T(0, foot, 0) @ Rz(180) @ Rx(a)):
            slab('note_back', w, L, 0.0005, [M['card'], M['card']], None, nx=1, ny=2)

def build_matchbook(M, R):
    pid, o, sz = IA['matchbook']
    with kit.interactive('matchbook', origin=o, td=3.0), kit.xform(T(o[0], o[1], o[2]) @ Rz(28)):
        w, h, t = 0.040, 0.047, 0.0058
        with kit.xform(T(0, -h / 2, 0)):
            slab('matchbook', w, h, t, [M['labels'], M['green']], R['matchbook'], nx=1, ny=1)
        # the paper matches peek out a hair at the open top edge
        kit.box('matchbook_heads', -w / 2 + 0.002, w / 2 - 0.002, h / 2 - 0.0012, h / 2 + 0.0004, 0.0014, t - 0.0012, M['card'], only=['+y', '+z'])

def build_cigarbox(M, R):
    pid, o, sz = IA['cigarbox']
    with kit.interactive('cigarbox', origin=o, td=2.1), kit.xform(T(o[0], o[1], o[2]) @ Rz(-9)):
        w, d, h = 0.222, 0.162, 0.050
        kit.box('cbox_body', -w / 2, w / 2, -d / 2, d / 2, 0.0, h, M['cedar'], skip='-z +z', bevel=0.0015, segs=1)
        kit.box('cbox_lid', -w / 2 - 0.002, w / 2 + 0.002, -d / 2 - 0.002, d / 2 + 0.002, h, h + 0.0075, M['cedar'], skip='-z', bevel=0.0018, segs=1)
        zl = h + 0.0076
        lw, lh = 0.192, 0.128
        rect = R['cigar_lid']
        with kit.props(td=2.8):
            kit.quad('cbox_label', [(-lw / 2, -lh / 2, zl), (lw / 2, -lh / 2, zl), (lw / 2, lh / 2, zl), (-lw / 2, lh / 2, zl)], M['labels'],
                     uv=[uvmap(rect, 0, 0), uvmap(rect, 1, 0), uvmap(rect, 1, 1), uvmap(rect, 0, 1)])
        # printed band on the front
        rb = R['cigar_band']; bw, bh = 0.180, 0.030; yf = -d / 2 - 0.0004
        kit.quad('cbox_band', [(-bw / 2, yf, 0.008), (bw / 2, yf, 0.008), (bw / 2, yf, 0.008 + bh), (-bw / 2, yf, 0.008 + bh)], M['labels'],
                 uv=[uvmap(rb, 0, 0), uvmap(rb, 1, 0), uvmap(rb, 1, 1), uvmap(rb, 0, 1)])
        # gold paper edging along the lid edges
        for (xa, xb, ya, yb) in ((-w / 2 - 0.0022, w / 2 + 0.0022, -d / 2 - 0.0022, -d / 2 + 0.006), (-w / 2 - 0.0022, -w / 2 + 0.006, -d / 2, d / 2 + 0.0022),
                                 (w / 2 - 0.006, w / 2 + 0.0022, -d / 2, d / 2 + 0.0022)):
            kit.box('cbox_edge', xa, xb, ya, yb, h + 0.0062, h + 0.0078, M['gold_paper'], skip='-z')
        # brass clasp: plate on the lid, hook down over a little pin on the body
        kit.box('cbox_clasp', -0.009, 0.009, -d / 2 - 0.0035, -d / 2 - 0.0020, h - 0.016, h + 0.004, M['brass'], skip='+y', bevel=0.0007, segs=1)
        kit.box('cbox_clasp_top', -0.007, 0.007, -d / 2 - 0.0035, -d / 2 + 0.006, h + 0.0078, h + 0.0092, M['brass'], skip='-z', bevel=0.0006, segs=1)
        with kit.xform(T(0, -d / 2 - 0.0035, h - 0.019) @ Rx(90)):
            kit.cyl('cbox_pin', 0, 0, 0, 0.003, 0.0028, M['brass'], segs=10, cap='t')

def build_paperback(M, R):
    pid, o, sz = IA['paperback']
    rect = R['book']
    with kit.interactive('paperback', origin=o, td=2.6), kit.xform(T(o[0], o[1], o[2]) @ Rz(-12)):
        al = math.radians(28); rs = 0.0164; Lc = 0.099; hy = 0.0875
        cz = Lc * math.sin(al) - rs * math.cos(al)
        n_r = Vector((math.sin(al), 0, math.cos(al))); n_l = Vector((-math.sin(al), 0, math.cos(al)))
        d_r = Vector((math.cos(al), 0, -math.sin(al))); d_l = Vector((-math.cos(al), 0, -math.sin(al)))
        Cc = Vector((0, 0, cz))
        pts = []   # (point, u) from the back fore-edge (-X) over the spine to the front fore-edge (+X)
        nc = 6
        for k in range(nc + 1):              # back cover, fore-edge -> hinge
            t = 1 - k / nc
            p = Cc + n_l * rs + d_l * (Lc * t) + n_l * (0.0022 * math.sin(math.pi * t))
            pts.append((p, 0.465 * (1 - t)))
        na = 6
        a0, a1 = math.pi / 2 + (math.pi / 2 - al), math.pi / 2 - (math.pi / 2 - al)
        for k in range(1, na):
            a = a0 + (a1 - a0) * k / na
            pts.append((Cc + Vector((math.cos(a), 0, math.sin(a))) * rs, 0.465 + 0.07 * k / na))
        for k in range(nc + 1):              # front cover, hinge -> fore-edge
            t = k / nc
            p = Cc + n_r * rs + d_r * (Lc * t) + n_r * (0.0022 * math.sin(math.pi * t))
            pts.append((p, 0.535 + 0.465 * t))
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new('uv_tex')
        ny = 2
        G = [[bm.verts.new((p.x, -hy + 2 * hy * j / ny, p.z)) for j in range(ny + 1)] for p, u in pts]
        for i in range(len(pts) - 1):
            for j in range(ny):
                f = bm.faces.new((G[i][j], G[i + 1][j], G[i + 1][j + 1], G[i][j + 1]))
                for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    lp[uvl].uv = uvmap(rect, pts[ii][1], jj / ny)
        bm.normal_update()
        bm.faces.ensure_lookup_table()
        if bm.faces[0].normal.z < 0:
            for f in bm.faces: f.normal_flip()
        kit.finish('book_cover', bm, M['labels_gloss'], smooth=True, sharp=50)
        # page blocks under each cover + the rolled pages under the spine
        for side, (dd, nn) in (('r', (d_r, n_r)), ('l', (d_l, n_l))):
            yax = Vector((0, 1, 0)) if side == 'r' else Vector((0, -1, 0))
            org = Cc + nn * rs
            m = Matrix(((dd.x, yax.x, nn.x, org.x), (dd.y, yax.y, nn.y, org.y), (dd.z, yax.z, nn.z, org.z), (0, 0, 0, 1)))
            with kit.xform(m):
                kit.box('book_pages_' + side, 0.0, Lc - 0.0015, -hy + 0.0025, hy - 0.0025, -0.0098, -0.0006, M['pages'], skip='+z')
        # the pages bound under the spine: a narrow wedge that fills the gap between the two page blocks
        # (it used to be a full cylinder, whose lower half hung out below the spine as a grey disc)
        prof = [Cc + n_l * (rs - 0.0006)]
        a_l, a_r = math.atan2(n_l.z, n_l.x), math.atan2(n_r.z, n_r.x)
        for k in range(1, 6):
            a = a_l + (a_r - a_l) * k / 6
            prof.append(Cc + Vector((math.cos(a), 0, math.sin(a))) * (rs - 0.0006))
        prof += [Cc + n_r * (rs - 0.0006), Cc + n_r * (rs - 0.0098), Cc + Vector((0, 0, 0.001)), Cc + n_l * (rs - 0.0098)]
        bm = bmesh.new(); y0, y1 = -hy + 0.0025, hy - 0.0025
        A = [bm.verts.new((q.x, y0, q.z)) for q in prof]; B = [bm.verts.new((q.x, y1, q.z)) for q in prof]
        bm.faces.new(A); bm.faces.new(B[::-1])
        for k in range(len(prof)):
            k2 = (k + 1) % len(prof); bm.faces.new((A[k], A[k2], B[k2], B[k]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        kit.finish('book_roll', bm, M['pages'], smooth=False)

def build_peanuts(M):
    px, py = -0.20, -0.585
    with kit.props(td=1.6), kit.xform(T(px, py, Z)):
        prof = [(0.033, 0.0), (0.036, 0.0015), (0.036, 0.0055), (0.048, 0.0135), (0.0555, 0.0215), (0.0548, 0.0228), (0.0505, 0.0205),
                (0.037, 0.0105), (0.020, 0.0082), (0, 0.0078)]
        lathe('nut_dish', prof, [M['porcelain'], M['cobalt']], segs=32, mi=[0, 0, 0, 0, 1, 1, 0, 0, 0])
        rnd = random.Random(1978)
        kern = [(0, -0.0062), (0.0032, -0.0052), (0.0044, -0.002), (0.0046, 0.0015), (0.0035, 0.0048), (0.0015, 0.0062), (0, 0.0064)]
        placed = []
        for k in range(24):
            for _ in range(40):
                rr = 0.040 * math.sqrt(rnd.random()); a = rnd.random() * 2 * math.pi
                xx, yy = rr * math.cos(a), rr * math.sin(a)
                lay = sum(1 for (qx, qy, ql) in placed if math.hypot(qx - xx, qy - yy) < 0.0085)
                if lay <= 2: break
            zz = 0.0078 + max(0.0, (rr - 0.02)) * 0.55 + 0.0042 + lay * 0.0058
            placed.append((xx, yy, lay))
            with kit.xform(T(xx, yy, zz) @ Rz(rnd.random() * 360) @ Ry(90 + rnd.uniform(-25, 25)) @ S(1.0, 0.85, 1.0)):
                lathe('peanut%d' % k, kern, M['peanut'], segs=5)

def build_opener(M):
    with kit.props(td=1.5), kit.xform(T(0.53, -0.86, Z) @ Rz(-31)):
        L, w = 0.105, 0.019
        pts = []
        for k in range(9):
            a = -math.pi / 2 + math.pi * k / 8
            pts.append((L / 2 - w / 2 + w / 2 * math.cos(a), w / 2 * math.sin(a)))
        for k in range(9):
            a = math.pi / 2 + math.pi * k / 8
            pts.append((-L / 2 + w * 0.42 + w * 0.42 * math.cos(a), w * 0.42 * math.sin(a)))
        flat_poly('opener', pts, 0.0, 0.0022, mats.metal('counter_opener', (0.42, 0.42, 0.43), rough=0.42, patina=0.45))
        kit.box('opener_slot', L / 2 - w * 1.25, L / 2 - w * 0.28, -0.0045, 0.0045, 0.0022, 0.00225, M['black'], only=['+z'])

def build_still_life(M, R):
    build_whisky(M, R); build_second(M, R); build_ashtray(M); build_note(M, R); build_matchbook(M, R)
    build_cigarbox(M, R); build_paperback(M, R); build_peanuts(M); build_opener(M)

# =========================================================================================== counter ends
def build_register(M, R):
    with kit.props(td=0.85), kit.xform(T(1.85, -0.58, Z) @ Rz(-20)):
        body = M['regbody']
        kit.box('reg_base', -0.17, 0.17, -0.20, 0.19, 0.0, 0.088, body, skip='-z', bevel=0.004, segs=2)
        kit.box('reg_drawer', -0.152, 0.152, -0.206, -0.199, 0.012, 0.076, body, skip='+y', bevel=0.002, segs=1)
        kit.tube('reg_pull', [(-0.05, -0.207, 0.046), (-0.05, -0.222, 0.046), (0.05, -0.222, 0.046), (0.05, -0.207, 0.046)], 0.0045, M['chrome'], segs=8)
        with kit.xform(T(0.11, -0.2065, 0.06) @ Rx(90)):
            kit.cyl('reg_lock', 0, 0, 0, 0.003, 0.0075, M['chrome'], segs=12, cap='t')
        prism_x('reg_deck', [(-0.19, 0.088), (0.06, 0.088), (0.06, 0.20), (-0.19, 0.118)], -0.165, 0.165, [body])
        # raised round keys, each cap printed with its number (cell of the 'keys' region)
        rk = R['keys']; ang = math.degrees(math.atan2(0.20 - 0.118, 0.25))
        for c in range(6):
            for r_ in range(5):
                t = 0.035 + (4 - r_) * 0.046                 # distance up the slope (row 0 = '9' row = top/back)
                yy = -0.19 + t * math.cos(math.radians(ang)); zz = 0.118 + t * math.sin(math.radians(ang))
                xx = -0.125 + c * 0.05
                with kit.xform(T(xx, yy, zz) @ Rx(ang)):
                    kit.cyl('reg_stem', 0, 0, 0.0, 0.011, 0.0035, M['chrome'], segs=4, cap='')
                    cs = (c + 0.5) / 6; ct = 1 - (r_ + 0.5) / 5
                    sub = (*uvmap(rk, cs - 26 / 512, ct - 20 / 256), *uvmap(rk, cs + 26 / 512, ct + 20 / 256))
                    with kit.xform(T(0, 0, 0.011)):
                        disc('reg_key', 0.0115, 0.0, 0.0045, [M['labels'], M['cup']], sub, segs=10)
        kit.box('reg_top', -0.145, 0.145, 0.06, 0.19, 0.088, 0.30, body, skip='-z', bevel=0.007, segs=2)
        kit.box('reg_tower', -0.10, 0.10, 0.085, 0.165, 0.30, 0.365, body, skip='-z', bevel=0.005, segs=2)
        kit.box('reg_crest', -0.105, 0.105, 0.08, 0.17, 0.365, 0.372, M['chrome'], skip='-z', bevel=0.002, segs=1)
        rf = R['flags']
        for yy, flip in ((0.0845, False), (0.1655, True)):
            pts = [(-0.08, yy, 0.31), (0.08, yy, 0.31), (0.08, yy, 0.35), (-0.08, yy, 0.35)]
            uv = [uvmap(rf, 0, 0), uvmap(rf, 1, 0), uvmap(rf, 1, 1), uvmap(rf, 0, 1)]
            if flip: pts = [pts[1], pts[0], pts[3], pts[2]]
            kit.quad('reg_flags', pts, M['labels'], uv=uv)
        rp = R['plate']
        kit.quad('reg_plate', [(-0.07, 0.0595, 0.225), (0.07, 0.0595, 0.225), (0.07, 0.0595, 0.251), (-0.07, 0.0595, 0.251)], M['labels'],
                 uv=[uvmap(rp, 0, 0), uvmap(rp, 1, 0), uvmap(rp, 1, 1), uvmap(rp, 0, 1)])
        kit.box('reg_trim', -0.171, 0.171, -0.201, 0.191, 0.086, 0.092, M['chrome'], skip='-z', bevel=0.002, segs=1)
        # crank on the right side
        with kit.xform(T(0.17, 0.0, 0.06) @ Ry(90)):
            kit.cyl('reg_hub', 0, 0, 0, 0.012, 0.016, M['chrome'], segs=14, cap='t')
        kit.tube('reg_crank', [(0.182, 0.0, 0.06), (0.192, 0.0, 0.06), (0.192, 0.05, 0.035), (0.192, 0.065, 0.028)], 0.0042, M['chrome'], segs=8)
        with kit.xform(T(0.192, 0.065, 0.028) @ Ry(90)):
            kit.cyl('reg_knob', 0, 0, 0.0, 0.03, 0.007, M['black'], segs=10)

def build_right_end(M, R):
    build_register(M, R)
    with kit.props(td=1.0):
        rnd = random.Random(42)
        x, y = 1.53, -0.44
        for k in range(13):
            ox, oy = rnd.uniform(-0.002, 0.002), rnd.uniform(-0.002, 0.002)
            with kit.xform(T(x + ox, y + oy, Z + k * 0.0042)):
                if k == 12: disc('cstack%d' % k, 0.047, 0.0, 0.0042, [M['labels'], M['cork']], R['coaster'], segs=24, rot=2.1)
                else: kit.cyl('cstack%d' % k, 0, 0, 0.0, 0.0042, 0.047, M['cork'], segs=16, cap='')
    # pencilled scorecard taped to the counter, pencil beside it
    with kit.props(td=1.6), kit.xform(T(1.47, -0.835, Z) @ Rz(5)):
        sw, sh = 0.208, 0.130
        with kit.xform(T(0, -sh / 2, 0)):
            slab('scorecard', sw, sh, 0.0003, [M['labels'], M['card']], R['score'], nx=1, ny=1)
        for sx, sy, a in ((-1, 1, 35), (1, 1, -35), (-1, -1, -30)):
            with kit.xform(T(sx * (sw / 2 - 0.004), sy * (sh / 2 - 0.004), 0.0003) @ Rz(a)):
                kit.box('tape', -0.017, 0.017, -0.008, 0.008, 0.0, 0.00025, M['tape'], only=['+z'])
    with kit.props(td=1.2), kit.xform(T(1.34, -0.80, Z + 0.0037) @ Rz(78)):
        # hexagonal pencil stub
        L = 0.062
        with kit.xform(Ry(90)):
            kit.cyl('pencil', 0, 0, -L / 2, L / 2 - 0.012, 0.0037, M['pencil'], segs=6, cap='b', smooth=False)
            kit.cyl('pencil_cone', 0, 0, L / 2 - 0.012, L / 2 - 0.001, 0.0037, M['pwood'], r1=0.0011, segs=6, cap='', smooth=False)
            kit.cyl('pencil_tip', 0, 0, L / 2 - 0.0012, L / 2, 0.0011, M['graphite'], r1=0.0002, segs=6, cap='t')

def build_siphon(M):
    with kit.props(td=1.0), kit.xform(T(-1.50, -0.56, Z)):
        g = M['glass']
        kit.cyl('siph_base', 0, 0.02, 0.0, 0.012, 0.072, M['chrome'], r1=0.068, segs=28, cap='t')
        kit.cyl('siph_rod', 0, 0.075, 0.012, 0.40, 0.0055, M['chrome'], segs=10, cap='t')
        # spirit burner
        lathe('siph_burner', [(0.030, 0.012), (0.033, 0.016), (0.034, 0.045), (0.028, 0.052), (0.014, 0.056), (0.012, 0.059)], g, segs=20)
        lathe('siph_fuel', [(0.0, 0.0125), (0.029, 0.0127), (0.031, 0.016), (0.0315, 0.032), (0.0, 0.032)], mats.glass('counter_spirit', (0.9, 0.9, 0.95)), segs=16)
        kit.cyl('siph_collar', 0, 0, 0.055, 0.064, 0.0125, M['brass'], segs=14, cap='t')
        kit.cyl('siph_wick', 0, 0, 0.064, 0.072, 0.0045, M['card'], segs=8, cap='t')
        # lower flask (round), a little coffee left in the bottom
        Rf, cz = 0.054, 0.150
        out = []
        for k in range(12):
            a = -math.pi / 2 + (math.pi * 0.5 + 1.2) * k / 11
            out.append((Rf * math.cos(a) if k else 0.0, cz + Rf * math.sin(a)))
        neck_r = 0.019
        prof = out + [(neck_r, 0.222), (neck_r + 0.0025, 0.226), (neck_r - 0.0012, 0.2265), (neck_r - 0.0015, 0.223),
                      (neck_r - 0.0015, cz + Rf * 0.92)] + [(r * (Rf - 0.0016) / Rf, cz + (z - cz) * (Rf - 0.0016) / Rf) for (r, z) in reversed(out)]
        prof[0] = (0.0, prof[0][1]); prof[-1] = (0.0, prof[-1][1])
        lathe('siph_flask', prof, g, segs=20)
        cof = [(0, cz - Rf + 0.002)]
        for k in range(1, 5):
            a = -math.pi / 2 + 0.55 * k / 4
            cof.append(((Rf - 0.002) * math.cos(a), cz + (Rf - 0.002) * math.sin(a)))
        cof.append((0, cof[-1][1]))
        lathe('siph_coffee', cof, M['coffee'], segs=20)
        # flask clamp from the rod
        torus('siph_clamp', neck_r + 0.004, 0.0028, 0.205, M['chrome'], n=16, segs=5)
        kit.tube('siph_arm', [(0, 0.023, 0.205), (0, 0.075, 0.205)], 0.0032, M['chrome'], segs=6)
        # upper bowl (hopper) sitting in the neck, rubber gasket, stem down into the flask
        kit.cyl('siph_gasket', 0, 0, 0.214, 0.236, neck_r - 0.002, M['rubber'], r1=neck_r + 0.001, segs=16)
        kit.cyl('siph_stem', 0, 0, 0.11, 0.236, 0.0052, g, segs=10)
        hop = [(0.010, 0.236), (0.026, 0.250), (0.038, 0.268), (0.0405, 0.290), (0.0405, 0.378), (0.0435, 0.384), (0.042, 0.386),
               (0.0388, 0.380), (0.0388, 0.291), (0.0365, 0.270), (0.025, 0.254), (0.009, 0.241), (0, 0.240)]
        lathe('siph_hopper', hop, g, segs=20)
        torus('siph_hclamp', 0.044, 0.0026, 0.33, M['chrome'], n=20, segs=5)
        kit.tube('siph_harm', [(0, 0.046, 0.33), (0, 0.075, 0.33)], 0.003, M['chrome'], segs=6)
        kit.cyl('siph_lid', 0.07, -0.03, 0.0, 0.006, 0.040, M['chrome'], segs=20, cap='t')   # hopper lid set aside
        kit.cyl('siph_lidknob', 0.07, -0.03, 0.006, 0.014, 0.006, M['black'], segs=8, cap='t')

def cup(name, M, handle_a=0.0):
    p = [(0.0185, 0.0), (0.0205, 0.0015), (0.0205, 0.0055), (0.0255, 0.0085), (0.0335, 0.019), (0.0385, 0.037), (0.0405, 0.056),
         (0.0402, 0.0605), (0.0384, 0.0598), (0.0366, 0.045), (0.031, 0.022), (0.021, 0.0115), (0, 0.0105)]
    lathe(name, p, [M['cup'], M['cupline']], segs=20, mi=[0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0])
    ca, sa = math.cos(handle_a), math.sin(handle_a)
    hp = [(0.0385, 0.050), (0.052, 0.050), (0.058, 0.040), (0.054, 0.026), (0.036, 0.020)]
    kit.tube(name + '_h', [(r * ca, r * sa, z) for r, z in hp], 0.0042, M['cup'], segs=6)

def saucer(name, M, simple=False):
    if simple:
        return lathe(name, [(0.047, 0.0015), (0.064, 0.0115), (0.0685, 0.0155), (0.0672, 0.0168), (0.060, 0.0128)], [M['cup'], M['cupline']],
                     segs=22, mi=[0, 1, 1, 0])
    lathe(name, [(0.044, 0.0), (0.047, 0.0015), (0.047, 0.004), (0.064, 0.0115), (0.0685, 0.0155), (0.0672, 0.0168), (0.060, 0.0128),
                 (0.033, 0.0068), (0.022, 0.0068), (0.0, 0.0062)], [M['cup'], M['cupline']], segs=24, mi=[0, 0, 0, 0, 1, 1, 0, 0, 0])

def build_left_end(M, R):
    build_siphon(M)
    with kit.props(td=0.9):
        with kit.xform(T(-1.20, -0.66, Z)):
            for k in range(4):
                with kit.xform(T(0, 0, k * 0.0068)): saucer('saucer%d' % k, M, simple=k < 3)
            with kit.xform(T(0.002, -0.001, 0.0062 + 3 * 0.0068 + 0.0605) @ Rx(180)): cup('cup_inv', M, 1.2)
        with kit.xform(T(-1.30, -0.84, Z) @ Rz(140)):
            saucer('saucer_b', M)
            with kit.xform(T(0, 0, 0.0062)): cup('cup_b', M, 0.0)
        # sugar pot with its spoon
        with kit.xform(T(-1.72, -0.79, Z)):
            lathe('sugar_pot', [(0.022, 0.0), (0.024, 0.002), (0.024, 0.005), (0.034, 0.016), (0.039, 0.032), (0.037, 0.048), (0.031, 0.056),
                                (0.0295, 0.058), (0.027, 0.057)], [M['porcelain'], M['cobalt']], segs=24, mi=[0, 0, 0, 0, 0, 1, 1, 0])
            lathe('sugar_lid', [(0.0315, 0.0565), (0.032, 0.0585), (0.026, 0.064), (0.012, 0.068), (0.008, 0.070), (0.010, 0.078), (0.006, 0.082),
                                (0, 0.083)], M['porcelain'], segs=24)
            kit.tube('sugar_spoon', [(0.010, 0.012, 0.03), (0.026, 0.030, 0.062), (0.036, 0.042, 0.082)], 0.0019, M['chrome'], segs=6)
        # menu card in a little wooden stand
        with kit.xform(T(-1.94, -0.66, Z) @ Rz(24)):
            kit.box('menu_foot', -0.035, 0.035, -0.016, 0.016, 0.0, 0.016, M['menuwood'], skip='-z', bevel=0.0025, segs=2)
            with kit.props(td=1.4), kit.xform(T(0, 0.0, 0.011) @ Rx(82)):
                slab('menu_card', 0.085, 0.124, 0.0006, [M['labels'], M['card']], R['menu'], nx=1, ny=1)

# =========================================================================================== entry
def build():
    with open(os.path.join(HERE, 'tex', 'regions.json')) as f: R = json.load(f)
    M = MATS()
    build_counter(M)
    build_stools(M)
    build_pendants(M)
    build_counter_lamp(M)
    build_still_life(M, R)
    build_right_end(M, R)
    build_left_end(M, R)

LIGHTS = []
