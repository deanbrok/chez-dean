"""THE LAYOUT CONTRACT for the bar. Blender coordinates, metres, Z up.
+Y = away from the viewer (toward the back bar), +X = viewer's right. Floor Z=0, ceiling Z=2.45.
Everybody builds in these room coordinates. Numbers here are binding; ask nothing, read this file.
"""
import math

PARTS = ['shell', 'counter', 'shelves', 'hifi', 'nook', 'lounge', 'cat']

ROOM = dict(x0=-3.4, x1=3.4, y0=-2.6, y1=1.6, z0=0.0, z1=2.45)       # main room interior
EYE = (0.0, -1.60, 1.26)                                              # the viewer on the bar stool

# ---- architecture (shell) -------------------------------------------------------------------------------------
WINDOW = dict(x=-3.4, y0=-1.5, y1=-0.1, z0=1.50, z1=2.25)             # high street-level window in the LEFT wall
DOOR = dict(y=1.6, x0=-3.1, x1=-2.3, z1=2.0, hinge_x=-3.1)            # door in the BACK wall, far left -> stairs DOWN
STAIRS = dict(x0=-3.2, x1=-2.2, y0=1.7, y1=4.5, top_y=1.95, step_run=0.25, step_rise=0.20, steps=10)   # descends toward +Y
NOOK_OPENING = dict(y=1.6, x0=2.2, x1=3.25, z1=2.05)                  # wide opening in the BACK wall, far right
NOOK = dict(x0=2.05, x1=3.4, y0=1.7, y1=3.5)                          # the little kitchen behind it (floor Z=0, ceiling 2.45)

# ---- counter ----------------------------------------------------------------------------------------------------
COUNTER = dict(x0=-2.2, x1=2.2, top_z=1.02, top_y0=-0.95, top_y1=-0.25, body_y0=-0.80, body_y1=-0.34)
STOOLS = [(-1.8, -1.35), (-1.0, -1.35), (1.0, -1.35), (1.8, -1.35)]   # (x, y) seat height 0.76; the viewer sits at x=0
PENDANTS = [(-1.9, -0.15), (-0.95, -0.15), (0.95, -0.15), (1.9, -0.15)]   # (x, y); shade rim Z=1.72, bulb Z=1.80, cord to ceiling
COUNTER_LAMP = (-0.05, -0.42)                                         # small brass lamp on the counter, bulb Z=1.28
# the still life on the counter, as seen from the stool (x, y); binding to within a few cm:
STILL_LIFE = dict(lamp=COUNTER_LAMP, whisky_glass=(0.16, -0.70), ashtray=(0.40, -0.52), second_drink=(0.72, -0.60),
                  note=(0.0, -0.80), matchbook=(0.34, -0.74), cigarbox=(0.78, -0.38), paperback=(-0.30, -0.80))
# the cigar in the ashtray: a 6 x 47 perfecto (152 mm long, 18.7 mm at its widest), resting in the notch that points -55 deg,
# lit end over the dish. Everything about where it lies comes from here (the modeller AND the web page use these numbers).
CIGAR = dict(angle=-55.0, length=0.1524, radius=0.00933,
             s_foot=-0.024, s_notch=0.060,      # distance from the ashtray centre along the notch direction: foot tip, resting point
             z_notch=0.0262 - 0.0095,           # height of the notch floor above the counter top
             drop=0.0035,                       # how much lower the foot's centre is than the centre at the notch
             burn=0.017,                        # distance from the foot tip to the burn line (everything before it is ash)
             band=(0.112, 0.128))               # the paper band, as distances from the foot tip
def cigar_point(d, up=0.0):
    """room coordinates of the point on the cigar's centre line d metres from the foot tip (+ up metres above it)"""
    c = CIGAR; a = math.radians(c['angle']); ax, ay = STILL_LIFE['ashtray']
    slope = c['drop'] / (c['s_notch'] - c['s_foot'])
    n = math.sqrt(1 + slope * slope)
    ux, uy, uz = math.cos(a) / n, math.sin(a) / n, slope / n
    zf = COUNTER['top_z'] + c['z_notch'] + c['radius'] - c['drop']
    return (ax + math.cos(a) * c['s_foot'] + ux * d, ay + math.sin(a) * c['s_foot'] + uy * d, zf + uz * d + up)
