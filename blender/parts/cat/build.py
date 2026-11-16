"""CAT part: the cat that owns DEAN'S, in three poses (cat_sleep / cat_sit / cat_watch), its wool blanket on the right
speaker and its bowl by the stair door.

Modelling: each pose is an implicit surface (signed distance field) made of ellipsoids and round cones placed along a
hand-specified spine, legs, head and tail, smooth-unioned, polygonised with marching cubes (skimage), Taubin-smoothed
and decimated.  Ears are thin curved shells, eyes small spheres.  The fur colour is driven by a per-vertex attribute
`cat_fur` = (stripe phase, dorsal-ness, cream amount, darkness) computed from the same primitives, read by a
procedural tabby material.
"""
import math
import numpy as np
import bpy, bmesh
from barkit import kit, mats, layout
from barkit.kit import T, Rz

GRID = 0.004          # marching-cubes cell (m)


# ============================================================================ small linear algebra (numpy, 3x3 / 4x4)
def nrm(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)

def rx(d):
    a = math.radians(d); c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

def ry(d):
    a = math.radians(d); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def rz(d):
    a = math.radians(d); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def frame(fwd, up):
    """columns (X, Y, Z) of a cat-style local frame whose -Y is `fwd` and Z is (close to) `up`"""
    y = -nrm(fwd); z = np.asarray(up, float); z = nrm(z - y * z.dot(y)); x = np.cross(y, z)
    return np.stack([x, y, z], 1)

def axis_frame(t, u):
    """columns (side, t, up) for an ellipsoid whose 2nd radius runs along t"""
    t = nrm(t); u = np.asarray(u, float); u = nrm(u - t * u.dot(t)); s = np.cross(t, u)
    return np.stack([s, t, u], 1)

def catmull(P, n):
    """Catmull-Rom through rows of P (N, D) -> ((N-1)*n+1, D)"""
    P = np.asarray(P, float); Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for j in range(n):
            t = j / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1]); return np.array(out)

def smin(a, b, k):
    if k <= 0: return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k * 0.25

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


# ============================================================================ implicit primitives
class Prim:
    """kind 'ell' (c, R, r) | 'rc' (a, b, ra, rb) | 'rbox' (c, R, half, rr).  Fur attributes:
    s0/sdir/freq -> stripe phase = (s0 + (p-ref).sdir) * freq ;  u -> dorsal direction ;  cream / creamv (ventral cream) ; dark"""
    def __init__(s, kind, k=0.01, sub=False, s0=0.0, sdir=None, freq=0.0, u=None, cream=0.0, creamv=0.0, dark=0.0, az=0, azax=None, **g):
        s.kind, s.k, s.sub, s.az = kind, k, sub, az
        s.azax = None if azax is None else nrm(azax)
        s.__dict__.update(g)
        s.s0, s.freq, s.cream, s.creamv, s.dark = s0, freq, cream, creamv, dark
        s.u = None if u is None else nrm(u)
        if kind == 'ell':
            s.c = np.asarray(s.c, float); s.r = np.asarray(s.r, float)
            s.R = np.eye(3) if s.R is None else np.asarray(s.R, float)
            ext = np.abs(s.R) @ s.r
            s.lo, s.hi = s.c - ext, s.c + ext
            s.ref = s.c; s.ax = s.R[:, 1]
        elif kind == 'rc':
            s.a = np.asarray(s.a, float); s.b = np.asarray(s.b, float)
            s.lo = np.minimum(s.a - s.ra, s.b - s.rb); s.hi = np.maximum(s.a + s.ra, s.b + s.rb)
            s.ref = s.a; s.ax = nrm(s.b - s.a)
        elif kind == 'rbox':
            s.c = np.asarray(s.c, float); s.half = np.asarray(s.half, float)
            s.R = np.eye(3) if s.R is None else np.asarray(s.R, float)
            ext = np.abs(s.R) @ s.half
            s.lo, s.hi = s.c - ext, s.c + ext
            s.ref = s.c; s.ax = s.R[:, 1]
        s.sdir = s.ax if sdir is None else nrm(sdir)

    def dist(s, P):
        if s.kind == 'ell':
            q = (P - s.c) @ s.R
            k0 = np.linalg.norm(q / s.r, axis=-1); k1 = np.linalg.norm(q / (s.r * s.r), axis=-1)
            return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
        if s.kind == 'rbox':
            q = np.abs((P - s.c) @ s.R) - s.half + s.rr
            return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - s.rr
        a, b, r1, r2 = s.a, s.b, s.ra, s.rb
        ba = b - a; l2 = ba.dot(ba); rr = r1 - r2; a2 = l2 - rr * rr; il2 = 1.0 / l2
        pa = P - a; y = pa @ ba; z = y - l2
        x2 = np.sum((pa * l2 - y[..., None] * ba) ** 2, -1); y2 = y * y * l2; z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        d3 = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
        d1 = np.sqrt(x2 + z2) * il2 - r2
        d2 = np.sqrt(x2 + y2) * il2 - r1
        return np.where(np.sign(z) * a2 * z2 > k, d1, np.where(np.sign(y) * a2 * y2 < k, d2, d3))

    def axis_point(s, P):
        if s.kind == 'rc':
            ba = s.b - s.a; t = np.clip((P - s.a) @ ba / ba.dot(ba), 0, 1)
            return s.a + t[:, None] * ba
        d = P - s.c
        return s.c + (d @ s.ax)[:, None] * s.ax

    def attrs(s, P):
        ph = (s.s0 + (P - s.ref) @ s.sdir) * s.freq
        if s.az:                    # stripes running ALONG the axis (forehead lines, nape): phase from the angle round it
            ax = s.ax if s.azax is None else s.azax
            ref = s.axis_point(P) if s.azax is None else s.ref + ((P - s.ref) @ ax)[:, None] * ax
            v = P - ref; e1 = s.u - ax * (s.u @ ax); e1 /= np.linalg.norm(e1); e2 = np.cross(ax, e1)
            ph = np.arctan2(v @ e2, v @ e1) / (2 * math.pi) * s.az
        if s.u is not None:
            v = P - s.axis_point(P); v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)
            dor = v @ s.u
        else:
            dor = np.zeros(len(P))
        cream = s.cream + s.creamv * smoothstep(0.05, -0.55, dor)
        dark = np.full(len(P), float(s.dark))
        if getattr(s, 'dark1', None) is not None and s.kind == 'rc':
            ba = s.b - s.a; t = np.clip((P - s.a) @ ba / ba.dot(ba), 0, 1)
            dark = s.dark + (s.dark1 - s.dark) * t
        return np.stack([ph, dor, cream, dark], 1)


