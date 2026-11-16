# DEAN'S — a basement jazz bar, a few minutes after closing

Shared brief for every agent on this build. Read all of it, then read `barkit/layout.py` (the binding
layout: every number you need), `barkit/kit.py` and `barkit/mats.py` (the modelling + material kit),
and `parts/example/build.py` (a working example part).

## 1. What we are making

A 3D personal website for Dean (a software engineer who loves jazz, vinyl, books, old maps,
old-school and retro things, and fiction). The site is ONE room: a small basement jazz bar in Tokyo
in the late 1970s — the kind a young novelist-to-be might have run: whisky and records,
always seen at night (the day version was dropped in Nov 2026), a cat that owns the place, and a kitchen table in the back where someone writes
after closing. The visitor sits on a bar stool. Different objects open different parts of the site.

Several agents each MODEL ONE PART of the room in Blender (by Python script). One agent builds the
web page. A separate assembler then puts all parts into one scene, lights it, bakes the (night) lighting
and exports it. You never see the other agents; this document and `layout.py`
are the only coordination, so follow them exactly.

### The mood (art direction — binding)

- **Time and place:** Tokyo, about 1975–1980. Basement, low ceiling, no neon, nothing digital.
  Wood, brass, glass, paper, cloth. Things are used, cared for, slightly worn; nothing is shabby.
- **The moment:** just after closing. The owner has stepped out. One record is still turning. You
  are the only customer. Ordinary and specific — and one or two things are quietly, precisely wrong.
  Understatement is the whole point: realism first, strangeness second, never spooky, never cute.
- **Palette:** walnut and mahogany browns, tobacco, mustard/ochre, bottle green, burnt orange,
  oxblood leather, nicotine-cream plaster, aged brass. NIGHT = pools of warm tungsten light with deep
  soft shadows. The ONLY cold
  colour in the room is a faint blue-green glow coming up the stairwell behind the half-open door.
- **Specificity beats quantity.** A few objects modelled with love (real proportions, bevels,
  wear, a believable arrangement) beat a hundred boxes. Think "still life", not "inventory".
- **Originality (hard rule):** invent everything. No real brands, logos, product designs, band or
  artist names, album titles, book titles, or quotations. No names or titles from any novelist's
  work. Labels and posters carry invented names (English, or simple Japanese — fonts available:
  `Noto Serif CJK JP`, `Noto Sans CJK JP`, `IPAGothic`; find files with `fc-list`). The bar's own
  name is "DEAN'S" and its emblem is a sitting cat seen from behind: use the shared file
  `blender/barkit/cat_emblem.png` (1024 px RGBA, black shape on transparent) wherever the
  emblem appears (coasters, matchbook, posters, labels, curtain), so it is the same cat everywhere.

### The quiet strangeness (who owns which detail)

| Detail | Owner |
|---|---|
| Stairs behind the door go DOWN, deeper than a basement should, old stone, cold glow from below | shell |
| A second, half-finished drink at the next seat, ice not yet melted; a note left by the owner | counter |
| One LP spine on the shelf is pure white, no text; a small sheep figurine among the books | shelves |
| The reel-to-reel is threaded and ready although the record is what is playing | hifi |
| Manuscript page mid-sentence, pen uncapped; a pot of spaghetti on the hob | nook |
| The wall clock is stopped; one of the two umbrellas in the stand is wet, with a small puddle | lounge |
| The cat is somewhere different each visit | cat + web |
| Two moons in the window, the phone that rings once | web |

## 2. The room (summary — `layout.py` has the exact numbers)

Blender coordinates, metres, Z up. +Y is away from the viewer, +X is the viewer's right.
Floor Z=0, ceiling Z=2.45. The viewer's eye is at (0, -1.60, 1.26) on a bar stool, looking +Y.