CIGAR_REST = 0.084                                 # the point (distance from the foot tip) that sits in the notch = the cigar's pivot
TURNTABLE = dict(x0=-0.88, x1=-0.40, y0=-0.70, y1=-0.32, z=1.02)      # reserved on the counter for the hi-fi agent
# hero view sees the counter top only for |x| < ~0.9 (far edge) / ~0.47 (near edge): the "still life" lives there.

# ---- back bar ---------------------------------------------------------------------------------------------------
CREDENZA = dict(x0=-1.95, x1=1.95, y0=1.12, y1=1.60, top_z=0.90)      # low cabinet along the back wall
SHELVING = dict(x0=-1.30, x1=1.30, y0=1.27, y1=1.60, rows=(1.40, 1.76), top_z=2.12)   # row = Z of the shelf board top
RECORDS_X = (-1.30, 0.45)                                             # both rows: LP spines
RIGHT_BLOCK_X = (0.50, 1.30)                                          # row 1.40: "bottle keep" bottles, row 1.76: books
SPEAKER_L = dict(x0=-1.95, x1=-1.35, y0=1.14, y1=1.58, z0=0.90, z1=1.95)
SPEAKER_R = dict(x0=1.35, x1=1.95, y0=1.14, y1=1.58, z0=0.90, z1=1.95)
# credenza top (Z 0.90 .. 1.38 clear under the shelf) split along X:
CRED_REEL = (-1.25, -0.75)      # hifi: reel-to-reel deck
CRED_BOTTLES = (-0.70, 0.20)    # shelves: house bottles + glasses
CRED_AMP = (0.25, 0.90)         # hifi: valve amp (+ preamp)
CRED_NOWPLAYING = (0.95, 1.30)  # hifi: "now playing" sleeve on a little stand

# ---- lounge (left side) -----------------------------------------------------------------------------------------
PIANO = dict(x0=-3.4, x1=-2.8, y0=-1.5, y1=0.0, top_z=1.25)           # upright against the left wall, under the window
FLOOR_LAMP = (-3.1, 0.2)                                              # bulb Z=1.45
PHONE = (-3.3, 0.75)                                                  # pay phone on a wall shelf, shelf top Z=1.0
CLOCK = (-2.7, 1.59, 2.22)                                            # wall clock above the stair door, faces -Y
LOUNGE_ZONE = dict(x0=-3.4, x1=-2.3, y0=-2.6, y1=1.6)                 # keep the door swing (x -3.2..-2.2, y 0.7..1.6) clear

# ---- nook (right, behind the back wall) -------------------------------------------------------------------------
NOOK_TABLE = dict(x0=2.35, x1=3.15, y0=2.2, y1=2.9, top_z=0.72)
NOOK_BULB = (2.75, 2.55, 1.75)                                        # bare bulb over the table
KITCHENETTE = dict(x0=2.05, x1=3.4, y0=3.0, y1=3.5, top_z=0.85)

# ---- cat spots (the cat agent builds each pose around the origin; these are where the assembler puts them) ---------
CAT_SPOTS = dict(cat_sleep=((1.65, 1.36, 1.95), 0), cat_sit=((-3.1, -0.55, 1.25), -90), cat_watch=((-2.7, 1.78, 0.0), 180))
# (position of the pose's base centre, rotation about Z in degrees applied to a cat whose head points to -Y)

# ---- camera stops: name -> (position, look-at target, vertical fov degrees) ---------------------------------------
STOPS = dict(
    bar=((0.0, -1.60, 1.26), (0.05, 1.6, 1.28), 45),
    records=((-0.10, -0.50, 1.72), (-0.10, 1.45, 1.71), 46),
    hifi=((-0.25, -1.15, 1.52), (-0.62, -0.50, 1.06), 40),
    table=((2.55, 0.35, 1.55), (2.75, 2.55, 0.80), 45),
    window=((-1.15, -1.75, 1.35), (-3.4, -0.55, 1.55), 50),
    stairs=((-2.30, 0.95, 1.60), (-2.68, 3.0, -0.60), 50),
)