class Model:
    def __init__(s, lumps=0.0016):
        s.prims = []; s.floor = None; s.lumps = lumps

    def add(s, p): s.prims.append(p); return p
    def ell(s, c, r, R=None, k=0.01, **kw): return s.add(Prim('ell', k=k, c=c, r=r, R=R, **kw))
    def rc(s, a, b, ra, rb, k=0.008, **kw): return s.add(Prim('rc', k=k, a=a, b=b, ra=ra, rb=rb, **kw))
    def rbox(s, c, half, rr, R=None, k=0.0, **kw): return s.add(Prim('rbox', k=k, c=c, half=half, rr=rr, R=R, **kw))

    def tube(s, pts, radii, n=4, k=0.004, freq=0.0, dark0=0.0, dark1=0.0, **kw):
        """smooth tapered tube through control points (Catmull-Rom) as a chain of round cones; stripes run round it"""
        D = catmull(np.column_stack([pts, radii]), n); P, R = D[:, :3], D[:, 3]
        L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]); tot = L[-1]
        for i in range(len(P) - 1):
            f0, f1 = L[i] / tot, L[i + 1] / tot
            s.rc(P[i], P[i + 1], R[i], R[i + 1], k=k, s0=L[i], freq=freq,
                 dark=dark0 + (dark1 - dark0) * f0, dark1=dark0 + (dark1 - dark0) * f1, **kw)
        return P, R

    def sweep(s, pts, W, H, ups, step=0.012, k=0.012, freq=0.0, Lmin=0.03, **kw):
        """torso: chain of ellipsoids (half-width W, half-depth H across the spine) along a Catmull-Rom spine"""
        P = np.asarray(pts, float)
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1).sum()
        n = max(2, int(round(seg / step / (len(P) - 1))))
        D = catmull(np.column_stack([P, W, H, ups]), n)
        C, Ws, Hs, U = D[:, :3], D[:, 3], D[:, 4], D[:, 5:8]
        L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))])
        for i in range(len(C)):
            t = C[min(i + 1, len(C) - 1)] - C[max(i - 1, 0)]
            R = axis_frame(t, U[i])
            s.ell(C[i], (Ws[i], max(Lmin, 0.6 * min(Ws[i], Hs[i])), Hs[i]), R, k=k, s0=L[i], freq=freq, u=R[:, 2], **kw)
        return C

    # ---------------------------------------------------------------- evaluation
    def field(s, P, prims=None):
        d = np.full(P.shape[:-1], 1.0)
        for p in (prims or s.prims):
            di = p.dist(P)
            d = -smin(-d, di, p.k) if p.sub else smin(d, di, p.k)
        if s.floor is not None: d = np.maximum(d, s.floor - P[..., 2])
        return d

    def grid(s, h=GRID):
        lo = np.min([p.lo for p in s.prims if not p.sub], 0) - 0.02
        hi = np.max([p.hi for p in s.prims if not p.sub], 0) + 0.02
        if s.floor is not None: lo[2] = max(lo[2], s.floor - 2 * h)
        n = np.ceil((hi - lo) / h).astype(int) + 1
        xs = [lo[i] + h * np.arange(n[i]) for i in range(3)]
        D = np.full(n, 1.0, np.float64)
        for p in s.prims:
            m = p.k + 3 * h
            i0 = [max(0, int((p.lo[i] - m - lo[i]) / h)) for i in range(3)]
            i1 = [min(n[i], int((p.hi[i] + m - lo[i]) / h) + 2) for i in range(3)]
            if any(i1[i] <= i0[i] for i in range(3)): continue
            X, Y, Z = np.meshgrid(xs[0][i0[0]:i1[0]], xs[1][i0[1]:i1[1]], xs[2][i0[2]:i1[2]], indexing='ij')
            di = p.dist(np.stack([X, Y, Z], -1))
            sl = (slice(i0[0], i1[0]), slice(i0[1], i1[1]), slice(i0[2], i1[2]))
            D[sl] = -smin(-D[sl], di, p.k) if p.sub else smin(D[sl], di, p.k)
        if s.lumps:                       # a slightly scruffy coat: low, irregular lumps (fixed, no randomness)
            X, Y, Z = np.meshgrid(*xs, indexing='ij')
            nz = (np.sin(X * 173 + Y * 61 + 1.3) * np.sin(Y * 151 - Z * 97 + 0.4) + np.sin(Z * 211 + X * 83 + 2.1) * np.sin(X * 127 - Y * 191)
                  + 0.6 * np.sin(X * 311 + Z * 263 + Y * 59))
            D = D + s.lumps * nz / 2.6
        if s.floor is not None:
            D = np.maximum(D, s.floor - xs[2][None, None, :])
        return D, lo, h

    def surface_point(s, origin, direction, prims=None, inset=0.0):
        """march from origin (inside) along direction to the surface of the union of `prims`"""
        o = np.asarray(origin, float); dv = nrm(direction)
        ts = np.linspace(0, 0.2, 401); P = o + ts[:, None] * dv
        d = s.field(P, prims); i = int(np.argmax(d > 0))
        return o + dv * (ts[i] - inset)

    def attrs(s, P):
        A = np.stack([p.attrs(P) for p in s.prims if not p.sub], 0)                  # (np, N, 4)
        D = np.stack([p.dist(P) for p in s.prims if not p.sub], 0)                   # (np, N)
        w = np.exp(-(D - D.min(0)) / 0.006)
        return (A * w[..., None]).sum(0) / w.sum(0)[:, None]

    def skin(s, name, tris, smooth_it=6):
        from skimage.measure import marching_cubes
        D, lo, h = s.grid()
        V, F, _, _ = marching_cubes(-D.astype(np.float32), 0.0, spacing=(h, h, h))
        V = V.astype(np.float64) + lo
        V = taubin(V, F, smooth_it)
        return decimate(name, V, F, tris)