```
                      back wall  Y = +1.6
  stairs DOWN (shell)                                            kitchen nook (nook)
   beyond the door     ┌───────── back bar (shelves + hifi) ─────────┐   through a wide opening
  ──┤door├─────────────┤ spk │ records  records │ bottles/books │ spk ├──────┤ opening ├──
  x -3.1..-2.3         x -1.95                 0                +1.95        x 2.2..3.25
        lounge:                     aisle behind the counter
        phone, lamp,   ══════════════ counter (counter) ══════════════   top Z 1.02, x -2.2..2.2
  win-  piano (left      [turntable]  lamp  glass  ashtray  cigar box     y -0.95..-0.25
  dow   wall), clock      stools            (viewer)            stools
  (left wall, high)                        eye (0,-1.6,1.26)
                      front wall Y = -2.6 (behind the viewer, never looked at)
```

Camera stops (the only viewpoints that exist; model for these, nothing is ever seen from elsewhere):
`bar` (hero, from the stool), `records` (close on the shelf), `hifi` (down onto the turntable),
`table` (the kitchen table in the nook), `window` (left side: piano, window, phone),
`stairs` (the half-open door and the stairs). Positions are in `layout.STOPS`. The camera eases
between them and has a few degrees of mouse parallax, so allow ~15 cm of slack around each view.

Zones — build ONLY inside your own:

| part | zone | owns |
|---|---|---|
| `shell` | everything architectural | floor, walls, ceiling, window (frame/glass/sill), stair door + stairwell, nook room shell, skirting, pipes, switches |
| `counter` | x -2.25..2.25, y -1.6..-0.25, plus pendants above | counter, foot rail, 4 stools, 4 pendant lamps, till, everything on the counter EXCEPT the turntable zone (`layout.TURNTABLE`) |
| `shelves` | x -1.95..1.95, y 1.1..1.6 | credenza, tiled backsplash, shelving, LP spines, 6 pull-out sleeves, books, bottle-keep bottles, house bottles + glasses, picture-light rail |
| `hifi` | on the counter and credenza, at the reserved spots | turntable (on the counter), valve amp + preamp, reel-to-reel, now-playing stand, the two big speakers, headphones |
| `nook` | x 2.05..3.4, y 1.7..3.5 (+ the short curtain in the opening) | kitchen table + chairs, manuscript, kitchenette, hob + pot, fridge, radio, calendar, bare bulb |
| `lounge` | x -3.4..-2.3, y -2.6..1.6 (floor and walls there) | upright piano + stool, floor lamp, pay phone on its shelf, coat stand, umbrella stand, wall clock, framed old map, posters, a café table with its chairs up |
| `cat` | three spots given in `layout.CAT_SPOTS` | the cat in three poses, plus its bowl and cushion |

Where parts touch (heights are binding): counter top Z=1.02; credenza top Z=0.90; shelf boards top
at Z=1.40 and 1.76, shelving top 2.12; speakers stand on the credenza ends (Z 0.90..1.95); piano top
Z=1.25; nook table top Z=0.72; kitchenette top Z=0.85. Lamp positions (pendants, counter lamp,
floor lamp, nook bulb) are fixed in `layout.py` because the assembler puts the real lights there:
put your lamp MESH exactly there.

Interactive objects: `layout.INTERACTIVE` lists every clickable/animated object — exact GLB name,
owning part, pivot position, rough size. Build each with `kit.interactive(name, origin=...)`.
Names are a hard contract with the web page.

## 3. How a modelling agent works

Your deliverable is ONE Python file `blender/parts/<part>/build.py` (plus painted textures
in `blender/parts/<part>/tex/` made by your own `tex.py`). It must define:

```python
from barkit import kit, mats, layout
def build():            # creates your objects in room coordinates, using kit / mats
    ...
LIGHTS = [...]          # optional small accent lights, same tuple format as layout.LIGHTS
```

Rules for `build()` (the assembler imports your file and calls it inside a scene with all parts):

- Only ADD mesh objects, through the kit helpers (`kit.box`, `lathe`, `cyl`, `tube`, `quad`,
  `cyl_patch`) or, for anything made another way (bpy.ops primitives, modifiers, curves, metaballs,
  bmesh of your own), by finishing with `kit.adopt(obj)`. Never reset the scene, never touch render
  settings, cameras, world or other objects, never create Light objects (declare `LIGHTS`), never
  write files or print loudly, no randomness without a fixed seed. Importing the file must do nothing.
