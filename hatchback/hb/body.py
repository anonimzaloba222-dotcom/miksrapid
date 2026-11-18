"""Body shell: lofted cross-sections -> subdivision -> sheet metal -> boolean panel gaps -> separate panels."""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix
from . import util as U

# ------------------------------------------------------------------ dimensions (metres)
WB = 2.40
YF, YR = WB / 2, -WB / 2          # axle positions
TRACK = 1.42
WHEEL_R_LOADED = 0.262
ARCH_R = 0.335
ARCH_ZC = 0.272


def tab(pairs):
    a = np.array(pairs, dtype=float)
    return lambda y: float(np.interp(y, a[:, 0], a[:, 1]))


Z_TOP = tab([(-1.800, 0.86), (-1.792, 0.93), (-1.775, 1.00), (-1.74, 1.10), (-1.70, 1.19), (-1.66, 1.268),
             (-1.62, 1.333), (-1.57, 1.383), (-1.50, 1.414), (-1.35, 1.434), (-0.9, 1.447), (-0.3, 1.452),
             (0.10, 1.448), (0.20, 1.437), (0.265, 1.418), (0.60, 1.186), (0.965, 0.925), (1.05, 0.908),
             (1.20, 0.888), (1.50, 0.848), (1.75, 0.808), (1.84, 0.792), (1.88, 0.775), (1.90, 0.75)])
Z_B = tab([(-1.80, 0.34), (-1.70, 0.26), (-1.45, 0.205), (-1.0, 0.19), (1.0, 0.19), (1.55, 0.22),
           (1.80, 0.28), (1.90, 0.33)])
W_MAX = tab([(-1.800, 0.745), (-1.790, 0.772), (-1.77, 0.790), (-1.70, 0.802), (-1.5, 0.808), (-1.0, 0.811),
             (0.9, 0.811), (1.5, 0.806), (1.75, 0.792), (1.84, 0.776), (1.88, 0.758), (1.90, 0.735)])
Z_SH = tab([(-1.8, 0.70), (-1.0, 0.68), (0.5, 0.66), (1.9, 0.64)])
BELT = tab([(-1.80, 0.985), (-1.5, 0.99), (-0.8, 0.975), (0.0, 0.958), (0.9, 0.93), (1.9, 0.90)])
W_TOP = tab([(-1.800, 0.690), (-1.775, 0.680), (-1.70, 0.645), (-1.60, 0.618), (-1.2, 0.626), (0.0, 0.633),
             (0.30, 0.636), (0.60, 0.675), (0.88, 0.715), (1.0, 0.722), (1.5, 0.716), (1.75, 0.700),
             (1.84, 0.690), (1.90, 0.660)])
CROWN = tab([(-1.8, 0.012), (-1.6, 0.022), (0.3, 0.026), (0.9, 0.02), (1.9, 0.016)])


def half_ring(y):
    zb, wm, zs = Z_B(y), W_MAX(y), Z_SH(y)
    ztop, wt, cr = Z_TOP(y), W_TOP(y), CROWN(y)
    zt = ztop - cr
    zbelt = min(BELT(y), zt - 0.035)
    wb = wm - 0.012
    p5 = Vector((wb, zbelt))
    p8 = Vector((wt, zt - 0.03))
    p6 = p5.lerp(p8, 0.35)
    p7 = p5.lerp(p8, 0.75)
    pts = [(0.0, zb), (0.45 * wm, zb), (wm - 0.07, zb), (wm - 0.012, zb + 0.06), (wm, zs),
           (p5.x, p5.y), (p6.x, p6.y), (p7.x, p7.y), (p8.x, p8.y), (wt - 0.05, zt),
           (0.55 * wt, zt + 0.6 * cr), (0.0, zt + cr)]
    # keep monotone in z where the greenhouse collapses
    out = []
    for i, (x, z) in enumerate(pts):
        if i > 4 and out:
            z = max(z, out[-1][1] - 0.0) if i < 9 else z
        out.append((x, z))
    return out