def taubin(V, F, it=6, lam=0.5, mu=-0.53):
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    deg = (np.bincount(E[:, 0], minlength=len(V)) + np.bincount(E[:, 1], minlength=len(V))).astype(float)[:, None]
    for _ in range(it):
        for f in (lam, mu):
            S = np.zeros_like(V)
            np.add.at(S, E[:, 0], V[E[:, 1]]); np.add.at(S, E[:, 1], V[E[:, 0]])
            V = V + f * (S / np.maximum(deg, 1) - V)
    return V


def decimate(name, V, F, tris):
    me = bpy.data.meshes.new(name + '_hi')
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.astype(np.float32).ravel())
    me.loops.add(F.size); me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel())
    me.polygons.add(len(F)); me.polygons.foreach_set('loop_start', np.arange(0, F.size, 3, dtype=np.int32))
    me.update(); me.validate()
    ob = bpy.data.objects.new(name + '_hi', me); bpy.context.scene.collection.objects.link(ob)
    md = ob.modifiers.new('dec', 'DECIMATE'); md.ratio = min(1.0, tris / max(1, len(F))); md.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); me2.name = name
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.meshes.remove(me)
    bpy.context.view_layer.update()
    return me2


def set_fur(me, A):
    a = me.color_attributes.new('cat_fur', 'FLOAT_COLOR', 'POINT')
    a.data.foreach_set('color', A.astype(np.float32).ravel())


def mesh_verts(me):
    V = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get('co', V); return V.reshape(-1, 3)


def new_object(me, mat_list):
    for m in mat_list: me.materials.append(m)
    ob = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def from_data(name, V, F, mi=None):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in V]
    for i, f in enumerate(F):
        try:
            face = bm.faces.new([vs[j] for j in f])
            if mi is not None: face.material_index = mi[i]
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me


# ============================================================================ head, ears, eyes
FUR_BODY = 1 / 0.030      # stripe frequencies (cycles per metre)
FUR_LEG = 1 / 0.019
FUR_TAIL = 1 / 0.028
FUR_HEAD = 1 / 0.010

def head(m, c, R, scale=1.1):
    """adds the head prims; c = cranium centre, R = head frame (cols X, Y(-forward), Z(up)). returns dict of anchors"""
    def P(x, y, z): return c + R @ (np.array([x, y, z]) * scale)
    up = R[:, 2]; S = scale; hp = []
    hp.append(m.ell(P(0, 0.006, 0.008), np.array([0.042, 0.046, 0.038]) * S, R, k=0.012, az=15, azax=R @ np.array([0, 0.5, -0.87]), u=up))
    for sx in (-1, 1):
        hp.append(m.ell(P(sx * 0.026, -0.013, -0.007), np.array([0.027, 0.029, 0.024]) * S, R @ rz(-sx * 12), k=0.016,
                        sdir=up, freq=1 / 0.020, u=up, creamv=0.55))
        hp.append(m.ell(P(sx * 0.0100, -0.044, -0.015), np.array([0.0130, 0.0110, 0.0108]) * S, R, k=0.008, cream=0.7, u=up, creamv=0.3))
    hp.append(m.ell(P(0, -0.028, 0.012), np.array([0.028, 0.022, 0.020]) * S, R @ rx(-18), k=0.012, az=15, azax=R @ np.array([0, 0.5, -0.87]), u=up))
    hp.append(m.ell(P(0, -0.040, 0.002), np.array([0.013, 0.018, 0.012]) * S, R @ rx(-20), k=0.008, u=up, dark=0.15))
    hp.append(m.ell(P(0, -0.0545, -0.005), np.array([0.0072, 0.0055, 0.0055]) * S, R, k=0.004, u=up, dark=0.35))
    hp.append(m.ell(P(0, -0.036, -0.026), np.array([0.011, 0.011, 0.008]) * S, R, k=0.010, cream=0.95, u=up))
    hp.append(m.ell(P(0, -0.012, -0.022), np.array([0.030, 0.030, 0.017]) * S, R, k=0.014, cream=0.6, u=up))
    return dict(c=c, R=R, prims=hp, scale=S)


def ear_mesh(W=0.060, H=0.044, D=0.021, th=0.0045, notch=False, nu=6, nv=6):
    """thin curved ear shell in ear space: base on z=0 centred at origin, opening toward -Y, back bulging toward +Y.
    x>0 is the OUTER edge. returns V, F, material indices (0 = outer fur, 1 = inner)"""
    V = []; idx = {}
    for side in (0, 1):                     # 0 = front (inner surface), 1 = back
        for j in range(nv + 1):
            v = j / nv
            w = W * ((1 - v ** 1.15) * (1 - v) ** 0.35 * 0.90 + 0.10)
            sk = -0.16 * W * v                                  # tip leans to the inner side
            for i in range(nu + 1):
                u = i / nu
                x = (u - 0.5) * w + sk
                if notch and u > 0.5 and 0.42 < v < 0.66:
                    x -= (u - 0.5) * 2 * 0.22 * W * max(0.0, 1 - abs(v - 0.54) / 0.12)
                bul = math.sin(math.pi * u) * (1 - v) ** 0.7
                y = D * bul * (0.78 if side == 0 else 1.0) + (th * (1 - 0.5 * v) if side else 0.0)
                z = H * v + 0.004 * math.sin(math.pi * u) * v - 0.008 * (2 * u - 1) ** 2 * (1 - v) ** 2   # corners sink into the head
                idx[side, j, i] = len(V); V.append((x, y, z))
    F = []; M = []
    for j in range(nv):
        for i in range(nu):
            F.append((idx[0, j, i], idx[0, j + 1, i], idx[0, j + 1, i + 1], idx[0, j, i + 1])); M.append(1)
            F.append((idx[1, j, i], idx[1, j, i + 1], idx[1, j + 1, i + 1], idx[1, j + 1, i])); M.append(0)
        F.append((idx[0, j, 0], idx[1, j, 0], idx[1, j + 1, 0], idx[0, j + 1, 0])); M.append(0)
        F.append((idx[0, j, nu], idx[0, j + 1, nu], idx[1, j + 1, nu], idx[1, j, nu])); M.append(0)
    for i in range(nu):
        F.append((idx[0, nv, i], idx[1, nv, i], idx[1, nv, i + 1], idx[0, nv, i + 1])); M.append(0)
    return np.array(V), F, M


