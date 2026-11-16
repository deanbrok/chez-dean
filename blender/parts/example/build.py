"""EXAMPLE PART — shows the conventions. Run:
   python3 blender/barkit/run.py preview example
   python3 blender/barkit/run.py baketest example
"""
from barkit import kit, mats, layout
from barkit.kit import T, Rz

def build():
    # materials: always prefix names with your part name
    brass = mats.metal('example_brass', (0.80, 0.55, 0.22), rough=0.25)
    wood = mats.wood('example_wood', axis='X')
    shade = mats.shade_paper('example_shade', (0.9, 0.62, 0.32))
    bulb = mats.emissive('example_bulb', (1.0, 0.75, 0.45), 30)          # -> "EMN_example_bulb": off in the day bake
    red = mats.plain('example_red', (0.45, 0.05, 0.04), rough=0.4)
    z = layout.COUNTER['top_z']
    # a little lamp standing on the counter. kit.xform() moves everything built inside it.
    with kit.xform(T(0.45, -0.5, z)), kit.props(td=1.5):                  # td = texel density weight (hero objects 1.5-2.5, far/hidden 0.3-0.6)
        kit.lathe('lamp_base', [(0, 0), (0.06, 0), (0.06, 0.012), (0.012, 0.03), (0.01, 0.2), (0, 0.2)], brass)
        kit.lathe('lamp_shade', [(0.10, 0.17), (0.05, 0.27)], shade, segs=24)    # open cone, lit by the bulb inside
        kit.lathe('lamp_bulb', [(0, 0.19), (0.018, 0.2), (0.022, 0.225), (0, 0.245)], bulb, segs=12)
    # an interactive piece: becomes its own mesh "example_box" in the GLB with its pivot at `origin`
    with kit.interactive('example_box', origin=(0.75, -0.5, z), td=2.0):
        kit.box('box', 0.65, 0.85, -0.58, -0.42, z, z + 0.06, wood, bevel=0.004)
        kit.box('box_label', 0.70, 0.80, -0.55, -0.45, z + 0.06, z + 0.061, red)

# optional: extra lights your part needs (the standard room lights already exist, see layout.LIGHTS)
LIGHTS = [('N_example_lamp', 'POINT', (0.45, -0.5, layout.COUNTER['top_z'] + 0.22), 2.0, layout.WARM, dict(radius=0.015))]