- Take positions from `layout` constants (import them; do not retype numbers).
- Materials: use `mats.*` (wood, metal, plain, noisy, leather, tiles, planks, glass, shade_paper,
  emissive, image, vinyl…) or build your own node materials with `mats.base/N/L/setp` helpers. Must
  be Principled-BSDF based and procedural (noise, wave, voronoi, brick, colour ramps, bump) or use a
  painted image via `mats.image(name, ABSOLUTE_PATH)` with the mesh's `uv_tex` layer. EVERY material
  name starts with your part name (`shelves_walnut`). No network: no downloaded textures or models.
- Light-emitting surfaces: `mats.emissive(name, colour, strength, night_only=True|False)`. Room lamps
  are `night_only=True` (an `EMN_` material), things like hi-fi pilot lamps and valves
  `night_only=False` (`EMA_`); there is only one (night) bake now, so both are lit. Lamp shades that should glow: `mats.shade_paper` around an emissive bulb.
- Glass: `mats.glass`. Liquids: tinted glass. Keep it simple; it all gets baked.
- Everything is baked into ONE 2048² texture atlas per part (hifi may use a second atlas
  `hifi_b`, shelves a second `shelves_b`, by wrapping some objects in `kit.props(atlas='shelves_b')`).
  Texel density is steered with `kit.props(td=...)`: 1.0 normal; 1.5–2.5 for hero objects seen close
  (things on the counter, interactive pieces, labels with text); 0.3–0.6 for big plain or distant
  surfaces. Delete faces that can never be seen (backs against walls, undersides, insides) with
  `kit.box(..., skip='-z +y')` — hidden faces waste atlas space.
- Triangle budget: shell 15k, counter 30k, shelves 40k, hifi 30k, nook 25k, lounge 30k, cat 15k.
  Curved things: 16–32 segments is enough. Bevel the edges that catch light (table tops, cabinet
  edges, equipment) — bevels are what make baked models look real.
- Painted textures (labels, posters, book spines, record sleeves, dials, the manuscript page,
  clock face…): write `tex.py` that paints them with PIL/numpy into `tex/` (one or two sheets,
  ≤ 2048 px), run it yourself, and map regions with `uv_tex`. `build()` must only READ them.

Your commands (never run two Blender processes at once; the machine has 2 cores shared by 8 agents,
so a preview takes 20–90 s — budget about 25 previews in total, and think before each one):

```
python3 blender/barkit/run.py preview <part> [--cam bar|records|hifi|table|window|stairs]
        [--at x,y,z --look x,y,z --fov 40]  [--res 640x360] [--spp 16] [--solo] [--out suffix] [--with otherpart,...]
python3 blender/barkit/run.py baketest <part>
```

`preview` renders your part inside a grey blockout of the rest of the room, under the real room
lights, to `parts/<part>/shots/`. `baketest` pushes your part through the real unwrap + bake + export
pipeline at low resolution and writes `shots/<atlas>.jpg` and
`shots/<part>.glb`. LOOK at every image you make (Read tool) and iterate until it is good.

You are done when: (1) hero-relevant previews look right from every camera
stop that sees your part, plus close-ups of your best objects; (2) `baketest` prints `BAKETEST OK`,
the atlas images show no black/pink/missing islands and the important objects clearly get the most
texels; (3) triangle count is within budget (baketest prints it); (4) all your interactive names
exist (baketest lists them).

Do not edit anything outside `blender/parts/<your part>/`. If `barkit` has a bug, work
around it inside your part and report it. Do not spawn agents. Do not ask questions; decide.

## 4. Final report (your last message)

1. What you built (one paragraph) and the 3–5 best preview image paths.
2. Triangles, atlas names, interactive objects (name → what it is), any `LIGHTS` you declared.
3. Honest assessment: what looks good, what is weak, what the assembler should watch for where your
   part meets others (gaps, overlaps, things that depend on another part's exact geometry).
4. Anything broken or not verified.
