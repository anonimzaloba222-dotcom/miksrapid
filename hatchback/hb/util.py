import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

COLL = {}


def coll(name):
    if name in COLL:
        return COLL[name]
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    COLL[name] = c
    return c


def obj_from_mesh(name, mesh, collection="Car", parent=None):
    o = bpy.data.objects.new(name, mesh)
    coll(collection).objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def mesh_from_data(name, verts, faces, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(clean_customdata=False)
    me.update()
    if smooth:
        me.shade_smooth()
    return me


def new_obj(name, verts, faces, collection="Car", smooth=True, mat=None, parent=None):
    o = obj_from_mesh(name, mesh_from_data(name, verts, faces, smooth), collection, parent)
    if mat is not None:
        set_mat(o, mat)
    return o


def set_mat(o, mat, slot=0):
    while len(o.data.materials) <= slot:
        o.data.materials.append(None)
    o.data.materials[slot] = mat


def bake(o, keep_modifiers=False):
    """Apply all modifiers of o into its mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = o.data
    o.modifiers.clear()
    o.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return o


def subsurf(o, levels=2, apply=True):
    m = o.modifiers.new("ss", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    if apply:
        bake(o)
    return o


def solidify(o, t, offset=-1.0, apply=True, mat_offset=0, rim=True):
    m = o.modifiers.new("sol", "SOLIDIFY")
    m.thickness = t
    m.offset = offset
    m.use_even_offset = True
    m.material_offset = mat_offset
    m.use_rim = rim
    if apply:
        bake(o)
    return o


def bevel(o, w, seg=2, angle=40, apply=True):
    m = o.modifiers.new("bev", "BEVEL")
    m.width = w
    m.segments = seg
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.harden_normals = False
    if apply:
        bake(o)
    return o


def boolean(o, cutter, op="DIFFERENCE", solver="MANIFOLD", apply=True):
    m = o.modifiers.new("bool", "BOOLEAN")
    m.operation = op
    m.object = cutter
    m.solver = solver
    if apply:
        bake(o)
    return o


def delete(o):
    me = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def shade_auto(o, angle=35.0):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    a = math.radians(angle)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.calc_face_angle(0.0) < a
        else:
            e.smooth = False
    bm.to_mesh(o.data)
    bm.free()


def transform_mesh(o, mat):
    o.data.transform(mat)
    o.data.update()


def set_origin(o, p):
    """Move object origin to world point p keeping geometry in place (object assumed untransformed)."""
    p = Vector(p)
    o.data.transform(Matrix.Translation(-p))
    o.location = o.location + p


# ---------------------------------------------------------------- primitives

def grid_faces(nu, nv, close_u=False, close_v=False):
    faces = []
    uu = nu if close_u else nu - 1
    vv = nv if close_v else nv - 1
    for i in range(uu):
        for j in range(vv):
            a = i * nv + j
            b = ((i + 1) % nu) * nv + j
            c = ((i + 1) % nu) * nv + (j + 1) % nv
            d = i * nv + (j + 1) % nv
            faces.append((a, b, c, d))
    return faces


def lathe(profile, seg=64, axis="X", center=(0, 0, 0), cap_start=False, cap_end=False, phase=0.0):
    """profile: list of (r, a) where a is coordinate along axis. Returns verts, faces."""
    verts = []
    n = len(profile)
    for i in range(seg):
        t = 2 * math.pi * i / seg + phase
        c, s = math.cos(t), math.sin(t)
        for (r, a) in profile:
            if axis == "X":
                verts.append((center[0] + a, center[1] + r * c, center[2] + r * s))
            elif axis == "Y":
                verts.append((center[0] + r * c, center[1] + a, center[2] + r * s))
            else:
                verts.append((center[0] + r * c, center[1] + r * s, center[2] + a))
    faces = grid_faces(seg, n, close_u=True)
    if cap_start:
        ci = len(verts)
        a = profile[0][1]
        verts.append({"X": (center[0] + a, center[1], center[2]),
                      "Y": (center[0], center[1] + a, center[2]),
                      "Z": (center[0], center[1], center[2] + a)}[axis])
        for i in range(seg):
            faces.append((ci, ((i + 1) % seg) * n, i * n))
    if cap_end:
        ci = len(verts)
        a = profile[-1][1]
        verts.append({"X": (center[0] + a, center[1], center[2]),
                      "Y": (center[0], center[1] + a, center[2]),
                      "Z": (center[0], center[1], center[2] + a)}[axis])
        for i in range(seg):
            faces.append((ci, i * n + n - 1, ((i + 1) % seg) * n + n - 1))
    return verts, faces


def box(name, size, loc=(0, 0, 0), mat=None, bev=0.0, seg=2, collection="Car", parent=None, rot=None, ss=0):
    sx, sy, sz = [s / 2 for s in size]
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = new_obj(name, v, f, collection, mat=mat, parent=parent)
    if bev > 0:
        bevel(o, min(bev, min(size) * 0.49), seg)
    if ss:
        subsurf(o, ss)
    m = Matrix.Translation(Vector(loc))
    if rot is not None:
        m = m @ rot
    transform_mesh(o, m)
    shade_auto(o, 40)
    return o


def cylinder(name, r, length, loc=(0, 0, 0), axis="X", seg=32, mat=None, collection="Car", parent=None, bev=0.0, rot=None):
    prof = [(0.0001, -length / 2), (r, -length / 2), (r, length / 2), (0.0001, length / 2)]
    v, f = lathe(prof, seg, axis)
    o = new_obj(name, v, f, collection, mat=mat, parent=parent)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002)
    bm.to_mesh(o.data); bm.free()
    if bev > 0:
        bevel(o, bev, 2)
    m = Matrix.Translation(Vector(loc))
    if rot is not None:
        m = m @ rot
    transform_mesh(o, m)
    shade_auto(o, 40)
    return o


def frame_along(path, i, up_hint=Vector((0, 0, 1)), closed=False):
    n = len(path)
    if closed:
        t = (path[(i + 1) % n] - path[(i - 1) % n])
    else:
        t = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
    t.normalize()
    side = t.cross(up_hint)
    if side.length < 1e-6:
        side = t.cross(Vector((1, 0, 0)))
    side.normalize()
    up = side.cross(t).normalized()
    return t, side, up


def sweep(name, path, profile, closed_path=False, closed_profile=True, up_hint=(0, 0, 1),
          mat=None, collection="Car", parent=None, cap=True, smooth=True, ups=None):
    """profile: list of (s, u) in the plane (side, up) of the path frame."""
    path = [Vector(p) for p in path]
    uh = Vector(up_hint)
    verts = []
    np_ = len(profile)
    for i, p in enumerate(path):
        t, side, up = frame_along(path, i, uh if ups is None else Vector(ups[i]), closed_path)
        for (s, u) in profile:
            verts.append(p + side * s + up * u)
    faces = grid_faces(len(path), np_, close_u=closed_path, close_v=closed_profile)
    if cap and not closed_path and closed_profile:
        faces.append(tuple(range(np_ - 1, -1, -1)))
        base = (len(path) - 1) * np_
        faces.append(tuple(base + k for k in range(np_)))
    return new_obj(name, verts, faces, collection, smooth=smooth, mat=mat, parent=parent)


def tube(name, path, r, seg=10, mat=None, parent=None, collection="Car", closed=False, up_hint=(0, 0, 1)):
    prof = [(r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
    return sweep(name, path, prof, closed_path=closed, mat=mat, collection=collection, parent=parent, up_hint=up_hint)


def circle_prof(r, seg=12, sx=1.0, sy=1.0):
    return [(r * sx * math.cos(2 * math.pi * k / seg), r * sy * math.sin(2 * math.pi * k / seg)) for k in range(seg)]


def rounded_rect(w, h, r, n=4):
    pts = []
    cs = [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]
    for cx, cy, a0 in cs:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def fillet(poly, r, n=4):
    """Round corners of a closed 2D polygon."""
    out = []
    m = len(poly)
    for i in range(m):
        p0 = Vector(poly[i - 1]); p1 = Vector(poly[i]); p2 = Vector(poly[(i + 1) % m])
        d0 = (p0 - p1); d2 = (p2 - p1)
        l0, l2 = d0.length, d2.length
        d0.normalize(); d2.normalize()
        rr = min(r, l0 * 0.45, l2 * 0.45)
        a = p1 + d0 * rr
        b = p1 + d2 * rr
        for k in range(n + 1):
            t = k / n
            # quadratic bezier
            q = (1 - t) ** 2 * a + 2 * (1 - t) * t * p1 + t * t * b
            out.append((q.x, q.y))
    return out


def map2d(axis, u, v, a):
    if axis == "X":
        return (a, u, v)
    if axis == "Y":
        return (u, a, v)
    return (u, v, a)


def prism(name, poly, axis, a0, a1, collection="Cutters"):
    """Extrude closed 2D polygon (u,v) along axis from a0 to a1."""
    n = len(poly)
    verts = [map2d(axis, u, v, a0) for (u, v) in poly] + [map2d(axis, u, v, a1) for (u, v) in poly]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    o = new_obj(name, verts, faces, collection, smooth=False)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="EAR_CLIP")
    bm.to_mesh(o.data); bm.free()
    o.hide_render = True
    return o


def thick_line_poly(pts, w):
    """Outline polygon of an open polyline with width w (miter joins), ends extended by w."""
    P = [Vector(p) for p in pts]
    n = len(P)
    # extend ends
    d0 = (P[1] - P[0]).normalized(); P[0] = P[0] - d0 * w
    d1 = (P[-1] - P[-2]).normalized(); P[-1] = P[-1] + d1 * w
    L, R = [], []
    for i in range(n):
        if i == 0:
            d = (P[1] - P[0]).normalized(); nrm = Vector((-d.y, d.x)); m = 1.0
        elif i == n - 1:
            d = (P[-1] - P[-2]).normalized(); nrm = Vector((-d.y, d.x)); m = 1.0
        else:
            da = (P[i] - P[i - 1]).normalized(); db = (P[i + 1] - P[i]).normalized()
            na = Vector((-da.y, da.x)); nb = Vector((-db.y, db.x))
            nrm = (na + nb).normalized()
            m = 1.0 / max(0.3, nrm.dot(na))
        L.append(P[i] + nrm * (w / 2) * m)
        R.append(P[i] - nrm * (w / 2) * m)
    return [(p.x, p.y) for p in L] + [(p.x, p.y) for p in reversed(R)]


def gap_cutter(name, pts, w, axis, a0, a1):
    return prism(name, thick_line_poly(pts, w), axis, a0, a1)


def circle_poly(cu, cv, r, n=48):
    return [(cu + r * math.cos(2 * math.pi * k / n), cv + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def split_loose(o):
    """Split object into connected components. Returns list of new objects (original removed)."""
    me = o.data
    nv = len(me.vertices)
    parent = np.arange(nv)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    ev = np.zeros(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    for a, b in ev:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([find(i) for i in range(nv)])
    labels = {r: k for k, r in enumerate(np.unique(roots))}
    comps = []
    bm_all = bmesh.new(); bm_all.from_mesh(me)
    bm_all.verts.ensure_lookup_table()
    groups = {}
    for f in bm_all.faces:
        groups.setdefault(labels[roots[f.verts[0].index]], []).append(f.index)
    bm_all.free()
    res = []
    for k, fidx in groups.items():
        bm = bmesh.new(); bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        keep = set(fidx)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
        m2 = bpy.data.meshes.new(o.name + "_part")
        bm.to_mesh(m2); bm.free()
        for mt in me.materials:
            m2.materials.append(mt)
        o2 = bpy.data.objects.new(o.name + "_part", m2)
        for c in o.users_collection:
            c.objects.link(o2)
        o2.parent = o.parent
        o2.matrix_world = o.matrix_world.copy()
        res.append(o2)
    delete(o)
    return res


def join(objs, name=None):
    """Join mesh objects into the first one (data-level, no ops)."""
    bm = bmesh.new()
    mats = []
    for o in objs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        # remap materials
        remap = []
        for m in o.data.materials:
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        for p in me.polygons:
            p.material_index = remap[p.material_index] if remap else 0
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    first = objs[0]
    me = bpy.data.meshes.new(name or first.name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name or first.name, me)
    for c in first.users_collection:
        c.objects.link(o)
    for ob in objs:
        delete(ob)
    return o


def bvh_of(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.transform(o.matrix_world)
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


def project(tree, origins, direction, offset=0.0):
    out = []
    d = Vector(direction).normalized()
    for p in origins:
        hit = tree.ray_cast(Vector(p), d)
        if hit[0] is None:
            out.append(None)
        else:
            n = hit[1]
            out.append(hit[0] + n * offset)
    return out


def rotm(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)