def ears(m, hd, splay=18, yaw=12, pitch=0, notch_side=1, H=0.044, W=0.060):
    """returns list of (V, F, M) ear meshes in cat space. splay = outward roll, yaw = opening turned outward,
    pitch = + tilts the ears forward"""
    out = []
    c, R, S = hd['c'], hd['R'], hd['scale']
    for sx in (-1, 1):
        d = R @ nrm((sx * 0.58, -0.08, 0.80))
        base = m.surface_point(c, d, hd['prims'], inset=0.0065 * S)
        V, F, M = ear_mesh(W * S, H * S, notch=(sx == notch_side))
        if sx < 0: V = V * np.array([-1, 1, 1]); F = [tuple(reversed(f)) for f in F]       # mirror: +x stays outward
        Rl = rz(sx * yaw) @ ry(sx * splay) @ rx(pitch)
        Vw = c + ((V @ Rl.T) + (base - c) @ R) @ R.T
        out.append((Vw, F, M))
        root = c + R @ ((base - c) @ R + Rl @ np.array([-0.006 * sx, 0.004, 0.004]) * S)
        m.ell(root, np.array([0.015, 0.010, 0.011]) * S, R @ Rl, k=0.012, u=R[:, 2], dark=0.4)
    return out


def eye_points(m, hd, spread=0.22, lift=0.05):
    out = []
    c, R, S = hd['c'], hd['R'], hd['scale']
    for sx in (-1, 1):
        o = c + R @ (np.array([sx * 0.017, -0.025, 0.008]) * S)
        d = R @ nrm((sx * spread, -1.0, lift))
        r = 0.0104 * S
        p = m.surface_point(o, d, hd['prims'], inset=0.0)
        out.append((p - d * r * 0.45, d, r))
    return out


def eye_mesh(name, eyes, mat):
    bm = bmesh.new()
    for (p, d, r) in eyes:
        g = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=r)
        Rm = frame(d, (0, 0, 1))
        for v in g['verts']:
            q = np.array((v.co.x, -v.co.z, v.co.y * 0.78))                # pole -> forward; slightly almond
            v.co = tuple(p + Rm @ q)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    # pupil attribute: R = forward-ness (1 at the front pole), G = sideways offset
    V = mesh_verts(me); A = np.zeros((len(V), 4))
    for (p, d, r) in eyes:
        sel = np.linalg.norm(V - p, axis=1) < r * 1.3
        A[sel, 0] = ((V[sel] - p) @ nrm(d)) / r
        side = np.cross(nrm(d), (0, 0, 1)); side = side / np.linalg.norm(side)
        A[sel, 1] = ((V[sel] - p) @ side) / r
    set_fur(me, A)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


# ============================================================================ the three poses (cat space: head toward -Y)
def leg_front(m, sx, shoulder, elbow, wrist, paw, rad=(0.028, 0.021, 0.015), paw_r=(0.019, 0.026, 0.014), u=(0, 1, 0)):
    m.rc(shoulder, elbow, rad[0], rad[1], k=0.012, freq=FUR_LEG, sdir=(0, 0, 1), u=u)
    m.rc(elbow, wrist, rad[1], rad[2], k=0.006, freq=FUR_LEG, sdir=(0, 0, 1), u=u, creamv=0.25)
    fw = nrm(np.asarray(paw) - np.asarray(wrist)); fw[2] = 0; fw = nrm(fw) if np.linalg.norm(fw) > 1e-6 else np.array([0, -1, 0])
    m.ell(paw, paw_r, frame(fw, (0, 0, 1)), k=0.008, cream=0.75)


def sit_like(m, crouch=0.0):
    """shared lower body for the seated poses. crouch 0 = upright, 1 = leaning forward (cat_watch)"""
    for sx in (-1, 1):
        # haunch (thigh folded forward) and the flat hind foot
        m.ell((sx * 0.058, 0.040 - 0.01 * crouch, 0.084 - 0.006 * crouch), (0.043, 0.088, 0.068), rx(-22 - 6 * crouch), k=0.022,
              sdir=(0, 1, 0.2), freq=FUR_LEG, u=(sx, 0.4, 0.6))
        m.rc((sx * 0.068, -0.030, 0.050), (sx * 0.064, 0.090, 0.022), 0.022, 0.016, k=0.01)
        m.rc((sx * 0.062, 0.092, 0.016), (sx * 0.060, -0.040, 0.014), 0.016, 0.017, k=0.006, freq=FUR_LEG, sdir=(0, 1, 0))
        m.ell((sx * 0.060, -0.048, 0.0135), (0.019, 0.024, 0.0135), None, k=0.006, cream=0.75)
    m.ell((0, 0.055, 0.050), (0.074, 0.088, 0.052), rx(-8), k=0.02, freq=FUR_BODY, sdir=(0, -0.4, 1), u=(0, 1, 0.2))   # seat


