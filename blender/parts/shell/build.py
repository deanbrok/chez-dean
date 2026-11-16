"""SHELL — the architecture of DEAN'S: floors, walls, ceiling + beams, the high street window, the stair door and
the old stone stairwell going down, the kitchen-nook shell, and a few small basement details.
Run:  python3 blender/barkit/run.py preview shell --cam stairs
"""
import os, math
from mathutils import Vector, Matrix
from barkit import kit, mats, layout
from barkit.kit import T, Rx, Ry, Rz
from barkit.mats import N, L

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')

R = layout.ROOM; WIN = layout.WINDOW; DR = layout.DOOR; ST = layout.STAIRS
NO = layout.NOOK_OPENING; NK = layout.NOOK; CR = layout.CREDENZA
DOOR_AJAR = 60.0          # degrees the leaf stands open, swung into the stairwell (+Y)
E = 0.02                  # overlap of surfaces into neighbouring surfaces (keeps the room light-tight)

# ====================================================================================================== node helpers
def xyz(nt):
    tc = N(nt, 'ShaderNodeTexCoord'); s = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, tc.outputs['Object'], s.inputs[0])
    return s.outputs[0], s.outputs[1], s.outputs[2], tc.outputs['Object']

def _set(nt, sock, val):
    if hasattr(val, 'links'): L(nt, val, sock)
    else: sock.default_value = val

def comb(nt, a, b, c):
    n = N(nt, 'ShaderNodeCombineXYZ')
    for s, v in zip(n.inputs, (a, b, c)): _set(nt, s, v)
    return n.outputs[0]