# ---- lights. (name, kind, location, energy W, colour, extra) ; N = room lamps (night), B = always on ---------------
WARM = (1.0, 0.66, 0.36); WARMER = (1.0, 0.56, 0.26); COLD = (0.30, 0.75, 0.80); MOON = (0.45, 0.60, 1.0); SKY = (0.62, 0.78, 1.0)
LIGHTS = []
for i, (x, y) in enumerate(PENDANTS):
    LIGHTS.append(('N_pend%d' % i, 'POINT', (x, y, 1.96), 9, WARM, dict(radius=0.03)))
LIGHTS += [
    ('N_counter_lamp', 'POINT', (COUNTER_LAMP[0], COUNTER_LAMP[1], 1.28), 2.4, WARM, dict(radius=0.015)),
    ('N_floor_lamp', 'POINT', (FLOOR_LAMP[0], FLOOR_LAMP[1], 1.45), 9, WARMER, dict(radius=0.05)),
    ('N_nook_bulb', 'POINT', NOOK_BULB, 22, (1.0, 0.72, 0.42), dict(radius=0.03)),
    ('N_shelf_wash_l', 'SPOT', (-0.75, 0.35, 2.40), 58, (1.0, 0.70, 0.42), dict(radius=0.04, spot_size=math.radians(58), spot_blend=0.85, aim=(-0.6, 1.42, 1.72))),
    ('N_shelf_wash_r', 'SPOT', (0.75, 0.35, 2.40), 58, (1.0, 0.70, 0.42), dict(radius=0.04, spot_size=math.radians(58), spot_blend=0.85, aim=(0.7, 1.42, 1.72))),
    ('N_cred_strip', 'AREA', (0.0, 1.30, 1.37), 5.0, WARM, dict(shape='RECTANGLE', size=2.5, size_y=0.03, aim=(0.0, 1.36, 0.9))),
    ('N_spk_l', 'SPOT', (-1.3, 0.3, 2.40), 24, (1.0, 0.68, 0.40), dict(radius=0.05, spot_size=math.radians(40), spot_blend=0.85, aim=(-1.65, 1.2, 1.35))),
    ('N_spk_r', 'SPOT', (1.3, 0.3, 2.40), 24, (1.0, 0.68, 0.40), dict(radius=0.05, spot_size=math.radians(40), spot_blend=0.85, aim=(1.65, 1.2, 1.35))),
    ('N_tubes', 'POINT', (0.57, 1.30, 1.10), 0.35, (1.0, 0.4, 0.1), dict(radius=0.08)),
    ('N_moon', 'SUN', (-6, -0.8, 4.0), 1.5, MOON, dict(angle=math.radians(2), aim=(-1.0, -0.2, 0.9))),
    ('N_fill', 'AREA', (0.0, -2.2, 2.0), 4, (0.42, 0.56, 1.0), dict(shape='SQUARE', size=0.7, aim=(0.0, 0.6, 1.1))),
    ('N_lounge_fill', 'AREA', (-2.4, -1.9, 2.3), 5, (0.55, 0.62, 0.9), dict(shape='SQUARE', size=0.6, aim=(-3.3, -1.2, 0.9))),
    ('B_stairs', 'AREA', (-2.7, 4.2, -1.3), 55, COLD, dict(shape='SQUARE', size=0.8, aim=(-2.7, 2.2, 0.2))),
]
WORLD = dict(night=(0.0015, 0.002, 0.004))

# ---- grey blockout of every zone, so each agent sees the rest of the room in previews: part -> [(x0,x1,y0,y1,z0,z1)] ----
def _stairs():
    s = STAIRS; out = []
    for i in range(s['steps']):
        y = s['top_y'] + i * s['step_run']; z = -(i + 1) * s['step_rise']
        out.append((s['x0'], s['x1'], y, y + s['step_run'], z - 0.2, z))
    out.append((s['x0'], s['x1'], s['y0'], s['top_y'], -0.2, 0.0))                       # landing
    out += [(s['x0'] - 0.1, s['x0'], s['y0'], s['y1'], -2.4, 2.45), (s['x1'], s['x1'] + 0.1, s['y0'], s['y1'], -2.4, 2.45),
            (s['x0'], s['x1'], s['y1'], s['y1'] + 0.1, -2.4, 2.45), (s['x0'], s['x1'], s['y0'], s['y1'], 2.45, 2.55),
            (s['x0'], s['x1'], s['y0'], s['y1'], -2.5, -2.4)]
    return out

