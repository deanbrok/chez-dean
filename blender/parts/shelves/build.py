"""SHELVES — the back bar of DEAN'S: walnut credenza, bottle-green tiles, a wall-hung walnut record shelf packed with
LPs (one connected mesh per run of spines, painted spine sheet), six pull-out sleeves, the bottle keep, the books
(four handmade ledgers), a ceramic sheep, a few things on top, a brass strip-light channel and two ceiling spot cans.
Textures: tex.py -> tex/spines.png (atlas `shelves`), tex/covers.png (atlas `shelves_b`, the interactive pieces).
"""
import os, math, json, random, importlib.util
import bmesh
from mathutils import Vector, Matrix
from barkit import kit, mats, layout
from barkit.kit import T, Rx, Ry, Rz

HERE = os.path.dirname(os.path.abspath(__file__))

def _tex():
    spec = importlib.util.spec_from_file_location('shelves_tex', os.path.join(HERE, 'tex.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

# ------------------------------------------------------------------ geometry constants (from layout)
SH = layout.SHELVING; CR = layout.CREDENZA
ROWS = SH['rows']                                   # shelf-board tops 1.40, 1.76
BOARD = 0.04
TOPZ = SH['top_z']
Y0, Y1 = SH['y0'], SH['y1']
BACK_Y = Y1 - 0.012                                 # front face of the back panel
UP_T = 0.025                                        # outer upright thickness
XL, XR = SH['x0'], SH['x1']
RX0, RX1 = layout.RECORDS_X
BX0, BX1 = layout.RIGHT_BLOCK_X
MID = (RX1 + 0.005, BX0 - 0.005)                    # middle upright 0.455..0.495
DIVS = [(-0.735, -0.715), (-0.155, -0.135)]         # record-bay dividers
BAYS = [(XL + UP_T, DIVS[0][0]), (DIVS[0][1], DIVS[1][0]), (DIVS[1][1], MID[0])]
REC_H = 0.315
REC_Y = Y0 + 0.005                                  # spine line of the record rows
REC_D = 0.312
INTER = layout.INTERACTIVE

class MB:
    """bmesh builder with shared (welded) vertices and per-loop uv_tex: runs of spines become ONE uv island"""
    def __init__(s):
        s.bm = bmesh.new(); s.uv = s.bm.loops.layers.uv.new('uv_tex'); s.vm = {}
    def V(s, p, share):
        if not share: return s.bm.verts.new(p)
        k = (round(p[0] * 2e4), round(p[1] * 2e4), round(p[2] * 2e4))
        v = s.vm.get(k)
        if v is None: v = s.vm[k] = s.bm.verts.new(p)
        return v
    def face(s, pts, uvs, mi=0, share=True):
        vs = [s.V(tuple(p), share) for p in pts]
        if len(set(vs)) < len(vs): return None
        try: f = s.bm.faces.new(vs)
        except ValueError: return None
        f.material_index = mi
        for l, u in zip(f.loops, uvs): l[s.uv].uv = u
        return f
    def quad(s, pts, r, mi=0, share=True, rot=0):
        u0, v0, u1, v1 = r
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        uvs = uvs[rot:] + uvs[:rot]
        return s.face(pts, uvs, mi, share)
    def done(s, name, mats_, smooth=False):
        if not s.bm.faces: s.bm.free(); return None
        return kit.finish(name, s.bm, mats_, smooth=smooth)

def box_faces(x0, x1, y0, y1, z0, z1):
    return {
        '-y': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        '+y': [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
        '-x': [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
        '+x': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        '+z': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        '-z': [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
    }

def tbox(mb, x0, x1, y0, y1, z0, z1, faces, M=None, share=False):
    """textured box: faces = {'-y': (uvrect, rot, mi), ...}; M = optional Matrix applied to the points"""
    F = box_faces(x0, x1, y0, y1, z0, z1)
    for k, spec in faces.items():
        r, rot, mi = (spec + (0, 0))[:3] if len(spec) < 3 else spec
        pts = F[k]
        if M is not None: pts = [tuple(M @ Vector(p)) for p in pts]
        mb.quad(pts, r, mi, share=share, rot=rot)

def sub(r, a0, b0, a1, b1):
    """sub-rect of a uv rect in fractions"""
    u0, v0, u1, v1 = r
    return (u0 + (u1 - u0) * a0, v0 + (v1 - v0) * b0, u0 + (u1 - u0) * a1, v0 + (v1 - v0) * b1)

# ------------------------------------------------------------------ materials
class Mt: pass
def materials(tx):
    m = Mt()
    m.walnut = mats.wood('shelves_walnut', axis='X', cols=((0.035, 0.016, 0.008), (0.10, 0.048, 0.022), (0.19, 0.095, 0.045)), rough=0.32, coat=0.25)
    m.walnut_v = mats.wood('shelves_walnut_v', axis='Z', cols=((0.035, 0.016, 0.008), (0.10, 0.048, 0.022), (0.19, 0.095, 0.045)), rough=0.38, coat=0.15)
    m.walnut_y = mats.wood('shelves_walnut_y', axis='Y', cols=((0.035, 0.016, 0.008), (0.10, 0.048, 0.022), (0.19, 0.095, 0.045)), rough=0.35, coat=0.2)
    m.back = mats.wood('shelves_backpanel', axis='Z', cols=((0.018, 0.009, 0.005), (0.05, 0.025, 0.012), (0.09, 0.045, 0.022)), rough=0.5)
    m.plinth = mats.plain('shelves_plinth', (0.012, 0.008, 0.006), rough=0.6)
    m.brass = mats.metal('shelves_brass', (0.78, 0.55, 0.24), rough=0.28, patina=0.4)
    m.steel = mats.metal('shelves_steel', (0.72, 0.72, 0.70), rough=0.18, patina=0.2)
    m.blackmetal = mats.plain('shelves_blackmetal', (0.015, 0.014, 0.013), rough=0.45, metal_=0.3)
    m.dark = mats.plain('shelves_dark', (0.01, 0.008, 0.007), rough=0.8)
    m.sheetA = mats.image('shelves_sheetA', tx.SHEET_A, rough=0.55)
    m.sheetA_gloss = mats.image('shelves_sheetA_label', tx.SHEET_A, rough=0.42)
    m.sheetB = mats.image('shelves_sheetB', tx.SHEET_B, rough=0.48, coat=0.08)
    m.sheetB_fill = fill_mat('shelves_sheetB_cover', tx.SHEET_B)
    m.tiles = tile_mat()
    m.glass = mats.glass('shelves_glass', (0.93, 0.95, 0.92), rough=0.02, shadow=(0.92, 0.92, 0.88))
    m.glass_brown = mats.glass('shelves_glass_brown', (0.42, 0.22, 0.07), rough=0.03, shadow=(0.55, 0.3, 0.1))
    m.glass_green = mats.glass('shelves_glass_green', (0.30, 0.55, 0.32), rough=0.03, shadow=(0.4, 0.65, 0.4))
    m.whisky = mats.glass('shelves_whisky', (0.85, 0.42, 0.10), rough=0.0, shadow=(0.9, 0.5, 0.15), ior=1.36)
    m.rum = mats.glass('shelves_rum', (0.40, 0.12, 0.03), rough=0.0, shadow=(0.5, 0.2, 0.06), ior=1.36)
    m.redwine = mats.glass('shelves_vermouth', (0.45, 0.06, 0.04), rough=0.0, shadow=(0.5, 0.1, 0.06), ior=1.36)
    for lq in (m.whisky, m.rum, m.redwine):      # a little diffuse body so the liquid reads as amber, not as a black hole
        bsdf = next(n for n in lq.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        mats.setp(bsdf, trans=0.82)
    m.caps = [mats.plain('shelves_cap_black', (0.02, 0.02, 0.02), rough=0.35), mats.metal('shelves_cap_gold', (0.75, 0.52, 0.2), rough=0.3),
              mats.plain('shelves_cap_red', (0.35, 0.03, 0.02), rough=0.4), mats.noisy('shelves_cork', (0.35, 0.22, 0.12), (0.5, 0.34, 0.2), rough=0.8, scale=200)]
    m.globe = mats.globe('shelves_globe')
    m.sheep = sheep_mat()
    m.sheep_face = mats.plain('shelves_sheep_face', (0.05, 0.045, 0.045), rough=0.25, coat=0.6)
    m.kraft = mats.noisy('shelves_kraft', (0.30, 0.19, 0.10), (0.38, 0.25, 0.13), rough=0.85, scale=40)
    m.towel = towel_mat()
    m.lens = shadowless('EMN_shelves_spot_lens', (1.0, 0.78, 0.5), 12.0, black=False)
    m.can = shadowless('shelves_spot_can', None, 0.0, black=True)
    m.tube = mats.emissive('shelves_strip_tube', (1.0, 0.72, 0.42), 8.0, night_only=True)
    m.string = mats.plain('shelves_string', (0.5, 0.42, 0.32), rough=0.9)
    return m

def fill_mat(name, path, strength=0.45):
    """covers that spend their life sandwiched between other sleeves/books bake almost black, yet the web page pulls them
    out into the light: a little self-illumination where they are occluded (1 - AO) keeps them readable, unoccluded parts are
    untouched"""
    m = mats.image(name, path, rough=0.5, coat=0.08)
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); src = nt.nodes['SRC']
    ao = mats.N(nt, 'ShaderNodeAmbientOcclusion'); ao.samples = 8; ao.inputs['Distance'].default_value = 0.08
    k = mats.math_(nt, 'MULTIPLY', mats.math_(nt, 'SUBTRACT', 1.0, ao.outputs['AO'], clamp=True), strength)
    mats.L(nt, src.outputs[0], b.inputs['Emission Color'])
    mats.L(nt, k, b.inputs['Emission Strength'])
    return m

def tile_mat():
    m, nt, b, _ = mats.base('shelves_tiles')
    N, L = mats.N, mats.L
    tc = N(nt, 'ShaderNodeTexCoord'); mp = N(nt, 'ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (math.radians(90), 0, 0)
    L(nt, tc.outputs['Object'], mp.inputs[0])
    br = N(nt, 'ShaderNodeTexBrick'); br.offset = 0.0; br.squash = 1.0
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.0025; br.inputs['Mortar Smooth'].default_value = 0.3
    br.inputs['Brick Width'].default_value = 0.0505; br.inputs['Row Height'].default_value = 0.0505; br.inputs['Bias'].default_value = 0.0
    br.inputs['Color1'].default_value = (0.020, 0.075, 0.048, 1); br.inputs['Color2'].default_value = (0.010, 0.042, 0.030, 1)
    br.inputs['Mortar'].default_value = (0.10, 0.09, 0.075, 1)
    L(nt, mp.outputs[0], br.inputs['Vector'])
    glaze = mats.noise(nt, mp.outputs[0], 60, 4, 0.6)
    col = mats.mixc(nt, br.outputs['Color'], mats.ramp(nt, glaze, [(0.3, (0.8, 0.85, 0.8)), (0.7, (1.15, 1.1, 1.0))]), 1.0)
    L(nt, col, b.inputs['Base Color'])
    L(nt, mats.math_(nt, 'ADD', 0.06, mats.math_(nt, 'MULTIPLY', br.outputs['Fac'], 0.7)), b.inputs['Roughness'])
    h = mats.math_(nt, 'ADD', mats.math_(nt, 'MULTIPLY', br.outputs['Fac'], -1.0), mats.math_(nt, 'MULTIPLY', glaze, 0.15))
    mats.bump(nt, b, h, 0.35, 0.002)
    mats.setp(b, coat=0.7, coat_rough=0.04)
    return m

def sheep_mat():
    m, nt, b, _ = mats.base('shelves_sheep_glaze')
    v = mats.coords(nt)
    vor = mats.N(nt, 'ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 420; mats.L(nt, v, vor.inputs['Vector'])
    n1 = mats.noise(nt, v, 60, 3, 0.5)
    mats.L(nt, mats.ramp(nt, n1, [(0.3, (0.70, 0.67, 0.60)), (0.7, (0.80, 0.78, 0.72))]), b.inputs['Base Color'])
    mats.setp(b, rough=0.22, coat=0.8, coat_rough=0.05)
    mats.bump(nt, b, vor.outputs[0], 0.5, 0.0015)
    return m

def towel_mat():
    m, nt, b, _ = mats.base('shelves_towel')
    tc = mats.N(nt, 'ShaderNodeTexCoord'); sep = mats.N(nt, 'ShaderNodeSeparateXYZ'); mats.L(nt, tc.outputs['Object'], sep.inputs[0])
    sx = mats.math_(nt, 'GREATER_THAN', mats.math_(nt, 'FRACT', mats.math_(nt, 'MULTIPLY', sep.outputs['X'], 28)), 0.82)
    sy = mats.math_(nt, 'GREATER_THAN', mats.math_(nt, 'FRACT', mats.math_(nt, 'MULTIPLY', sep.outputs['Y'], 28)), 0.82)
    stripe = mats.math_(nt, 'MAXIMUM', sx, sy)
    col = mats.mixc(nt, (0.62, 0.55, 0.42), (0.30, 0.05, 0.03), stripe, 'MIX')
    mats.L(nt, col, b.inputs['Base Color'])
    mats.setp(b, rough=0.9, sheen=0.6)
    mats.bump(nt, b, mats.noise(nt, mats.coords(nt), 600, 2, 0.5), 0.15, 0.001)
    return m

def shadowless(name, col, strength, black):
    """spot-can parts are invisible to shadow rays, so the assembler's spot light (which sits inside the can) shines through"""
    m, nt, b, out = mats.base(name)
    if black: mats.setp(b, col=(0.012, 0.011, 0.010), rough=0.4, metal=0.4)
    else: mats.setp(b, col=(0.0, 0.0, 0.0), emit=col, emit_s=strength, rough=0.3)
    tr = mats.N(nt, 'ShaderNodeBsdfTransparent'); lp = mats.N(nt, 'ShaderNodeLightPath'); mx = mats.N(nt, 'ShaderNodeMixShader')
    mats.L(nt, lp.outputs['Is Shadow Ray'], mx.inputs[0])
    mats.L(nt, b.outputs[0], mx.inputs[1]); mats.L(nt, tr.outputs[0], mx.inputs[2]); mats.L(nt, mx.outputs[0], out.inputs[0])
    return m

# ------------------------------------------------------------------ credenza + tiles
def credenza(M):
    x0, x1, y0, y1, top = CR['x0'], CR['x1'], CR['y0'], CR['y1'], CR['top_z']
    with kit.props(td=1.0):
        kit.box('cred_top', x0, x1, y0 - 0.005, y1, top - 0.035, top, M.walnut, skip='+y', bevel=0.004, segs=2)
    with kit.props(td=0.3):
        kit.box('cred_ends', x0 + 0.005, x1 - 0.005, y0 + 0.02, y1, 0.07, top - 0.035, M.walnut_v, only=['-x', '+x'])
        kit.box('cred_plinth', x0 + 0.04, x1 - 0.04, y0 + 0.06, y1, 0.0, 0.07, M.plinth, only=['-y', '-x', '+x'])
        kit.box('cred_rail', x0 + 0.005, x1 - 0.005, y0 + 0.012, y0 + 0.045, top - 0.05, top - 0.035, M.dark, only=['-y', '-z'])
        n = 4; w = (x1 - x0 - 0.02) / n
        for i in range(n):
            dx0 = x0 + 0.01 + i * w - (0.012 if i % 2 else 0); dx1 = x0 + 0.01 + (i + 1) * w + (0.012 if i % 2 else 0)
            fy = y0 + (0.012 if i % 2 == 0 else 0.030)
            kit.box('cred_door%d' % i, dx0, dx1, fy, fy + 0.018, 0.075, top - 0.045, M.walnut_v, skip='+y', bevel=0.0025, segs=1)
    # finger pulls: brass cups set high enough to be seen above the counter
    with kit.props(td=0.8):
        for i in range(n):
            dx0 = x0 + 0.01 + i * w; dx1 = dx0 + w
            fy = y0 + (0.012 if i % 2 == 0 else 0.030)
            px = (dx1 - 0.07) if i % 2 == 0 else (dx0 + 0.07)
            with kit.xform(T(px, fy, 0.80) @ Rx(90)):
                kit.lathe('cred_pull%d' % i, [(0.0, -0.004), (0.016, -0.004), (0.016, 0.0015), (0.019, 0.0015), (0.019, 0.0005)], M.brass, segs=20)
                kit.lathe('cred_pull_in%d' % i, [(0.0, -0.0035), (0.0145, -0.0035), (0.0, -0.0036)], M.dark, segs=20)
    # backsplash: small glazed bottle-green tiles, wall from the credenza top up to the lowest shelf
    with kit.props(td=0.6):
        kit.box('tiles', XL, XR, Y1 - 0.008, Y1, top, ROWS[0] - BOARD, M.tiles, only=['-y'])
        kit.box('tiles_edge_l', XL - 0.008, XL, Y1 - 0.03, Y1, top, ROWS[0] - BOARD, M.tiles, only=['-x', '-y'])
        kit.box('tiles_edge_r', XR, XR + 0.008, Y1 - 0.03, Y1, top, ROWS[0] - BOARD, M.tiles, only=['+x', '-y'])

# ------------------------------------------------------------------ carcass + strip light
def carcass(M):
    zb = ROWS[0] - BOARD
    with kit.props(td=0.6):
        # bottom board with a routed channel for the strip light (layout light N_cred_strip sits in it at Z 1.37)
        ch0, ch1, chz = 1.283, 1.317, 1.386
        kit.box('board0_lip', XL + UP_T, XR - UP_T, Y0, ch0, zb, ROWS[0], M.walnut, skip='+y', bevel=0.003, segs=2)
        kit.box('board0_mid', XL + UP_T, XR - UP_T, ch0, ch1, chz, ROWS[0], M.walnut, only=['+z'])
        kit.box('board0_back', XL + UP_T, XR - UP_T, ch1, BACK_Y, zb, ROWS[0], M.walnut, only=['+z', '-z'])
        for i, (z0, z1) in enumerate([(ROWS[1] - BOARD, ROWS[1]), (TOPZ - BOARD, TOPZ)]):
            kit.box('board%d' % (i + 1), XL + UP_T, XR - UP_T, Y0, BACK_Y, z0, z1, M.walnut, skip='+y', bevel=0.003, segs=2)
        # uprights
        kit.box('up_l', XL, XL + UP_T, Y0, Y1, zb, TOPZ, M.walnut_v, skip='+y', bevel=0.003, segs=2)
        kit.box('up_r', XR - UP_T, XR, Y0, Y1, zb, TOPZ, M.walnut_v, skip='+y', bevel=0.003, segs=2)
        for (a, b) in [MID] + DIVS:
            for r in range(2):
                z0 = ROWS[r]; z1 = (ROWS[1] - BOARD) if r == 0 else (TOPZ - BOARD)
                kit.box('div', a, b, Y0 + (0.0 if (a, b) == MID else 0.004), BACK_Y, z0, z1, M.walnut_v, only=['-y', '-x', '+x'], bevel=0.002, segs=1)
    with kit.props(td=0.35):
        kit.box('backpanel', XL + UP_T, XR - UP_T, BACK_Y, Y1, ROWS[0], TOPZ - BOARD, M.back, only=['-y'])
    with kit.props(td=0.8):
        # brass channel lining, the glowing tube up in the channel, and a 12 mm brass fascia on the room side.
        # The fascia hangs lower than the back wall of the channel on purpose: from the bar stool (eye 10 cm below the
        # board, 3 m away) the back wall's inner face, lit point-blank by the tube, used to show as a sliver a millimetre
        # tall - under half a pixel of very bright brass, which crawled and flickered as the camera breathed. Now the
        # sight line under the fascia passes below the back wall, and what the room sees is a calm band of brass.
        kit.box('strip_ceiling', XL + UP_T, XR - UP_T, ch0, ch1, chz - 0.001, chz, M.brass, only=['-z'])
        kit.box('strip_wall_f', XL + UP_T, XR - UP_T, ch0, ch0 + 0.0015, zb - 0.012, chz, M.brass, only=['+y', '-z', '-y'])
        kit.box('strip_wall_b', XL + UP_T, XR - UP_T, ch1 - 0.0015, ch1, zb, chz, M.brass, only=['-y'])
    with kit.props(td=0.2):
        kit.box('strip_tube', -1.25, 1.25, 1.2935, 1.3065, chz - 0.006, chz - 0.001, M.tube, only=['-z', '-y', '+y'])

def spot_cans(M):
    with kit.props(td=0.4):
        for nm, kind, loc, e, col, ex in layout.LIGHTS:
            if nm not in ('N_shelf_wash_l', 'N_shelf_wash_r'): continue
            p = Vector(loc); d = (Vector(ex['aim']) - p).normalized()
            q = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()     # local +Z = aim direction
            lens = p + d * 0.02
            with kit.xform(T(*lens) @ q):
                kit.lathe('can_' + nm, [(0.0, -0.075), (0.026, -0.075), (0.030, -0.07), (0.030, 0.0), (0.027, 0.0), (0.027, -0.012)], M.can, segs=20)
                kit.cyl('lens_' + nm, 0, 0, -0.0125, -0.012, 0.027, M.lens, segs=20, cap='t')
            # canopy + stem to the ceiling
            back = lens - d * 0.075
            kit.cyl('canopy_' + nm, p.x, p.y, 2.435, 2.45, 0.032, M.can, segs=20, cap='b')
            kit.tube('stem_' + nm, [(back.x, back.y, back.z), (p.x, p.y, 2.44)], 0.006, M.can, segs=8)

# ------------------------------------------------------------------ records
def lp_rect(tx, i): return tx.uv(tx.LP(i))

def records(M, tx):
    rng = random.Random(4417)
    lum = json.load(open(os.path.join(HERE, 'tex', 'meta.json')))['lp_lum']
    dark_ids = [i for i, l in enumerate(lum) if l < 50]
    side_rects = [tx.uv(tx.SIDE(i)) for i in range(tx.N_SIDE)]
    fronts = MB(); sides = MB()
    slots = {}                                          # (row) -> list of x centres of interactive sleeves
    for k in range(6):
        _, (x, y, z), _ = INTER['rec_%d' % k]
        slots.setdefault(z, []).append(x)
    # per bay arrangement (row index, bay index) -> options
    cfg = {(1, 0): dict(gap='r', gw=0.075), (1, 1): dict(mid=0.012), (1, 2): dict(boxes=2),
           (0, 0): dict(boxes=2, gap='l', gw=0.05), (0, 1): dict(white=-0.585), (0, 2): dict(gap='r', gw=0.055, mid=0.016)}
    count = 0
    for ri, z0 in enumerate(ROWS):
        for bi, (bx0, bx1) in enumerate(BAYS):
            c = cfg.get((ri, bi), {})
            rs = [x for x in slots.get(z0, []) if bx0 < x < bx1]
            items = []          # (x0, x1, yf, rect, h, kind)
            gw = c.get('gw', 0.0)
            lim0 = bx0 + 0.0008 + (gw if c.get('gap') == 'l' else 0)
            lim1 = bx1 - 0.0008 - (gw if c.get('gap') == 'r' else 0)
            x = lim0; yf = REC_Y + rng.choice([0, 0.002, 0.004]); gid = 0
            boxes_left = c.get('boxes', 0); box_at = sorted(rng.uniform(lim0 + 0.05, lim1 - 0.08) for _ in range(boxes_left))
            mid_at = (lim0 + lim1) / 2 + rng.uniform(-0.1, 0.1) if c.get('mid') else None
            white = c.get('white'); white_done = False
            prev_dark = False
            while True:
                # interactive slot ahead?
                hit = [s for s in rs if s - 0.0040 - 1e-6 <= x < s + 0.0039]
                if hit:
                    items.append(('slot', hit[0] - 0.0040, hit[0] + 0.0040))
                    x = hit[0] + 0.0040; gid += 1; yf = REC_Y + rng.choice([0, 0.0015, 0.003]); continue
                if mid_at is not None and x > mid_at:
                    items.append(('gap', x, x + c['mid'])); x += c['mid']; mid_at = None; gid += 1; continue
                if white is not None and not white_done and x > white - 0.012:
                    # the white spine: dark neighbours on both sides so it reads, nothing written on it
                    for j in range(3):
                        t = rng.uniform(0.0034, 0.0042)
                        items.append(('lp', x, x + t, yf, lp_rect(tx, rng.choice(dark_ids)), REC_H, gid)); x += t
                    t = 0.0052
                    items.append(('lp', x, x + t, yf, tx.uv(tx.WHITE), REC_H, gid)); x += t
                    for j in range(3):
                        t = rng.uniform(0.0034, 0.0042)
                        items.append(('lp', x, x + t, yf, lp_rect(tx, rng.choice(dark_ids)), REC_H, gid)); x += t
                    white_done = True; continue
                if box_at and x > box_at[0]:
                    box_at.pop(0); t = rng.uniform(0.022, 0.034)
                    if x + t > lim1: break
                    if any(x - 0.0045 < s_ < x + t + 0.0045 for s_ in rs): continue
                    gid += 1
                    items.append(('box', x, x + t, REC_Y - 0.003, tx.uv(tx.BOX(rng.randrange(tx.N_BOX))), REC_H + 0.002, gid))
                    x += t; gid += 1; continue
                u = rng.random()
                t = rng.uniform(0.0030, 0.0042) if u < 0.68 else (rng.uniform(0.0050, 0.0065) if u < 0.92 else rng.uniform(0.0075, 0.0095))
                if x + t > lim1: break
                # next spine must not run into an upcoming slot
                if any(x + t > s - 0.0040 and x < s - 0.0040 for s in rs):
                    s = min(s for s in rs if s - 0.0040 >= x); t = s - 0.0040 - x
                    if t < 0.0022:
                        if items and items[-1][0] == 'lp' and abs(items[-1][2] - x) < 1e-9:
                            it = items[-1]; items[-1] = (it[0], it[1], s - 0.0040) + it[3:]
                        x = s - 0.0040; continue
                r = rng.random()
                if r < 0.07: gid += 1; yf = REC_Y + rng.choice([0, 0.0015, 0.003, 0.0045, 0.007])
                if r > 0.985:      # one pulled a centimetre forward
                    gid += 1
                    items.append(('lp', x, x + t, REC_Y - rng.uniform(0.008, 0.012), lp_rect(tx, rng.randrange(tx.N_LP)), REC_H, gid))
                    gid += 1; x += t; continue
                items.append(('lp', x, x + t, yf, lp_rect(tx, rng.randrange(tx.N_LP)), REC_H, gid))
                x += t
            # fill the leftover sliver (no gap config) by stretching the last spine
            # --- leaning fan into an end gap
            lean = []
            if c.get('gap'):
                side = c['gap']
                k = rng.randint(5, 8)
                # take k sleeves at the gap end and fan them toward the gap
                if side == 'r':
                    base = [it for it in items if it[0] == 'lp'][-k:]
                else:
                    base = [it for it in items if it[0] == 'lp'][:k]
                for it in base: items.remove(it)
                ts = [it[2] - it[1] for it in base]
                rects = [it[4] for it in base]
                if side == 'r':
                    px = base[0][1]; free = bx1 - 0.0008
                    n = len(ts)
                    tot = sum(ts)
                    th_max = math.asin(min(0.4, max(0.02, (free - (px + tot)) / REC_H)))
                    angs = [th_max * (i + 1) / n for i in range(n)]
                    xx = px
                    for i in range(n):
                        xx += ts[i] / math.cos(angs[i]) + (ts[i] * math.sin(angs[i]) * math.tan(angs[i - 1]) if i else 0)
                        lean.append((xx, angs[i], ts[i], rects[i], +1))
                        xx += 0.0004
                else:
                    px = base[-1][2]; free = bx0 + 0.0008
                    n = len(ts); tot = sum(ts)
                    th_max = math.asin(min(0.4, max(0.02, ((px - tot) - free) / REC_H)))
                    angs = [th_max * (i + 1) / n for i in range(n)]
                    xx = px
                    for i in range(n):
                        j = n - 1 - i
                        xx -= ts[j] / math.cos(angs[i]) + (ts[j] * math.sin(angs[i]) * math.tan(angs[i - 1]) if i else 0)
                        lean.append((xx, angs[i], ts[j], rects[j], -1))
                        xx -= 0.0004
            for it in items:
                if it[0] in ('lp', 'box'):
                    assert not any(it[1] < s_ + 0.0033 and it[2] > s_ - 0.0033 for s_ in rs), ('spine overlaps a pull-out sleeve', it[:3])
            # --- emit straight groups
            spines = [it for it in items if it[0] in ('lp', 'box')]
            spines.sort(key=lambda it: it[1])
            groups = []
            for it in spines:
                if groups and groups[-1][-1][6] == it[6] and abs(groups[-1][-1][2] - it[1]) < 1e-6 and groups[-1][-1][3] == it[3]:
                    groups[-1].append(it)
                else: groups.append([it])
            for gi, g in enumerate(groups):
                yfg = g[0][3]; h = g[0][5]
                for it in g:
                    fronts.quad([(it[1], yfg, z0), (it[2], yfg, z0), (it[2], yfg, z0 + h), (it[1], yfg, z0 + h)], it[4])
                    count += 1
                # exposed group ends
                for end in (0, 1):
                    xe = g[0][1] if end == 0 else g[-1][2]
                    nb = groups[gi - 1] if (end == 0 and gi > 0) else (groups[gi + 1] if (end == 1 and gi + 1 < len(groups)) else None)
                    touching = nb is not None and abs((nb[-1][2] if end == 0 else nb[0][1]) - xe) < 1e-6
                    if touching:
                        depth = (nb[0][3] - yfg) if nb[0][3] > yfg else 0.0
                        if nb[0][5] < h - 1e-4: depth = max(depth, 0.0)
                    else:
                        near_wall = (xe - bx0 < 0.006) if end == 0 else (bx1 - xe < 0.006)
                        depth = 0.0 if near_wall else REC_D
                    if depth < 0.0008: continue
                    sr = rng.choice(side_rects)
                    frac = depth / REC_D
                    if end == 0:
                        pts = [(xe, yfg + depth, z0), (xe, yfg, z0), (xe, yfg, z0 + h), (xe, yfg + depth, z0 + h)]
                        sides.quad(pts, sub(sr, 1 - frac, 0, 1, 1), share=False)
                    else:
                        pts = [(xe, yfg, z0), (xe, yfg + depth, z0), (xe, yfg + depth, z0 + h), (xe, yfg, z0 + h)]
                        sides.quad(pts, sub(sr, 0, 0, frac, 1), share=False)
                # box sets / pulled singles: tops so their forward edge reads
                if g[0][0] == 'box' or yfg < REC_Y - 0.005:
                    for it in g:
                        sides.quad([(it[1], yfg, z0 + h), (it[2], yfg, z0 + h), (it[2], yfg + 0.04, z0 + h), (it[1], yfg + 0.04, z0 + h)], tx.uv(tx.EDGE), share=False)
            # --- emit the leaning fan
            for (pv, ang, t, rect, sgn) in lean:
                Mx = T(pv, 0, z0) @ Ry(math.degrees(ang) * sgn)
                lx0, lx1 = (-t, 0.0) if sgn > 0 else (0.0, t)
                yfl = REC_Y + 0.003
                F = box_faces(lx0, lx1, yfl, yfl + REC_D, 0.0, REC_H)
                tf = lambda pts: [tuple(Mx @ Vector(p)) for p in pts]
                fronts.quad(tf(F['-y']), rect, share=False); count += 1
                sr = rng.choice(side_rects)
                sides.quad(tf(F['-x']), sr, share=False)
                sides.quad(tf(F['+x']), sr, share=False)
                sides.quad(tf(F['+z']), tx.uv(tx.EDGE), share=False)
    with kit.props(td=2.0):
        fronts.done('lp_spines', [M.sheetA])
    with kit.props(td=0.55):
        sides.done('lp_sides', [M.sheetA])
    return count

# ------------------------------------------------------------------ interactive sleeves
def sleeves(M, tx):
    T_ = 0.0064
    for k in range(6):
        _, (x, y, z), _ = INTER['rec_%d' % k]
        with kit.interactive('rec_%d' % k, origin=(x, y, z)):
            x0, x1, y0, y1, z0, z1 = x - T_ / 2, x + T_ / 2, y, y + 0.315, z + 0.0005, z + 0.3155
            for faces, td in (({'-x': (tx.uv(tx.FRONT(k), 1.0), 0, 1)}, 3.0),
                              ({'+x': (tx.uv(tx.BACK(k), 1.0), 0, 1)}, 1.5),
                              ({'-y': (tx.uv(tx.SPINE(k)), 0, 0)}, 2.5),
                              ({'+z': (tx.uv(tx.B_EDGE), 0, 0), '-z': (tx.uv(tx.B_EDGE), 0, 0), '+y': (tx.uv(tx.B_INNER), 0, 0)}, 0.4)):
                with kit.props(td=td):
                    mb = MB(); tbox(mb, x0, x1, y0, y1, z0, z1, faces); mb.done('rec%d' % k, [M.sheetB, M.sheetB_fill])

# ------------------------------------------------------------------ books
def books(M, tx):
    rng = random.Random(902)
    z0 = ROWS[1]
    fronts = MB(); rest = MB()
    inter = [(INTER['book_%d' % j][1][0], j) for j in range(4)]
    SHEEP_X = (1.203, 1.241)
    forb = sorted([(cx - 0.0205, cx + 0.0205) for cx, j in inter] + [(SHEEP_X[0] - 0.003, SHEEP_X[1] + 0.003)])
    xend = XR - UP_T - 0.001
    x = MID[1] + 0.001; spine_ids = list(range(tx.N_BOOK)); rng.shuffle(spine_ids)
    placed = []
    while x < xend - 0.012:
        inside = [f for f in forb if f[0] - 1e-6 <= x < f[1]]
        if inside: x = inside[0][1] + 0.0005; continue
        lim = min([f[0] for f in forb if f[0] > x] + [xend])
        t = rng.uniform(0.016, 0.042)
        if x + t > lim:
            t = lim - x
            if t < 0.012: x = lim; continue
        h = rng.uniform(0.19, 0.30); d = rng.uniform(0.14, 0.21); yf = 1.332 + rng.uniform(0, 0.012)
        placed.append((x, x + t, yf, d, h)); x += t + rng.uniform(0.0003, 0.0012)
    for i, (a, b, yf, d, h) in enumerate(placed):
        r = tx.uv(tx.BOOK(spine_ids[i % tx.N_BOOK]))
        r = sub(r, 0, 1 - min(1, h / 0.30), 1, 1)          # short books use the top of the strip
        fronts.quad([(a, yf, z0), (b, yf, z0), (b, yf, z0 + h), (a, yf, z0 + h)], r, share=False)
        side = sub(r, 0.02, 0.1, 0.07, 0.9)
        tbox(rest, a, b, yf, yf + d, z0, z0 + h, {'-x': (side, 0, 0), '+x': (side, 0, 0), '+z': (tx.uv(tx.PAGES), 0, 0)})
    with kit.props(td=1.6):
        fronts.done('book_spines', [M.sheetA])
    with kit.props(td=0.5):
        rest.done('book_rest', [M.sheetA])
    # four interactive ledgers, 2 cm proud
    for j in range(4):
      with kit.props(atlas='shelves_b'):
          _, (cx, cy, cz), (sx, sy, sz) = INTER['book_%d' % j]
          with kit.interactive('book_%d' % j, origin=(cx, cy, cz)):
              a, b = cx - 0.02, cx + 0.02; yf = 1.312; d = 0.165; h = 0.222
              cov = tx.uv(tx.BCOVER(j))
              for faces, td in (({'-y': (tx.uv(tx.BSPINE(j)), 0, 0)}, 2.5), ({'+x': (cov, 0, 1), '-x': (cov, 0, 1)}, 2.0),
                                ({'+z': (tx.uv(tx.B_PAGES), 0, 0), '+y': (tx.uv(tx.B_PAGES), 0, 0), '-z': (tx.uv(tx.B_PAGES), 0, 0)}, 0.5)):
                  with kit.props(td=td):
                      mb = MB(); tbox(mb, a, b, yf, yf + d, cz + 0.0005, cz + h, faces); mb.done('ledger%d' % j, [M.sheetB, M.sheetB_fill])
    sheep(M, (SHEEP_X[0] + SHEEP_X[1]) / 2, 1.37, z0)

def ellipsoid(name, c, r, mat, us=16, vs=10, M_=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=us, v_segments=vs, radius=1.0)
    for v in bm.verts:
        v.co = Vector((c[0] + v.co.x * r[0], c[1] + v.co.y * r[1], c[2] + v.co.z * r[2]))
        if M_ is not None: v.co = M_ @ v.co
    return kit.finish(name, bm, mat, smooth=True)

def sheep(M, x, y, z):
    """small glazed ceramic sheep, tucked between two books, looking out at the room"""
    with kit.props(td=1.4), kit.xform(T(x, y, z) @ Rz(8)):
        ellipsoid('sheep_body', (0, 0.004, 0.026), (0.017, 0.026, 0.016), M.sheep, 16, 10)
        ellipsoid('sheep_head', (0, -0.026, 0.036), (0.008, 0.011, 0.008), M.sheep_face, 12, 8, M_=Matrix.Rotation(math.radians(-25), 4, 'X'))
        for sx in (-1, 1):
            ellipsoid('sheep_ear', (sx * 0.0095, -0.022, 0.042), (0.005, 0.0025, 0.0022), M.sheep_face, 8, 6)
        for lx, ly in ((-0.008, -0.013), (0.008, -0.013), (-0.008, 0.019), (0.008, 0.019)):
            kit.cyl('sheep_leg', lx, ly, 0.0, 0.016, 0.0028, M.sheep_face, segs=8, r1=0.0032, cap='b')

# ------------------------------------------------------------------ bottles
PROF = {
    'round':   [(0, 0), (0.036, 0), (0.0375, 0.004), (0.0375, 0.180), (0.034, 0.205), (0.022, 0.222), (0.0145, 0.236), (0.0135, 0.262), (0.0, 0.262)],
    'slim':    [(0, 0), (0.031, 0), (0.0325, 0.004), (0.0325, 0.215), (0.026, 0.245), (0.0135, 0.262), (0.012, 0.305), (0.0, 0.305)],
    'gin':     [(0, 0), (0.038, 0), (0.040, 0.005), (0.040, 0.190), (0.038, 0.200), (0.016, 0.212), (0.0145, 0.250), (0.0, 0.250)],
    'rum':     [(0, 0), (0.040, 0), (0.042, 0.006), (0.044, 0.150), (0.040, 0.175), (0.020, 0.195), (0.015, 0.232), (0.0, 0.232)],
    'decant':  [(0, 0), (0.046, 0), (0.050, 0.010), (0.052, 0.090), (0.046, 0.130), (0.022, 0.150), (0.018, 0.175), (0.0, 0.175)],
    'isshobin': [(0, 0), (0.048, 0), (0.050, 0.006), (0.050, 0.235), (0.043, 0.275), (0.020, 0.315), (0.016, 0.360), (0.0, 0.360)],
    'vermouth': [(0, 0), (0.036, 0), (0.0375, 0.004), (0.0375, 0.160), (0.030, 0.200), (0.014, 0.240), (0.0125, 0.285), (0.0, 0.285)],
}
def bottle(M, name, x, y, z, shape, glass, liquid, fill, cap, lab_rect, lab_mat, lab_td=2.0, rot=0, label_h=(0.05, 0.14), keep_tag=None, tag_mat=None):
    with kit.xform(T(x, y, z) @ Rz(rot)):
        if shape == 'square':
            w = 0.036
            kit.box(name + '_glass', -w, w, -w, w, 0, 0.19, glass, bevel=0.006, segs=2, skip='-z')
            kit.lathe(name + '_neck', [(0.03, 0.19), (0.024, 0.205), (0.0145, 0.215), (0.0135, 0.245), (0, 0.245)], glass, segs=16)
            top = 0.245; nr = 0.0135
            if liquid: kit.box(name + '_liq', -w + 0.004, w - 0.004, -w + 0.004, w - 0.004, 0.006, fill, liquid, skip='-z')
            with kit.props(td=lab_td):
                kit.quad(name + '_label', [(-0.029, -w - 0.0008, label_h[0]), (0.029, -w - 0.0008, label_h[0]), (0.029, -w - 0.0008, label_h[1]), (-0.029, -w - 0.0008, label_h[1])],
                         lab_mat, uv=((lab_rect[0], lab_rect[1]), (lab_rect[2], lab_rect[1]), (lab_rect[2], lab_rect[3]), (lab_rect[0], lab_rect[3])))
        elif shape == 'flask':
            kit.box(name + '_glass', -0.05, 0.05, -0.022, 0.022, 0, 0.17, glass, bevel=0.012, segs=2, skip='-z')
            kit.lathe(name + '_neck', [(0.02, 0.17), (0.013, 0.185), (0.0125, 0.205), (0, 0.205)], glass, segs=14)
            top = 0.205; nr = 0.0125
            if liquid: kit.box(name + '_liq', -0.045, 0.045, -0.018, 0.018, 0.006, fill, liquid, skip='-z')
            with kit.props(td=lab_td):
                kit.quad(name + '_label', [(-0.034, -0.0228, label_h[0]), (0.034, -0.0228, label_h[0]), (0.034, -0.0228, label_h[1]), (-0.034, -0.0228, label_h[1])],
                         lab_mat, uv=((lab_rect[0], lab_rect[1]), (lab_rect[2], lab_rect[1]), (lab_rect[2], lab_rect[3]), (lab_rect[0], lab_rect[3])))
        else:
            P = PROF[shape]
            kit.lathe(name + '_glass', P[1:], glass, segs=18)
            rb = P[3][0]; top = P[-1][1]; nr = P[-2][0]
            if liquid:
                zf = min(fill, P[3][1])
                kit.lathe(name + '_liq', [(rb - 0.003, 0.005), (rb - 0.003, zf), (0, zf)], liquid, segs=14)
            with kit.props(td=lab_td):
                kit.cyl_patch(name + '_label', 0, 0, label_h[0], label_h[1], rb + 0.0007, -150, -30, lab_mat, uvrect=lab_rect, segs=8)
        kit.cyl(name + '_cap', 0, 0, top - 0.022, top + 0.004, nr + 0.0018, cap, segs=14, cap='t')
        if keep_tag is not None:
            # paper tag on a string round the neck, hanging in front
            zt = top - 0.034
            kit.tube(name + '_str', [(-nr, -0.002, zt + 0.008), (-0.006, -nr - 0.006, zt - 0.004), (-0.004, -nr - 0.012, zt - 0.014)], 0.0006, M.string, segs=4, caps=False)
            with kit.props(td=lab_td * 1.2), kit.xform(T(-0.004, -nr - 0.013, zt - 0.014) @ Rz(-12) @ Rx(-8) @ Ry(14)):
                tw, th = 0.044, 0.022
                r = keep_tag
                kit.quad(name + '_tag', [(-0.004, 0, -th), (tw, 0, -th), (tw, 0, 0), (-0.004, 0, 0)], tag_mat,
                         uv=((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])))

def house_bottles(M, tx):
    a0, a1 = layout.CRED_BOTTLES; z = CR['top_z']
    lab = lambda i: tx.uv(tx.LAB(i))
    spec = [  # x, y, shape, glass, liquid, fill, cap, label index
        (a0 + 0.05, 1.50, 'isshobin', M.glass_brown, None, 0, M.caps[0], 12),
        (a0 + 0.15, 1.47, 'square', M.glass, M.whisky, 0.13, M.caps[1], 1),
        (a0 + 0.25, 1.51, 'slim', M.glass, M.redwine, 0.17, M.caps[2], 15),
        (a0 + 0.35, 1.46, 'round', M.glass, M.whisky, 0.09, M.caps[0], 0),
        (a0 + 0.45, 1.52, 'gin', M.glass_green, None, 0, M.caps[0], 8),
        (a0 + 0.55, 1.47, 'rum', M.glass_brown, None, 0, M.caps[1], 7),
        (a0 + 0.645, 1.51, 'decant', M.glass, M.whisky, 0.06, M.caps[3], 10),
        (a0 + 0.74, 1.46, 'flask', M.glass, M.whisky, 0.11, M.caps[0], 11),
        (a0 + 0.84, 1.50, 'vermouth', M.glass_green, None, 0, M.caps[1], 9),
    ]
    with kit.props(td=1.0):
        for i, (x, y, sh, g, lq, fl, cp, li) in enumerate(spec):
            lh = {'isshobin': (0.08, 0.22), 'decant': (0.035, 0.095), 'flask': (0.04, 0.14), 'slim': (0.06, 0.18)}.get(sh, (0.05, 0.15))
            bottle(M, 'hb%d' % i, x, y, z, sh, g, lq, fl, cp, lab(li), M.sheetA_gloss, lab_td=1.8, rot=[-4, 6, -10, 3, 8, -6, 0, 5, -3][i], label_h=lh)

def bar_tools(M):
    z = CR['top_z']; a0 = layout.CRED_BOTTLES[0]
    with kit.props(td=1.1):
        # ice bucket with tongs
        with kit.xform(T(a0 + 0.10, 1.25, z)):
            kit.lathe('bucket', [(0.0, 0.0), (0.060, 0.0), (0.066, 0.006), (0.074, 0.125), (0.077, 0.128), (0.077, 0.131), (0.071, 0.131),
                                 (0.064, 0.012), (0.0, 0.012)], M.steel, segs=28)
            for sx in (-1, 1):
                kit.tube('bucket_ring', [(sx * 0.074, -0.012, 0.105), (sx * 0.086, -0.010, 0.098), (sx * 0.090, 0.0, 0.092), (sx * 0.086, 0.010, 0.098), (sx * 0.074, 0.012, 0.105)], 0.0025, M.brass, segs=6)
            kit.lathe('bucket_ice', [(0.0, 0.085), (0.060, 0.085), (0.0, 0.088)], M.glass, segs=12)
            kit.tube('tong_a', [(0.0, -0.02, 0.06), (0.03, -0.035, 0.13), (0.075, -0.05, 0.16)], 0.0028, M.steel, segs=6)
            kit.tube('tong_b', [(0.006, -0.008, 0.06), (0.036, -0.022, 0.13), (0.075, -0.05, 0.16)], 0.0028, M.steel, segs=6)
        # two rocks glasses: one upright, one upturned on the credenza to drain
        for s_, (gx, gy, inv) in enumerate([(a0 + 0.27, 1.22, False), (a0 + 0.365, 1.25, True)]):
            M_ = T(gx, gy, z + (0.088 if inv else 0.0)) @ (Rx(180) if inv else Matrix.Identity(4))
            with kit.xform(M_):
                kit.lathe('rocks%d' % s_, [(0.0, 0.0), (0.033, 0.0), (0.035, 0.004), (0.041, 0.088), (0.038, 0.088), (0.0325, 0.013), (0.0, 0.011)], M.glass, segs=22)
        # jigger + cobbler shaker
        with kit.xform(T(a0 + 0.48, 1.20, z)):
            kit.lathe('jigger', [(0.0, 0.0), (0.022, 0.0), (0.009, 0.040), (0.009, 0.044), (0.018, 0.090), (0.0165, 0.090), (0.0, 0.050)], M.steel, segs=18)
        with kit.xform(T(a0 + 0.58, 1.24, z)):
            kit.lathe('shaker', [(0.0, 0.0), (0.040, 0.0), (0.042, 0.006), (0.047, 0.125), (0.047, 0.131), (0.044, 0.134), (0.040, 0.150),
                                 (0.024, 0.182), (0.024, 0.186), (0.018, 0.190), (0.018, 0.212), (0.012, 0.216), (0.0, 0.216)], M.steel, segs=22)
        # bar spoon lying on the credenza
        kit.tube('spoon', [(a0 + 0.68, 1.16, z + 0.003), (a0 + 0.78, 1.21, z + 0.003), (a0 + 0.88, 1.26, z + 0.004)], 0.0022, M.steel, segs=6)
        ellipsoid('spoon_bowl', (a0 + 0.895, 1.267, z + 0.005), (0.011, 0.007, 0.003), M.steel, 10, 6, M_=None)

def bottle_keep(M, tx):
    z = ROWS[0]
    tags = [tx.uv(tx.TAG(i)) for i in range(8)]
    lab = lambda i: tx.uv(tx.LAB(i))
    others = [(0.535, 1.46, 'slim', 3, 0.07, 0), (0.71, 1.53, 'square', 5, 0.11, 1), (0.89, 1.53, 'round', 13, 0.15, 2),
              (1.07, 1.53, 'square', 14, 0.05, 3), (1.238, 1.46, 'slim', 6, 0.12, 4)]
    with kit.props(td=1.0):
        for i, (x, y, sh, li, fl, ti) in enumerate(others):
            bottle(M, 'kb%d' % i, x, y, z, sh, M.glass, M.whisky, fl, M.caps[i % 2], lab(li), M.sheetA_gloss, lab_td=1.6, rot=[5, -8, 4, -6, 9][i],
                   keep_tag=tags[ti], tag_mat=M.sheetA_gloss)
    shapes = ['round', 'square', 'round', 'round']; fills = [0.06, 0.14, 0.10, 0.03]
    with kit.props(atlas='shelves_b'):
        for j in range(4):
            _, (x, y, zz), _ = INTER['bottle_%d' % j]
            with kit.interactive('bottle_%d' % j, origin=(x, y, zz)), kit.props(td=1.4):
                bottle(M, 'ib%d' % j, x, y, zz, shapes[j], M.glass, M.whisky, fills[j], M.caps[j % 2], tx.uv(tx.BLABEL(j)), M.sheetB, lab_td=2.6,
                       rot=[-3, 4, -6, 2][j], keep_tag=tx.uv(tx.BTAG(j)), tag_mat=M.sheetB)

# ------------------------------------------------------------------ on top of the shelving
def on_top(M, tx):
    z = TOPZ
    with kit.props(td=1.0):
        # small globe on a turned walnut stand, tilted on its axis
        gx, gy = -0.95, 1.44
        with kit.xform(T(gx + 0.033, gy, z)):
            kit.lathe('globe_base', [(0.0, 0.0), (0.055, 0.0), (0.055, 0.008), (0.040, 0.016), (0.012, 0.024), (0.008, 0.074), (0.0, 0.074)], M.walnut_v, segs=20)
    with kit.props(td=1.0), kit.xform(T(gx, gy, z + 0.150) @ Ry(-23)):
        ellipsoid('globe', (0, 0, 0), (0.078, 0.078, 0.078), M.globe, 24, 14)
        pts = [(0.084 * math.sin(math.radians(a)), 0.0, 0.084 * math.cos(math.radians(a))) for a in range(-200, 21, 20)]
        kit.tube('globe_meridian', pts, 0.0028, M.brass, segs=6, caps=True)
        kit.cyl('globe_pin', 0, 0, 0.076, 0.090, 0.003, M.brass, segs=8)
    # box of 7-inch singles
    sx, sy = 0.22, 1.44; bw, bd, bh = 0.205, 0.20, 0.13
    with kit.props(td=0.8):
        kit.box('singles_box', sx - bw / 2, sx + bw / 2, sy - bd / 2, sy + bd / 2, z, z + bh, M.kraft, skip='-z')
        kit.box('singles_box_in', sx - bw / 2 + 0.003, sx + bw / 2 - 0.003, sy - bd / 2 + 0.003, sy + bd / 2 - 0.003, z + 0.004, z + bh, M.kraft, only=['+z'])
    mb = MB(); rng = random.Random(45)
    x = sx - bw / 2 + 0.005; yf = sy - bd / 2 + 0.008
    while x < sx + bw / 2 - 0.008:
        t = rng.uniform(0.0022, 0.0035); h = 0.178 + rng.uniform(-0.003, 0.004); yo = rng.uniform(0, 0.006)
        r = tx.uv(tx.LP(rng.randrange(tx.N_LP)))
        r = sub(r, 0, 0.0, 1, 0.55)
        tbox(mb, x, x + t, yf + yo, yf + yo + 0.18, z + 0.004, z + 0.004 + h, {'-y': (r, 0, 0), '+z': (tx.uv(tx.EDGE), 0, 0)})
        x += t + rng.uniform(0.0002, 0.0012)
    with kit.props(td=0.9):
        mb.done('singles', [M.sheetA])
        lb = MB(); lr = tx.uv(tx.SINGLES)
        yl = sy - bd / 2 - 0.0008
        lb.quad([(sx - 0.0125, yl, z + 0.022), (sx + 0.0125, yl, z + 0.022), (sx + 0.0125, yl, z + 0.105), (sx - 0.0125, yl, z + 0.105)], lr)
        lb.done('singles_label', [M.sheetA])
    # folded cloth: two folded bar towels, slightly askew
    with kit.props(td=0.7):
        with kit.xform(T(0.92, 1.43, z) @ Rz(7)):
            kit.box('towel_a', -0.12, 0.12, -0.085, 0.085, 0.0, 0.022, M.towel, bevel=0.009, segs=3, skip='-z')
        with kit.xform(T(0.935, 1.425, z + 0.021) @ Rz(-4)):
            kit.box('towel_b', -0.115, 0.115, -0.08, 0.08, 0.0, 0.020, M.towel, bevel=0.009, segs=3, skip='-z')

# ------------------------------------------------------------------ build
def build():
    tx = _tex()
    M = materials(tx)
    credenza(M)
    carcass(M)
    spot_cans(M)
    records(M, tx)
    with kit.props(atlas='shelves_b'):
        sleeves(M, tx)
    books(M, tx)
    house_bottles(M, tx)
    bar_tools(M)
    bottle_keep(M, tx)
    on_top(M, tx)

LIGHTS = []