def M(nt, op, a, b=None, c=None, clamp=False):
    n = N(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    for s, v in zip(n.inputs, (a, b, c)):
        if v is not None: _set(nt, s, v)
    return n.outputs[0]

def mr(nt, v, a, b, c=0.0, d=1.0):
    n = N(nt, 'ShaderNodeMapRange'); n.clamp = True
    _set(nt, n.inputs['Value'], v)
    n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b
    n.inputs['To Min'].default_value = c; n.inputs['To Max'].default_value = d
    return n.outputs[0]

def wn1(nt, w):
    n = N(nt, 'ShaderNodeTexWhiteNoise', noise_dimensions='1D'); _set(nt, n.inputs['W'], w)
    return n.outputs[0]

def band(nt, t, c, w):
    """exp(-((t-c)/w)^2)"""
    d = M(nt, 'DIVIDE', M(nt, 'SUBTRACT', t, c), w)
    return M(nt, 'EXPONENT', M(nt, 'MULTIPLY', M(nt, 'MULTIPLY', d, d), -1.0))

def ao(nt, dist):
    n = N(nt, 'ShaderNodeAmbientOcclusion'); n.inputs['Distance'].default_value = dist
    return n.outputs['AO']

def edge_mask(nt, radius=0.005):
    bv = N(nt, 'ShaderNodeBevel'); bv.inputs['Radius'].default_value = radius
    g = N(nt, 'ShaderNodeNewGeometry')
    dp = N(nt, 'ShaderNodeVectorMath', operation='DOT_PRODUCT')
    L(nt, bv.outputs[0], dp.inputs[0]); L(nt, g.outputs['Normal'], dp.inputs[1])
    return mr(nt, dp.outputs['Value'], 0.995, 0.85)

def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')

# ====================================================================================================== materials
_MAT = {}
def mat(key):
    if key not in _MAT: _MAT[key] = MAKERS[key]()
    return _MAT[key]

def m_plaster(name='shell_plaster', c0=(0.36, 0.27, 0.15), c1=(0.44, 0.34, 0.19), stain=(0.62, 0.52, 0.38), top=True):
    m, nt, b, _ = mats.base(name)
    x, y, z, v = xyz(nt)
    big = mats.noise(nt, v, 0.8, 3, 0.55)
    mid = mats.noise(nt, v, 3.5, 4, 0.6)
    fine = mats.noise(nt, v, 38, 3, 0.6)
    col = mats.ramp(nt, mid, [(0.3, c0), (0.7, c1)])
    col = mats.mixc(nt, col, mats.ramp(nt, big, [(0.52, (1, 1, 1)), (0.72, stain)]), 1.0)
    # water / smoke tide marks: faint streaks running down from the ceiling
    streak = mats.noise(nt, comb(nt, M(nt, 'MULTIPLY', M(nt, 'ADD', x, y), 7.0), M(nt, 'MULTIPLY', z, 0.5), 0.0), 1.0, 3, 0.5)
    col = mats.mixc(nt, col, (0.80, 0.72, 0.60), M(nt, 'MULTIPLY', mr(nt, streak, 0.55, 0.75), mr(nt, z, 1.3, 2.45)))
    if top:
        col = mats.mixc(nt, col, (0.55, 0.43, 0.30), mr(nt, z, 1.35, 2.45, 0.0, 0.85))
    col = mats.mixc(nt, col, mats.ramp(nt, ao(nt, 0.45), [(0.15, (0.40, 0.32, 0.22)), (0.9, (1, 1, 1))]), 1.0)
    L(nt, col, b.inputs['Base Color'])
    mats.setp(b, rough=0.86)
    mats.bump(nt, b, M(nt, 'ADD', M(nt, 'MULTIPLY', fine, 0.5), mid), 0.18, 0.004)
    return m

def m_plaster_nook():
    return m_plaster('shell_plaster_nook', (0.46, 0.39, 0.25), (0.54, 0.46, 0.30), (0.80, 0.72, 0.58), top=False)

def m_tg(name='shell_wainscot', cols=((0.030, 0.013, 0.006), (0.060, 0.027, 0.012), (0.098, 0.048, 0.022)), w=0.088):
    """vertical tongue-and-groove boards; works on walls facing X or Y (board coordinate = x + y)"""
    m, nt, b, _ = mats.base(name)
    x, y, z, v = xyz(nt)
    h = M(nt, 'ADD', x, y)
    u = M(nt, 'DIVIDE', h, w); bid = M(nt, 'FLOOR', u); fu = M(nt, 'FRACT', u)
    seam = M(nt, 'LESS_THAN', fu, 0.055)
    grain = mats.noise(nt, comb(nt, M(nt, 'MULTIPLY', h, 30.0), M(nt, 'MULTIPLY', z, 0.9), M(nt, 'MULTIPLY', bid, 3.7)), 1.0, 6, 0.62, 1.3)
    col = mats.ramp(nt, grain, [(0.3, cols[0]), (0.52, cols[1]), (0.74, cols[2])])
    col = mats.mixc(nt, col, (0.80, 0.80, 0.80), 1.0)
    tint = M(nt, 'ADD', 0.72, M(nt, 'MULTIPLY', wn1(nt, bid), 0.56))
    col = mats.mixc(nt, col, comb(nt, tint, tint, tint), 1.0)
    col = mats.mixc(nt, col, (0.25, 0.25, 0.25), seam)
    # scuffs low down (feet, chairs)
    scuff = M(nt, 'MULTIPLY', mr(nt, z, 0.45, 0.05), mr(nt, mats.noise(nt, v, 6, 3, 0.6), 0.5, 0.7))
    col = mats.mixc(nt, col, (0.11, 0.075, 0.05), M(nt, 'MULTIPLY', scuff, 0.6), 'MIX')
    L(nt, col, b.inputs['Base Color'])
    L(nt, M(nt, 'ADD', 0.34, M(nt, 'MULTIPLY', grain, 0.2)), b.inputs['Roughness'])
    mats.setp(b, coat=0.12, coat_rough=0.2)
    mats.bump(nt, b, M(nt, 'ADD', M(nt, 'SUBTRACT', 1.0, seam), M(nt, 'MULTIPLY', grain, 0.05)), 0.5, 0.003)
    return m

def m_trim():
    return mats.wood('shell_trim', axis='X', cols=((0.022, 0.010, 0.005), (0.05, 0.022, 0.010), (0.085, 0.040, 0.018)), rough=0.34, bmp=0.08, coat=0.15)

def m_trim_v():
    return mats.wood('shell_trim_v', axis='Z', cols=((0.022, 0.010, 0.005), (0.05, 0.022, 0.010), (0.085, 0.040, 0.018)), rough=0.34, bmp=0.08, coat=0.15)

def m_floor():
    m, nt, b, _ = mats.base('shell_floor')
    x, y, z, v = xyz(nt)
    u = M(nt, 'DIVIDE', x, 0.13); bid = M(nt, 'FLOOR', u); fu = M(nt, 'FRACT', u)
    r1 = wn1(nt, bid)
    vv = M(nt, 'DIVIDE', M(nt, 'ADD', y, M(nt, 'MULTIPLY', r1, 5.0)), 1.7)
    seg = M(nt, 'FLOOR', vv); fv = M(nt, 'FRACT', vv)
    seam = M(nt, 'MAXIMUM', M(nt, 'LESS_THAN', fu, 0.03), M(nt, 'LESS_THAN', fv, 0.0035))
    grain = mats.noise(nt, comb(nt, M(nt, 'MULTIPLY', x, 26.0), M(nt, 'ADD', M(nt, 'MULTIPLY', y, 1.0), M(nt, 'MULTIPLY', r1, 13.0)), M(nt, 'MULTIPLY', seg, 2.3)), 1.0, 6, 0.62, 1.2)
    col = mats.ramp(nt, grain, [(0.3, (0.020, 0.010, 0.0055)), (0.55, (0.048, 0.025, 0.012)), (0.76, (0.082, 0.044, 0.021))])
    t = M(nt, 'ADD', 0.62, M(nt, 'MULTIPLY', wn1(nt, M(nt, 'ADD', M(nt, 'MULTIPLY', bid, 17.31), M(nt, 'MULTIPLY', seg, 3.17))), 0.76))
    col = mats.mixc(nt, col, comb(nt, t, t, t), 1.0)
    # wear: customers' walking line in front of the counter, the aisle behind it, and a path to the stair door
    w = M(nt, 'ADD', band(nt, y, -1.9, 0.32), M(nt, 'MULTIPLY', band(nt, y, 0.45, 0.28), 0.8))
    path = M(nt, 'MULTIPLY', band(nt, x, -2.72, 0.28), mr(nt, y, 0.2, 1.45))
    w = M(nt, 'ADD', w, M(nt, 'MULTIPLY', path, 0.9))
    w = M(nt, 'MULTIPLY', w, mr(nt, mats.noise(nt, v, 2.2, 4, 0.6), 0.3, 0.7, 0.35, 1.0), clamp=True)
    col = mats.mixc(nt, col, (0.11, 0.08, 0.055), M(nt, 'MULTIPLY', w, 0.5), 'MIX')
    col = mats.mixc(nt, col, (0.15, 0.15, 0.15), seam)
    col = mats.mixc(nt, col, mats.ramp(nt, ao(nt, 0.3), [(0.2, (0.5, 0.5, 0.5)), (0.9, (1, 1, 1))]), 1.0)
    L(nt, col, b.inputs['Base Color'])
    L(nt, M(nt, 'ADD', M(nt, 'ADD', 0.36, M(nt, 'MULTIPLY', w, 0.3)), M(nt, 'MULTIPLY', grain, 0.15)), b.inputs['Roughness'])
    mats.bump(nt, b, M(nt, 'ADD', M(nt, 'SUBTRACT', 1.0, seam), M(nt, 'MULTIPLY', grain, 0.08)), 0.35, 0.003)
    return m

def m_lino():
    m, nt, b, _ = mats.base('shell_lino')
    x, y, z, v = xyz(nt)
    s = 0.20
    cx = M(nt, 'FLOOR', M(nt, 'DIVIDE', x, s)); cy = M(nt, 'FLOOR', M(nt, 'DIVIDE', y, s))
    par = M(nt, 'MULTIPLY', M(nt, 'FRACT', M(nt, 'MULTIPLY', M(nt, 'ADD', cx, cy), 0.5)), 2.0)
    col = mats.mixc(nt, (0.46, 0.41, 0.28), (0.10, 0.16, 0.10), par, 'MIX')
    gx = M(nt, 'FRACT', M(nt, 'DIVIDE', x, s)); gy = M(nt, 'FRACT', M(nt, 'DIVIDE', y, s))
    gl = M(nt, 'MAXIMUM', M(nt, 'LESS_THAN', gx, 0.012), M(nt, 'LESS_THAN', gy, 0.012))
    dirt = mats.noise(nt, v, 4, 5, 0.6)
    col = mats.mixc(nt, col, mats.ramp(nt, dirt, [(0.35, (1, 1, 1)), (0.7, (0.7, 0.62, 0.5))]), 1.0)
    col = mats.mixc(nt, col, (0.5, 0.45, 0.4), gl)
    col = mats.mixc(nt, col, mats.ramp(nt, ao(nt, 0.25), [(0.2, (0.55, 0.5, 0.45)), (0.9, (1, 1, 1))]), 1.0)
    L(nt, col, b.inputs['Base Color'])
    L(nt, M(nt, 'ADD', 0.35, M(nt, 'MULTIPLY', dirt, 0.25)), b.inputs['Roughness'])
    mats.bump(nt, b, M(nt, 'SUBTRACT', 1.0, gl), 0.2, 0.001)
    return m

def m_wall_tiles():
    """white square 15 cm kitchen tiles, stack bond (x + y = along the wall)"""
    m, nt, b, _ = mats.base('shell_wall_tiles')
    x, y, z, v = xyz(nt)
    s = 0.15
    h = M(nt, 'ADD', x, y)
    u = M(nt, 'DIVIDE', h, s); w = M(nt, 'DIVIDE', z, s)
    g = M(nt, 'MAXIMUM', M(nt, 'LESS_THAN', M(nt, 'FRACT', u), 0.022), M(nt, 'LESS_THAN', M(nt, 'FRACT', w), 0.022))
    tid = M(nt, 'ADD', M(nt, 'FLOOR', u), M(nt, 'MULTIPLY', M(nt, 'FLOOR', w), 31.7))
    t = M(nt, 'ADD', 0.9, M(nt, 'MULTIPLY', wn1(nt, tid), 0.12))
    col = mats.mixc(nt, (0.60, 0.59, 0.54), comb(nt, t, t, M(nt, 'MULTIPLY', t, 0.97)), 1.0)
    col = mats.mixc(nt, col, (0.26, 0.23, 0.19), g, 'MIX')
    grime = mats.noise(nt, v, 3, 4, 0.6)
    col = mats.mixc(nt, col, mats.ramp(nt, grime, [(0.4, (1, 1, 1)), (0.75, (0.82, 0.76, 0.62))]), 1.0)
    col = mats.mixc(nt, col, mats.ramp(nt, ao(nt, 0.3), [(0.2, (0.5, 0.45, 0.38)), (0.9, (1, 1, 1))]), 1.0)
    L(nt, col, b.inputs['Base Color'])
    L(nt, M(nt, 'ADD', 0.08, M(nt, 'MULTIPLY', g, 0.7)), b.inputs['Roughness'])
    mats.setp(b, coat=0.4, coat_rough=0.05)
    mats.bump(nt, b, M(nt, 'SUBTRACT', 1.0, g), 0.5, 0.002)
    return m

def m_stone(name='shell_stone', vault=False):
    """old, rough, damp ashlar — much older than the building"""
    m, nt, b, _ = mats.base(name)
    x, y, z, v = xyz(nt)
    h = M(nt, 'ADD', x, y)
    dn = M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', mats.noise(nt, v, 1.6, 3, 0.5), 0.5), 0.14)
    dn2 = M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', mats.noise(nt, v, 7.0, 2, 0.5), 0.5), 0.025)
    dn = M(nt, 'ADD', dn, dn2)
    br = N(nt, 'ShaderNodeTexBrick'); br.offset = 0.5; br.offset_frequency = 2; br.squash = 0.68; br.squash_frequency = 3
    if vault: L(nt, comb(nt, M(nt, 'ADD', y, dn), M(nt, 'ADD', x, M(nt, 'MULTIPLY', dn, 0.6)), 0.0), br.inputs['Vector'])
    else: L(nt, comb(nt, M(nt, 'ADD', h, dn), M(nt, 'ADD', z, M(nt, 'MULTIPLY', dn, 0.6)), 0.0), br.inputs['Vector'])
    for k, val in (('Scale', 1.0), ('Mortar Size', 0.016), ('Mortar Smooth', 0.3), ('Bias', 0.0), ('Brick Width', 0.43), ('Row Height', 0.25)):
        br.inputs[k].default_value = val
    br.inputs['Color1'].default_value = (0.27, 0.235, 0.18, 1); br.inputs['Color2'].default_value = (0.075, 0.075, 0.068, 1)
    br.inputs['Mortar'].default_value = (0.06, 0.058, 0.05, 1)
    fac = br.outputs['Fac']
    pits = mats.noise(nt, v, 9, 6, 0.68)
    col = mats.mixc(nt, br.outputs['Color'], mats.ramp(nt, pits, [(0.3, (0.6, 0.6, 0.6)), (0.72, (1.12, 1.1, 1.05))]), 1.0)
    # damp: lower down, and in streaks running down the joints
    low = mr(nt, z, 1.0, -1.6)
    streak = mr(nt, mats.noise(nt, comb(nt, M(nt, 'MULTIPLY', h, 5.0), M(nt, 'MULTIPLY', z, 0.35), 0.0), 1.0, 4, 0.6), 0.48, 0.66)
    wet = M(nt, 'ADD', M(nt, 'MULTIPLY', low, 0.65), M(nt, 'MULTIPLY', streak, 0.45), clamp=True)
    col = mats.mixc(nt, col, (0.42, 0.44, 0.42), wet)
    col = mats.mixc(nt, col, (0.035, 0.05, 0.036), M(nt, 'MULTIPLY', M(nt, 'MULTIPLY', wet, fac), 0.7), 'MIX')    # green-black in the joints
    salt = M(nt, 'MULTIPLY', mr(nt, mats.noise(nt, v, 2.2, 4, 0.6), 0.6, 0.74), mr(nt, z, -1.2, 0.6, 0.0, 0.6))
    col = mats.mixc(nt, col, (0.36, 0.36, 0.33), salt, 'MIX')                                                 # pale salt bloom
    col = mats.mixc(nt, col, mats.ramp(nt, ao(nt, 0.35), [(0.15, (0.45, 0.45, 0.45)), (0.9, (1, 1, 1))]), 1.0)
    L(nt, col, b.inputs['Base Color'])
    L(nt, M(nt, 'SUBTRACT', 0.88, M(nt, 'MULTIPLY', wet, 0.55)), b.inputs['Roughness'])
    tool = mats.noise(nt, v, 16, 8, 0.75, 0.4)                       # rough tooling / spalling
    hgt = M(nt, 'ADD', M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', 1.0, fac), 0.6),
            M(nt, 'ADD', M(nt, 'MULTIPLY', mats.noise(nt, v, 4.0, 5, 0.6), 0.35), M(nt, 'ADD', M(nt, 'MULTIPLY', pits, 0.35), M(nt, 'MULTIPLY', tool, 0.45))))
    mats.bump(nt, b, hgt, 0.9, 0.012)
    return m

def m_steps():
    m, nt, b, _ = mats.base('shell_steps')
    x, y, z, v = xyz(nt)
    wear = mr(nt, M(nt, 'ABSOLUTE', M(nt, 'ADD', x, 2.78)), 0.42, 0.05)
    sid = M(nt, 'FLOOR', M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', y, 1.95), 4.0))
    t = M(nt, 'ADD', 0.78, M(nt, 'MULTIPLY', wn1(nt, sid), 0.44))
    n1 = mats.noise(nt, v, 6, 6, 0.65)
    col = mats.ramp(nt, n1, [(0.3, (0.10, 0.095, 0.082)), (0.7, (0.21, 0.195, 0.165))])
    col = mats.mixc(nt, col, comb(nt, t, t, t), 1.0)
    col = mats.mixc(nt, col, (0.72, 0.70, 0.66), wear)                 # polished-dark in the worn path
    damp = mr(nt, z, -0.3, -1.8)
    col = mats.mixc(nt, col, (0.55, 0.58, 0.56), damp)
    col = mats.mixc(nt, col, mats.ramp(nt, ao(nt, 0.3), [(0.15, (0.4, 0.4, 0.4)), (0.9, (1, 1, 1))]), 1.0)
    L(nt, col, b.inputs['Base Color'])
    L(nt, M(nt, 'SUBTRACT', 0.85, M(nt, 'ADD', M(nt, 'MULTIPLY', wear, 0.4), M(nt, 'MULTIPLY', damp, 0.3)), clamp=True), b.inputs['Roughness'])
    mats.bump(nt, b, M(nt, 'MULTIPLY', mats.noise(nt, v, 14, 5, 0.65), M(nt, 'SUBTRACT', 1.0, M(nt, 'MULTIPLY', wear, 0.8))), 0.5, 0.004)
    return m

def m_door_paint():
    m, nt, b, _ = mats.base('shell_door_paint')
    x, y, z, v = xyz(nt)
    brush = mats.noise(nt, comb(nt, M(nt, 'MULTIPLY', x, 40.0), M(nt, 'MULTIPLY', y, 40.0), M(nt, 'MULTIPLY', z, 2.5)), 1.0, 4, 0.6)
    col = mats.ramp(nt, brush, [(0.3, (0.020, 0.058, 0.036)), (0.7, (0.032, 0.085, 0.052))])
    chips_n = mats.noise(nt, v, 24, 6, 0.7)
    chips = M(nt, 'MULTIPLY', edge_mask(nt, 0.006), mr(nt, chips_n, 0.5, 0.6))
    chips = M(nt, 'ADD', chips, M(nt, 'MULTIPLY', mr(nt, chips_n, 0.74, 0.78), 0.8), clamp=True)
    col = mats.mixc(nt, col, (0.075, 0.042, 0.02), chips, 'MIX')
    # hand grime around the knob
    d = N(nt, 'ShaderNodeVectorMath', operation='DISTANCE'); L(nt, v, d.inputs[0]); d.inputs[1].default_value = KNOB_WORLD[0]
    grime = M(nt, 'MULTIPLY', mr(nt, d.outputs['Value'], 0.20, 0.03), mr(nt, mats.noise(nt, v, 8, 3, 0.6), 0.3, 0.65, 0.4, 1.0))
    col = mats.mixc(nt, col, (0.45, 0.42, 0.36), grime)
    L(nt, col, b.inputs['Base Color'])
    L(nt, M(nt, 'ADD', M(nt, 'SUBTRACT', 0.36, M(nt, 'MULTIPLY', grime, 0.12)), M(nt, 'MULTIPLY', chips, 0.35)), b.inputs['Roughness'])
    mats.bump(nt, b, M(nt, 'SUBTRACT', M(nt, 'MULTIPLY', brush, 0.15), chips), 0.25, 0.002)
    return m

def m_steel():
    return mats.noisy('shell_steel', (0.022, 0.026, 0.024), (0.05, 0.048, 0.042), rough=0.42, scale=25, bmp=0.2, rvar=0.2, metal_=0.3)

def m_iron():
    return mats.noisy('shell_iron', (0.025, 0.02, 0.017), (0.085, 0.042, 0.02), rough=0.55, scale=35, bmp=0.3, rvar=0.3, metal_=0.5)

def m_rail():
    m = mats.metal('shell_rail', (0.10, 0.085, 0.07), rough=0.32, rvar=0.2, patina=0.6, scale=30)
    return m

def m_brass():
    return mats.metal('shell_brass', (0.78, 0.55, 0.24), rough=0.26, rvar=0.2, patina=0.45)

def m_plate():
    m = mats.image('shell_plate', os.path.join(TEX, 'plate.png'), rough=0.3)
    mats.setp(bsdf(m), metal=0.85)
    return m

def m_fuse_label():
    return mats.image('shell_fuse_label', os.path.join(TEX, 'fuse.png'), rough=0.7)

def m_sill():
    return mats.noisy('shell_sill', (0.30, 0.26, 0.18), (0.42, 0.37, 0.27), rough=0.42, scale=9, bmp=0.15, rvar=0.15)

def m_concrete():
    return mats.noisy('shell_concrete', (0.06, 0.058, 0.054), (0.13, 0.125, 0.115), rough=0.9, scale=14, bmp=0.4)

def m_ceiling():
    return mats.planks('shell_ceiling', axis='X', cols=((0.010, 0.007, 0.005), (0.022, 0.015, 0.010), (0.036, 0.025, 0.016)), width=0.115, rough=0.7)

def m_beam():
    return mats.wood('shell_beam', axis='Y', cols=((0.012, 0.008, 0.005), (0.030, 0.018, 0.010), (0.050, 0.030, 0.016)), rough=0.62, bmp=0.3, scale=0.8)

def m_pipe():
    return mats.noisy('shell_pipe', (0.10, 0.065, 0.025), (0.30, 0.22, 0.09), rough=0.5, scale=11, bmp=0.3, rvar=0.2)

def m_conduit():
    return mats.noisy('shell_conduit', (0.26, 0.22, 0.15), (0.36, 0.31, 0.22), rough=0.45, scale=20, bmp=0.1)

def m_bakelite():
    return mats.noisy('shell_bakelite', (0.022, 0.010, 0.006), (0.05, 0.022, 0.011), rough=0.2, scale=30, rvar=0.1)

def m_fusebox():
    return mats.noisy('shell_fusebox', (0.05, 0.06, 0.052), (0.085, 0.095, 0.08), rough=0.45, scale=16, bmp=0.15, rvar=0.15)

def m_vent():
    return mats.noisy('shell_vent', (0.10, 0.095, 0.085), (0.17, 0.16, 0.14), rough=0.55, scale=20, bmp=0.15)

def m_void():
    return mats.plain('shell_void', (0.004, 0.004, 0.004), rough=0.9)

def m_cream_paint():
    return mats.noisy('shell_cream_paint', (0.45, 0.42, 0.34), (0.55, 0.52, 0.43), rough=0.32, scale=12, rvar=0.1)

def m_frosted():
    return mats.glass('shell_frosted', col=(0.85, 0.9, 0.88), rough=0.85, shadow=(0.9, 0.93, 0.92), shadow_amt=0.8)

MAKERS = dict(vault=lambda: m_stone('shell_vault', vault=True), plaster=m_plaster, plaster_nook=m_plaster_nook, wainscot=m_tg, trim=m_trim, trim_v=m_trim_v, floor=m_floor,
              lino=m_lino, wall_tiles=m_wall_tiles, stone=m_stone, steps=m_steps, door_paint=m_door_paint, steel=m_steel,
              iron=m_iron, rail=m_rail, brass=m_brass, plate=m_plate, fuse_label=m_fuse_label, sill=m_sill,
              concrete=m_concrete, ceiling=m_ceiling, beam=m_beam, pipe=m_pipe, conduit=m_conduit, bakelite=m_bakelite,
              fusebox=m_fusebox, vent=m_vent, void=m_void, cream_paint=m_cream_paint, frosted=m_frosted)

# ====================================================================================================== geometry helpers
def quad_n(name, pts, m, n):
    """quad with its normal forced toward n"""
    p = [Vector(q) for q in pts]
    if (p[1] - p[0]).cross(p[2] - p[0]).dot(Vector(n)) < 0: pts = list(reversed(pts))
    return kit.quad(name, pts, m)

def wrect(name, axis, c, a0, a1, b0, b1, s, m):
    """axis-aligned rectangle: plane axis = c; (a, b) = (y, z) for 'x', (x, z) for 'y', (x, y) for 'z'; faces sign s"""
    if axis == 'x': pts = [(c, a0, b0), (c, a1, b0), (c, a1, b1), (c, a0, b1)]; n = (s, 0, 0)
    elif axis == 'y': pts = [(a0, c, b0), (a1, c, b0), (a1, c, b1), (a0, c, b1)]; n = (0, s, 0)
    else: pts = [(a0, b0, c), (a1, b0, c), (a1, b1, c), (a0, b1, c)]; n = (0, 0, s)
    return quad_n(name, pts, m, n)

def abox(name, axis, c0, c1, a0, a1, z0, z1, m, skip=(), bevel=0.0, segs=2):
    """box measured off a wall: axis 'x' -> x in c0..c1, y in a0..a1; axis 'y' -> y in c0..c1, x in a0..a1"""
    lo, hi = min(c0, c1), max(c0, c1)
    if axis == 'x': return kit.box(name, lo, hi, a0, a1, z0, z1, m, skip=skip, bevel=bevel, segs=segs)
    return kit.box(name, a0, a1, lo, hi, z0, z1, m, skip=skip, bevel=bevel, segs=segs)

def back_of(axis, s): return ('-' if s > 0 else '+') + axis

def wainscot(tag, axis, c, a0, a1, s, rail=True, skirt=True):
    """lower 0.95 m: vertical boards + chair rail + skirting, on the wall plane axis=c facing s"""
    wrect(tag + '_tg', axis, c + s * 0.012, a0, a1, 0.0, 0.95, s, mat('wainscot'))
    if rail:
        abox(tag + '_rail', axis, c, c + s * 0.034, a0, a1, 0.915, 0.968, mat('trim'), skip=back_of(axis, s), bevel=0.007, segs=2)
    if skirt:
        abox(tag + '_skirt', axis, c, c + s * 0.026, a0, a1, 0.0, 0.135, mat('trim'), skip=(back_of(axis, s), '-z'), bevel=0.005, segs=1)

def wob(a, b):
    return 0.5 + 0.22 * math.sin(5.3 * a + 2.1 * b + 0.4) + 0.18 * math.sin(2.2 * a - 6.7 * b + 1.9) + 0.1 * math.sin(13.1 * a + 9.7 * b)

def grid_mesh(name, cols, rows, pos, m, skipf=None, smooth=True):
    """generic quad grid; pos(i, j) -> Vector or None.  Duplicate positions merge (lets a grid end on a slanted edge)."""
    import bmesh
    bm = bmesh.new(); cache = {}
    def V(i, j):
        p = pos(i, j)
        key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
        if key not in cache: cache[key] = bm.verts.new(p)
        return cache[key]
    for i in range(len(cols) - 1):
        for j in range(len(rows) - 1):
            if skipf and skipf(i, j): continue
            vs = []
            for v in (V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)):
                if v not in vs: vs.append(v)
            if len(vs) >= 3:
                try: bm.faces.new(vs)
                except ValueError: pass
    return kit.finish(name, bm, m, smooth=smooth, sharp=50)

# ====================================================================================================== the room
def floors_and_ceilings():
    x0, x1, y0, y1, z1 = R['x0'], R['x1'], R['y0'], R['y1'], R['z1']
    with kit.props(td=0.38):
        wrect('floor_main', 'z', 0.0, x0 - E, x1 + E, y0 - E, y1, 1, mat('floor'))
    with kit.props(td=0.5):
        wrect('floor_nook', 'z', 0.0, NK['x0'] - E, NK['x1'] + E, NK['y0'] - 0.02, NK['y1'] + E, 1, mat('lino'))
        # timber threshold under the nook opening
        kit.box('nook_threshold', NO['x0'], NO['x1'], R['y1'] - 0.005, NK['y0'] + 0.01, -0.02, 0.008, mat('trim'), skip='-z', bevel=0.004, segs=1)
    with kit.props(td=0.3):
        wrect('ceiling_main', 'z', z1, x0 - E, x1 + E, y0 - E, y1 + E, -1, mat('ceiling'))
    with kit.props(td=0.25):
        wrect('ceiling_nook', 'z', z1, NK['x0'] - E, NK['x1'] + E, NK['y0'] - 0.03, NK['y1'] + E, -1, mat('plaster_nook'))

def beams_and_pipe():
    y0, y1, z1 = R['y0'] - E, R['y1'] + E, R['z1']
    # beam x positions keep clear of the ceiling spots / pendant cords (layout.LIGHTS) and the wall clock above the door
    with kit.props(td=0.45):
        for i, bx in enumerate((-2.30, -1.55, 1.55, 2.30)):
            kit.box('beam_%d' % i, bx - 0.075, bx + 0.075, y0, y1, z1 - 0.19, z1 + 0.01, mat('beam'), skip='+z -y +y', bevel=0.012, segs=2)
    # an old painted pipe along the -X side of the beam at x=-1.55, with strap clamps
    px, pz, pr = -1.55 - 0.075 - 0.032, z1 - 0.085, 0.024
    with kit.props(td=0.7):
        kit.tube('pipe', [(px, y0, pz), (px, y1, pz)], pr, mat('pipe'), segs=10, caps=False)
        for k, yy in enumerate((-2.1, -1.0, 0.1, 1.2)):
            kit.box('pipe_clamp_%d' % k, px - pr - 0.004, -1.55 - 0.075, yy - 0.012, yy + 0.012, pz - pr - 0.004, pz + pr + 0.004, mat('iron'), skip='+x')

def left_wall():
    x, y0, y1, z1 = R['x0'], R['y0'], R['y1'], R['z1']
    s = 1
    with kit.props(td=0.55):
        wainscot('lw', 'x', x, y0 - E, y1 + E, s)
        P = mat('plaster')
        wrect('lw_pl_a', 'x', x, y0 - E, WIN['y0'], 0.9, z1 + E, s, P)
        wrect('lw_pl_b', 'x', x, WIN['y1'], y1 + E, 0.9, z1 + E, s, P)
        wrect('lw_pl_c', 'x', x, WIN['y0'], WIN['y1'], 0.9, WIN['z0'], s, P)
        wrect('lw_pl_d', 'x', x, WIN['y0'], WIN['y1'], WIN['z1'], z1 + E, s, P)

def window():
    """deep splayed reveal, sloped sill, 3-pane steel frame, iron bars outside. Panes are left EMPTY (the page draws the sky)."""
    xi = WIN['x']                  # inner wall face
    xf, xfo, xo = xi - 0.145, xi - 0.19, xi - 0.26   # frame inner face, frame outer face, outer wall face
    yi0, yi1, zi0, zi1 = WIN['y0'], WIN['y1'], WIN['z0'], WIN['z1']
    yf0, yf1, zf0, zf1 = yi0 + 0.06, yi1 - 0.06, zi0 + 0.11, zi1 - 0.03     # frame opening
    P = mat('plaster')
    with kit.props(td=1.5):
        # splayed inner reveal (plaster)
        quad_n('win_rev_l', [(xi, yi0, zi0), (xi, yi0, zi1), (xf, yf0, zf1), (xf, yf0, zf0)], P, (0, 1, 0))
        quad_n('win_rev_r', [(xi, yi1, zi0), (xi, yi1, zi1), (xf, yf1, zf1), (xf, yf1, zf0)], P, (0, -1, 0))
        quad_n('win_rev_t', [(xi, yi0, zi1), (xi, yi1, zi1), (xf, yf1, zf1), (xf, yf0, zf1)], P, (0, 0, -1))
        # sloped painted sill board with a rounded lip into the room
        S = mat('sill')
        quad_n('win_sill', [(xi + 0.025, yi0 - 0.02, zi0), (xi + 0.025, yi1 + 0.02, zi0), (xf, yf1, zf0), (xf, yf0, zf0)], S, (0.4, 0, 1))
        kit.box('win_sill_lip', xi - 0.01, xi + 0.032, yi0 - 0.03, yi1 + 0.03, zi0 - 0.03, zi0 + 0.004, S, skip='-x', bevel=0.008, segs=2)
    with kit.props(td=0.9):
        C = mat('concrete')
        quad_n('win_out_l', [(xfo, yf0, zf0 - 0.05), (xfo, yf0, zf1), (xo, yf0, zf1), (xo, yf0, zf0 - 0.05)], C, (0, 1, 0))
        quad_n('win_out_r', [(xfo, yf1, zf0 - 0.05), (xfo, yf1, zf1), (xo, yf1, zf1), (xo, yf1, zf0 - 0.05)], C, (0, -1, 0))
        quad_n('win_out_t', [(xfo, yf0, zf1), (xfo, yf1, zf1), (xo, yf1, zf1), (xo, yf0, zf1)], C, (0, 0, -1))
        quad_n('win_out_s', [(xf + 0.005, yf0, zf0), (xf + 0.005, yf1, zf0), (xo, yf1, zf0 - 0.04), (xo, yf0, zf0 - 0.04)], C, (0, 0, 1))
    # steel frame: perimeter + 2 mullions (3 panes wide) + one slim glazing bar
    St = mat('steel')
    fw, bw = 0.036, 0.024
    with kit.props(td=2.0):
        kit.box('win_fr_b', xfo, xf, yf0, yf1, zf0, zf0 + fw, St, bevel=0.003, segs=1)
        kit.box('win_fr_t', xfo, xf, yf0, yf1, zf1 - fw, zf1, St, bevel=0.003, segs=1)
        kit.box('win_fr_l', xfo, xf, yf0, yf0 + fw, zf0, zf1, St, bevel=0.003, segs=1)
        kit.box('win_fr_r', xfo, xf, yf1 - fw, yf1, zf0, zf1, St, bevel=0.003, segs=1)
        for k in (1, 2):
            ym = yf0 + (yf1 - yf0) * k / 3.0
            kit.box('win_mul_%d' % k, xfo + 0.004, xf - 0.004, ym - bw / 2, ym + bw / 2, zf0 + fw, zf1 - fw, St, bevel=0.003, segs=1)
        zt = zf0 + fw + (zf1 - zf0 - 2 * fw) * 0.62
        kit.box('win_bar_h', xfo + 0.008, xf - 0.008, yf0 + fw, yf1 - fw, zt - 0.008, zt + 0.008, St, bevel=0.002, segs=1)
        # a small cam latch on the middle pane
        ym = (yf0 + yf1) / 2
        kit.box('win_latch_base', xf - 0.002, xf + 0.012, ym - 0.03, ym + 0.03, zf0 + fw, zf0 + fw + 0.022, St, bevel=0.002, segs=1)
        kit.box('win_latch_lever', xf + 0.008, xf + 0.018, ym - 0.008, ym + 0.065, zf0 + fw + 0.006, zf0 + fw + 0.016, St, bevel=0.002, segs=1)
    # iron bars outside the frame
    Ir = mat('iron')
    xb = (xfo + xo) / 2 - 0.005
    with kit.props(td=1.2):
        for k in range(1, 6):
            yb = yf0 + (yf1 - yf0) * k / 6.0
            kit.cyl('win_ironbar_%d' % k, xb, yb, zf0 - 0.06, zf1 + 0.01, 0.0115, Ir, segs=10, cap='')

def back_wall():
    y, x0, x1, z1 = R['y1'], R['x0'], R['x1'], R['z1']
    s = -1
    P = mat('plaster')
    a_w = 0.068          # architrave width
    dl, dr = DR['x0'] - a_w, DR['x1'] + a_w
    nl, nr = NO['x0'] - a_w, NO['x1'] + a_w
    with kit.props(td=0.75):
        # left of the stair door, between the door and the back bar
        wainscot('bw_a', 'y', y, x0 - E, dl, s)
        wrect('bw_pl_a', 'y', y, x0 - E, DR['x0'], 0.9, z1 + E, s, P)
        wainscot('bw_b', 'y', y, dr, CR['x0'], s)
        wrect('bw_pl_b', 'y', y, DR['x1'], CR['x0'], 0.9, z1 + E, s, P)
        wrect('bw_pl_door', 'y', y, DR['x0'], DR['x1'], DR['z1'], z1 + E, s, P)
    with kit.props(td=0.12):     # behind the credenza / shelving / speakers: plain and cheap
        wrect('bw_hidden', 'y', y, CR['x0'], CR['x1'], 0.0, 1.95, s, P)
    with kit.props(td=0.6):      # the strip above the shelving IS seen from the stool
        wrect('bw_top', 'y', y, CR['x0'], CR['x1'], 1.95, z1 + E, s, P)
    with kit.props(td=0.45):
        wainscot('bw_c', 'y', y, CR['x1'], nl, s)
        wrect('bw_pl_c', 'y', y, CR['x1'], NO['x0'], 0.9, z1 + E, s, P)
        wrect('bw_pl_nook', 'y', y, NO['x0'], NO['x1'], NO['z1'], z1 + E, s, P)
        wainscot('bw_d', 'y', y, nr, x1 + E, s)
        wrect('bw_pl_d', 'y', y, NO['x1'], x1 + E, 0.9, z1 + E, s, P)

def right_and_front_walls():
    with kit.props(td=0.3):
        wainscot('rw', 'x', R['x1'], R['y0'] - E, R['y1'] + E, -1)
        wrect('rw_pl', 'x', R['x1'], R['y0'] - E, R['y1'] + E, 0.9, R['z1'] + E, -1, mat('plaster'))
    with kit.props(td=0.15):
        wainscot('fw', 'y', R['y0'], R['x0'] - E, R['x1'] + E, 1)
        wrect('fw_pl', 'y', R['y0'], R['x0'] - E, R['x1'] + E, 0.9, R['z1'] + E, 1, mat('plaster'))

def opening_frame(tag, x0, x1, ztop, wall_y0, wall_y1, td=1.4):
    """timber linings in the wall thickness + architrave and plinth blocks on the room face"""
    Tv, Th = mat('trim_v'), mat('trim')
    a_w, a_t = 0.068, 0.022
    with kit.props(td=td):
        kit.box(tag + '_jamb_l', x0 - 0.02, x0, wall_y0, wall_y1, 0.0, ztop, Tv, skip='-x -z')
        kit.box(tag + '_jamb_r', x1, x1 + 0.02, wall_y0, wall_y1, 0.0, ztop, Tv, skip='+x -z')
        kit.box(tag + '_head', x0 - 0.02, x1 + 0.02, wall_y0, wall_y1, ztop, ztop + 0.02, Th, skip='+z')
        y0 = wall_y0 - a_t
        kit.box(tag + '_arch_l', x0 - a_w, x0, y0, wall_y0, 0.13, ztop, Tv, skip='+y', bevel=0.006, segs=2)
        kit.box(tag + '_arch_r', x1, x1 + a_w, y0, wall_y0, 0.13, ztop, Tv, skip='+y', bevel=0.006, segs=2)
        kit.box(tag + '_arch_t', x0 - a_w, x1 + a_w, y0, wall_y0, ztop, ztop + a_w, Th, skip='+y', bevel=0.006, segs=2)
        kit.box(tag + '_plinth_l', x0 - a_w - 0.006, x0 + 0.002, y0 - 0.006, wall_y0, 0.0, 0.15, Tv, skip='+y -z', bevel=0.004, segs=1)
        kit.box(tag + '_plinth_r', x1 - 0.002, x1 + a_w + 0.006, y0 - 0.006, wall_y0, 0.0, 0.15, Tv, skip='+y -z', bevel=0.004, segs=1)

# ====================================================================================================== the door
def door():
    hx, hy = DR['hinge_x'], DR['y']
    W = DR['x1'] - DR['x0']
    H = DR['z1']
    t = 0.04
    P, Br = mat('door_paint'), mat('brass')
    with kit.xform(T(hx, hy, 0.0) @ Rz(DOOR_AJAR)), kit.interactive('door', origin=(0, 0, 0), td=1.6):
        # local coords: hinge line on the z axis, leaf along +x, room face at y=0, stair face at y=t
        a, b = 0.006, W - 0.008
        st, tr, lr0, lr1, br_ = 0.115, 0.125, 0.86, 1.04, 0.225
        mx0, mx1 = W / 2 - 0.05, W / 2 + 0.05
        bev = 0.0045
        fr = dict(skip='+y', bevel=bev, segs=2)
        kit.box('dr_stile_h', a, a + st, 0, t, 0.02, H - 0.005, P, **fr)
        kit.box('dr_stile_l', b - st, b, 0, t, 0.02, H - 0.005, P, **fr)
        kit.box('dr_rail_t', a + st, b - st, 0, t, H - 0.005 - tr, H - 0.005, P, **fr)
        kit.box('dr_rail_m', a + st, b - st, 0, t, lr0, lr1, P, **fr)
        kit.box('dr_rail_b', a + st, b - st, 0, t, 0.02, br_, P, **fr)
        kit.box('dr_mun_lo', mx0, mx1, 0, t, br_, lr0, P, **fr)
        kit.box('dr_mun_hi', mx0, mx1, 0, t, lr1, H - 0.005 - tr, P, **fr)
        # four sunk panels with a raised field on the room side
        for k, (px0, px1, pz0, pz1) in enumerate(((a + st, mx0, br_, lr0), (mx1, b - st, br_, lr0),
                                                   (a + st, mx0, lr1, H - 0.005 - tr), (mx1, b - st, lr1, H - 0.005 - tr))):
            kit.box('dr_panel_%d' % k, px0 - 0.004, px1 + 0.004, 0.013, 0.027, pz0 - 0.004, pz1 + 0.004, P, only=('-y',))
            kit.box('dr_field_%d' % k, px0 + 0.035, px1 - 0.035, 0.006, 0.0135, pz0 + 0.035, pz1 - 0.035, P, skip='+y', bevel=0.007, segs=2)
        # the stairwell face: never seen, one flat cheap quad
        with kit.props(td=0.25):
            quad_n('dr_back', [(a, t, 0.02), (b, t, 0.02), (b, t, H - 0.005), (a, t, H - 0.005)], P, (0, 1, 0))
        # brass knob + rose on the room side, keyhole escutcheon
        kx, kz = b - 0.062, 0.95
        with kit.xform(T(kx, 0, kz) @ Rx(90)), kit.props(td=3.0):
            kit.lathe('dr_knob', [(0, 0.0), (0.030, 0.0), (0.031, 0.004), (0.026, 0.009), (0.010, 0.012), (0.008, 0.035),
                                  (0.014, 0.040), (0.023, 0.047), (0.027, 0.058), (0.026, 0.067), (0.019, 0.075),
                                  (0.009, 0.0795), (0, 0.0805)], Br, segs=20)
        with kit.props(td=2.5):
            kit.box('dr_escut', kx - 0.016, kx + 0.016, -0.003, 0.0, kz - 0.135, kz - 0.075, Br, skip='+y', bevel=0.003, segs=1)
            kit.box('dr_keyhole', kx - 0.0035, kx + 0.0035, -0.0034, -0.002, kz - 0.118, kz - 0.096, mat('void'), skip='+y')
            # hinge knuckles
            for hz in (0.24, 1.72):
                kit.cyl('dr_hinge_%d' % int(hz * 100), -0.002, -0.004, hz - 0.055, hz + 0.055, 0.0085, Br, segs=10)
        # the small brass plate on the upper muntin: only a downward arrow
        with kit.props(td=4.0):
            pc, pzc, pw, ph = W / 2, 1.43, 0.06, 0.09
            kit.box('dr_plate', pc - pw / 2, pc + pw / 2, -0.0022, 0.0, pzc - ph / 2, pzc + ph / 2, Br, skip='+y', bevel=0.0012, segs=1)
            kit.quad('dr_plate_face', [(pc - pw / 2 + 0.002, -0.0024, pzc - ph / 2 + 0.002), (pc + pw / 2 - 0.002, -0.0024, pzc - ph / 2 + 0.002),
                                       (pc + pw / 2 - 0.002, -0.0024, pzc + ph / 2 - 0.002), (pc - pw / 2 + 0.002, -0.0024, pzc + ph / 2 - 0.002)], mat('plate'))

def _knob_world():
    W = DR['x1'] - DR['x0']
    m = Matrix.Translation((DR['hinge_x'], DR['y'], 0)) @ Matrix.Rotation(math.radians(DOOR_AJAR), 4, 'Z')
    return [tuple(m @ Vector((W - 0.008 - 0.062, -0.06, 0.95)))]
KNOB_WORLD = _knob_world()

# ====================================================================================================== the stairwell
X0, X1 = ST['x0'], ST['x1']
TOPY = ST['top_y']; RUN = ST['step_run']; RISE = ST['step_rise']
NSTEP = 8                                  # regular steps; then a landing where the stair turns left
LAND_Z = -(NSTEP + 1) * RISE                # -1.8
LAND_Y = TOPY + NSTEP * RUN                 # 3.95
TURN_Y0, TURN_Y1, TURN_Z1 = 3.99, 4.46, -0.15   # opening in the left wall at the bottom
SY0, SY1 = DR['y'] + 0.1 - 0.01, ST['y1']   # stairwell walls run from the back of the door wall to the end wall

def spring(y):
    """height of the vault's springing line: flat just behind the door, then falling with the stair"""
    return min(2.2, 2.2 - 0.8 * (y - 1.775)) if y > 1.775 else 2.2

def step_mesh(name, yf, yb, zt, nosing=True, wx=(X0 - E, X1 + E)):
    import bmesh
    xs = [wx[0] + (wx[1] - wx[0]) * k / 8.0 for k in range(9)]
    bm = bmesh.new(); cols = []
    for x in xs:
        w = max(0.0, 1.0 - ((x + 2.78) / 0.40) ** 2)            # wear across the tread (people keep near the rail side)
        pr = [(yf - 0.004, zt), (yf + 0.07, zt - 0.003 * w), (yb - 0.09, zt - 0.014 * w)]
        if nosing:
            r = 0.010 + 0.028 * w; e = 0.022 * w
            pr += [(yb - e - r, zt - 0.010 * w), (yb - e - r * 0.35, zt - 0.006 * w - r * 0.3),
                   (yb - e * 0.5, zt - r - 0.004 * w), (yb, zt - r - 0.03), (yb, zt - RISE - 0.004)]
        else:
            pr += [(yb, zt - 0.006 * w)]
        cols.append([bm.verts.new((x, py, pz)) for (py, pz) in pr])
    for i in range(len(xs) - 1):
        A, B = cols[i], cols[i + 1]
        for k in range(len(A) - 1):
            bm.faces.new((A[k], B[k], B[k + 1], A[k + 1]))
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < -0.1 or f.normal.y < -0.5: f.normal_flip()
    return kit.finish(name, bm, mat('steps'), smooth=True, sharp=40)

def stairwell():
    St = mat('stone')
    ys = [SY0, 1.775, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, TURN_Y0, 4.22, TURN_Y1, SY1 + E]
    zs = [-2.6, -2.2, LAND_Z, -1.45, -1.15, -0.85, -0.5, TURN_Z1, 0.2, 0.5, 0.8, 1.1, 1.4, 1.7, 2.0, 2.4]

    def wall(name, xw, sgn, opening):
        def edge(i, j):
            return opening and (TURN_Y0 - 1e-6 <= ys[i] <= TURN_Y1 + 1e-6) and (LAND_Z - 1e-6 <= zs[j] <= TURN_Z1 + 1e-6)
        def pos(i, j):
            y = ys[i]; top = spring(y) + 0.03
            z = min(zs[j], top)
            d = 0.0 if (edge(i, j) or i == 0) else 0.004 + 0.024 * wob(y * 1.1, z * 0.9 + xw)
            return (xw + sgn * d, y, z)
        def skip(i, j):
            if not opening: return False
            yc, zc = (ys[i] + ys[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
            return TURN_Y0 < yc < TURN_Y1 and LAND_Z < zc < TURN_Z1
        ob = grid_mesh(name, ys, zs, pos, St, skipf=skip)
        # make normals face into the stairwell
        me = ob.data
        if me.polygons and me.polygons[0].normal.x * sgn < 0:
            me.flip_normals()
        return ob

    with kit.props(td=0.6):
        wall('stair_wall_l', X0, 1, True)
        wall('stair_wall_r', X1, -1, False)
        # the vault: a shallow segmental barrel following the stair down
        xs = [X0 - E + (X1 - X0 + 2 * E) * k / 6.0 for k in range(7)]
        def vpos(i, k):
            y = ys[i]; tt = k / 6.0
            return (xs[k], y, spring(y) + 0.16 * math.sin(math.pi * tt))
        ob = grid_mesh('stair_vault', ys, xs, vpos, mat('vault'))
        if ob.data.polygons and ob.data.polygons[0].normal.z > 0: ob.data.flip_normals()
    with kit.props(td=0.5):
        wrect('stair_end', 'y', SY1, X0 - E, X1 + E, -2.6, spring(SY1) + 0.2, -1, St)
        # back of the door wall, seen only from inside the stairwell
        yb = DR['y'] + 0.1
        wrect('stair_back_l', 'y', yb, X0 - E, DR['x0'], -0.3, 2.42, 1, St)
        wrect('stair_back_r', 'y', yb, DR['x1'], X1 + E, -0.3, 2.42, 1, St)
        wrect('stair_back_t', 'y', yb, DR['x0'], DR['x1'], DR['z1'], 2.42, 1, St)
    # steps: worn landing, 8 dished steps, bottom landing
    with kit.props(td=1.4):
        kit.box('stair_threshold', DR['x0'] - 0.02, DR['x1'] + 0.02, DR['y'] - 0.006, DR['y'] + 0.12, -0.06, 0.014, mat('steps'), skip='-z', bevel=0.006, segs=2)
        step_mesh('stair_landing', DR['y'] + 0.11, TOPY, 0.0)
    with kit.props(td=1.0):
        for i in range(NSTEP):
            yf = TOPY + i * RUN
            step_mesh('stair_step_%d' % i, yf, yf + RUN, -(i + 1) * RISE)
        step_mesh('stair_bottom', LAND_Y, SY1 + E, LAND_Z, nosing=False)
    # around the corner: a short passage turning left (-X), stepping further down; never seen directly
    with kit.props(td=0.15):
        px1 = X0 - 1.05
        wrect('turn_wall_a', 'y', TURN_Y0, px1, X0, -2.8, TURN_Z1, 1, St)
        wrect('turn_wall_b', 'y', TURN_Y1, px1, X0, -2.8, TURN_Z1, -1, St)
        wrect('turn_ceiling', 'z', TURN_Z1, px1, X0 + 0.01, TURN_Y0, TURN_Y1, -1, St)
        wrect('turn_end', 'x', px1, TURN_Y0, TURN_Y1, -2.8, TURN_Z1, 1, St)
        Sp = mat('steps')
        wrect('turn_floor0', 'z', LAND_Z, X0 - 0.25, X0 + 0.01, TURN_Y0, TURN_Y1, 1, Sp)
        for k in range(3):
            xa, xb = X0 - 0.25 - (k + 1) * RUN, X0 - 0.25 - k * RUN
            zt = LAND_Z - (k + 1) * RISE
            wrect('turn_riser%d' % k, 'x', xb, TURN_Y0, TURN_Y1, zt, zt + RISE, -1, Sp)
            wrect('turn_tread%d' % k, 'z', zt, max(xa, px1), xb, TURN_Y0, TURN_Y1, 1, Sp)
    # thin iron handrail on the left wall, on two brackets, stopping short of the turn
    Rl = mat('rail')
    def rz(y): return 2.44 - 0.8 * y + 0.0
    xr = X0 + 0.065
    with kit.props(td=1.0):
        ya, yb2 = 2.42, 3.82
        kit.tube('stair_rail', [(X0 + 0.01, ya - 0.06, rz(ya - 0.06) - 0.03), (xr, ya, rz(ya)), (xr, yb2, rz(yb2)),
                                (X0 + 0.01, yb2 + 0.06, rz(yb2 + 0.06) - 0.03)], 0.0155, Rl, segs=10)
        for k, yy in enumerate((2.75, 3.45)):
            zr = rz(yy)
            kit.tube('stair_rail_br%d' % k, [(X0 - 0.01, yy, zr - 0.075), (xr - 0.012, yy, zr - 0.07), (xr, yy, zr - 0.014)], 0.0055, Rl, segs=6)
            kit.cyl('stair_rail_rose%d' % k, X0 + 0.0, yy, zr - 0.09, zr - 0.06, 0.018, Rl, segs=10)

# ====================================================================================================== the nook
def nook():
    x0, x1, y0, y1, z1 = NK['x0'], NK['x1'], NK['y0'], NK['y1'], R['z1']
    TL, Pn = mat('wall_tiles'), mat('plaster_nook')
    th = 1.40
    nw = dict(y0=2.9, y1=3.3, z0=1.5, z1=1.9)
    with kit.props(td=0.6):
        # left wall (x0, faces +x): plaster all the way down, small skirting
        wrect('nk_wall_l', 'x', x0, y0 - 0.1, y1 + E, 0.0, z1 + E, 1, Pn)
        kit.box('nk_skirt_l', x0, x0 + 0.018, y0 - 0.1, y1, 0.0, 0.09, mat('cream_paint'), skip='-x -z', bevel=0.003, segs=1)
        # back wall (y1, faces -y): tiles to 1.4 m, plaster above
        wrect('nk_wall_b_tiles', 'y', y1, x0 - E, x1 + E, 0.0, th, -1, TL)
        wrect('nk_wall_b_pl', 'y', y1, x0 - E, x1 + E, th, z1 + E, -1, Pn)
        # right wall (x1, faces -x): tiles to 1.4 m, plaster above around the little window
        wrect('nk_wall_r_tiles', 'x', x1, y0 - 0.1, y1 + E, 0.0, th, -1, TL)
        wrect('nk_wall_r_pl_a', 'x', x1, y0 - 0.1, nw['y0'], th, z1 + E, -1, Pn)
        wrect('nk_wall_r_pl_b', 'x', x1, nw['y1'], y1 + E, th, z1 + E, -1, Pn)
        wrect('nk_wall_r_pl_c', 'x', x1, nw['y0'], nw['y1'], th, nw['z0'], -1, Pn)
        wrect('nk_wall_r_pl_d', 'x', x1, nw['y0'], nw['y1'], nw['z1'], z1 + E, -1, Pn)
        # bullnose capping row on top of the tiles
        kit.box('nk_cap_b', x0, x1, y1 - 0.014, y1, th - 0.012, th + 0.01, TL, skip='+y', bevel=0.006, segs=2)
        kit.box('nk_cap_r', x1 - 0.014, x1, y0 - 0.1, y1, th - 0.012, th + 0.01, TL, skip='+x', bevel=0.006, segs=2)
    # the small high frosted window
    rd = 0.13
    xo = x1 + rd
    with kit.props(td=1.2):
        quad_n('nkw_rev_l', [(x1, nw['y0'], nw['z0']), (x1, nw['y0'], nw['z1']), (xo, nw['y0'], nw['z1']), (xo, nw['y0'], nw['z0'])], Pn, (0, 1, 0))
        quad_n('nkw_rev_r', [(x1, nw['y1'], nw['z0']), (x1, nw['y1'], nw['z1']), (xo, nw['y1'], nw['z1']), (xo, nw['y1'], nw['z0'])], Pn, (0, -1, 0))
        quad_n('nkw_rev_t', [(x1, nw['y0'], nw['z1']), (x1, nw['y1'], nw['z1']), (xo, nw['y1'], nw['z1']), (xo, nw['y0'], nw['z1'])], Pn, (0, 0, -1))
        quad_n('nkw_rev_s', [(x1 - 0.03, nw['y0'] - 0.02, nw['z0']), (x1 - 0.03, nw['y1'] + 0.02, nw['z0']), (xo, nw['y1'], nw['z0']), (xo, nw['y0'], nw['z0'])], mat('cream_paint'), (0, 0, 1))
        Cp = mat('cream_paint'); fx0, fx1 = x1 + 0.07, x1 + 0.11; f = 0.035
        kit.box('nkw_fr_b', fx0, fx1, nw['y0'], nw['y1'], nw['z0'], nw['z0'] + f, Cp, bevel=0.003, segs=1)
        kit.box('nkw_fr_t', fx0, fx1, nw['y0'], nw['y1'], nw['z1'] - f, nw['z1'], Cp, bevel=0.003, segs=1)
        kit.box('nkw_fr_l', fx0, fx1, nw['y0'], nw['y0'] + f, nw['z0'], nw['z1'], Cp, bevel=0.003, segs=1)
        kit.box('nkw_fr_r', fx0, fx1, nw['y1'] - f, nw['y1'], nw['z0'], nw['z1'], Cp, bevel=0.003, segs=1)
        kit.box('nkw_pane', fx0 + 0.015, fx0 + 0.02, nw['y0'] + f - 0.005, nw['y1'] - f + 0.005, nw['z0'] + f - 0.005, nw['z1'] - f + 0.005, mat('frosted'))
        kit.box('nkw_lip', x1 - 0.035, x1 + 0.01, nw['y0'] - 0.03, nw['y1'] + 0.03, nw['z0'] - 0.025, nw['z0'] + 0.003, Cp, skip='+x', bevel=0.006, segs=2)
    # plain timber frame for the wide opening
    opening_frame('nko', NO['x0'], NO['x1'], NO['z1'], R['y1'], R['y1'] + 0.1, td=0.9)

# ====================================================================================================== details
def details():
    y = R['y1']
    sx = (DR['x1'] + 0.068 + CR['x0']) / 2          # centre of the strip between the door architrave and the back bar
    with kit.props(td=2.0):
        # bakelite toggle switch on a round wooden pattress
        with kit.xform(T(sx, y, 1.30) @ Rx(90)):
            kit.lathe('sw_pattress', [(0, 0.014), (0.040, 0.014), (0.044, 0.010), (0.045, 0.0)], mat('trim'), segs=20)
            kit.lathe('sw_dome', [(0, 0.034), (0.012, 0.033), (0.024, 0.029), (0.031, 0.021), (0.033, 0.014)], mat('bakelite'), segs=20)
            kit.tube('sw_lever', [(0, 0, 0.032), (0, -0.006, 0.046)], 0.0045, mat('bakelite'), segs=8)
        # fuse box above it, its paper card
        fb = dict(x0=sx - 0.09, x1=sx + 0.09, z0=1.60, z1=1.88)
        Fb = mat('fusebox')
        kit.box('fuse_box', fb['x0'], fb['x1'], y - 0.075, y, fb['z0'], fb['z1'], Fb, skip='+y', bevel=0.005, segs=2)
        kit.box('fuse_door', fb['x0'] + 0.008, fb['x1'] - 0.008, y - 0.079, y - 0.074, fb['z0'] + 0.008, fb['z1'] - 0.008, Fb, skip='+y', bevel=0.002, segs=1)
        kit.cyl('fuse_latch', fb['x1'] - 0.024, y - 0.079, fb['z0'] + 0.13, fb['z0'] + 0.15, 0.006, mat('brass'), segs=8)
        lx0, lx1, lz0 = sx - 0.055, sx + 0.035, fb['z1'] - 0.075
        kit.quad('fuse_card', [(lx0, y - 0.0795, lz0), (lx1, y - 0.0795, lz0), (lx1, y - 0.0795, lz0 + 0.05625), (lx0, y - 0.0795, lz0 + 0.05625)], mat('fuse_label'))
    with kit.props(td=0.8):
        Cd = mat('conduit'); cy = y - 0.011
        kit.tube('cond_sw', [(sx, cy, 1.335), (sx, cy, fb['z0'])], 0.0095, Cd, segs=8, caps=False)
        kit.tube('cond_up', [(sx, cy, fb['z1']), (sx, cy, R['z1'] + 0.01)], 0.0095, Cd, segs=8, caps=False)
        for k, zz in enumerate((1.48, 2.05, 2.30)):
            kit.box('cond_saddle_%d' % k, sx - 0.016, sx + 0.016, y - 0.024, y, zz - 0.008, zz + 0.008, Cd, skip='+y')
        # a second conduit: from the ceiling down the corner to the switch box of the stair (light for the stair, long dead)
        cx2 = R['x0'] + 0.015
        kit.tube('cond_corner', [(cx2, y - 0.015, R['z1'] + 0.01), (cx2, y - 0.015, 1.62)], 0.009, Cd, segs=8, caps=False)
        kit.box('cond_corner_box', cx2 - 0.006, cx2 + 0.05, y - 0.06, y, 1.53, 1.62, Cd, skip='+y -x', bevel=0.004, segs=1)
    # surface-mounted louvred grille in the left wall beside the window head (air brick to the light well)
    xv = R['x0']; vy0, vy1, vz0, vz1 = 0.06, 0.30, 2.26, 2.38
    Vt = mat('vent')
    with kit.props(td=1.2):
        kit.box('vent_w_back', xv, xv + 0.002, vy0, vy1, vz0, vz1, mat('void'), only=('+x',))
        for nm, (a0, a1, b0, b1) in dict(t=(vy0 - 0.012, vy1 + 0.012, vz1, vz1 + 0.014), b=(vy0 - 0.012, vy1 + 0.012, vz0 - 0.014, vz0),
                                         l=(vy0 - 0.012, vy0, vz0, vz1), r=(vy1, vy1 + 0.012, vz0, vz1)).items():
            kit.box('vent_w_' + nm, xv, xv + 0.016, a0, a1, b0, b1, Vt, skip='-x', bevel=0.002, segs=1)
        for k in range(4):
            zc = vz0 + (vz1 - vz0) * (k + 0.5) / 4
            with kit.xform(T(xv + 0.009, (vy0 + vy1) / 2, zc) @ Ry(-35)):
                kit.box('vent_w_slat%d' % k, -0.012, 0.012, -(vy1 - vy0) / 2, (vy1 - vy0) / 2, -0.0018, 0.0018, Vt)
    # ceiling grille near the back-left corner
    cx0, cx1, cy0, cy1, z1 = -3.15, -2.87, 0.98, 1.16, R['z1']
    with kit.props(td=0.9):
        kit.box('vent_c_back', cx0, cx1, cy0, cy1, z1 - 0.002, z1, mat('void'), only=('-z',))
        for nm, (a0, a1, b0, b1) in dict(x0=(cx0 - 0.014, cx0, cy0 - 0.014, cy1 + 0.014), x1=(cx1, cx1 + 0.014, cy0 - 0.014, cy1 + 0.014),
                                         y0=(cx0, cx1, cy0 - 0.014, cy0), y1=(cx0, cx1, cy1, cy1 + 0.014)).items():
            kit.box('vent_c_' + nm, a0, a1, b0, b1, z1 - 0.016, z1, Vt, skip='+z', bevel=0.002, segs=1)
        for k in range(6):
            xc = cx0 + (cx1 - cx0) * (k + 0.5) / 6
            with kit.xform(T(xc, (cy0 + cy1) / 2, z1 - 0.008) @ Ry(40)):
                kit.box('vent_c_slat%d' % k, -0.011, 0.011, -(cy1 - cy0) / 2, (cy1 - cy0) / 2, -0.0016, 0.0016, Vt)

# ====================================================================================================== build
def build():
    _MAT.clear()
    floors_and_ceilings()
    beams_and_pipe()
    left_wall()
    window()
    back_wall()
    right_and_front_walls()
    opening_frame('sdr', DR['x0'], DR['x1'], DR['z1'], R['y1'], R['y1'] + 0.1, td=1.4)
    door()
    stairwell()
    nook()
    details()

LIGHTS = []