BLOCKS = dict(
    shell=[(-3.4, 3.4, -2.6, 1.6, -0.1, 0.0), (2.05, 3.4, 1.6, 3.5, -0.1, 0.0),                 # floors
           (-3.5, 3.5, -2.7, 1.7, 2.45, 2.55), (1.95, 3.5, 1.6, 3.6, 2.45, 2.55),               # ceilings
           (-3.5, -3.4, -2.6, -1.5, 0, 2.45), (-3.5, -3.4, -0.1, 1.6, 0, 2.45), (-3.5, -3.4, -1.5, -0.1, 0, 1.5), (-3.5, -3.4, -1.5, -0.1, 2.25, 2.45),   # left wall + window
           (3.4, 3.5, -2.6, 3.5, 0, 2.45),                                                      # right wall
           (-3.5, -3.1, 1.6, 1.7, 0, 2.45), (-3.1, -2.3, 1.6, 1.7, 2.0, 2.45), (-2.3, 2.2, 1.6, 1.7, 0, 2.45),
           (2.2, 3.25, 1.6, 1.7, 2.05, 2.45), (3.25, 3.5, 1.6, 1.7, 0, 2.45),                    # back wall + door + nook opening
           (-3.5, 3.5, -2.7, -2.6, 0, 2.45),                                                    # front wall (behind the viewer)
           (1.95, 3.5, 3.5, 3.6, 0, 2.45), (1.95, 2.05, 1.7, 3.5, 0, 2.45)] + _stairs(),         # nook walls
    counter=[(-2.2, 2.2, -0.80, -0.34, 0, 0.97), (-2.25, 2.25, -0.95, -0.25, 0.97, 1.02)]
            + [(x - 0.17, x + 0.17, y - 0.17, y + 0.17, 0.70, 0.76) for x, y in STOOLS]
            + [(x - 0.2, x + 0.2, y - 0.2, y + 0.2, 1.72, 1.95) for x, y in PENDANTS],
    shelves=[(-1.95, 1.95, 1.12, 1.60, 0, 0.90), (-1.30, 1.30, 1.27, 1.60, 1.36, 1.40), (-1.30, 1.30, 1.27, 1.60, 1.72, 1.76),
             (-1.30, 1.30, 1.27, 1.60, 2.08, 2.12), (-1.30, 0.45, 1.29, 1.60, 1.40, 1.715), (-1.30, 0.45, 1.29, 1.60, 1.76, 2.075),
             (0.5, 1.3, 1.35, 1.58, 1.40, 1.68), (0.5, 1.3, 1.35, 1.58, 1.76, 2.0), (-0.7, 0.2, 1.3, 1.55, 0.90, 1.18)],
    hifi=[(-1.95, -1.35, 1.14, 1.58, 0.90, 1.95), (1.35, 1.95, 1.14, 1.58, 0.90, 1.95), (-0.88, -0.40, -0.70, -0.32, 1.02, 1.13),
          (0.25, 0.90, 1.2, 1.55, 0.90, 1.12), (-1.25, -0.75, 1.25, 1.55, 0.90, 1.36), (0.98, 1.28, 1.3, 1.5, 0.90, 1.24)],
    nook=[(2.35, 3.15, 2.2, 2.9, 0.68, 0.72), (2.05, 3.4, 3.0, 3.5, 0, 0.85)],
    lounge=[(-3.4, -2.8, -1.5, 0.0, 0, 1.25), (-3.4, -3.15, 0.55, 0.95, 0.97, 1.0), (-3.2, -3.0, 0.1, 0.3, 0, 1.6)],
    cat=[],
)