def pose_sit():
    m = Model(); m.floor = 0.0
    sit_like(m, 0)
    sp = [(0, 0.085, 0.080), (0, 0.052, 0.122), (0, 0.012, 0.168), (0, -0.022, 0.207), (0, -0.040, 0.236)]
    m.sweep(sp, [0.072, 0.075, 0.071, 0.062, 0.050], [0.066, 0.078, 0.078, 0.068, 0.054],
            [(0, 1, 0.25), (0, 1, 0.35), (0, 1, 0.45), (0, 1, 0.6), (0, 1, 0.9)], freq=FUR_BODY, creamv=0.5, k=0.014)
    m.ell((0, -0.058, 0.168), (0.047, 0.040, 0.062), rx(-12), k=0.022, cream=0.55, u=(0, 1, 0.3), creamv=0.5)   # breast
    for sx in (-1, 1):
        leg_front(m, sx, (sx * 0.036, -0.048, 0.180), (sx * 0.037, -0.050, 0.112), (sx * 0.032, -0.078, 0.030), (sx * 0.032, -0.092, 0.0142))
    m.rc((0, -0.040, 0.232), (0, -0.068, 0.284), 0.047, 0.041, k=0.022, u=(0, 1, 0.5), creamv=0.8, az=13)
    R = rz(14) @ rx(-32)
    hd = head(m, np.array([0.0, -0.088, 0.302]), R)
    # tail: from the rump down to the floor and round the left side (+X, toward the camera) to the front paws
    tp = [(0.0, 0.118, 0.060), (0.02, 0.150, 0.030), (0.075, 0.150, 0.0185), (0.122, 0.105, 0.0175), (0.138, 0.030, 0.0175),
          (0.118, -0.045, 0.0175), (0.078, -0.098, 0.0185), (0.040, -0.118, 0.020)]
    m.tube(tp, [0.024, 0.022, 0.0205, 0.0195, 0.0185, 0.017, 0.0145, 0.010], n=4, k=0.006, freq=FUR_TAIL, dark0=0.0, dark1=0.9)
    return m, hd, dict(splay=14, yaw=10, pitch=4)


def pose_watch():
    m = Model(); m.floor = 0.0
    sit_like(m, 1)
    # spine nearly level: haunches down, chest lowered, shoulders forward, head held low out over the top step
    sp = [(0, 0.086, 0.080), (0, 0.046, 0.104), (0, -0.004, 0.122), (0, -0.054, 0.130), (0, -0.094, 0.130)]
    m.sweep(sp, [0.072, 0.072, 0.063, 0.057, 0.051], [0.066, 0.074, 0.072, 0.064, 0.054],
            [(0, 0.5, 1), (0, 0.3, 1), (0, 0.15, 1), (0, 0.05, 1), (0, 0.0, 1)], freq=FUR_BODY, creamv=0.5, k=0.014)
    m.ell((0, -0.112, 0.092), (0.044, 0.038, 0.048), rx(18), k=0.022, cream=0.55, u=(0, 0.3, 1), creamv=0.5)   # breast
    for sx in (-1, 1):
        m.ell((sx * 0.031, -0.080, 0.172), (0.021, 0.034, 0.021), rx(-8), k=0.016, u=(0, 0, 1), freq=FUR_BODY, sdir=(0, 1, 0))  # shoulder blades
        leg_front(m, sx, (sx * 0.040, -0.100, 0.118), (sx * 0.046, -0.076, 0.072), (sx * 0.036, -0.140, 0.028), (sx * 0.034, -0.156, 0.0142))
    m.rc((0, -0.094, 0.140), (0, -0.158, 0.172), 0.044, 0.038, k=0.022, u=(0, 0.1, 1), creamv=0.8, az=13)
    R = rx(30)                                                         # neck stretched forward, face tipped down the stairs
    hd = head(m, np.array([0.0, -0.180, 0.184]), R)
    tp = [(0.0, 0.122, 0.052), (0.0, 0.160, 0.022), (0.004, 0.230, 0.0175), (0.006, 0.310, 0.0172), (0.004, 0.380, 0.0172),
          (0.0, 0.425, 0.026), (-0.004, 0.452, 0.046)]
    m.tube(tp, [0.024, 0.021, 0.0195, 0.0185, 0.0165, 0.0135, 0.0095], n=4, k=0.006, freq=FUR_TAIL, dark0=0.0, dark1=0.9)
    return m, hd, dict(splay=8, yaw=-4, pitch=16)


SLEEP_Z = 0.030          # blanket top above the speaker top (cat space z of the blanket surface)
SLEEP_OFF = (-0.035, 0.03)   # the curl sits a little left of and behind the spot centre: from the stool the pendant shade
                             # at (0.95, -0.15) hangs just above it, and this keeps the ears out from under the rim

