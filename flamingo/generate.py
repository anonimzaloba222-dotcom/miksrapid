#!/usr/bin/env python3
import os
import numpy as np
import manifold3d as m3d
import trimesh
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

SCALE = 1.0
L = 120.0
R = 5.0
SEG = 96
FIT = 0.25
BELLY_CUT = 0.8
PIN_D = 3.0
PIN_X = 58.0
PIN_H = 3.6
HOLE_DEPTH = 4.2

WING_T = 2.0
WING_Z = 2.0
TAIL_T = 1.6

TITLE = "FP-5 «ФЛАМІНГО»"
SUBTITLE = "2025"
STAND_LEN, STAND_W, STAND_H = 140.0, 46.0, 6.0
POST_H = 32.0
POST_Y = 6.0

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")


def to_trimesh(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)


def prism(poly_xy, z0, z1):
    cs = m3d.CrossSection([poly_xy])
    return m3d.Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def plate_xz(poly_xz, thickness):
    cs = m3d.CrossSection([poly_xz])
    p = m3d.Manifold.extrude(cs, thickness).translate([0, 0, -thickness / 2])
    return p.rotate([90, 0, 0])


def along_x(radius_profile):
    pts = [(max(r, 0.0), x) for x, r in radius_profile]
    pts = [(0.0, radius_profile[0][0])] + pts + [(0.0, radius_profile[-1][0])]
    solid = m3d.CrossSection([pts]).revolve(SEG)
    return solid.rotate([0, 90, 0])


def text_solid(text, size, height, font="DejaVu Sans", weight="bold"):
    fp = FontProperties(family=font, weight=weight)
    path = TextPath((0, 0), text, size=size, prop=fp)
    polys = [p for p in path.to_polygons() if len(p) >= 3]
    cs = m3d.CrossSection([[tuple(v) for v in p] for p in polys],
                          m3d.FillRule.EvenOdd)
    (x0, y0, x1, y1) = cs.bounds()
    cs = cs.translate([-(x0 + x1) / 2, -(y0 + y1) / 2])
    return m3d.Manifold.extrude(cs, height)


def fuselage_body():
    prof = []
    nose = 24.0
    for t in np.linspace(0, 1, 40):
        x = nose * t
        prof.append((x, R * np.sqrt(1 - (1 - t) ** 2)))
    prof[0] = (0.0, 0.0)
    prof += [(L - 14.0, R), (L - 1.0, 3.2), (L, 2.6)]
    body = along_x(prof)

    for gx in (24.5, 40.0, 76.0, L - 14.5):
        ring = m3d.Manifold.cylinder(0.5, R + 1, R + 1, SEG).rotate([0, 90, 0])
        inner = m3d.Manifold.cylinder(0.5, R - 0.3, R - 0.3, SEG).rotate([0, 90, 0])
        body = body - (ring - inner).translate([gx, 0, 0])

    nac_r, nac_z = 3.4, R + 4.2
    nac = along_x([(0, 3.0), (2, nac_r), (24, nac_r), (30, 2.4)])
    intake = m3d.Manifold.cylinder(3.0, 2.3, 2.3, SEG).rotate([0, 90, 0])
    nozzle = m3d.Manifold.cylinder(2.5, 1.6, 1.6, SEG).rotate([0, 90, 0])
    nac = nac - intake.translate([-0.5, 0, 0]) - nozzle.translate([28, 0, 0])
    nac = nac.translate([82.0, 0, nac_z])
    pylon = plate_xz([(86, 0), (106, 0), (108, nac_z), (92, nac_z)], 2.2)
    fillet = along_x([(0, 0.6), (4, 1.6), (18, 1.6), (22, 0.6)]) \
        .scale([1, 1, 2.2]).translate([86, 0, nac_z - 2.4])
    body = body + pylon + nac + fillet

    fairing = along_x([(0, 0.0), (4, 2.6), (18, 2.6), (26, 0.0)]) \
        .scale([1, 1, 0.55]).translate([40, 0, R - 0.6])
    body = body + fairing
    return body


