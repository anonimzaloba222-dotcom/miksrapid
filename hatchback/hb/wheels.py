"""Tyres (155/70 R13 with modelled asymmetric tread), steel wheels, hubcaps, brakes, suspension."""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix
from . import util as U
from .body import YF, YR, TRACK, WHEEL_R_LOADED

R_TIRE = 0.2735
SEC_W = 0.155


def tire_profile():
    # (r, w) from outboard bead across tread to inboard bead, then closing along the rim seat
    half = [(0.1665, 0.0570), (0.1700, 0.0610), (0.1800, 0.0675), (0.1950, 0.0735), (0.2100, 0.0768),
            (0.2220, 0.0775), (0.2350, 0.0762), (0.2460, 0.0730), (0.2550, 0.0680), (0.2625, 0.0625),
            (0.2685, 0.0560), (0.2722, 0.0470)]
    out = list(half)
    nt = 36
    for i in range(1, nt):
        w = 0.0470 - 0.094 * i / nt
        out.append((R_TIRE - 0.0012 * (2 * w / 0.094) ** 2 + 0.0012, w))
    out += [(r, -w) for (r, w) in reversed(half)]
    return out


def resample(prof, step):
    P = [np.array(p, float) for p in prof]
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        L = np.linalg.norm(b - a)
        n = max(1, int(math.ceil(L / step)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out)


def tread_depth(theta, w, depth, seed):
    """Asymmetric tread: two circumferential grooves, angled lateral grooves, sipes."""
    N = 58
    ph = theta * N / (2 * math.pi)
    d = np.zeros_like(theta)
    tread = np.abs(w) < 0.058
    g1 = np.abs(w + 0.021) < 0.0042
    g2 = np.abs(w - 0.017) < 0.0048
    outer = w > 0.0215
    inner = w < -0.0252
    mid = (~outer) & (~inner) & (~g1) & (~g2)
    fo = np.mod(ph + (w - 0.02) * 28.0, 1.0)
    fi = np.mod(ph * 1.0 + 0.5 - (w + 0.03) * 18.0, 1.0)
    fm = np.mod(ph * 2.0 + w * 40.0, 1.0)
    lat_o = outer & (fo < 0.11) & (w < 0.060)
    lat_i = inner & (fi < 0.10) & (w > -0.060)
    sipe_o = outer & (np.abs(fo - 0.55) < 0.012)
    sipe_i = inner & (np.abs(fi - 0.55) < 0.012)
    sipe_m = mid & (np.abs(fm - 0.5) < 0.02)
    d[g1 | g2] = depth
    d[lat_o | lat_i] = depth * 0.92
    d[sipe_o | sipe_i | sipe_m] = depth * 0.55
    d[~tread] = 0
    return d


def make_tire(name, depth, seg=900, seed=0, collection="Car"):
    prof = resample(tire_profile(), 0.0022)
    r0 = prof[:, 0]; w0 = prof[:, 1]
    n = len(prof)
    th = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    TH, R = np.meshgrid(th, r0, indexing="ij")
    _, W = np.meshgrid(th, w0, indexing="ij")
    tread_zone = R > 0.262
    # wear: crown worn more than shoulders on the fronts (slightly)
    d = tread_depth(TH, W, depth, seed) * tread_zone
    Rr = R - d
    # assemble: X = lateral, Y/Z = radial
    X = W
    Y = Rr * np.cos(TH)
    Z = Rr * np.sin(TH)
    # loaded flat spot + sidewall bulge at the contact patch
    lim = -WHEEL_R_LOADED
    bulge = np.clip((-Z - 0.20) / 0.07, 0, 1) ** 2
    X = X * (1 + 0.07 * bulge * (R < 0.262) * (R > 0.18))
    Z = np.maximum(Z, lim + 0.0004 * np.cos(W * 30))
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    faces = U.grid_faces(seg, n, close_u=True, close_v=True)
    o = U.new_obj(name, verts, faces, collection)
    return o


def make_rim(name, mat, collection="Car"):
    prof = [(0.1715, 0.0600), (0.1735, 0.0575), (0.1725, 0.0545), (0.1680, 0.0520), (0.1655, 0.0500),
            (0.1650, 0.0380), (0.1500, 0.0280), (0.1460, 0.0150), (0.1460, -0.0300), (0.1500, -0.0360),
            (0.1650, -0.0420), (0.1655, -0.0500), (0.1680, -0.0520), (0.1725, -0.0545), (0.1735, -0.0575),
            (0.1715, -0.0600)]
    v, f = U.lathe([(r, w) for (r, w) in prof], 96, "X")
    o = U.new_obj(name, v, f, collection, mat=mat)
    U.solidify(o, 0.0028, -1)
    disc = [(0.146, 0.005), (0.130, 0.012), (0.105, 0.028), (0.085, 0.040), (0.060, 0.044), (0.032, 0.044), (0.030, 0.040)]
    v, f = U.lathe(disc, 96, "X")
    d = U.new_obj(name + "_disc", v, f, collection, mat=mat)
    U.solidify(d, 0.0035, -1)
    # 4 bolt holes + 4 cooling slots
    cuts = []
    for k in range(4):
        a = math.radians(45 + 90 * k)
        cuts.append(U.prism("bh", U.circle_poly(50e-3 * math.cos(a), 50e-3 * math.sin(a), 0.0065, 16), "X", 0.0, 0.08))
        a = math.radians(90 * k)
        poly = []
        for t in np.linspace(-0.28, 0.28, 8):
            poly.append((0.112 * math.cos(a + t), 0.112 * math.sin(a + t)))
        for t in np.linspace(0.28, -0.28, 8):
            poly.append((0.093 * math.cos(a + t), 0.093 * math.sin(a + t)))
        cuts.append(U.prism("slot", poly, "X", 0.0, 0.08))
    for c in cuts:
        U.boolean(d, c)
        U.delete(c)
    o = U.join([o, d], name)
    U.shade_auto(o, 50)
    return o


def make_hubcap(name, mat, kind="slots", crack=False, collection="Car"):
    if kind == "slots":
        prof = [(0.0005, 0.0745), (0.030, 0.0740), (0.034, 0.0725), (0.040, 0.0705), (0.075, 0.0690),
                (0.110, 0.0670), (0.140, 0.0640), (0.158, 0.0610), (0.168, 0.0580), (0.1725, 0.0545),
                (0.1720, 0.0505)]
    else:
        prof = [(0.0005, 0.0715), (0.026, 0.0712), (0.030, 0.0690), (0.080, 0.0660), (0.120, 0.0650),
                (0.150, 0.0640), (0.165, 0.0600), (0.1715, 0.0550), (0.1712, 0.0505)]
    v, f = U.lathe(prof, 128, "X")
    o = U.new_obj(name, v, f, collection, mat=mat)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
    bm.to_mesh(o.data); bm.free()
    U.solidify(o, 0.0025, -1)
    cuts = []
    if kind == "slots":
        for k in range(5):
            a = 2 * math.pi * k / 5 + 0.3
            ca, sa = math.cos(a), math.sin(a)
            pts = U.rounded_rect(0.052, 0.020, 0.0095, 4)
            poly = [(0.118 * ca + px * ca - py * sa, 0.118 * sa + px * sa + py * ca) for px, py in pts]
            cuts.append(U.prism("hs", poly, "X", 0.03, 0.09))
    else:
        for k in range(8):
            a = 2 * math.pi * k / 8
            cuts.append(U.prism("hh", U.circle_poly(0.118 * math.cos(a), 0.118 * math.sin(a), 0.0135, 20), "X", 0.03, 0.09))
    if crack:
        pts = [(0.0, 0.176), (0.004, 0.160), (-0.003, 0.150), (0.003, 0.138), (-0.001, 0.128)]
        cuts.append(U.gap_cutter("crk", pts, 0.0012, "X", 0.03, 0.09))
    for c in cuts:
        U.boolean(o, c)
        U.delete(c)
    U.shade_auto(o, 45)
    return o


def helix(name, r, z0, z1, turns, wire, mat, center, collection="Car", parent=None, axis_rot=None):
    pts = []
    n = int(turns * 24)
    for i in range(n + 1):
        t = i / n
        a = 2 * math.pi * turns * t
        z = z0 + (z1 - z0) * t
        pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    o = U.tube(name, pts, wire, 8, mat, parent=parent, collection=collection)
    m = Matrix.Translation(Vector(center))
    if axis_rot is not None:
        m = m @ axis_rot
    U.transform_mesh(o, m)
    return o


def build_wheels(M, sprung):
    out = {}
    specs = [("FL", -1, YF, 0.0028), ("FR", 1, YF, 0.0030), ("RL", -1, YR, 0.0050), ("RR", 1, YR, 0.0047)]
    for key, s, ya, depth in specs:
        c = Vector((s * TRACK / 2, ya, WHEEL_R_LOADED))
        tire = make_tire("Tire_" + key, depth, seed=hash(key) % 100)
        U.set_mat(tire, M["tire"])
        rim = make_rim("Wheel_" + key, M["wheel"])
        kind = "holes" if key == "RL" else "slots"
        hub = make_hubcap("Hubcap_" + key, M["hubcap_odd"] if key == "RL" else M["hubcap"], kind, crack=(key == "FR"))
        if s < 0:
            for o in (tire, rim, hub):
                U.transform_mesh(o, Matrix.Scale(-1, 4, (1, 0, 0)))
                o.data.flip_normals()
        # FR hubcap: missing clip -> sits tilted and proud on one side
        if key == "FR":
            U.transform_mesh(hub, Matrix.Translation((0.004, 0, 0)) @ U.rotm("Z", 1.6))
        # brake
        if ya > 0:
            v, f = U.lathe([(0.03, -0.006), (0.119, -0.006), (0.119, 0.006), (0.03, 0.006)], 96, "X")
            disc = U.new_obj("BrakeDisc_" + key, v, f, mat=M["disc"])
            U.transform_mesh(disc, Matrix.Translation((-s * 0.040, 0, 0)))
        else:
            v, f = U.lathe([(0.03, -0.035), (0.100, -0.035), (0.102, -0.030), (0.102, 0.015), (0.06, 0.02), (0.03, 0.02)], 64, "X")
            disc = U.new_obj("BrakeDrum_" + key, v, f, mat=M["rust_heavy"])
            U.transform_mesh(disc, Matrix.Translation((-s * 0.030, 0, 0)))
        for o in (tire, rim, hub, disc):
            o.location = c
        rim.parent = sprung
        for o in (tire, hub, disc):
            o.parent = rim
            o.location = (0, 0, 0)
        rim.location = c
        out[key] = rim
        # non-rotating: caliper (front), backing plate
        if ya > 0:
            cal = U.box("Caliper_" + key, (0.05, 0.075, 0.055), (0, 0, 0), M["caliper"], 0.01, parent=sprung)
            U.transform_mesh(cal, Matrix.Translation(Vector((c.x - s * 0.04, c.y, c.z))) @ U.rotm("X", -40) @ Matrix.Translation((0, -0.105, 0)))
        bp_v, bp_f = U.lathe([(0.03, 0), (0.115, 0), (0.121, -0.012)], 64, "X")
        bp = U.new_obj("BackingPlate_" + key, bp_v, bp_f, mat=M["rust"], parent=sprung)
        U.transform_mesh(bp, Matrix.Translation(c + Vector((-s * (0.058 if ya > 0 else 0.07), 0, 0))) @ (Matrix.Scale(-1, 4, (1, 0, 0)) if s < 0 else Matrix()))
    return out


def build_suspension(M, sprung):
    objs = []
    for s in (1, -1):
        # --- front MacPherson
        hub = Vector((s * 0.62, YF, 0.262))
        top = Vector((s * 0.565, YF - 0.035, 0.80))
        damper = U.tube("Strut_" + ("R" if s > 0 else "L"), [hub + Vector((-s * 0.03, 0, 0.06)), top], 0.025, 16, M["metal_dirty"], parent=sprung)
        rod = U.tube("StrutBody", [hub + Vector((-s * 0.03, 0, 0.05)), hub.lerp(top, 0.55)], 0.0285, 16, M["rust"], parent=sprung)
        axis = (top - hub).normalized()
        rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
        spr = helix("CoilF_" + ("R" if s > 0 else "L"), 0.068, 0.0, 0.30, 5.0, 0.0062, M["engine_black"], hub.lerp(top, 0.42), parent=sprung, axis_rot=rot)
        seat = U.cylinder("SpringSeat", 0.08, 0.008, hub.lerp(top, 0.41), "Z", 24, M["rust"], parent=sprung)
        knuckle = U.box("Knuckle", (0.04, 0.09, 0.16), hub + Vector((-s * 0.075, 0, -0.01)), M["rust"], 0.01, parent=sprung)
        # lower control arm
        objs.append(U.tube("ControlArm", [hub + Vector((-s * 0.06, 0, -0.07)), Vector((s * 0.32, YF + 0.03, 0.215)), Vector((s * 0.33, YF - 0.25, 0.215)), hub + Vector((-s * 0.06, 0, -0.07))], 0.016, 8, M["rust"], parent=sprung))
        for p in (Vector((s * 0.32, YF + 0.03, 0.215)), Vector((s * 0.33, YF - 0.25, 0.215))):
            U.cylinder("Bushing", 0.026, 0.05, p, "Y", 16, M["rubber"], parent=sprung)
        # tie rod + boot
        U.tube("TieRod", [hub + Vector((-s * 0.09, -0.11, 0.03)), Vector((s * 0.33, YF - 0.12, 0.30))], 0.009, 8, M["metal_dirty"], parent=sprung)
        U.cylinder("TieRodEnd", 0.017, 0.035, hub + Vector((-s * 0.09, -0.11, 0.03)), "Z", 12, M["rust"], parent=sprung)
        # drive shaft + CV boots
        U.tube("DriveShaft", [Vector((s * 0.16, YF, 0.29)), hub + Vector((-s * 0.10, 0, 0))], 0.012, 8, M["metal_dirty"], parent=sprung)
        for p0, ln in ((hub + Vector((-s * 0.11, 0, 0)), 0.09), (Vector((s * 0.20, YF, 0.29)), 0.08)):
            prof = [(0.020 + 0.012 * (0.5 + 0.5 * math.cos(k * math.pi / 2)) * (1 - k / 14) + 0.012 * (k < 12) * 0, -ln / 2 + ln * k / 14) for k in range(15)]
            prof = [(0.018 + 0.014 * (1 - k / 14) + 0.004 * math.cos(k * 1.5), -ln / 2 + ln * k / 14) for k in range(15)]
            v, f = U.lathe(prof, 24, "X")
            b = U.new_obj("CVBoot", v, f, mat=M["hose"], parent=sprung)
            U.transform_mesh(b, Matrix.Translation(p0) @ (Matrix.Scale(-1, 4, (1, 0, 0)) if s < 0 else Matrix()))
        # --- rear: trailing arm + torsion beam, spring, damper
        hubr = Vector((s * 0.62, YR, 0.262))
        U.tube("TrailingArm", [hubr + Vector((-s * 0.07, 0, 0)), Vector((s * 0.58, YR + 0.36, 0.285))], 0.028, 12, M["rust"], parent=sprung)
        U.cylinder("ArmBushing", 0.035, 0.05, Vector((s * 0.58, YR + 0.36, 0.285)), "X", 16, M["rubber"], parent=sprung)
        helix("CoilR", 0.055, 0.0, 0.17, 4.0, 0.0058, M["engine_black"], Vector((s * 0.47, YR + 0.03, 0.25)), parent=sprung)
        U.tube("RearDamper", [Vector((s * 0.55, YR - 0.07, 0.21)), Vector((s * 0.54, YR - 0.11, 0.56))], 0.022, 12, M["metal_dirty"], parent=sprung)
    U.tube("TorsionBeam", [Vector((-0.56, YR + 0.07, 0.25)), Vector((0.56, YR + 0.07, 0.25))], 0.032, 12, M["rust_heavy"], parent=sprung)
    # steering rack
    U.tube("SteeringRack", [Vector((-0.33, YF - 0.12, 0.30)), Vector((0.33, YF - 0.12, 0.30))], 0.022, 12, M["metal_dirty"], parent=sprung)
    for s in (1, -1):
        prof = [(0.016 + 0.006 * (0.5 + 0.5 * math.cos(k * 1.6)), 0.08 * k / 14) for k in range(15)]
        v, f = U.lathe(prof, 20, "X")
        b = U.new_obj("RackBoot", v, f, mat=M["hose"], parent=sprung)
        U.transform_mesh(b, Matrix.Translation((s * 0.33, YF - 0.12, 0.30)) @ (Matrix.Scale(-1, 4, (1, 0, 0)) if s < 0 else Matrix()))


def build_arch_liners(M, sprung):
    for ya, front in ((YF, True), (YR, False)):
        for s in (1, -1):
            n = 48
            r = 0.325
            verts, faces = [], []
            a0, a1 = math.radians(-20 if front else -10), math.radians(200 if front else 190)
            xs = (0.52, 0.80)
            for i in range(n + 1):
                a = a0 + (a1 - a0) * i / n
                for x in xs:
                    verts.append((s * x, ya + r * math.cos(a), 0.272 + r * math.sin(a)))
            for i in range(n):
                faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
            # inner wall
            base = len(verts)
            for i in range(n + 1):
                a = a0 + (a1 - a0) * i / n
                verts.append((s * 0.52, ya + r * math.cos(a), 0.272 + r * math.sin(a)))
                verts.append((s * 0.52, ya + 0.0 * math.cos(a), 0.272 + 0.0 * math.sin(a) + 0.12))
            for i in range(n):
                faces.append((base + 2 * i, base + 2 * i + 2, base + 2 * i + 3, base + 2 * i + 1))
            o = U.new_obj("ArchLiner_" + ("F" if front else "R") + ("R" if s > 0 else "L"), verts, faces, mat=M["under"], parent=sprung)
            U.solidify(o, 0.003, 1)
            if s < 0:
                o.data.flip_normals()
