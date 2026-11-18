"""Exterior parts: lamps, grille, bumpers, plates, mirrors, handles, mouldings, wipers, cowl, seals, exhaust."""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix
from . import util as U
from . import body as B


def headlights(M, P):
    for s, side in ((1, "R"), (-1, "L")):
        cx, cz, yf = s * 0.515, 0.628, 1.900
        # reflector bowl (paraboloid) opening at y=1.893, depth ~6 cm
        prof = []
        for k in range(17):
            r = 0.018 + (0.084 - 0.018) * k / 16
            prof.append((r, 1.893 - (0.084 ** 2 - r ** 2) / (4 * 0.028)))
        v, f = U.lathe([(r, y) for (r, y) in prof], 64, "Y", (cx, 0, cz))
        bowl = U.new_obj("Headlight_Reflector_" + side, v, f, mat=M["reflector"], parent=P)
        U.solidify(bowl, 0.002, 1)
        # facets: rotate every other ring segment slightly for a multi-facet look
        # H4 bulb with rubber boot behind
        U.cylinder("H4Bulb_" + side, 0.0065, 0.035, (cx, 1.845, cz), "Y", 16, M["bulb"], parent=P)
        U.cylinder("BulbShield_" + side, 0.008, 0.006, (cx, 1.864, cz), "Y", 16, M["metal_dirty"], parent=P)
        U.cylinder("HeadlightBoot_" + side, 0.035, 0.05, (cx, 1.80, cz), "Y", 24, M["rubber"], parent=P)
        # lens: slightly domed, 3 mm thick
        lp = [(0.0005, yf + 0.010), (0.03, yf + 0.0092), (0.06, yf + 0.0062), (0.080, yf + 0.0025), (0.088, yf - 0.0015), (0.089, yf - 0.012)]
        v, f = U.lathe([(r, y) for (r, y) in lp], 96, "Y", (cx, 0, cz))
        lens = U.new_obj("Headlight_Lens_" + side, v, f, mat=M["hl_lens_" + side], parent=P)
        bm = bmesh.new(); bm.from_mesh(lens.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0006); bm.to_mesh(lens.data); bm.free()
        U.solidify(lens, 0.003, -1)
        # black surround ring
        ring = []
        for k in range(97):
            a = 2 * math.pi * k / 96
            ring.append(Vector((cx + 0.091 * math.cos(a), yf - 0.004, cz + 0.091 * math.sin(a))))
        U.sweep("Headlight_Bezel_" + side, ring[:-1], [(0.0, -0.004), (0.006, -0.003), (0.006, 0.006), (0.0, 0.007), (-0.004, 0.0)],
                closed_path=True, up_hint=(0, 1, 0), mat=M["trim"], parent=P)
        # indicator: amber lens with reflector behind
        ix = s * 0.666
        ind = U.box("Indicator_" + side, (0.066, 0.012, 0.085), (ix, 1.902, 0.6285), M["ind_lens"], 0.006, parent=P)
        U.box("Indicator_Reflector_" + side, (0.060, 0.03, 0.078), (ix, 1.880, 0.6285), M["reflector"], 0.004, parent=P)
        U.cylinder("Indicator_Bulb_" + side, 0.007, 0.02, (ix, 1.875, 0.6285), "Y", 12, M["tail_amber"], parent=P)


def grille(M, P):
    frame = [Vector((x, 1.906, z)) for (x, z) in U.fillet([(-0.362, 0.563), (0.362, 0.563), (0.362, 0.702), (-0.362, 0.702)], 0.03, 4)]
    frame.reverse()
    U.sweep("Grille_Frame", frame, [(-0.004, -0.006), (0.006, -0.006), (0.008, 0.004), (0.0, 0.010), (-0.006, 0.004)],
            closed_path=True, up_hint=(0, 1, 0), mat=M["trim"], parent=P)
    zs = np.linspace(0.580, 0.685, 7)
    for i, z in enumerate(zs):
        if i == 3:   # one slat with a broken-off chunk
            U.box("Grille_Slat_%d_a" % i, (0.40, 0.024, 0.006), (-0.155, 1.895, z), M["trim"], 0.0015, parent=P, rot=U.rotm("X", -18))
            U.box("Grille_Slat_%d_b" % i, (0.24, 0.024, 0.006), (0.235, 1.895, z), M["trim"], 0.0015, parent=P, rot=U.rotm("X", -18))
        else:
            U.box("Grille_Slat_%d" % i, (0.70, 0.024, 0.006), (0, 1.895, z), M["trim"], 0.0015, parent=P, rot=U.rotm("X", -18))
    for x in (-0.12, 0.12):
        U.box("Grille_Rib", (0.008, 0.03, 0.13), (x, 1.893, 0.632), M["trim"], 0.002, parent=P)
    # radiator + fan shroud visible behind slats
    U.box("Radiator", (0.62, 0.035, 0.30), (0, 1.80, 0.52), M["engine_black"], 0.004, parent=P)
    U.box("RadiatorCore", (0.58, 0.012, 0.26), (0, 1.82, 0.52), M["metal_dirty"], 0.0, parent=P)


