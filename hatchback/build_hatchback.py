"""Build the used early-2000s economy hatchback and (optionally) render the preview.

Usage (Blender 4.2+ / 5.x, or the `bpy` pip module):
    python3 build_hatchback.py [--render preview|final|none] [--res 2400] [--samples 256]
                               [--view front34|rear34] [--out renders/...png] [--blend out.blend]
    blender -b -P build_hatchback.py -- --render final

Real-world scale in metres, origin at the centre of ground contact between the wheels,
+Y forward, +Z up, +X = right-hand (passenger) side; LHD, driver on -X.
"""
import argparse
import math
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy
import bmesh
from mathutils import Vector, Matrix

from hb import util as U, body as B, materials as MAT, wheels as W, parts as PT, interior as INT


def args():
    a = sys.argv
    a = a[a.index("--") + 1:] if "--" in a else a[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--render", default="preview", choices=["preview", "final", "none"])
    p.add_argument("--res", type=int, default=0)
    p.add_argument("--samples", type=int, default=0)
    p.add_argument("--view", default="front34", choices=["front34", "rear34", "side", "front34L", "detail_front", "detail_wheel", "interior"])
    p.add_argument("--out", default="")
    p.add_argument("--blend", default="")
    p.add_argument("--level", type=int, default=3, help="body subdivision level")
    p.add_argument("--hdri", default=os.path.join(HERE, "assets", "kloofendal_overcast_puresky_2k.hdr"))
    p.add_argument("--dist", type=float, default=0)
    return p.parse_args(a)


def reset():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    U.COLL.clear()


def assign_underbody(o, mat_under):
    me = o.data
    if mat_under.name not in [m.name for m in me.materials if m]:
        me.materials.append(mat_under)
    idx = [m.name if m else "" for m in me.materials].index(mat_under.name)
    for p in me.polygons:
        c = p.center
        if (p.normal.z < -0.35 and c.z < 0.30) or (c.z < 0.62 and abs(c.x) > 0.5 and p.material_index == 0 and
                                                   min(math.hypot(c.y - 1.2, c.z - 0.272), math.hypot(c.y + 1.2, c.z - 0.272)) < 0.333 and abs(c.x) < 0.80):
            p.material_index = idx


def build(level=3):
    t0 = time.time()
    reset()
    M = MAT.build_all()
    print("materials", round(time.time() - t0, 1))
    root = bpy.data.objects.new("Car_Root", None)
    U.coll("Car").objects.link(root)
    sprung = bpy.data.objects.new("Sprung_Body", None)
    U.coll("Car").objects.link(sprung)
    sprung.parent = root
    # stance: slight nose-down (softened springs / front weight) and ~3 mm driver-side sag
    sprung.rotation_euler = (math.radians(-0.32), math.radians(-0.22), 0.0)
    sprung.location = (0, 0, -0.004)

    surf, shell, cutters = B.build_body({"paint": M["paint"], "paint_inner": M["paint_inner"]}, level)
    body, panels = B.separate(shell)
    print("body + panels", list(panels), round(time.time() - t0, 1))
    tree = U.bvh_of(surf)
    glass = B.build_glass(surf, M, cutters)
    glass["Glass_Windshield"].data.materials[0] = M["glass_ws"]
    glass["Glass_Door_FL"].data.materials[0] = M["glass_drv"]
    for c in cutters:
        if c.name in bpy.data.objects:
            U.delete(c)

    pivots = {"Door_FL": (-0.80, 0.80, 0.60), "Door_FR": (0.80, 0.80, 0.60), "Door_RL": (-0.80, -0.12, 0.60),
              "Door_RR": (0.80, -0.12, 0.60), "Hood": (0, 1.03, 0.92), "Hatch": (0, -1.50, 1.415), "FuelFlap": (0.80, -1.31, 0.80)}
    for o in [body] + list(panels.values()):
        U.shade_auto(o, 40)
        assign_underbody(o, M["under"])
        for c in list(o.users_collection):
            c.objects.unlink(o)
        U.coll("Car").objects.link(o)
        if o.name in pivots:
            U.set_origin(o, pivots[o.name])
        o.parent = sprung
    for g in glass.values():
        g.parent = sprung
    # glass in doors moves with the door
    for gname, dname in (("Glass_Door_FL", "Door_FL"), ("Glass_Door_FR", "Door_FR"), ("Glass_Door_RL", "Door_RL"),
                         ("Glass_Door_RR", "Door_RR"), ("Glass_Rear", "Hatch")):
        if dname in panels:
            g = glass[gname]; d = panels[dname]
            g.parent = d
            g.matrix_parent_inverse = d.matrix_basis.inverted()

    W.build_wheels(M, root)
    W.build_suspension(M, sprung)
    W.build_arch_liners(M, sprung)
    PT.build_all(M, sprung, tree)
    INT.build_all(M, sprung, surf)
    U.delete(surf)
    for c in list(bpy.data.collections):
        if c.name in ("Work", "Cutters"):
            for o in list(c.objects):
                U.delete(o)
            bpy.data.collections.remove(c)
    print("built", len(bpy.data.objects), "objects", round(time.time() - t0, 1))
    return root


# ------------------------------------------------------------------ studio
def studio(view, hdri, dist_override=0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Overcast")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    if not os.path.exists(hdri):
        try:
            os.makedirs(os.path.dirname(hdri), exist_ok=True)
            urllib.request.urlretrieve("https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/kloofendal_overcast_puresky_2k.hdr", hdri)
        except Exception as e:
            print("HDRI download failed:", e)
    if os.path.exists(hdri):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri)
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(120))
        nt.links.new(tc.outputs["Generated"], mp.inputs[0]); nt.links.new(mp.outputs[0], env.inputs[0])
        nt.links.new(env.outputs[0], bg.inputs[0])
        bg.inputs[1].default_value = 0.45
    else:
        sky = nt.nodes.new("ShaderNodeTexGradient")
        bg.inputs[0].default_value = (0.75, 0.77, 0.80, 1)
        bg.inputs[1].default_value = 0.8
    nt.links.new(bg.outputs[0], out.inputs[0])

    az = {"front34": 38.0, "rear34": 215.0, "side": 90.0, "front34L": -38.0, "detail_front": 25.0, "detail_wheel": 70.0, "interior": 60.0}[view]
    a = math.radians(az)
    vdir = Vector((math.sin(a), math.cos(a), 0))       # from car towards camera
    right = Vector((0, 0, 1)).cross(vdir).normalized() * -1   # camera right
    # seamless cyclorama behind the car (as seen from the camera)
    prof = []
    R = 3.0
    for k in range(25):
        t = k / 24
        ang = t * math.pi / 2
        prof.append((-7.0 - R * math.sin(ang), R - R * math.cos(ang)))
    prof = [(20.0, 0.0), (5.0, 0.0), (0.0, 0.0), (-4.0, 0.0), (-7.0, 0.0)] + prof[1:] + [(-10.0, 9.0)]
    verts, faces = [], []
    for j, wv in enumerate((-25.0, 25.0)):
        for (u, z) in prof:
            p = vdir * u + right * wv
            verts.append((p.x, p.y, z))
    n = len(prof)
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
    bd = U.new_obj("Backdrop", verts, faces, "Studio", mat=bpy.data.materials["backdrop"])
    bd.data.flip_normals() if False else None

    def area(name, size, energy, loc, target=(0, 0, 0.6), sy=None, glossy=True):
        l = bpy.data.lights.new(name, "AREA")
        l.shape = "RECTANGLE"; l.size = size; l.size_y = sy or size
        l.energy = energy
        l.color = (1.0, 0.99, 0.98)
        o = bpy.data.objects.new(name, l)
        U.coll("Studio").objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        try:
            l.spread = math.radians(110)
        except Exception:
            pass
        if not glossy:
            o.visible_glossy = False
        return o
    key = vdir * 3.0 - right * 5.0 + Vector((0, 0, 5.0))
    area("Key_Softbox", 4.0, 1300, key, sy=2.6)
    fill = vdir * 4.0 + right * 6.0 + Vector((0, 0, 2.2))
    area("Fill", 4.0, 260, fill, sy=3.0)
    rim = -vdir * 6.0 + right * 2.0 + Vector((0, 0, 3.5))
    area("Rim", 2.5, 450, rim, sy=1.2)
    area("Top", 6.0, 380, Vector((0, 0, 5.5)), target=(0, 0, 0), sy=3.0, glossy=False)

    cam = bpy.data.cameras.new("Camera")
    cam.lens = 60
    cam.sensor_width = 36
    co = bpy.data.objects.new("Camera", cam)
    U.coll("Studio").objects.link(co)
    sc.camera = co
    dist = {"front34": 9.3, "rear34": 9.3, "side": 10.5, "front34L": 9.3, "detail_front": 3.2, "detail_wheel": 2.2, "interior": 2.6}[view]
    dist = dist_override or dist
    tgt = {"detail_front": Vector((0.30, 1.75, 0.55)), "detail_wheel": Vector((0.71, 1.20, 0.30)),
           "interior": Vector((-0.1, 0.35, 0.85))}.get(view, Vector((0, 0.0, 0.66)))
    lift = {"detail_front": 0.45, "detail_wheel": 0.15, "interior": 0.55}.get(view, 1.15)
    co.location = tgt + vdir * dist + Vector((0, 0, lift))
    co.rotation_euler = (tgt - co.location).to_track_quat("-Z", "Y").to_euler()
    cam.dof.use_dof = False


def render_settings(kind, res, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    if kind == "preview":
        res = res or 1200
        samples = samples or 64
    else:
        res = res or 2400
        samples = samples or 256
    sc.render.resolution_x = res
    sc.render.resolution_y = int(res * 2 / 3)
    sc.render.resolution_percentage = 100
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.01
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    cy.max_bounces = 12
    cy.glossy_bounces = 6
    cy.transmission_bounces = 12
    cy.transparent_max_bounces = 16
    cy.diffuse_bounces = 4
    cy.blur_glossy = 0.6
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Base Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"


def main():
    a = args()
    build(a.level)
    studio(a.view, a.hdri, a.dist)
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend), compress=True)
        print("saved", a.blend)
    if a.render != "none":
        render_settings(a.render, a.res, a.samples)
        out = a.out or os.path.join(HERE, "renders", "hatchback_%s_%s.png" % (a.view, a.render))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        bpy.context.scene.render.filepath = os.path.abspath(out)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print("rendered", out, round(time.time() - t, 1), "s")


if __name__ == "__main__":
    main()