def wing_shape(t=WING_T):
    span = 58.0
    root_le, root_c = 44.0, 14.0
    tip_le, tip_c = 47.0, 9.0
    h = span / 2
    poly = [(tip_le + 1.5, -h), (tip_le + tip_c, -h), (root_le + root_c, 0),
            (tip_le + tip_c, h), (tip_le + 1.5, h), (root_le, 0)]
    return prism(poly, -t / 2, t / 2)


def tail_shape(t=TAIL_T, with_fins=True):
    span = 30.0
    h = span / 2
    le_root, c_root = L - 13.0, 10.5
    le_tip, c_tip = L - 9.5, 7.5
    poly = [(le_root, 0), (le_tip, -h), (le_tip + c_tip, -h),
            (le_root + c_root, 0), (le_tip + c_tip, h), (le_tip, h)]
    st = prism(poly, -t / 2, t / 2)
    if with_fins:
        fin = [(le_tip, 0), (le_tip + c_tip, 0), (le_tip + c_tip + 1.0, 8.0),
               (le_tip + 4.5, 8.0)]
        for y in (-h + 0.8, h - 0.8):
            st = st + plate_xz(fin, 1.4).translate([0, y, t / 2 - 0.01])
    return st


def fuselage_printable():
    body = fuselage_body()
    body = body - wing_slot() - tail_slot()
    cut = m3d.Manifold.cube([L + 20, 40, 20]).translate([-10, -20, -R + BELLY_CUT - 20])
    body = body - cut
    hole = m3d.Manifold.cylinder(HOLE_DEPTH + 1, (PIN_D + FIT * 2) / 2, (PIN_D + FIT * 2) / 2, 48)
    body = body - hole.translate([PIN_X, 0, -R + BELLY_CUT - 1])
    return body


def wing_slot():
    poly = [(44.0 - FIT, -20), (58.0 + FIT, -20), (58.0 + FIT, 20), (44.0 - FIT, 20)]
    return prism(poly, WING_Z - WING_T / 2 - FIT, WING_Z + WING_T / 2 + FIT)


def tail_slot():
    poly = [(L - 13.0 - FIT, -20), (L - 2.5 + FIT, -20), (L - 2.5 + FIT, 20),
            (L - 13.0 - FIT, 20)]
    return prism(poly, -TAIL_T / 2 - FIT, TAIL_T / 2 + FIT)


def wing_part():
    return wing_shape()


def rocket_full():
    return (fuselage_body() + wing_shape().translate([0, 0, WING_Z]) +
            tail_shape())


def stand():
    base = m3d.Manifold.cube([STAND_LEN, STAND_W, STAND_H], center=False) \
        .translate([-STAND_LEN / 2, -STAND_W / 2, 0])
    top = m3d.Manifold.cube([STAND_LEN - 4, STAND_W - 4, 0.01]) \
        .translate([-(STAND_LEN - 4) / 2, -(STAND_W - 4) / 2, STAND_H - 0.01])
    bot = m3d.Manifold.cube([STAND_LEN, STAND_W, 0.01]) \
        .translate([-STAND_LEN / 2, -STAND_W / 2, 0])
    base = m3d.Manifold.batch_hull([top, bot])
    frame_o = m3d.Manifold.cube([STAND_LEN - 10, STAND_W - 10, 0.6]) \
        .translate([-(STAND_LEN - 10) / 2, -(STAND_W - 10) / 2, STAND_H - 0.6])
    frame_i = m3d.Manifold.cube([STAND_LEN - 12, STAND_W - 12, 0.6]) \
        .translate([-(STAND_LEN - 12) / 2, -(STAND_W - 12) / 2, STAND_H - 0.6])
    base = base - (frame_o - frame_i)

    t1 = text_solid(TITLE, 8.0, 1.0).translate([0, -11.0, STAND_H])
    t2 = text_solid(SUBTITLE, 5.0, 1.0).translate([-46.0, 9.0, STAND_H])
    base = base + t1 + t2

    post = m3d.Manifold.cylinder(POST_H, 6.0, 3.5, SEG).translate([0, 0, STAND_H])
    collar = m3d.Manifold.cylinder(2.0, 8.0, 6.0, SEG).translate([0, 0, STAND_H])
    pin = m3d.Manifold.cylinder(PIN_H - 0.6, PIN_D / 2, PIN_D / 2, 48) \
        .translate([0, 0, STAND_H + POST_H])
    tip = m3d.Manifold.cylinder(0.6, PIN_D / 2, PIN_D / 2 - 0.5, 48) \
        .translate([0, 0, STAND_H + POST_H + PIN_H - 0.6])
    return base + (post + collar + pin + tip).translate([0, POST_Y, 0])