def bumper(name, M, P, path, prof, z0):
    path3 = [Vector((x, y, z0)) for (x, y) in path]
    o = U.sweep(name, path3, prof, closed_path=False, mat=M["bumper"], parent=P)
    U.subsurf(o, 2)
    U.shade_auto(o, 60)
    return o


def bumpers(M, P):
    fpath_r = [(0.808, 1.545), (0.818, 1.62), (0.822, 1.70), (0.812, 1.79), (0.780, 1.875), (0.700, 1.930), (0.520, 1.956), (0.260, 1.963)]
    fpath = fpath_r + [(0.0, 1.965)] + [(-x, y) for (x, y) in reversed(fpath_r)]
    fprof = [(-0.07, 0.205), (-0.03, 0.200), (0.000, 0.213), (0.016, 0.243), (0.024, 0.300), (0.026, 0.370),
             (0.022, 0.420), (0.012, 0.456), (0.000, 0.470), (-0.05, 0.472)]
    fb = bumper("Bumper_Front", M, P, fpath, list(reversed(fprof)), 0.0)
    rpath_l = [(-0.800, -1.505), (-0.815, -1.56), (-0.822, -1.65), (-0.808, -1.74), (-0.768, -1.815), (-0.680, -1.850), (-0.40, -1.862)]
    rpath = rpath_l + [(0.0, -1.865)] + [(-x, y) for (x, y) in reversed(rpath_l)]
    rprof = [(-0.07, 0.245), (-0.03, 0.240), (0.000, 0.253), (0.016, 0.283), (0.023, 0.340), (0.024, 0.430),
             (0.020, 0.505), (0.010, 0.540), (0.000, 0.553), (-0.05, 0.556)]
    rb = bumper("Bumper_Rear", M, P, rpath, list(reversed(rprof)), 0.0)
    # lower intake with plastic mesh in the front bumper
    U.box("Intake_Recess", (0.58, 0.02, 0.040), (0, 1.975, 0.243), M["engine_black"], 0.008, parent=P)
    mesh_pts = []
    for i in range(30):
        x = -0.28 + 0.56 * i / 29
        U.box("IntakeMeshV", (0.003, 0.006, 0.036), (x, 1.986, 0.243), M["trim"], 0.0, parent=P, rot=U.rotm("Y", 35))
    for z in (0.232, 0.243, 0.254):
        U.box("IntakeMeshH", (0.56, 0.005, 0.003), (0, 1.987, z), M["trim"], 0.0, parent=P)
    # front plate recess + blank plate (pressed border) + screws
    plate(M, P, "Plate_Front", (0, 1.995, 0.345), 0.0)
    plate(M, P, "Plate_Rear", (0, -1.818, 0.705), 180.0)
    # tow eye (rear right), fog lamp slot (rear left), soot stain handled by material
    U.tube("TowEye", [Vector((0.42 + 0.018 * math.cos(a), -1.885, 0.30 + 0.018 * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 25)[:-1]],
           0.0045, 8, M["rust"], parent=P, closed=True, up_hint=(0, 1, 0))
    U.box("TowEyeBoss", (0.03, 0.03, 0.02), (0.42, -1.872, 0.28), M["rust"], 0.004, parent=P)
    U.box("RearFog_Lens", (0.11, 0.012, 0.035), (-0.42, -1.885, 0.31), M["tail_red"], 0.004, parent=P)
    U.box("RearFog_Housing", (0.12, 0.03, 0.045), (-0.42, -1.872, 0.31), M["trim"], 0.004, parent=P)
    return fb, rb


def plate(M, P, name, loc, rotz):
    w, h = 0.520, 0.112
    o = U.box(name, (w, 0.0012, h), (0, 0, 0), M["plate"], 0.0, parent=P)
    # pressed border: raised rim
    rim = [Vector((x, -0.0012, z)) for (x, z) in U.rounded_rect(w - 0.012, h - 0.012, 0.006, 3)]
    r = U.sweep(name + "_Border", rim, [(-0.0015, 0), (0.0015, 0), (0.0012, 0.0012), (-0.0012, 0.0012)], closed_path=True,
                up_hint=(0, -1, 0), mat=M["plate"], parent=P)
    parts = [o, r]
    for sx in (-0.17, 0.17):
        sc = U.cylinder(name + "_Screw", 0.0055, 0.003, (sx, -0.0018, 0.0), "Y", 16, M["rust"], parent=P)
        parts.append(sc)
    j = U.join(parts, name)
    j.parent = P
    U.transform_mesh(j, Matrix.Translation(loc) @ U.rotm("Z", rotz) @ U.rotm("Z", 180))
    return j


def tail_lights(M, P):
    for s, side in ((1, "R"), (-1, "L")):
        x0, x1 = 0.600, 0.735
        cx = s * (x0 + x1) / 2
        w = x1 - x0
        yb = -1.808
        U.box("TailLight_Housing_" + side, (w + 0.008, 0.05, 0.36), (cx, yb + 0.03, 0.795), M["trim"], 0.01, parent=P)
        segs = [("tail_red", 0.875, 0.16), ("tail_amber", 0.745, 0.09), ("tail_clear", 0.672, 0.05), ("tail_red", 0.628, 0.035)]
        for mat, zc, hz in segs:
            U.box("TailLight_Lens_" + mat + "_" + side, (w, 0.010, hz - 0.003), (cx, yb, zc), M[mat], 0.004, parent=P)
            U.box("TailLight_Refl_" + side, (w - 0.012, 0.004, hz - 0.012), (cx, yb + 0.020, zc), M["reflector"], 0.0, parent=P)
            U.cylinder("TailLight_Bulb_" + side, 0.008, 0.02, (cx, yb + 0.012, zc), "Y", 12, M["bulb"], parent=P)


def mirrors(M, P):
    for s, side in ((1, "R"), (-1, "L")):
        base = Vector((s * 0.800, 0.760, 0.995))
        sail = U.box("Mirror_Sail_" + side, (0.03, 0.07, 0.06), base, M["trim"], 0.01, parent=P)
        arm = U.box("Mirror_Arm_" + side, (0.08, 0.035, 0.03), base + Vector((s * 0.05, 0.0, 0.005)), M["trim"], 0.008, parent=P)
        h = U.box("Mirror_Housing_" + side, (0.150, 0.075, 0.105), (0, 0, 0), M["trim"], 0.0, parent=P, ss=2)
        bm = bmesh.new(); bm.from_mesh(h.data)
        for v in bm.verts:   # taper toward the front, flat mirror face at the back
            if v.co.y > 0:
                v.co.x *= 0.92; v.co.z *= 0.88
        bm.to_mesh(h.data); bm.free()
        U.transform_mesh(h, Matrix.Translation(base + Vector((s * 0.135, 0.005, 0.015))) @ U.rotm("Z", -s * 8))
        g = U.box("Mirror_Glass_" + side, (0.125, 0.003, 0.082), base + Vector((s * 0.135, -0.034, 0.015)), M["reflector"], 0.002, parent=P, rot=U.rotm("Z", -s * 8))
        U.shade_auto(h, 60)


def handles(M, P, tree):
    for s, side in ((1, "R"), (-1, "L")):
        for yc, front in ((-0.045, True), (-0.745, False)):
            hit = U.project(tree, [Vector((s * 1.2, yc, 0.875))], (-s, 0, 0))[0]
            x = hit.x if hit else s * 0.80
            U.box("DoorHandle_" + ("F" if front else "R") + side, (0.018, 0.115, 0.030), (x + s * 0.004, yc, 0.875), M["trim"], 0.007, parent=P)
            U.box("DoorHandleRecess_" + ("F" if front else "R") + side, (0.006, 0.09, 0.022), (x + s * 0.0005, yc, 0.875), M["engine_black"], 0.004, parent=P)
            if front:
                U.cylinder("DoorLock_" + side, 0.0085, 0.008, (x + s * 0.003, yc + 0.085, 0.876), "X", 20, M["metal_dirty"], parent=P)
        # side mouldings on doors
        for (ya, yb) in ((0.785, -0.112), (-0.132, -0.812)):
            ys = np.linspace(ya, yb, 40)
            pts = []
            for y in ys:
                hit = U.project(tree, [Vector((s * 1.2, y, 0.525))], (-s, 0, 0))[0]
                pts.append(Vector((hit.x + s * 0.0005 if hit else s * 0.81, y, 0.525)))
            prof = [(0.0, -0.021), (0.006, -0.020), (0.011, -0.012), (0.012, 0.0), (0.011, 0.012), (0.006, 0.020), (0.0, 0.021)]
            prof = [(s * -1 * a if False else a, b) for (a, b) in prof]
            if s > 0:
                pts.reverse()
            U.sweep("SideMoulding_" + side, pts, prof + [(-0.002, 0.0)], closed_path=False, up_hint=(0, 0, 1), mat=M["trim"], parent=P)


def windshield_frame():
    # point on windshield plane at (x, t) where t is distance up the glass from the base line
    p0 = Vector((0, 0.965, 0.925)); d = Vector((0, 0.265 - 0.965, 1.418 - 0.925)).normalized()
    n = Vector((0, -d.z, d.y)) * -1
    if n.z < 0:
        n = -n
    return p0, d, n


def wipers(M, P, tree):
    p0, d, n = windshield_frame()
    for px, length in ((-0.30, 0.50), (0.27, 0.40)):
        piv_g = Vector((px, 0.99, 1.2))
        hit = U.project(tree, [piv_g], (0, 0, -1))[0]
        piv = hit if hit else Vector((px, 0.99, 0.92))
        U.cylinder("WiperPivotCover", 0.017, 0.022, piv + Vector((0, 0, 0.008)), "Z", 20, M["trim"], parent=P)
        U.box("WiperPivotCrack", (0.001, 0.02, 0.003), piv + Vector((0.006, 0, 0.019)), M["engine_black"], 0.0, parent=P)
        # arm: from pivot, rises onto the glass, runs along +X near the bottom of the glass
        a0 = piv + Vector((0, 0, 0.02))
        on = []
        for k in range(9):
            x = px + 0.03 + length * k / 8
            g = Vector((x, 0.0, 0.0))
            # glass point at t=0.06 above the base line
            gp = p0 + d * (0.06 + 0.01 * k / 8) + Vector((x, 0, 0)) + n * 0.022
            on.append(gp)
        arm = U.sweep("WiperArm", [a0] + on, [(-0.006, -0.002), (0.006, -0.002), (0.006, 0.002), (-0.006, 0.002)], up_hint=tuple(n), mat=M["engine_black"], parent=P)
        blade = [p0 + d * (0.06 + 0.01 * k / 8) + Vector((px + 0.06 + length * 0.95 * k / 8 - length * 0.02, 0, 0)) + n * 0.008 for k in range(9)]
        U.sweep("WiperBlade", blade, [(-0.004, -0.004), (0.004, -0.004), (0.004, 0.006), (-0.004, 0.006)], up_hint=tuple(n), mat=M["trim"], parent=P)
        rub = [b - n * 0.0055 for b in blade]
        U.sweep("WiperRubber", rub, [(-0.0015, -0.0025), (0.0015, -0.0025), (0.0006, 0.0015), (-0.0006, 0.0015)], up_hint=tuple(n), mat=M["rubber"], parent=P)
    # rear wiper on the hatch glass
    base = Vector((0.0, -1.73, 1.065))
    hit = U.project(tree, [Vector((0, -2.2, 1.065))], (0, 1, 0))[0]
    if hit:
        base = hit
    U.cylinder("RearWiperPivot", 0.016, 0.03, base + Vector((0, -0.01, 0)), "Y", 20, M["trim"], parent=P)
    pts = []
    for k in range(7):
        x = 0.02 + 0.36 * k / 6
        h = U.project(tree, [Vector((x, -2.2, 1.075))], (0, 1, 0))[0]
        pts.append((h if h else Vector((x, -1.73, 1.075))) + Vector((0, -0.018, 0)))
    U.sweep("RearWiperArm", pts, [(-0.005, -0.002), (0.005, -0.002), (0.005, 0.002), (-0.005, 0.002)], up_hint=(0, -0.3, 1), mat=M["engine_black"], parent=P)
    U.sweep("RearWiperBlade", [p + Vector((0, 0.010, 0)) for p in pts], [(-0.003, -0.004), (0.003, -0.004), (0.003, 0.004), (-0.003, 0.004)], up_hint=(0, -0.3, 1), mat=M["rubber"], parent=P)


def cowl(M, P, tree):
    xs = np.linspace(-0.69, 0.69, 60)
    ys = np.linspace(0.952, 1.025, 6)
    verts, faces = [], []
    for x in xs:
        for y in ys:
            h = U.project(tree, [Vector((x, y, 2.0))], (0, 0, -1))[0]
            verts.append(tuple((h if h else Vector((x, y, 0.92))) + Vector((0, 0, 0.004))))
    faces = U.grid_faces(len(xs), len(ys))
    o = U.new_obj("Cowl", verts, faces, mat=M["trim"], parent=P)
    U.solidify(o, 0.003, 1)
    # vent slots
    for x in np.linspace(-0.55, 0.55, 23):
        if abs(x + 0.30) < 0.04 or abs(x - 0.27) < 0.04:
            continue
        h = U.project(tree, [Vector((x, 0.99, 2.0))], (0, 0, -1))[0]
        if h:
            U.box("CowlSlot", (0.008, 0.045, 0.002), h + Vector((0, 0, 0.0075)), M["engine_black"], 0.0, parent=P, rot=U.rotm("X", -10))
    # a few dried leaves in the corners
    rng = np.random.default_rng(7)
    for i, (x, y) in enumerate([(0.62, 0.975), (0.655, 0.99), (0.60, 1.0), (-0.64, 0.98), (-0.61, 0.995)]):
        h = U.project(tree, [Vector((x, y, 2.0))], (0, 0, -1))[0]
        if not h:
            continue
        L = 0.035 + 0.02 * rng.random()
        n = 9
        vv, ff = [], []
        for k in range(n):
            t = k / (n - 1)
            wd = math.sin(math.pi * t) * L * 0.33
            curl = 0.004 * math.sin(math.pi * t) + 0.003 * (2 * t - 1) ** 2
            vv += [(-wd, L * (t - 0.5), curl + 0.002 * rng.random()), (0, L * (t - 0.5), 0.0), (wd, L * (t - 0.5), curl)]
        for k in range(n - 1):
            ff += [(3 * k, 3 * k + 1, 3 * k + 4, 3 * k + 3), (3 * k + 1, 3 * k + 2, 3 * k + 5, 3 * k + 4)]
        lf = U.new_obj("DryLeaf_%d" % i, vv, ff, mat=M["leaf"], parent=P)
        U.solidify(lf, 0.0004, 0)
        U.transform_mesh(lf, Matrix.Translation(h + Vector((0, 0, 0.009))) @ U.rotm("Z", rng.random() * 360) @ U.rotm("X", rng.normal() * 15))


def seals(M, P, tree):
    """Rubber window seals following the window openings on the real body surface."""
    def loop_x(poly, s):
        pts = U.fillet(poly, 0.03, 4)
        cu = sum(p[0] for p in pts) / len(pts); cv = sum(p[1] for p in pts) / len(pts)
        out = []
        for (u, v) in pts:
            dd = Vector((u - cu, v - cv)).normalized()
            q = (u + dd.x * 0.003, v + dd.y * 0.003)
            h = U.project(tree, [Vector((s * 1.3, q[0], q[1]))], (-s, 0, 0))[0]
            if h:
                out.append(h + Vector((s * 0.0005, 0, 0)))
        return out
    for s, side in ((1, "R"), (-1, "L")):
        for nm, poly in (("FrontDoor", B.FRONT_WIN), ("RearDoor", B.REAR_WIN), ("Quarter", B.QUARTER_WIN)):
            pts = loop_x(poly, s)
            if len(pts) > 6:
                U.tube("Seal_%s_%s" % (nm, side), pts, 0.0042, 8, M["rubber_soft"], P, closed=True, up_hint=(s, 0, 0))
    # windshield & rear glass surrounds
    ws = U.fillet([(-0.655, 0.948), (0.655, 0.948), (0.570, 0.292), (-0.570, 0.292)], 0.05, 5)
    cu = sum(p[0] for p in ws) / len(ws); cv = sum(p[1] for p in ws) / len(ws)
    pts = []
    for (u, v) in ws:
        dd = Vector((u - cu, v - cv)).normalized()
        h = U.project(tree, [Vector((u + dd.x * 0.004, v + dd.y * 0.004, 2.5))], (0, 0, -1))[0]
        if h:
            pts.append(h)
    U.tube("Seal_Windshield", pts, 0.0055, 8, M["rubber_soft"], P, closed=True, up_hint=(0, 0.6, 0.8))
    rg = U.fillet([(-0.555, 1.06), (0.555, 1.06), (0.530, 1.362), (-0.530, 1.362)], 0.06, 5)
    cu = sum(p[0] for p in rg) / len(rg); cv = sum(p[1] for p in rg) / len(rg)
    pts = []
    for (u, v) in rg:
        dd = Vector((u - cu, v - cv)).normalized()
        h = U.project(tree, [Vector((u + dd.x * 0.004, -2.5, v + dd.y * 0.004))], (0, 1, 0))[0]
        if h:
            pts.append(h)
    U.tube("Seal_RearGlass", pts, 0.0055, 8, M["rubber_soft"], P, closed=True, up_hint=(0, -0.9, 0.4))
    # roof drip rails
    for s, side in ((1, "R"), (-1, "L")):
        pts = []
        for y in np.linspace(0.24, -1.46, 50):
            zt = B.Z_TOP(y) - B.CROWN(y) - 0.018
            h = U.project(tree, [Vector((s * 1.2, y, zt))], (-s, 0, 0))[0]
            if h:
                pts.append(h + Vector((0, 0, 0.004)))
        if s < 0:
            pts.reverse()
        U.sweep("DripRail_" + side, pts, [(0.0, -0.002), (0.004, -0.002), (0.0045, 0.004), (0.0, 0.003)], up_hint=(0, 0, 1), mat=M["paint"], parent=P)
        # belt weatherstrips (outer, along the window bottoms)
        for (ya, yb, z) in ((0.74, -0.105, 0.978), (-0.165, -0.79, 0.985)):
            pts = []
            for y in np.linspace(ya, yb, 30):
                h = U.project(tree, [Vector((s * 1.2, y, z - 0.008))], (-s, 0, 0))[0]
                if h:
                    pts.append(h)
            if s < 0:
                pts.reverse()
            U.sweep("BeltSeal_" + side, pts, [(-0.001, -0.006), (0.004, -0.006), (0.005, 0.004), (0.0, 0.006)], up_hint=(0, 0, 1), mat=M["rubber_soft"], parent=P)


def hatch_details(M, P, tree):
    h = U.project(tree, [Vector((0, -2.2, 0.80))], (0, 1, 0))[0]
    y = h.y if h else -1.80
    U.box("Hatch_HandleArea", (0.20, 0.016, 0.045), (0, y - 0.004, 0.80), M["trim"], 0.006, parent=P)
    U.box("Hatch_LockCyl", (0.02, 0.01, 0.02), (0, y - 0.013, 0.80), M["metal_dirty"], 0.004, parent=P)
    # hinges at the roof edge
    for s in (1, -1):
        U.box("HatchHinge", (0.03, 0.04, 0.012), (s * 0.48, -1.50, 1.418), M["engine_black"], 0.003, parent=P)
    # third brake light? (base trim: none). Rubber bump stops
    for s in (1, -1):
        U.cylinder("HatchStop", 0.009, 0.01, (s * 0.60, -1.79, 0.58), "Y", 12, M["rubber"], parent=P)


def exhaust_tip(M, P):
    pts = [Vector((-0.45, -1.55, 0.205)), Vector((-0.45, -1.75, 0.205)), Vector((-0.452, -1.885, 0.215))]
    o = U.tube("Exhaust_Tailpipe", pts, 0.022, 20, M["exhaust"], P)
    U.solidify(o, 0.0015, -1)
    U.cylinder("Exhaust_Soot", 0.0205, 0.004, (-0.452, -1.86, 0.214), "Y", 20, M["engine_black"], parent=P)


def fuel_flap_hinge(M, P):
    U.box("FuelFlap_Hinge", (0.004, 0.012, 0.02), (0.808, -1.31, 0.80), M["engine_black"], 0.001, parent=P)


def build_all(M, P, tree):
    headlights(M, P)
    grille(M, P)
    bumpers(M, P)
    tail_lights(M, P)
    mirrors(M, P)
    handles(M, P, tree)
    wipers(M, P, tree)
    cowl(M, P, tree)
    seals(M, P, tree)
    hatch_details(M, P, tree)
    exhaust_tip(M, P)
    fuel_flap_hinge(M, P)
