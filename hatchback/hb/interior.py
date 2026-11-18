"""Interior (LHD, driver at -X), engine bay and underbody."""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix
from . import util as U
from . import body as B

DRV = -0.37


def rbox(name, size, loc, mat, P, r=0.02, rot=None, ss=1):
    o = U.box(name, size, (0, 0, 0), mat, min(r, min(size) * 0.45), 2, parent=P)
    if ss:
        U.subsurf(o, ss)
    m = Matrix.Translation(Vector(loc))
    if rot is not None:
        m = m @ rot
    U.transform_mesh(o, m)
    U.shade_auto(o, 50)
    return o


def dashboard(M, P):
    prof = U.fillet([(0.985, 0.915), (0.63, 0.905), (0.555, 0.875), (0.545, 0.79), (0.58, 0.62), (0.70, 0.46), (0.98, 0.44)], 0.03, 4)
    o = U.prism("Dashboard", prof, "X", -0.735, 0.735, collection="Car")
    o.hide_render = False
    o.parent = P
    U.set_mat(o, M["dash"])
    U.bevel(o, 0.012, 3, 30)
    U.shade_auto(o, 35)
    # cluster hood + cluster
    hood = rbox("ClusterHood", (0.36, 0.10, 0.06), (DRV, 0.60, 0.925), M["dash"], P, 0.02)
    face = U.cylinder("ClusterFace", 0.155, 0.01, (DRV, 0.56, 0.835), "Y", 48, M["gauge"], parent=P)
    U.transform_mesh(face, Matrix.Scale(1, 4))
    for gx, gr in ((DRV - 0.075, 0.048), (DRV + 0.075, 0.048), (DRV, 0.032)):
        gz = 0.835 if gr > 0.04 else 0.80
        ring = [Vector((gx + gr * math.cos(a), 0.553, gz + gr * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 49)[:-1]]
        U.tube("GaugeRing", ring, 0.0018, 6, M["int_plastic"], P, closed=True, up_hint=(0, 1, 0))
        for k in range(21):   # tick marks, no numerals
            a = math.radians(225 - 270 * k / 20)
            L = 0.009 if k % 5 == 0 else 0.005
            p = Vector((gx + (gr - 0.006 - L / 2) * math.cos(a), 0.5535, gz + (gr - 0.006 - L / 2) * math.sin(a)))
            U.box("Tick", (0.0015, 0.0008, L), p, M["gauge_mark"], 0, parent=P, rot=U.rotm("Y", -(90 - math.degrees(a))))
        U.box("Needle", (0.0022, 0.001, gr * 0.8), Vector((gx, 0.552, gz)) + Vector((-0.3 * gr * 0.4, 0, -0.2 * gr * 0.4)), M["needle"], 0, parent=P, rot=U.rotm("Y", 50))
        U.cylinder("NeedleHub", 0.005, 0.004, (gx, 0.551, gz), "Y", 12, M["gauge"], parent=P)
    U.box("OdoLCD", (0.04, 0.001, 0.012), (DRV - 0.075, 0.5525, 0.81), M["lcd"], 0, parent=P)
    for k in range(6):
        U.cylinder("WarnLamp", 0.0035, 0.001, (DRV - 0.03 + k * 0.012, 0.5525, 0.875), "Y", 10, M["needle"] if k % 2 else M["lcd"], parent=P)
    # scratched clear lens over cluster (separate glass)
    lens = U.box("ClusterLens", (0.30, 0.002, 0.13), (DRV, 0.545, 0.835), M["glass"], 0.004, parent=P, rot=U.rotm("X", 8))
    # center stack: radio-cassette (single DIN), heater knobs, lighter
    U.box("CenterStack", (0.22, 0.04, 0.26), (0.0, 0.565, 0.70), M["int_plastic"], 0.008, parent=P)
    U.box("Radio", (0.180, 0.012, 0.050), (0.0, 0.543, 0.765), M["engine_black"], 0.003, parent=P)
    U.box("CassetteDoor", (0.10, 0.003, 0.016), (0.012, 0.536, 0.772), M["int_plastic"], 0.001, parent=P)
    U.box("RadioDisplay", (0.05, 0.002, 0.012), (0.03, 0.536, 0.752), M["lcd"], 0.0, parent=P)
    for kx in (-0.072, 0.072):
        U.cylinder("RadioKnob", 0.009, 0.012, (kx, 0.533, 0.765), "Y", 16, M["int_plastic"], parent=P)
    for k in range(6):
        U.box("RadioBtn", (0.012, 0.004, 0.007), (-0.045 + k * 0.016, 0.536, 0.748), M["int_plastic"], 0.001, parent=P)
    for kx in (-0.065, 0.0, 0.065):
        U.cylinder("HeaterKnobBase", 0.024, 0.004, (kx, 0.545, 0.66), "Y", 24, M["dash"], parent=P)
        U.cylinder("HeaterKnob", 0.017, 0.018, (kx, 0.537, 0.66), "Y", 24, M["int_plastic"], parent=P)
        U.box("KnobPointer", (0.003, 0.002, 0.012), (kx, 0.527, 0.667), M["gauge_mark"], 0, parent=P)
    U.cylinder("CigLighter", 0.011, 0.012, (0.0, 0.548, 0.605), "Y", 20, M["metal_dirty"], parent=P)
    # round air vents
    for vx in (-0.62, -0.10, 0.10, 0.62):
        U.cylinder("VentHousing", 0.042, 0.03, (vx, 0.555, 0.82), "Y", 32, M["engine_black"], parent=P)
        ring = [Vector((vx + 0.043 * math.cos(a), 0.540, 0.82 + 0.043 * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 41)[:-1]]
        U.tube("VentBezel", ring, 0.004, 8, M["int_plastic"], P, closed=True, up_hint=(0, 1, 0))
        for k in range(5):
            U.box("VentVane", (0.07, 0.006, 0.0018), (vx, 0.545, 0.80 + k * 0.01), M["int_plastic"], 0, parent=P)
    # defroster slots
    for sx in (-0.45, 0.0, 0.45):
        for k in range(4):
            U.box("DefrostSlot", (0.20, 0.004, 0.002), (sx, 0.82 + k * 0.012, 0.9185), M["engine_black"], 0, parent=P)
    # glove box
    U.box("GloveBox", (0.38, 0.012, 0.15), (0.38, 0.575, 0.66), M["dash"], 0.01, parent=P, rot=U.rotm("X", -25))
    U.box("GloveLatch", (0.05, 0.012, 0.018), (0.38, 0.565, 0.72), M["int_plastic"], 0.003, parent=P)


def steering(M, P):
    hub = Vector((DRV, 0.36, 0.80))
    col0 = Vector((DRV, 0.62, 0.70))
    U.tube("SteeringColumn", [col0, hub + Vector((0, 0.04, -0.015))], 0.022, 16, M["int_plastic"], P)
    rbox("ColumnShroud", (0.11, 0.18, 0.09), (DRV, 0.52, 0.74), M["int_plastic"], P, 0.03, rot=U.rotm("X", -22))
    # wheel built in local XZ plane (normal = -Y), then tilted
    R = 0.185
    ring = [Vector((R * math.cos(a), 0, R * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 97)[:-1]]
    w = U.tube("SteeringWheel", ring, 0.0145, 16, M["steering"], None, closed=True, up_hint=(0, 1, 0))
    sp1 = rbox("Spoke", (0.33, 0.016, 0.05), (0, 0.008, -0.03), M["steering"], None, 0.01)
    pad = rbox("HornPad", (0.12, 0.04, 0.10), (0, -0.01, -0.01), M["int_plastic"], None, 0.03)
    w = U.join([w, sp1, pad], "SteeringWheel")
    w.parent = P
    w.location = hub
    w.rotation_euler = (math.radians(-24), 0, 0)


def seats(M, P):
    for s in (1, -1):
        x = s * 0.37
        c = rbox("SeatCushion_" + ("R" if s > 0 else "L"), (0.48, 0.50, 0.11), (x, -0.12, 0.43), M["seat"], P, 0.04, rot=U.rotm("X", 6))
        for bx in (-0.22, 0.22):
            rbox("SeatBolster", (0.07, 0.46, 0.08), (x + bx, -0.12, 0.475), M["seat"], P, 0.03, rot=U.rotm("X", 6))
        br = rbox("SeatBack_" + ("R" if s > 0 else "L"), (0.48, 0.10, 0.58), (x, -0.43, 0.78), M["seat"], P, 0.04, rot=U.rotm("X", -16))
        for bx in (-0.21, 0.21):
            rbox("BackBolster", (0.08, 0.10, 0.50), (x + bx, -0.40, 0.77), M["seat"], P, 0.035, rot=U.rotm("X", -16) @ U.rotm("Z", -s * np.sign(bx) * 10))
        hr = rbox("Headrest", (0.25, 0.065, 0.16), (x, -0.545, 1.16), M["seat"], P, 0.025, rot=U.rotm("X", -12))
        for px in (-0.07, 0.07):
            U.tube("HeadrestPost", [Vector((x + px, -0.53, 1.06)), Vector((x + px, -0.545, 1.10))], 0.0055, 8, M["metal_dirty"], P)
        U.box("SeatBase", (0.40, 0.42, 0.12), (x, -0.10, 0.30), M["engine_black"], 0.01, parent=P)
        for rx in (-0.17, 0.17):
            U.box("SeatRail", (0.03, 0.62, 0.02), (x + rx, -0.08, 0.235), M["metal_dirty"], 0.003, parent=P)
        if s < 0:
            U.box("SeatHeightLever", (0.02, 0.12, 0.02), (x - 0.255, -0.02, 0.38), M["int_plastic"], 0.006, parent=P)
    # rear bench (lighter wear handled by the material)
    rbox("RearCushion", (1.22, 0.48, 0.12), (0, -0.96, 0.43), M["seat"], P, 0.05, rot=U.rotm("X", 5))
    rbox("RearBack", (1.20, 0.10, 0.52), (0, -1.24, 0.73), M["seat"], P, 0.05, rot=U.rotm("X", -18))
    U.box("RearBackHinge", (0.04, 0.02, 0.02), (0.20, -1.17, 0.47), M["metal_dirty"], 0.004, parent=P)


def floor_and_controls(M, P):
    U.box("Carpet", (1.46, 2.0, 0.012), (0, -0.30, 0.205), M["carpet"], 0.004, parent=P)
    U.box("CarpetFirewall", (1.40, 0.012, 0.30), (0, 0.78, 0.36), M["carpet"], 0.004, parent=P, rot=U.rotm("X", -40))
    rbox("Tunnel", (0.22, 1.30, 0.11), (0, 0.05, 0.255), M["carpet"], P, 0.04)
    for (x, y, w, l) in ((DRV, 0.45, 0.42, 0.50), (0.37, 0.45, 0.42, 0.46), (-0.38, -0.62, 0.40, 0.36), (0.38, -0.62, 0.40, 0.36)):
        U.box("FloorMat", (w, l, 0.008), (x, y, 0.215), M["mat"], 0.01, parent=P)
    for (x, y) in ((0.09, 0.30), (0.12, 0.27)):
        U.cylinder("Coin", 0.0115, 0.0018, (x, y, 0.262), "Z", 24, M["metal_dirty"], parent=P)
    for k, px in enumerate((DRV - 0.10, DRV, DRV + 0.10)):
        size = (0.06, 0.015, 0.075) if k < 2 else (0.05, 0.015, 0.11)
        U.box("PedalPad", size, (px, 0.67, 0.31 if k < 2 else 0.30), M["rubber"], 0.006, parent=P, rot=U.rotm("X", -30))
        U.tube("PedalArm", [Vector((px, 0.68, 0.34)), Vector((px, 0.74, 0.58))], 0.006, 8, M["metal_dirty"], P)
    # gear lever with cracked boot, handbrake
    prof = [(0.085, 0.0), (0.07, 0.03), (0.055, 0.06), (0.04, 0.09), (0.025, 0.12), (0.013, 0.15)]
    v, f = U.lathe([(r * (1 + 0.06 * math.sin(i * 2.5)), z) for i, (r, z) in enumerate(prof)], 24, "Z", (0, 0.36, 0.30))
    U.new_obj("GearBoot", v, f, mat=M["int_plastic"], parent=P)
    U.tube("GearStick", [Vector((0, 0.36, 0.40)), Vector((0, 0.34, 0.52))], 0.007, 8, M["metal_dirty"], P)
    U.cylinder("GearKnob", 0.022, 0.05, (0, 0.335, 0.54), "Z", 20, M["int_plastic"], parent=P, bev=0.008)
    U.tube("Handbrake", [Vector((0, -0.05, 0.31)), Vector((0, 0.17, 0.39))], 0.012, 10, M["int_plastic"], P)
    U.tube("HandbrakeGrip", [Vector((0, 0.10, 0.365)), Vector((0, 0.19, 0.395))], 0.017, 10, M["steering"], P)


def door_cards(M, P):
    for s in (1, -1):
        for (ya, yb, front) in ((0.74, -0.10, True), (-0.15, -0.80, False)):
            yc, L = (ya + yb) / 2, (ya - yb)
            x = s * 0.755
            U.box("DoorCard", (0.015, L, 0.62), (x, yc, 0.62), M["int_grey"], 0.008, parent=P)
            U.box("DoorFabric", (0.006, L * 0.75, 0.16), (x - s * 0.009, yc, 0.74), M["fabric_ins"], 0.004, parent=P)
            rbox("Armrest", (0.06, L * 0.5, 0.04), (x - s * 0.03, yc - 0.02, 0.66), M["int_grey"], P, 0.015)
            U.box("PullHandle", (0.03, 0.12, 0.025), (x - s * 0.035, yc + 0.08, 0.80), M["int_plastic"], 0.008, parent=P)
            # manual window crank
            cp = Vector((x - s * 0.012, yc - 0.12, 0.56))
            U.cylinder("CrankHub", 0.016, 0.012, cp, "X", 16, M["int_plastic"], parent=P)
            U.box("CrankArm", (0.008, 0.012, 0.075), cp + Vector((-s * 0.008, 0.0, -0.03)), M["int_plastic"], 0.003, parent=P, rot=U.rotm("X", 30))
            U.cylinder("CrankKnob", 0.009, 0.03, cp + Vector((-s * 0.025, 0.018, -0.06)), "X", 12, M["int_plastic"], parent=P)
            # sagging door pocket
            U.box("DoorPocket", (0.035, L * 0.6, 0.09), (x - s * 0.022, yc, 0.40), M["int_grey"], 0.006, parent=P, rot=U.rotm("Z", s * 2) @ U.rotm("Y", s * 6))


def headliner(M, P, surf):
    me = surf.data.copy()
    o = U.obj_from_mesh("Headliner", me, "Car", P)
    o.data.materials.clear()
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.normal_update()
    kill = [f for f in bm.faces if not (f.normal.z > 0.75 and f.calc_center_median().z > 1.33 and -1.50 < f.calc_center_median().y < 0.27)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    for v in bm.verts:
        sag = 0.012 * max(0.0, min(1.0, (-v.co.y - 0.9) / 0.5))
        v.co.z -= 0.022 + sag
        v.co.x *= 0.985
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    U.set_mat(o, M["headliner"])
    U.solidify(o, 0.006, -1)
    for s in (1, -1):
        U.box("SunVisor", (0.36, 0.20, 0.018), (s * 0.34, 0.12, 1.385), M["headliner"], 0.008, parent=P, rot=U.rotm("X", 30))
    U.tube("MirrorStalk", [Vector((0, 0.20, 1.40)), Vector((0, 0.24, 1.33))], 0.006, 8, M["int_plastic"], P)
    U.box("InteriorMirror", (0.20, 0.025, 0.055), (0, 0.245, 1.315), M["int_plastic"], 0.012, parent=P)
    U.box("InteriorMirrorGlass", (0.185, 0.002, 0.045), (0, 0.232, 1.315), M["reflector"], 0.004, parent=P)
    # generic unbranded air-freshener tree on a string
    U.tube("FreshenerString", [Vector((0.0, 0.245, 1.29)), Vector((0.004, 0.245, 1.21))], 0.0006, 4, M["gauge_mark"], P)
    pts = [(0, 0.0), (0.012, -0.02), (0.006, -0.02), (0.02, -0.045), (0.008, -0.045), (0.026, -0.075), (0.005, -0.075), (0.005, -0.09),
           (-0.005, -0.09), (-0.005, -0.075), (-0.026, -0.075), (-0.008, -0.045), (-0.02, -0.045), (-0.006, -0.02), (-0.012, -0.02)]
    tr = U.prism("AirFreshener", pts, "Y", -0.001, 0.001, collection="Car")
    tr.hide_render = False
    U.set_mat(tr, M["freshener"])
    tr.parent = P
    U.transform_mesh(tr, Matrix.Translation((0.004, 0.245, 1.21)) @ U.rotm("Z", 25))


def engine_bay(M, P):
    U.box("EngineBlock", (0.42, 0.24, 0.28), (0.05, 1.42, 0.50), M["alu_engine"], 0.015, parent=P)
    U.box("CylinderHead", (0.40, 0.22, 0.10), (0.05, 1.42, 0.69), M["alu_engine"], 0.01, parent=P)
    U.box("ValveCover", (0.38, 0.15, 0.055), (0.05, 1.42, 0.765), M["engine_black"], 0.015, parent=P)
    U.box("OilSeepage", (0.39, 0.155, 0.01), (0.05, 1.42, 0.735), M["engine_black"], 0.004, parent=P)
    for k in range(4):
        U.cylinder("SparkBoot", 0.012, 0.05, (-0.10 + k * 0.10, 1.42, 0.80), "Z", 12, M["hose"], parent=P)
        U.tube("HTLead", [Vector((-0.10 + k * 0.10, 1.42, 0.82)), Vector((-0.10 + k * 0.10, 1.33, 0.83)), Vector((0.30, 1.25, 0.76))], 0.0035, 6, M["hose"], P)
    U.cylinder("Gearbox", 0.12, 0.28, (-0.32, 1.38, 0.45), "X", 32, M["alu_engine"], parent=P)
    U.box("AirBox", (0.26, 0.18, 0.10), (0.42, 1.48, 0.72), M["plastic_int"], 0.02, parent=P)
    U.tube("AirIntake", [Vector((0.42, 1.38, 0.72)), Vector((0.30, 1.30, 0.74)), Vector((0.12, 1.32, 0.74))], 0.035, 16, M["hose"], P)
    U.box("Battery", (0.24, 0.17, 0.18), (-0.48, 1.55, 0.62), M["battery"], 0.006, parent=P)
    for tx in (-0.55, -0.41):
        U.cylinder("BatteryTerminal", 0.010, 0.025, (tx, 1.60, 0.72), "Z", 12, M["metal_dirty"], parent=P)
        U.box("TerminalCorrosion", (0.04, 0.035, 0.022), (tx, 1.60, 0.722), M["corrosion"], 0.008, parent=P, ss=1)
    U.cylinder("CoolantTank", 0.055, 0.14, (0.55, 1.18, 0.74), "Z", 24, M["reservoir"], parent=P, bev=0.02)
    U.cylinder("CoolantCap", 0.025, 0.02, (0.55, 1.18, 0.82), "Z", 16, M["engine_black"], parent=P)
    U.cylinder("BrakeBooster", 0.11, 0.08, (-0.42, 1.05, 0.70), "Y", 32, M["engine_black"], parent=P)
    U.box("BrakeFluidRes", (0.08, 0.05, 0.06), (-0.42, 1.12, 0.80), M["reservoir"], 0.01, parent=P)
    for (x, r) in ((0.29, 0.065), (0.29, 0.045)):
        pass
    pul = [(0.30, 1.38, 0.40, 0.065), (0.30, 1.50, 0.62, 0.05), (0.30, 1.32, 0.66, 0.06)]
    for (x, y, z, r) in pul:
        U.cylinder("Pulley", r, 0.025, (x, y, z), "X", 32, M["metal_dirty"], parent=P)
    belt = []
    for (x, y, z, r) in pul + [pul[0]]:
        belt.append(Vector((x, y, z)))
    U.tube("Belt", [Vector((0.30, p.y, p.z)) for p in belt], 0.006, 6, M["hose"], P)
    U.tube("RadHoseTop", [Vector((0.25, 1.48, 0.70)), Vector((0.25, 1.65, 0.68)), Vector((0.22, 1.78, 0.62))], 0.018, 12, M["hose"], P)
    U.tube("RadHoseLow", [Vector((0.15, 1.52, 0.40)), Vector((0.20, 1.68, 0.40)), Vector((0.22, 1.78, 0.42))], 0.018, 12, M["hose"], P)
    U.tube("Harness", [Vector((-0.48, 1.62, 0.75)), Vector((-0.30, 1.62, 0.78)), Vector((0.0, 1.55, 0.80)), Vector((0.40, 1.60, 0.78)), Vector((0.60, 1.70, 0.70))], 0.010, 8, M["hose"], P)
    U.box("Firewall", (1.40, 0.02, 0.45), (0, 0.98, 0.62), M["paint_inner"], 0.0, parent=P)
    for s in (1, -1):
        U.box("StrutTower", (0.16, 0.28, 0.40), (s * 0.60, 1.20, 0.62), M["paint_inner"], 0.03, parent=P)
    # hood underside ribs + prop rod (stowed)
    for xx in (-0.45, 0.0, 0.45):
        pts = [Vector((xx, y, B.Z_TOP(y) - 0.022 - 0.03 * abs(xx) ** 2)) for y in np.linspace(1.10, 1.82, 12)]
        U.sweep("HoodRib", pts, [(-0.03, -0.008), (0.03, -0.008), (0.022, 0.004), (-0.022, 0.004)], mat=M["paint_inner"], parent=P)
    U.tube("HoodProp", [Vector((-0.55, 1.83, 0.72)), Vector((0.20, 1.83, 0.72))], 0.004, 8, M["metal_dirty"], P)


def underbody(M, P):
    for x in (-0.55, -0.30, 0.30, 0.55):
        U.box("FloorRib", (0.05, 1.70, 0.012), (x, -0.25, 0.183), M["under"], 0.004, parent=P)
    U.box("Subframe", (1.00, 0.12, 0.06), (0, 1.12, 0.21), M["rust_heavy"], 0.01, parent=P)
    U.box("SubframeOilSeep", (0.30, 0.10, 0.004), (0.05, 1.20, 0.178), M["engine_black"], 0.002, parent=P)
    U.box("OilSump", (0.36, 0.20, 0.08), (0.05, 1.42, 0.33), M["alu_engine"], 0.01, parent=P)
    for x in (-0.60, 0.60):
        U.box("Sill_Underside", (0.06, 1.70, 0.04), (x, 0.0, 0.205), M["under"], 0.01, parent=P)
    # exhaust: manifold -> downpipe -> cat -> mid silencer -> rear silencer -> tailpipe
    path = [Vector((0.05, 1.58, 0.45)), Vector((0.05, 1.62, 0.30)), Vector((0.03, 1.48, 0.21)), Vector((0.0, 1.20, 0.195)), Vector((0.0, 1.05, 0.20))]
    U.tube("Exhaust_Downpipe", path, 0.022, 14, M["exhaust"], P)
    U.cylinder("Exhaust_Cat", 0.062, 0.30, (0.0, 0.88, 0.21), "Y", 24, M["exhaust"], parent=P, bev=0.02, rot=Matrix.Scale(1, 4))
    U.tube("Exhaust_Mid1", [Vector((0.0, 0.72, 0.21)), Vector((0.0, 0.0, 0.215)), Vector((0.0, -0.15, 0.215))], 0.022, 14, M["exhaust"], P)
    U.cylinder("Exhaust_MidSilencer", 0.058, 0.38, (0.0, -0.34, 0.215), "Y", 24, M["exhaust"], parent=P, bev=0.02)
    U.tube("Exhaust_Mid2", [Vector((0.0, -0.53, 0.215)), Vector((-0.10, -0.85, 0.24)), Vector((-0.20, -1.10, 0.31)), Vector((-0.24, -1.30, 0.27))], 0.022, 14, M["exhaust"], P)
    U.box("Exhaust_RearSilencer", (0.36, 0.24, 0.13), (-0.30, -1.44, 0.255), M["exhaust"], 0.05, parent=P)
    U.tube("Exhaust_Out", [Vector((-0.42, -1.50, 0.215)), Vector((-0.45, -1.56, 0.205))], 0.022, 14, M["exhaust"], P)
    for (x, y, z) in ((0.0, 0.25, 0.235), (-0.20, -1.08, 0.33), (-0.30, -1.58, 0.30), (-0.18, -1.40, 0.31)):
        U.cylinder("ExhaustHanger", 0.012, 0.045, (x, y, z), "Z", 12, M["rubber"], parent=P)
    # fuel tank + straps
    U.box("FuelTank", (0.46, 0.42, 0.16), (0.30, -0.78, 0.26), M["under"], 0.03, parent=P)
    for y in (-0.70, -0.88):
        U.box("TankStrap", (0.50, 0.03, 0.004), (0.30, y, 0.178), M["rust"], 0.001, parent=P)
    U.tube("FillerNeck", [Vector((0.50, -0.85, 0.30)), Vector((0.66, -1.10, 0.45)), Vector((0.76, -1.36, 0.78))], 0.022, 12, M["hose"], P)
    # brake/fuel lines, handbrake cables
    for dx in (0.0, 0.012, 0.024):
        U.tube("Line", [Vector((0.40 + dx, 1.0, 0.185)), Vector((0.40 + dx, -0.5, 0.18)), Vector((0.42 + dx, -1.0, 0.185))], 0.0025, 6, M["metal_dirty"], P)
    for s in (1, -1):
        U.tube("HandbrakeCable", [Vector((0.0, -0.10, 0.19)), Vector((s * 0.25, -0.55, 0.185)), Vector((s * 0.52, -1.05, 0.22)), Vector((s * 0.56, -1.17, 0.24))], 0.004, 6, M["hose"], P)


def build_all(M, P, surf):
    dashboard(M, P)
    steering(M, P)
    seats(M, P)
    floor_and_controls(M, P)
    door_cards(M, P)
    headliner(M, P, surf)
    engine_bay(M, P)
    underbody(M, P)