def stations():
    s = [-1.800, -1.797, -1.790, -1.778, -1.76, -1.735, -1.70, -1.665, -1.63, -1.60, -1.565, -1.52, -1.45]
    y = -1.35
    while y < 1.75:
        s.append(round(y, 4))
        y += 0.1
    s += [1.76, 1.80, 1.835, 1.86, 1.88, 1.893, 1.899, 1.900]
    return sorted(set(s))


def build_cage():
    st = stations()
    verts, rings = [], []
    for y in st:
        h = half_ring(y)
        ring = [(0.0, y, h[0][1])]
        ring += [(x, y, z) for (x, z) in h[1:-1]]
        ring += [(0.0, y, h[-1][1])]
        ring += [(-x, y, z) for (x, z) in reversed(h[1:-1])]
        rings.append(ring)
    nr = len(rings[0])
    for r in rings:
        verts.extend(r)
    faces = []
    for i in range(len(rings) - 1):
        for j in range(nr):
            a = i * nr + j
            b = i * nr + (j + 1) % nr
            c = (i + 1) * nr + (j + 1) % nr
            d = (i + 1) * nr + j
            faces.append((a, b, c, d))
    # caps: strip quads between right and left halves
    half = (nr - 2) // 2
    for k, base in ((0, 0), (1, (len(rings) - 1) * nr)):
        R = [base + 0] + [base + 1 + i for i in range(half)] + [base + half + 1]
        L = [base + 0] + [base + nr - 1 - i for i in range(half)] + [base + half + 1]
        for i in range(len(R) - 1):
            if i == 0:
                f = (R[0], L[1], R[1])
            elif i == len(R) - 2:
                f = (R[i], L[i], R[i + 1])
            else:
                f = (R[i], L[i], L[i + 1], R[i + 1])
            if k == 1:
                f = tuple(reversed(f))
            faces.append(f)
    return verts, faces


def body_surface(level=3):
    v, f = build_cage()
    o = U.new_obj("BodySurface", v, f, "Work")
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    U.subsurf(o, level)
    return o


# ------------------------------------------------------------------ window and gap layouts (side view y,z)
def windshield_y(z):
    return 0.965 - (z - 0.925) / (1.418 - 0.925) * (0.965 - 0.265)


FRONT_WIN = [(0.73, 0.978), (0.252, 1.352), (-0.088, 1.352), (-0.088, 0.978)]
REAR_WIN = [(-0.152, 0.982), (-0.152, 1.352), (-0.655, 1.352), (-0.786, 1.13), (-0.786, 0.99)]
QUARTER_WIN = [(-0.885, 0.995), (-0.885, 1.345), (-1.13, 1.342), (-1.335, 1.09), (-1.34, 1.02)]


def gap_lines():
    """Panel gap polylines (axis, pts, width, a0, a1)."""
    G = []
    for s in (1, -1):
        x0, x1 = (0.40, 1.2) if s > 0 else (-1.2, -0.40)
        G.append(("X", [(0.80, 0.235), (0.80, 0.94), (0.79, 0.975), (0.245, 1.383), (0.215, 1.388), (-0.835, 1.388)], 0.0042, x0, x1))
        G.append(("X", [(-0.12, 1.42), (-0.12, 0.23)], 0.0045, x0, x1))
        G.append(("X", [(-0.825, 1.42), (-0.825, 0.62), (-0.835, 0.45), (-0.83, 0.23)], 0.0040, x0, x1))
        G.append(("X", [(0.83, 0.272), (-0.85, 0.272)], 0.0038, x0, x1))
    # hood: uneven, wider on the right (+X)
    G.append(("Z", [(0.704, 1.99), (0.704, 1.03), (0.0, 1.03)], 0.0052, 0.72, 1.25))
    G.append(("Z", [(0.0, 1.03), (-0.700, 1.03), (-0.700, 1.99)], 0.0036, 0.72, 1.25))
    G.append(("X", [(1.78, 0.745), (2.05, 0.745)], 0.0042, -0.712, 0.712))
    # rear hatch (tighter at the bottom)
    G.append(("X", [(-1.50, 1.0), (-1.50, 1.62)], 0.0042, -0.668, 0.668))
    G.append(("Y", [(0.66, 1.50), (0.66, 0.565), (-0.66, 0.565), (-0.66, 1.50)], 0.0032, -2.1, -1.49))
    return G