# ---- interactive meshes: EXACT object names in the GLB.  name -> (part, pivot/origin, (sx, sy, sz) rough size) ----------
# Positions are binding to within a few cm; the pivot is where the object's origin must be (kit.interactive(origin=...)).
def _I():
    d = dict(
        door=('shell', (-3.1, 1.6, 0.0), (0.8, 0.04, 2.0)),            # pivot = hinge axis; leaf modelled ajar ~20 deg into the stairwell
        note=('counter', (0.0, -0.80, 1.02), (0.10, 0.05, 0.07)),       # folded tent card left by the owner
        cigarbox=('counter', (0.78, -0.38, 1.02), (0.24, 0.18, 0.06)),
        matchbook=('counter', (0.34, -0.74, 1.02), (0.05, 0.04, 0.012)),
        paperback=('counter', (-0.30, -0.80, 1.02), (0.13, 0.19, 0.05)),  # face-down, tented open
        cigar=('counter', cigar_point(CIGAR_REST), (0.09, 0.13, 0.02)),      # the perfecto in the ashtray: body + band + ember; pivot in the notch
        cigar_ash=('counter', cigar_point(CIGAR['burn']), (0.012, 0.016, 0.012)),  # its ash, a separate piece (it grows and is tapped off); pivot on the burn line
        platter_record=('hifi', (-0.69, -0.51, 1.115), (0.30, 0.30, 0.004)),   # pivot = spindle; spins about Z
        tonearm=('hifi', (-0.47, -0.37, 1.13), (0.04, 0.24, 0.03)),      # pivot = arm pivot; swings about Z
        reel_l=('hifi', (-1.13, 1.26, 1.24), (0.18, 0.02, 0.18)),        # pivot = hub; spins about Y
        reel_r=('hifi', (-0.87, 1.26, 1.24), (0.18, 0.02, 0.18)),
        nowplaying=('hifi', (1.12, 1.38, 0.92), (0.315, 0.03, 0.315)),   # sleeve on a stand, cover faces -Y
        manuscript=('nook', (2.70, 2.45, 0.72), (0.26, 0.36, 0.03)),     # stack of squared manuscript paper, pen beside it
        radio=('nook', (3.22, 3.25, 0.85), (0.24, 0.08, 0.15)),
        phone=('lounge', (-3.28, 0.75, 1.0), (0.2, 0.22, 0.2)),          # pink pay phone on its wall shelf
        piano_keys=('lounge', (-2.72, -0.75, 0.72), (0.16, 1.25, 0.03)),
        clock_hour=('lounge', (-2.7, 1.575, 2.22), (0.02, 0.01, 0.09)),  # pivot = clock centre; hands rotate about Y
        clock_min=('lounge', (-2.7, 1.572, 2.22), (0.015, 0.01, 0.13)),
        clock_sec=('lounge', (-2.7, 1.569, 2.22), (0.006, 0.01, 0.14)),
        mapframe=('lounge', (-3.385, 0.75, 1.70), (0.03, 0.55, 0.42)),   # framed old map on the left wall above the phone
    )
    for i, (x, row) in enumerate([(-1.10, 1.76), (-0.55, 1.76), (0.05, 1.76), (-0.90, 1.40), (-0.35, 1.40), (0.25, 1.40)]):
        d['rec_%d' % i] = ('shelves', (x, 1.24, row), (0.007, 0.315, 0.315))     # LP sleeve standing 3 cm proud; pivot = bottom front corner line
    for i, x in enumerate([0.62, 0.80, 0.98, 1.16]):
        d['book_%d' % i] = ('shelves', (x, 1.33, 1.76), (0.04, 0.16, 0.22))
        d['bottle_%d' % i] = ('shelves', (x, 1.42, 1.40), (0.08, 0.08, 0.28))    # "bottle keep" bottles with name tags
    for k, (pos, rot) in CAT_SPOTS.items(): d[k] = ('cat', pos, (0.3, 0.45, 0.25))
    return d
INTERACTIVE = _I()

# points the web page animates around (Blender coords)
POINTS = dict(smoke=cigar_point(CIGAR['burn'] - 0.004, 0.006), cigar_foot=cigar_point(0.0), cigar_ember=cigar_point(CIGAR['burn']),
              cigar_head=cigar_point(CIGAR['length']), stairs_glow=(-2.7, 3.2, -0.8), phone=(-3.28, 0.75, 1.1), spindle=(-0.69, -0.51, 1.12),
              valves=(0.57, 1.30, 1.10), hob=(2.45, 3.25, 0.95))

def three(p):
    """Blender (x, y, z) -> three.js / glTF (x, z, -y)"""
    return [round(p[0], 4), round(p[2], 4), round(-p[1], 4)]