def pose_sleep():
    m = Model(); zb = SLEEP_Z; m.floor = zb - 0.004
    beta = math.radians(26)

    def pol(th, r, z): a = math.radians(th); return np.array([r * math.cos(a), r * math.sin(a), z])
    def rad(th): a = math.radians(th); return np.array([math.cos(a), math.sin(a), 0.0])

    # spine (body centre line) spirals inward from the rump (272 deg) to the shoulders (146 deg)
    ths = [272, 305, 340, 15, 50, 85, 118, 146]
    Rr = [0.100, 0.099, 0.097, 0.095, 0.093, 0.091, 0.088, 0.084]
    W = [0.086, 0.094, 0.098, 0.100, 0.098, 0.092, 0.084, 0.072]
    H = [0.072, 0.084, 0.090, 0.092, 0.090, 0.084, 0.074, 0.062]
    zc = [zb + 0.034, zb + 0.032, zb + 0.030, zb + 0.030, zb + 0.030, zb + 0.031, zb + 0.033, zb + 0.036]
    sp = [pol(t, r, z) for t, r, z in zip(ths, Rr, zc)]
    ups = [rad(t) * math.cos(beta) + np.array([0, 0, math.sin(beta)]) for t in ths]
    m.sweep(sp, W, H, ups, freq=FUR_BODY, creamv=0.45, k=0.016)
    # upper hind leg: haunch at the rump end, foot tucked up toward the face
    m.ell(pol(296, 0.092, zb + 0.092), (0.046, 0.078, 0.052), axis_frame(pol(245, 0.05, 0) - pol(305, 0.10, 0), (0, 0, 1)), k=0.022,
          freq=FUR_LEG, sdir=rad(296), u=(0, 0, 1))
    m.rc(pol(262, 0.060, zb + 0.070), pol(226, 0.070, zb + 0.050), 0.020, 0.016, k=0.010, freq=FUR_LEG)
    m.ell(pol(221, 0.072, zb + 0.044), (0.018, 0.026, 0.013), axis_frame(pol(205, 0.075, 0) - pol(228, 0.07, 0), (0, 0, 1)), k=0.006, cream=0.6)
    # front legs folded under the chin
    for dz, a1 in ((0.0, 192), (0.020, 200)):
        m.rc(pol(150, 0.060, zb + 0.040 + dz), pol(a1, 0.045, zb + 0.032 + dz), 0.020, 0.016, k=0.008, freq=FUR_LEG)
        m.ell(pol(a1 + 5, 0.046, zb + 0.028 + dz), (0.017, 0.022, 0.012), axis_frame(pol(a1 + 10, 0.05, 0) - pol(a1, 0.05, 0), (0, 0, 1)),
              k=0.006, cream=0.75)
    # neck + head: the head lies at the end of the curl, nose tucked toward the tail, top of the head facing out and up
    hc = pol(186, 0.080, zb + 0.088)
    m.rc(sp[-1], hc + np.array([0, 0, -0.010]), 0.052, 0.044, k=0.022, u=(0, 0, 1), freq=FUR_BODY, creamv=0.4)
    fwd = nrm(rad(282) - rad(186) * 0.30 + np.array([0, 0, -0.60]))
    upv = nrm(rad(186) * 0.50 + np.array([0, 0, 1.0]))
    hd = head(m, hc, frame(fwd, upv))
    # tail: leaves the rump, wraps round the outside of the curl on the blanket and lays its tip over the nose
    tp = [pol(266, 0.112, zb + 0.066), pol(257, 0.162, zb + 0.036), pol(242, 0.190, zb + 0.024), pol(224, 0.192, zb + 0.024),
          pol(208, 0.176, zb + 0.032), pol(201, 0.146, zb + 0.052), pol(212, 0.118, zb + 0.074)]
    m.tube(tp, [0.023, 0.022, 0.021, 0.020, 0.018, 0.015, 0.010], n=4, k=0.006, freq=FUR_TAIL, dark0=0.0, dark1=0.9)
    return m, hd, dict(splay=34, yaw=30, pitch=-12)