def build_body(mats, level=3):
    surf = body_surface(level)
    surf.data.materials.append(mats["paint"])
    surf.data.materials.append(mats["paint_inner"])
    shell = U.obj_from_mesh("BodyShell", surf.data.copy(), "Work")
    U.solidify(shell, 0.0012, -1.0, mat_offset=1)
    cut = []

    # wheel arches
    for ya in (YF, YR):
        for s in (1, -1):
            x0, x1 = (0.50, 1.2) if s > 0 else (-1.2, -0.50)
            cut.append(U.prism("arch", U.circle_poly(ya, ARCH_ZC, ARCH_R, 96), "X", x0, x1))
    # side windows
    for s in (1, -1):
        x0, x1 = (0.45, 1.2) if s > 0 else (-1.2, -0.45)
        for poly in (FRONT_WIN, REAR_WIN, QUARTER_WIN):
            cut.append(U.prism("win", U.fillet(poly, 0.03, 4), "X", x0, x1))
    # windshield (top view prism)
    ws = [(-0.655, 0.948), (0.655, 0.948), (0.570, 0.292), (-0.570, 0.292)]
    cut.append(U.prism("wsh", U.fillet(ws, 0.05, 5), "Z", 0.90, 1.70))
    # rear glass (rear view prism)
    rg = [(-0.555, 1.06), (0.555, 1.06), (0.530, 1.362), (-0.530, 1.362)]
    cut.append(U.prism("rgl", U.fillet(rg, 0.06, 5), "Y", -2.1, -1.52))
    # headlight holes, indicators, grille opening
    for s in (1, -1):
        cut.append(U.prism("hl", U.circle_poly(s * 0.515, 0.628, 0.086, 64), "Y", 1.70, 2.1))
        cut.append(U.prism("ind", U.fillet([(s * 0.632, 0.585), (s * 0.700, 0.585), (s * 0.700, 0.672), (s * 0.632, 0.672)], 0.012, 3), "Y", 1.70, 2.1))
    cut.append(U.prism("grl", U.fillet([(-0.36, 0.565), (0.36, 0.565), (0.36, 0.700), (-0.36, 0.700)], 0.03, 4), "Y", 1.70, 2.1))
    # fuel flap (rear right quarter)
    cut.append(U.gap_cutter("fuel", U.circle_poly(-1.37, 0.80, 0.064, 48) + [U.circle_poly(-1.37, 0.80, 0.064, 48)[0]], 0.0035, "X", 0.55, 1.2))

    for c in cut:
        U.boolean(shell, c)
    for (ax, pts, w, a0, a1) in gap_lines():
        c = U.gap_cutter("gap", pts, w, ax, a0, a1)
        U.boolean(shell, c)
        cut.append(c)
    return surf, shell, cut


