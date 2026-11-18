"""Tiny node-graph DSL for building procedural Cycles materials in code."""
import bpy

_SOCK = bpy.types.NodeSocket


def is_sock(x):
    return isinstance(x, _SOCK)


class NB:
    def __init__(self, name):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        self.mat = m
        self.nt = m.node_tree
        self.nt.nodes.clear()
        self.N = self.nt.nodes
        self.L = self.nt.links
        self._geo = None
        self._tc = None
        self._lp = None

    # -- plumbing
    def new(self, t, **props):
        n = self.N.new(t)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def put(self, sock, val):
        if val is None:
            return
        if is_sock(val):
            self.L.new(val, sock)
        else:
            if isinstance(val, (int, float)) and hasattr(sock, "default_value") and hasattr(sock.default_value, "__len__"):
                n = len(sock.default_value)
                val = (val,) * n if n != 4 else (val, val, val, 1.0)
            elif isinstance(val, (tuple, list)) and hasattr(sock.default_value, "__len__") and len(sock.default_value) == 4 and len(val) == 3:
                val = tuple(val) + (1.0,)
            sock.default_value = val

    # -- inputs
    def geo(self, out="Position"):
        if self._geo is None:
            self._geo = self.new("ShaderNodeNewGeometry")
        return self._geo.outputs[out]

    def tc(self, out="Object"):
        if self._tc is None:
            self._tc = self.new("ShaderNodeTexCoord")
        return self._tc.outputs[out]

    def lightpath(self, out="Is Shadow Ray"):
        if self._lp is None:
            self._lp = self.new("ShaderNodeLightPath")
        return self._lp.outputs[out]

    def xyz(self, v):
        n = self.new("ShaderNodeSeparateXYZ")
        self.put(n.inputs[0], v)
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def vec(self, x, y, z):
        n = self.new("ShaderNodeCombineXYZ")
        self.put(n.inputs[0], x); self.put(n.inputs[1], y); self.put(n.inputs[2], z)
        return n.outputs[0]

    def rgb(self, c):
        n = self.new("ShaderNodeRGB")
        n.outputs[0].default_value = tuple(c) + ((1.0,) if len(c) == 3 else ())
        return n.outputs[0]

    def val(self, v):
        n = self.new("ShaderNodeValue")
        n.outputs[0].default_value = v
        return n.outputs[0]

    # -- math
    def m(self, op, a, b=None, c=None, clamp=False):
        n = self.new("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if c is not None:
            self.put(n.inputs[2], c)
        return n.outputs[0]

    def add(self, a, b, clamp=False): return self.m("ADD", a, b, clamp=clamp)
    def sub(self, a, b, clamp=False): return self.m("SUBTRACT", a, b, clamp=clamp)
    def mul(self, a, b, clamp=False): return self.m("MULTIPLY", a, b, clamp=clamp)
    def mx(self, a, b): return self.m("MAXIMUM", a, b)
    def mn(self, a, b): return self.m("MINIMUM", a, b)
    def abs(self, a): return self.m("ABSOLUTE", a)
    def inv(self, a): return self.m("SUBTRACT", 1.0, a, clamp=True)

    def madd(self, *terms):
        out = terms[0]
        for t in terms[1:]:
            out = self.add(out, t)
        return out

    def mulall(self, *terms):
        out = terms[0]
        for t in terms[1:]:
            out = self.mul(out, t)
        return out

    def mr(self, x, a, b, c=0.0, d=1.0, interp="SMOOTHSTEP", clamp=True):
        n = self.new("ShaderNodeMapRange", interpolation_type=interp, clamp=clamp)
        self.put(n.inputs["Value"], x)
        self.put(n.inputs["From Min"], a); self.put(n.inputs["From Max"], b)
        self.put(n.inputs["To Min"], c); self.put(n.inputs["To Max"], d)
        return n.outputs["Result"]

    def band(self, x, a0, a1, b1, b0):
        """1 between a1..b1, ramps to 0 at a0 and b0."""
        return self.mul(self.mr(x, a0, a1), self.mr(x, b0, b1))

    def vm(self, op, a, b=None, scale=None):
        n = self.new("ShaderNodeVectorMath", operation=op)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if scale is not None:
            self.put(n.inputs["Scale"], scale)
        return n.outputs[1] if op in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else n.outputs[0]

    def dist(self, p, c):
        return self.vm("DISTANCE", p, c)

    # -- textures
    def noise(self, v, scale=5.0, detail=2.0, rough=0.5, distort=0.0, out="Fac", lac=2.0):
        n = self.new("ShaderNodeTexNoise")
        self.put(n.inputs["Vector"], v)
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = distort
        n.inputs["Lacunarity"].default_value = lac
        return n.outputs[out]

    def voronoi(self, v, scale=5.0, feature="F1", out="Distance", rnd=1.0, metric="EUCLIDEAN"):
        n = self.new("ShaderNodeTexVoronoi", feature=feature, distance=metric)
        self.put(n.inputs["Vector"], v)
        n.inputs["Scale"].default_value = scale
        n.inputs["Randomness"].default_value = rnd
        return n.outputs[out]

    def wave(self, v, scale=5.0, dist=0.0, detail=0.0, kind="BANDS", direction="X", profile="SIN", out="Fac"):
        n = self.new("ShaderNodeTexWave", wave_type=kind, bands_direction=direction, wave_profile=profile)
        if kind == "RINGS":
            n.rings_direction = "SPHERICAL"
        self.put(n.inputs["Vector"], v)
        n.inputs["Scale"].default_value = scale
        n.inputs["Distortion"].default_value = dist
        n.inputs["Detail"].default_value = detail
        return n.outputs[out]

    def white(self, v):
        n = self.new("ShaderNodeTexWhiteNoise")
        n.noise_dimensions = "3D"
        self.put(n.inputs["Vector"], v)
        return n.outputs["Value"]

    def scale(self, v, s):
        if isinstance(s, (tuple, list)):
            return self.vm("MULTIPLY", v, tuple(s))
        return self.vm("SCALE", v, scale=s)

    # -- colour
    def mixc(self, f, a, b, blend="MIX"):
        n = self.new("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True)
        self.put(n.inputs[0], f)
        self.put(n.inputs[6], a); self.put(n.inputs[7], b)
        return n.outputs[2]

    def mixf(self, f, a, b):
        n = self.new("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        self.put(n.inputs[0], f)
        self.put(n.inputs[2], a); self.put(n.inputs[3], b)
        return n.outputs[0]

    def ramp(self, f, stops, interp="LINEAR"):
        n = self.new("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = tuple(stops[0][1]) + ((1.0,) if len(stops[0][1]) == 3 else ())
        for pos, col in stops[1:]:
            e = cr.elements.new(pos)
            e.color = tuple(col) + ((1.0,) if len(col) == 3 else ())
        self.put(n.inputs[0], f)
        return n.outputs[0]

    def hsv(self, c, h=0.5, s=1.0, v=1.0):
        n = self.new("ShaderNodeHueSaturation")
        self.put(n.inputs["Color"], c)
        self.put(n.inputs["Hue"], h); self.put(n.inputs["Saturation"], s); self.put(n.inputs["Value"], v)
        return n.outputs[0]

    def bw(self, c):
        n = self.new("ShaderNodeRGBToBW")
        self.put(n.inputs[0], c)
        return n.outputs[0]

    # -- shading helpers
    def bump(self, h, strength=1.0, distance=1.0, normal=None, invert=False):
        n = self.new("ShaderNodeBump", invert=invert)
        self.put(n.inputs["Height"], h)
        n.inputs["Strength"].default_value = strength
        n.inputs["Distance"].default_value = distance
        if normal is not None:
            self.put(n.inputs["Normal"], normal)
        return n.outputs[0]

    def ao(self, distance=0.03, local=True, samples=8):
        n = self.new("ShaderNodeAmbientOcclusion", only_local=local, samples=samples)
        n.inputs["Distance"].default_value = distance
        return n.outputs["AO"]

    def bevel_n(self, radius=0.005, samples=6):
        n = self.new("ShaderNodeBevel", samples=samples)
        n.inputs["Radius"].default_value = radius
        return n.outputs[0]

    def edge_mask(self, radius=0.005, a=0.02, b=0.25):
        d = self.vm("DOT_PRODUCT", self.bevel_n(radius), self.geo("Normal"))
        return self.mr(self.sub(1.0, d), a, b)

    def principled(self, **kw):
        n = self.new("ShaderNodeBsdfPrincipled")
        for k, v in kw.items():
            key = k.replace("_", " ")
            self.put(n.inputs[key], v)
        return n.outputs[0]

    def shader(self, t, **kw):
        n = self.new(t)
        for k, v in kw.items():
            self.put(n.inputs[k.replace("_", " ")], v)
        return n.outputs[0]

    def mixs(self, f, a, b):
        n = self.new("ShaderNodeMixShader")
        self.put(n.inputs[0], f)
        self.L.new(a, n.inputs[1]); self.L.new(b, n.inputs[2])
        return n.outputs[0]

    def out(self, surface, displacement=None):
        o = self.new("ShaderNodeOutputMaterial")
        self.L.new(surface, o.inputs["Surface"])
        if displacement is not None:
            self.L.new(displacement, o.inputs["Displacement"])
        try:
            self.mat.displacement_method = "BUMP"
        except Exception:
            pass
        return self.mat