def lay_flat(man):
    b = man.bounding_box()
    return man.translate([0, 0, -b[2]])


def main():
    os.makedirs(OUT, exist_ok=True)
    s = SCALE
    parts = {
        "fuselage": lay_flat(fuselage_printable().scale([s, s, s])),
        "wing": lay_flat(wing_part().scale([s, s, s])),
        "tail": lay_flat(tail_shape().scale([s, s, s])),
        "stand": lay_flat(stand()),
        "rocket_full": lay_flat(rocket_full().scale([s, s, s])),
    }
    for name, man in parts.items():
        tm = to_trimesh(man)
        assert tm.is_watertight, f"{name} is not watertight"
        tm.export(os.path.join(OUT, f"{name}.stl"))
        bb = tm.bounds
        print(f"{name:12s} {bb[1][0]-bb[0][0]:6.1f} x {bb[1][1]-bb[0][1]:6.1f} x "
              f"{bb[1][2]-bb[0][2]:5.1f} мм, об'єм {tm.volume/1000:6.2f} см³")

    scene = trimesh.Scene()
    layout = {"stand": (0, 0), "fuselage": (-60, 40), "wing": (-50, 85),
              "tail": (40, 85)}
    for name, (dx, dy) in layout.items():
        tm = to_trimesh(parts[name])
        c = tm.bounds.mean(axis=0)
        tm.apply_translation([dx - c[0], dy - c[1], 0])
        scene.add_geometry(tm, node_name=name)
    scene.export(os.path.join(OUT, "flamingo_set.3mf"))
    export_3d()


def export_3d():
    out = os.path.join(os.path.dirname(OUT), "3d")
    os.makedirs(out, exist_ok=True)
    zr = STAND_H + POST_H + R - BELLY_CUT
    pos = [-PIN_X, POST_Y, zr]
    pink = [240, 98, 146, 255]
    grey = [120, 130, 140, 255]
    items = [
        ("stand", stand(), grey),
        ("fuselage", fuselage_printable().translate(pos), pink),
        ("wing", wing_part().translate([-PIN_X, POST_Y, zr + WING_Z]), pink),
        ("tail", tail_shape().translate(pos), pink),
    ]
    y_up = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
    scene = trimesh.Scene()
    for name, man, color in items:
        tm = to_trimesh(man)
        tm.apply_scale(0.001)
        tm.apply_transform(y_up)
        mat = trimesh.visual.material.PBRMaterial(
            name="rocket_pink" if color is pink else "stand_grey", baseColorFactor=color, metallicFactor=0.0, roughnessFactor=0.6)
        tm.visual = trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(tm, node_name=name, geom_name=name)
    scene.export(os.path.join(out, "flamingo.glb"))
    scene.export(os.path.join(out, "flamingo.obj"), mtl_name="flamingo.mtl")
    whole = trimesh.util.concatenate([to_trimesh(m) for _, m, _ in items])
    whole.export(os.path.join(out, "flamingo_assembly.stl"))
    whole.export(os.path.join(out, "flamingo_assembly.ply"))


if __name__ == "__main__":
    main()