def classify(parts):
    named = {}
    body_parts = []
    for p in parts:
        n = len(p.data.vertices)
        co = np.zeros(n * 3); p.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        c = co.mean(0); mn = co.min(0); mx = co.max(0)
        name = None
        if n < 60:
            body_parts.append(p); continue
        if mx[2] > 0.70 and c[1] > 1.0 and mn[1] > 0.9 and mn[2] > 0.70 and abs(c[0]) < 0.2:
            name = "Hood"
        elif c[1] < -1.6 and abs(c[0]) < 0.2 and mn[2] > 0.5 and mx[0] < 0.70:
            name = "Hatch"
        elif mn[1] > -0.14 and mx[1] < 0.82 and abs(c[0]) > 0.6 and mn[2] > 0.2 and (mx[0] - mn[0]) < 0.4:
            name = "Door_FR" if c[0] > 0 else "Door_FL"
        elif mn[1] > -0.85 and mx[1] < -0.10 and abs(c[0]) > 0.6 and mn[2] > 0.2 and (mx[0] - mn[0]) < 0.4:
            name = "Door_RR" if c[0] > 0 else "Door_RL"
        elif (mx[1] - mn[1]) < 0.16 and c[0] > 0.7 and abs(c[1] + 1.37) < 0.05:
            name = "FuelFlap"
        if name and name not in named:
            named[name] = p
        else:
            body_parts.append(p)
    return named, body_parts


def separate(shell):
    parts = U.split_loose(shell)
    named, rest = classify(parts)
    rest.sort(key=lambda o: -len(o.data.vertices))
    body = U.join(rest, "Body") if len(rest) > 1 else rest[0]
    body.name = "Body"
    for k, o in named.items():
        o.name = k
        o.data.name = k
    return body, named


# ------------------------------------------------------------------ glass
def build_glass(surf, mats, cutters):
    """Glass = body surface pushed inward, made 3.6 mm thick, intersected with enlarged window prisms."""
    out = {}
    specs = []
    for s, side in ((1, "R"), (-1, "L")):
        x0, x1 = (0.45, 1.2) if s > 0 else (-1.2, -0.45)
        specs.append(("Glass_Door_F" + side, U.fillet(FRONT_WIN, 0.03, 4), "X", x0, x1, 0.012))
        specs.append(("Glass_Door_R" + side, U.fillet(REAR_WIN, 0.03, 4), "X", x0, x1, 0.012))
        specs.append(("Glass_Quarter_" + side, U.fillet(QUARTER_WIN, 0.03, 4), "X", x0, x1, 0.012))
    ws = [(-0.655, 0.948), (0.655, 0.948), (0.570, 0.292), (-0.570, 0.292)]
    specs.append(("Glass_Windshield", U.fillet(ws, 0.05, 5), "Z", 0.90, 1.70, 0.016))
    rg = [(-0.555, 1.06), (0.555, 1.06), (0.530, 1.362), (-0.530, 1.362)]
    specs.append(("Glass_Rear", U.fillet(rg, 0.06, 5), "Y", -2.1, -1.52, 0.016))
    for name, poly, ax, a0, a1, grow in specs:
        g = U.obj_from_mesh(name, surf.data.copy(), "Car")
        g.data.materials.clear()
        # recess: offset inward 5 mm, thickness 3.6 mm
        m = g.modifiers.new("sol", "SOLIDIFY"); m.thickness = 0.0036; m.offset = -1
        U.bake(g)
        bm = bmesh.new(); bm.from_mesh(g.data)
        for v in bm.verts:
            v.co -= v.normal * 0.0
        bm.to_mesh(g.data); bm.free()
        # enlarge polygon
        cu = sum(p[0] for p in poly) / len(poly); cv = sum(p[1] for p in poly) / len(poly)
        big = []
        for (u, v) in poly:
            d = Vector((u - cu, v - cv)); L = d.length
            big.append((u + d.x / L * grow, v + d.y / L * grow))
        c = U.prism(name + "_cut", big, ax, a0, a1)
        U.boolean(g, c, "INTERSECT")
        U.delete(c)
        # push glass inward along its own normals by 5 mm so it sits under the frame
        bm = bmesh.new(); bm.from_mesh(g.data)
        bm.normal_update()
        avg = Vector((0, 0, 0))
        for f in bm.faces:
            avg += f.normal * f.calc_area()
        avg.normalize()
        for v in bm.verts:
            v.co -= avg * 0.005
        bm.to_mesh(g.data); bm.free()
        U.set_mat(g, mats["glass"])
        U.shade_auto(g, 60)
        out[name] = g
    return out