# ============================================================================ materials
def fur_material():
    name = 'cat_fur'
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    N, L = mats.N, mats.L
    at = N(nt, 'ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='cat_fur')
    sep = N(nt, 'ShaderNodeSeparateColor'); L(nt, at.outputs['Color'], sep.inputs[0])
    ph, dor, cream = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    dark = at.outputs['Alpha']
    v = mats.coords(nt)
    n1 = mats.noise(nt, v, 16, 4, 0.6, 0.4)                # stripe wobble
    n2 = mats.noise(nt, v, 11, 3, 0.55)                     # stripe break-up
    tick = mats.noise(nt, v, 260, 2, 0.6)                   # agouti ticking
    # mackerel stripes: dark where sin(2pi(phase + wobble)) is high
    p = mats.math_(nt, 'ADD', ph, mats.math_(nt, 'MULTIPLY', mats.math_(nt, 'SUBTRACT', n1, 0.5), 1.5))
    sn = mats.math_(nt, 'SINE', mats.math_(nt, 'MULTIPLY', p, 2 * math.pi))
    sn = mats.math_(nt, 'ADD', sn, mats.math_(nt, 'MULTIPLY', mats.math_(nt, 'SUBTRACT', n2, 0.5), 1.7))
    stripe = maprange(nt, sn, 0.15, 0.85)
    # dark dorsal line + per-vertex darkness (tail tip)
    dl = maprange(nt, mats.math_(nt, 'ADD', dor, mats.math_(nt, 'MULTIPLY', mats.math_(nt, 'SUBTRACT', n2, 0.5), 0.4)), 0.62, 0.92)
    dk = mats.math_(nt, 'MAXIMUM', mats.math_(nt, 'MULTIPLY', stripe, 0.92), mats.math_(nt, 'MULTIPLY', dl, 0.75))
    dk = mats.math_(nt, 'MAXIMUM', dk, maprange(nt, mats.math_(nt, 'ADD', dark, mats.math_(nt, 'MULTIPLY', sn, 0.25)), 0.35, 0.8))
    base = mats.ramp(nt, tick, [(0.28, (0.060, 0.038, 0.022)), (0.52, (0.135, 0.085, 0.046)), (0.80, (0.215, 0.150, 0.088))])
    darkc = mats.ramp(nt, tick, [(0.35, (0.013, 0.010, 0.008)), (0.7, (0.040, 0.028, 0.019))])
    col = mats.mixc(nt, base, darkc, dk, 'MIX')
    cr = maprange(nt, mats.math_(nt, 'ADD', cream, mats.math_(nt, 'MULTIPLY', mats.math_(nt, 'SUBTRACT', n1, 0.5), 0.5)), 0.30, 0.62)
    creamc = mats.ramp(nt, tick, [(0.3, (0.32, 0.24, 0.16)), (0.75, (0.50, 0.40, 0.28))])
    col = mats.mixc(nt, col, creamc, cr, 'MIX')
    L(nt, col, b.inputs['Base Color'])
    mats.setp(b, rough=0.88, sheen=0.12, spec=0.22)
    if 'Sheen Roughness' in b.inputs: b.inputs['Sheen Roughness'].default_value = 0.35
    fine = mats.noise(nt, mats.coords(nt, (1.0, 1.0, 3.0)), 520, 2, 0.6)
    mats.bump(nt, b, fine, 0.22, 0.0006)
    return m


def maprange(nt, x, a, b):
    n = mats.N(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
    mats.L(nt, x, n.inputs['Value']); n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b
    n.inputs['To Min'].default_value = 0.0; n.inputs['To Max'].default_value = 1.0
    return n.outputs['Result']


def ear_inner_material():
    name = 'cat_ear_in'
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    v = mats.coords(nt)
    n1 = mats.noise(nt, v, 180, 3, 0.6)
    mats.L(nt, mats.ramp(nt, n1, [(0.35, (0.30, 0.17, 0.13)), (0.7, (0.58, 0.47, 0.37))]), b.inputs['Base Color'])
    mats.setp(b, rough=0.7, sheen=0.6)
    return m


def eye_material(name, glow=0.0):
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    N, L = mats.N, mats.L
    at = N(nt, 'ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='cat_fur')
    sep = N(nt, 'ShaderNodeSeparateColor'); L(nt, at.outputs['Color'], sep.inputs[0])
    fw = sep.outputs[0]
    pupil = maprange(nt, fw, 0.80, 0.86)                                   # round, dilated (it is dark in here)
    iris = mats.ramp(nt, fw, [(0.45, (0.20, 0.10, 0.015)), (0.72, (0.62, 0.36, 0.05)), (0.80, (0.42, 0.24, 0.03))])
    col = mats.mixc(nt, iris, (0.004, 0.004, 0.004), pupil, 'MIX')
    L(nt, col, b.inputs['Base Color'])
    mats.setp(b, rough=0.12, coat=1.0, coat_rough=0.02)
    if glow > 0:
        L(nt, mats.mixc(nt, (0.55, 0.62, 0.30), (0, 0, 0), pupil, 'MIX'), b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = glow
    return m


def wool_material():
    name = 'cat_wool'
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    N, L = mats.N, mats.L
    tc = N(nt, 'ShaderNodeTexCoord'); sx = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, tc.outputs['Object'], sx.inputs[0])
    fuzz = mats.noise(nt, mats.coords(nt), 90, 3, 0.6)
    def bands(axis, period, width):
        f = mats.math_(nt, 'FRACT', mats.math_(nt, 'DIVIDE', sx.outputs[axis], period))
        return mats.math_(nt, 'LESS_THAN', mats.math_(nt, 'ABSOLUTE', mats.math_(nt, 'SUBTRACT', f, 0.5)), width)
    gx = bands('X', 0.085, 0.16); gy = bands('Y', 0.085, 0.16)
    rx_ = bands('X', 0.085 / 3, 0.05); ry_ = bands('Y', 0.085 / 3, 0.05)
    col = (0.20, 0.115, 0.035)                                             # mustard / tobacco ground
    c = mats.mixc(nt, col, (0.045, 0.070, 0.040), mats.math_(nt, 'MULTIPLY', gx, 0.6), 'MIX')   # bottle green warp
    c = mats.mixc(nt, c, (0.045, 0.070, 0.040), mats.math_(nt, 'MULTIPLY', gy, 0.6), 'MIX')
    c = mats.mixc(nt, c, (0.12, 0.028, 0.020), mats.math_(nt, 'MULTIPLY', mats.math_(nt, 'MAXIMUM', rx_, ry_), 0.8), 'MIX')   # oxblood line
    c = mats.mixc(nt, c, mats.ramp(nt, fuzz, [(0.3, (0.7, 0.7, 0.7)), (0.7, (1.1, 1.05, 1.0))]), 1.0, 'MULTIPLY')
    L(nt, c, b.inputs['Base Color'])
    mats.setp(b, rough=0.95, sheen=0.8)
    mats.bump(nt, b, mats.noise(nt, mats.coords(nt), 400, 2, 0.6), 0.3, 0.0008)
    return m


# ============================================================================ build
def ear_object(name, ear_list, fur, inner):
    Vs, Fs, Ms = [], [], []; off = 0
    for V, F, M in ear_list:
        Vs.append(V); Fs += [tuple(i + off for i in f) for f in F]; Ms += M; off += len(V)
    V = np.vstack(Vs)
    me = from_data(name, V, Fs, Ms)
    me.materials.append(fur); me.materials.append(inner)
    # tabby ears: dark backs, a little stripe
    Vm = mesh_verts(me); A = np.zeros((len(Vm), 4)); A[:, 3] = 0.55; A[:, 0] = Vm[:, 2] * 40
    set_fur(me, A)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def make_cat(name, pose, tris, eyes=None, fit=None):
    fur = fur_material(); inner = ear_inner_material()
    m, hd, ek = pose()
    ear_list = ears(m, hd, **ek)
    me = m.skin(name + '_body', tris)
    set_fur(me, m.attrs(mesh_verts(me)))
    me.materials.append(fur)
    obs = [bpy.data.objects.new(me.name, me)]
    bpy.context.scene.collection.objects.link(obs[0])
    obs.append(ear_object(name + '_ears', ear_list, fur, inner))
    if eyes is not None:
        obs.append(eye_mesh(name + '_eyes', eye_points(m, hd), eyes))
    if fit is not None:                                   # re-seat the whole pose (cat space) to clear its surroundings
        from mathutils import Matrix
        M = fit(np.vstack([mesh_verts(o.data) for o in obs]))
        for o in obs: o.data.transform(Matrix(M.tolist()))
    for o in obs: kit.adopt(o, smooth=True)


def _door_ajar(default=40.0):
    """the stair door leaf's opening angle as the shell part builds it (shell/build.py DOOR_AJAR); read, never imported"""
    import os, re
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shell', 'build.py')) as f:
            mt = re.search(r'^DOOR_AJAR\s*=\s*([0-9.]+)', f.read(), re.M)
        return float(mt.group(1)) if mt else default
    except Exception:
        return default

def watch_fit(V, margin=0.015):
    """cat_watch sits just inside the stair door.  If the open leaf (as the shell part builds it) stands in front of the
    cat, turn the cat a little toward the gap (toward the visible stairs and the glow) and slide it back toward the room
    just enough that nothing crosses the leaf's room face.  If the leaf is out of the way, this is the identity.
    returns a 4x4 matrix in cat space."""
    pos, rot = layout.CAT_SPOTS['cat_watch']
    H = np.array([layout.DOOR['hinge_x'], layout.DOOR['y']]); leaf_w = layout.DOOR['x1'] - layout.DOOR['x0']
    a = math.radians(_door_ajar())
    along_dir = np.array([math.cos(a), math.sin(a)]); n = np.array([math.sin(a), -math.cos(a)])   # leaf direction, room-side normal
    W2 = rz(rot)[:2, :2]; P0 = np.array(pos[:2])

    def world(Vc): return P0 + Vc[:, :2] @ W2.T

    def blocked(yaw):
        Vr = V @ rz(yaw).T; Wp = world(Vr)
        al = (Wp - H) @ along_dir; on = (al > -0.02) & (al < leaf_w + 0.02)
        d = (Wp - H) @ n
        return Vr, (margin - d[on]).max() if on.any() else -1.0

    # does the cat's straight-ahead gaze run into the leaf within a metre?
    g = P0 + W2 @ np.array([0.0, -1.0]) * np.linspace(0.0, 1.0, 50)[:, None]
    al = (g - H) @ along_dir; d = (g - H) @ n
    yaw = -22.0 if ((al > 0) & (al < leaf_w) & (d < 0)).any() else 0.0      # turn toward the gap (world +x for this spot)
    Vr, need = blocked(yaw)
    need = max(0.0, need)
    nl = W2.T @ n; back = np.array([0.0, 1.0])            # slide straight back along the cat's own axis (+Y)
    shift = back * need / max(1e-6, back @ nl)
    M = np.eye(4); M[:3, :3] = rz(yaw); M[0, 3], M[1, 3] = shift
    return M


def blanket():
    """folded wool blanket on the right speaker top, dented where the cat sleeps (cat space of cat_sleep)"""
    m = Model(lumps=0.0); m.floor = 0.0
    t = 0.032
    m.rbox((0.0, 0.0, t / 2), (0.245, 0.185, t / 2), 0.0155, k=0.0)
    m.ell((-0.20, 0.10, t * 0.8), (0.05, 0.09, 0.012), rz(20), k=0.02)              # a soft ruck in the wool
    m.ell((0.17, -0.13, t * 0.8), (0.07, 0.04, 0.010), rz(-30), k=0.02)
    m.ell((0.01, -0.01, t - 0.006), (0.215, 0.16, 0.010), None, k=0.012)                 # puffed middle
    m.add(Prim('ell', k=0.045, sub=True, c=(SLEEP_OFF[0], SLEEP_OFF[1], t + 0.058), r=(0.17, 0.16, 0.064), R=None))
    for z in (t * 0.36, t * 0.70):                                                   # layers at the open (front) edge
        m.add(Prim('rbox', k=0.0, sub=True, c=(0.0, -0.192, z), half=(0.26, 0.012, 0.0016), rr=0.0012, R=None))
    from skimage.measure import marching_cubes
    D, lo, h = m.grid(0.004)
    V, F, _, _ = marching_cubes(-D.astype(np.float32), 0.0, spacing=(h, h, h))
    V = taubin(V.astype(np.float64) + lo, F, 3)
    me = decimate('cat_blanket', V, F, 900)
    me.materials.append(wool_material())
    ob = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def bowl():
    glaze = mats.plain('cat_bowl_glaze', (0.62, 0.55, 0.42), rough=0.18, coat=0.6)
    water = mats.glass('cat_water', (0.85, 0.9, 0.9))
    x, y = BOWL
    with kit.xform(T(x, y, 0.0)), kit.props(td=0.6):
        kit.lathe('cat_bowl', [(0.0, 0.0), (0.050, 0.0), (0.056, 0.004), (0.068, 0.040), (0.072, 0.044), (0.068, 0.046),
                               (0.060, 0.012), (0.0, 0.010)], glaze, segs=24, sharp=50)
        kit.cyl('cat_bowl_water', 0, 0, 0.027, 0.028, 0.0632, water, segs=24, r1=0.0634, cap='t')


BOWL = (-2.09, 1.44)        # on the floor between the stair door jamb and the credenza end


def build():
    spots = layout.CAT_SPOTS
    eye = eye_material('cat_eye'); eye_w = eye_material('cat_eye_watch', glow=0.12)
    pos, rot = spots['cat_sleep']
    with kit.xform(T(*pos) @ Rz(rot)):
        with kit.props(td=0.7):
            kit.adopt(blanket(), smooth=True)
        with kit.interactive('cat_sleep', origin=(0, 0, 0), td=2.0), kit.xform(T(*SLEEP_OFF, 0.0)):
            make_cat('cat_sleep', pose_sleep, 3700)
    pos, rot = spots['cat_sit']
    with kit.xform(T(*pos) @ Rz(rot)), kit.interactive('cat_sit', origin=(0, 0, 0), td=2.0):
        make_cat('cat_sit', pose_sit, 3700, eyes=eye)
    pos, rot = spots['cat_watch']
    with kit.xform(T(*pos) @ Rz(rot)), kit.interactive('cat_watch', origin=(0, 0, 0), td=2.0):
        make_cat('cat_watch', pose_watch, 3700, eyes=eye_w, fit=watch_fit)
    bowl()


# a soft warm downlight over the right speaker (the room's speaker spots aim at the cabinet fronts, so without it the
# sleeping cat and its blanket sit in near darkness at the top of the hero view)
LIGHTS = [('N_cat_spk', 'SPOT', (1.22, 0.85, 2.40), 9.0, layout.WARM,   # assembler: moved out of the ceiling beam at x=1.55
           dict(radius=0.05, spot_size=math.radians(55), spot_blend=0.9, aim=(1.65, 1.40, 1.95)))]
