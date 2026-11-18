# Used early-2000s economy hatchback — procedural Blender model

A procedurally built, real-scale 3D model of a fictional, unbadged, base-trim 5-door city hatchback.
It is about 20 years old, has done ~230,000 km and has had three owners. All of the geometry and
materials are generated in Python by Blender (`bpy`). The repo holds no model or texture files apart
from one CC0 HDRI (Poly Haven, *Kloofendal Overcast Puresky*) used for lighting.

```bash
pip install bpy            # or run inside Blender 4.2+/5.x:  blender -b -P build_hatchback.py -- ...
python3 build_hatchback.py --render final --res 2400 --samples 256 --blend hatchback.blend
python3 build_hatchback.py --render none --blend hatchback.blend     # model only
# views: --view front34 | front34L | rear34 | side | detail_front | detail_wheel | interior
```

## Scale and axes
Units are metres. The origin is the centre of ground contact between the four wheels. +Y points forward,
+Z up and +X to the right. The car is left-hand drive, so the driver sits on −X.
Length 3.75, width 1.65, height 1.45, wheelbase 2.40, front/rear overhang 0.75/0.60, track 1.42.
Tyres are 155/70 R13 at a 0.262 m loaded radius.
The body sits about 0.3° nose-down and about 3 mm lower on the driver's side. This is done with the
`Sprung_Body` empty, so the wheels stay planted on the ground.

## How it is built (`hb/`)
| module | contents |
|---|---|
| `body.py` | Cross-section loft, then subdivision, then 1.2 mm sheet metal (solidify). Boolean prisms cut the window openings and wheel arches. 3–5 mm gap cutters split the shell into separate, really-gapped objects: `Body`, `Hood`, `Door_FL/FR/RL/RR` and `Hatch`. The gaps are uneven on purpose (hood gap wider on the right, hatch tighter at the bottom). Each glass pane is the body surface intersected with its window prism and recessed 5 mm. Pivots sit at the hinges. |
| `wheels.py` | The tyre is a mesh with a modelled asymmetric tread: grooves, angled lateral grooves and sipes. Front tyres are more worn. The tyre has a loaded flat spot and sidewall bulge. Also: steel rims, five-slot hubcaps (one odd replacement, one cracked and sitting tilted from a missing clip), front discs with calipers, rear drums, MacPherson struts with coil springs, control arms, bushings, tie rods, CV boots, torsion-beam rear axle and arch liners. Each `Wheel_XX` pivots at the axle centre. |
| `parts.py` | Round halogen headlights (paraboloid reflector, H4 bulb, boot, domed lens), indicators, slatted grille with a broken slat, radiator, swept bumpers with an intake mesh, blank pressed plates with screws, tail lights with separate red/amber/white sections, tow eye, rear fog lamp, rusty tail pipe with soot, mirrors, door handles and locks, side mouldings, wipers (front pair and rear), cowl with dry leaves, window seals and drip rails projected onto the body surface. |
| `interior.py` | Dashboard, gauge cluster (tick marks, no text), single-DIN radio-cassette, three heater knobs, round vents, glovebox, two-spoke steering wheel, cloth seats and rear bench, carpet, mats and coins, pedals, gear lever and handbrake, door cards with window cranks, sagging headliner, visors, mirror with air-freshener tree. Also the engine bay (1.2 L I4, battery with corroded terminals, reservoirs, belts, hoses, harness) and the underbody (exhaust with cat and two silencers on rubber hangers, fuel tank and straps, lines, cables, subframe). |
| `materials.py` | Layered Principled materials, all procedural. Wear masks follow the car's history, driven by world position and normals: UV fade and chalky clear-coat failure on horizontal surfaces; peeling near the rear of the roof; stone chips at the front (to primer, and to bare metal with a rust halo); salt rust at sill ends, arch lips, door bottoms and the hatch lip; arch-lip blisters; touch-up blobs on the right rear fender; shallow cart dents; a tide line, mud behind the wheels, streaks under the mirrors and lamps, pollen and a bird dropping; swirl marks, orange peel and oil-canning bumps; key scratches by the driver's door handle; wiper-arc grime and a scratched driver's window. Bumpers are sun-bleached, scuffed and gouged on the front-right corner. |

## Known limitations
* Textures are **procedural** (resolution-independent shader networks). They are not 8K/4K bitmaps.
  To get image maps, bake them in Blender with Cycles → Bake.
* The GLB/FBX exporters can't carry procedural shaders. Use the `.blend` for rendering.
* The topology comes from subdivision plus booleans. It is suited to rendering, not to a hand-retopologised quad cage.
* Doors, hood and hatch are modelled shut. Hinge geometry is simplified.
* Tyre "markings" are moulded rings only, with no lettering, in line with the brief's no-text rule.
