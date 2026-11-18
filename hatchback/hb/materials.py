"""Procedural PBR materials. All wear masks are driven by world position / normals so that the
wear follows the car's history (sun from above, salt from below, gravel from the front, driver on -X)."""
from .nodes import NB

ARCH_Y = (1.20, -1.20)
ARCH_Z = 0.272


def _arch_dist(b, P):
    x, y, z = b.xyz(P)
    dz = b.sub(z, ARCH_Z)
    ds = []
    for ya in ARCH_Y:
        dy = b.sub(y, ya)
        ds.append(b.m("SQRT", b.add(b.mul(dy, dy), b.mul(dz, dz))))
    return b.sub(b.mn(ds[0], ds[1]), 0.335)


def rust_layers(b, P, amount, scale=1.0):
    """3-layer rust: light orange surface, dark brown core, flaking edge. Returns (color, rough, height)."""
    n1 = b.noise(b.scale(P, 40 * scale), 6, 8, 0.7)
    n2 = b.noise(b.scale(P, 260 * scale), 4, 6, 0.6)
    r = b.add(amount, b.mul(b.sub(n1, 0.5), 0.5))
    col = b.ramp(b.add(r, b.mul(b.sub(n2, 0.5), 0.2)), [
        (0.00, (0.20, 0.075, 0.025)),   # flaking edge / thin orange stain
        (0.35, (0.36, 0.13, 0.04)),     # light orange surface rust
        (0.60, (0.17, 0.06, 0.022)),    # brown
        (0.85, (0.06, 0.025, 0.012)),   # dark core
    ])
    h = b.add(b.mul(n2, 0.0006), b.mul(n1, 0.0004))
    return col, 0.88, h


def paint(name="paint"):
    b = NB(name)
    P = b.geo("Position"); Nw = b.geo("Normal")
    x, y, z = b.xyz(P)
    nx, ny, nz = b.xyz(Nw)
    ax = b.abs(x)
    up = b.mr(nz, 0.45, 0.88)
    vert = b.inv(b.mr(b.abs(nz), 0.25, 0.6))

    # ---- base colour: faded light blue-grey metallic; horizontals ~10% lighter and duller (UV)
    base = (0.150, 0.190, 0.235)
    faded = (0.205, 0.228, 0.250)
    mott = b.noise(b.scale(P, 1.3), 3, 0.55)
    col = b.mixc(b.add(b.mul(up, 0.95), b.mul(b.sub(mott, 0.5), 0.35)), base, faded)
    col = b.mixc(b.mul(b.noise(b.scale(P, 7), 4, 0.6), 0.12), col, (0.13, 0.17, 0.21))

    # ---- clear coat oxidation (matte chalky patches with a fairly sharp boundary) on roof/hood
    oxn = b.noise(b.scale(P, 1.6), 7, 0.62, 0.35)
    ox_zone = b.mulall(up, b.mr(z, 0.82, 0.95), b.add(b.mr(z, 1.2, 1.4), 0.55))
    ox = b.mul(ox_zone, b.mr(oxn, 0.47, 0.485))
    ox_soft = b.mul(ox_zone, b.mr(oxn, 0.38, 0.47))
    col = b.mixc(b.mul(ox, 0.7), col, (0.26, 0.27, 0.28))
    # clear-coat peeling near roof rear edge
    peel = b.mulall(b.mr(z, 1.35, 1.40), b.band(y, -1.60, -1.56, -1.38, -1.30),
                    b.mr(b.noise(b.scale(P, 9), 6, 0.7, 0.4), 0.56, 0.565))
    peel_edge = b.mulall(b.mr(z, 1.35, 1.40), b.band(y, -1.60, -1.56, -1.38, -1.30),
                         b.band(b.noise(b.scale(P, 9), 6, 0.7, 0.4), 0.54, 0.555, 0.558, 0.562))
    col = b.mixc(peel, col, (0.33, 0.35, 0.37))
    col = b.mixc(b.mul(peel_edge, 0.6), col, (0.55, 0.56, 0.56))

    # ---- stone chips: hood front edge, front face, lower doors behind the front wheels
    chip_zone = b.madd(
        b.mul(b.mr(y, 1.45, 1.86), b.mr(z, 0.70, 0.78)),
        b.mul(b.mr(y, 1.86, 1.90), 0.8),
        b.mulall(b.band(y, -0.9, -0.6, 0.75, 0.86), b.mr(z, 0.45, 0.30), 0.5),
        b.mul(b.mr(y, 0.9, 1.3), b.mulall(up, 0.12)))
    vd = b.voronoi(b.scale(P, 95), 5, "F1", "Distance")
    vc = b.voronoi(b.scale(P, 95), 5, "F1", "Color")
    r1, r2, r3 = b.xyz(vc)
    sel = b.mr(r1, b.sub(1.0, b.mul(chip_zone, 0.32)), b.add(b.sub(1.0, b.mul(chip_zone, 0.32)), 0.002), interp="LINEAR")
    rad = b.add(0.08, b.mul(r2, 0.16))
    chip = b.mul(sel, b.mr(vd, rad, b.sub(rad, 0.015)))
    bare = b.mulall(sel, b.mr(r3, 0.55, 0.56), b.mr(vd, b.mul(rad, 0.5), b.sub(b.mul(rad, 0.5), 0.01)))
    halo = b.mulall(sel, b.mr(r3, 0.55, 0.56), b.mr(vd, b.mul(rad, 1.25), b.mul(rad, 0.5)))
    col = b.mixc(chip, col, (0.30, 0.30, 0.29))                 # grey primer
    col = b.mixc(b.mul(halo, 0.85), col, (0.26, 0.09, 0.03))     # orange rust halo
    col = b.mixc(bare, col, (0.30, 0.28, 0.26))                  # bare steel

    # ---- salt rust at the lowest points: sill ends, arch lips, door bottoms, hatch lip
    ad = _arch_dist(b, P)
    arch_lip = b.mulall(b.band(ad, -0.01, 0.0, 0.03, 0.06), b.mr(z, 0.62, 0.40), b.mr(ax, 0.55, 0.70))
    sill_end = b.mulall(b.mr(z, 0.36, 0.24),
                        b.add(b.band(y, 0.70, 0.78, 0.86, 0.90), b.band(y, -0.92, -0.88, -0.80, -0.70)))
    door_bot = b.mulall(b.mr(z, 0.31, 0.275), b.band(y, -0.84, -0.80, 0.78, 0.80), b.mr(ax, 0.6, 0.7))
    hatch_lip = b.mulall(b.mr(y, -1.76, -1.80), b.band(z, 0.54, 0.56, 0.60, 0.64), b.mr(ax, 0.66, 0.5))
    low = b.mr(z, 0.33, 0.20)
    rust_src = b.madd(b.mul(arch_lip, 0.9), b.mul(sill_end, 1.0), b.mul(door_bot, 0.9), b.mul(hatch_lip, 0.8), b.mul(low, 0.12))
    rn = b.noise(b.scale(P, 14), 8, 0.66, 0.2)
    rust = b.mr(b.add(b.mul(rust_src, 0.55), b.mul(rn, 0.55)), 0.76, 0.80)
    rust_halo = b.mr(b.add(b.mul(rust_src, 0.55), b.mul(rn, 0.55)), 0.69, 0.76)
    rcol, rrough, rh = rust_layers(b, P, rust)
    col = b.mixc(b.mul(rust_halo, 0.55), col, (0.22, 0.12, 0.07))
    col = b.mixc(rust, col, rcol)
    # paint blisters along the arch lip
    blv = b.voronoi(b.scale(P, 320), 1, "F1", "Distance")
    blc = b.voronoi(b.scale(P, 320), 1, "F1", "Color")
    blr, _, _ = b.xyz(blc)
    blis = b.mulall(arch_lip, b.mr(blr, 0.55, 0.56), b.mr(b.noise(b.scale(P, 6), 3), 0.45, 0.55))
    blis_h = b.mul(blis, b.mul(b.mr(blv, 0.45, 0.0), 0.0006))

    # ---- touch-up paint blobs (mismatched blue) on the right rear fender
    tu = None
    for c, r in (((0.81, -1.42, 0.70), 0.006), ((0.81, -1.53, 0.56), 0.0045), ((0.81, -1.30, 0.66), 0.004), ((0.81, -1.47, 0.62), 0.003)):
        d = b.dist(P, c)
        d = b.add(d, b.mul(b.sub(b.noise(b.scale(P, 600), 2), 0.5), 0.003))
        t = b.mr(d, r, r * 0.75)
        tu = t if tu is None else b.mx(tu, t)
    tu = b.mul(tu, b.mr(x, 0.6, 0.7))
    col = b.mixc(tu, col, (0.13, 0.22, 0.40))

    # ---- shallow dents (shopping carts / doors) — height in metres
    dent_h = None
    for c, r, dpt in (((0.81, 0.35, 0.63), 0.035, 0.0018), ((0.81, -0.46, 0.70), 0.025, 0.0012),
                      ((-0.81, 0.12, 0.60), 0.045, 0.0022), ((-0.81, -0.56, 0.67), 0.02, 0.001),
                      ((0.80, -1.05, 0.78), 0.03, 0.0012)):
        d = b.dist(P, c)
        t = b.mul(b.m("POWER", b.mr(d, r, 0.0, interp="SMOOTHSTEP"), 1.5), -dpt)
        dent_h = t if dent_h is None else b.add(dent_h, t)

    # ---- dirt: tide line, mud splash behind wheels, water streaks, pollen, cavity grime, bird dropping
    zz = b.add(z, b.mul(b.sub(b.noise(b.scale(P, (3, 3, 1)), 4, 0.6), 0.5), 0.09))
    tide = b.mr(zz, 0.44, 0.17)
    tide_line = b.mul(b.band(zz, 0.40, 0.42, 0.43, 0.46), 0.35)
    mud = None
    for ya in ARCH_Y:
        dyb = b.sub(ya, y)
        zone = b.mulall(b.band(dyb, 0.28, 0.36, 0.62, 0.85), b.mr(z, 0.60, 0.25), b.mr(ax, 0.55, 0.72))
        mud = zone if mud is None else b.add(mud, zone)
    spl = b.mr(b.noise(b.scale(P, (1, 1, 0.4)), 30, 6, 0.65, 0.2), 0.52, 0.60)
    mud = b.mul(mud, spl)
    u = b.mul(b.add(x, y), 1.0)
    streakn = b.noise(b.vec(b.mul(u, 70), b.mul(z, 2.5), 0.0), 1.0, 3, 0.5)
    streak_v = b.mr(streakn, 0.56, 0.68)
    sz = b.madd(
        b.mulall(b.band(y, 0.55, 0.62, 0.84, 0.90), b.band(z, 0.35, 0.50, 0.95, 0.99), b.mr(ax, 0.7, 0.78)),
        b.mulall(b.mr(y, -1.72, -1.80), b.band(ax, 0.50, 0.58, 0.76, 0.80), b.mr(z, 0.66, 0.50)),
        b.mulall(b.mr(y, 1.86, 1.90), b.band(ax, 0.40, 0.44, 0.70, 0.74), b.mr(z, 0.58, 0.42)),
        b.mulall(b.band(y, -0.10, -0.07, 0.02, 0.05), b.band(z, 0.55, 0.65, 0.87, 0.89), b.mr(ax, 0.7, 0.78), 0.6),
        b.mulall(b.band(y, -0.80, -0.77, -0.68, -0.64), b.band(z, 0.55, 0.65, 0.87, 0.89), b.mr(ax, 0.7, 0.78), 0.6))
    streaks = b.mulall(streak_v, sz, vert)
    pollen = b.mul(up, b.mr(b.noise(b.scale(P, 380), 2, 0.5), 0.45, 0.75))
    dust = b.add(b.mul(up, 0.35), 0.10)
    cav = b.inv(b.ao(0.025, True, 8))
    cav = b.mr(cav, 0.05, 0.5)
    bird_d = b.dist(P, (0.24, -0.38, 1.45))
    bird_d = b.add(bird_d, b.mul(b.sub(b.noise(b.scale(P, 70), 4, 0.6), 0.5), 0.03))
    bird = b.mr(bird_d, 0.03, 0.026)
    bird_core = b.mr(bird_d, 0.012, 0.006)
    bird_ring = b.band(bird_d, 0.028, 0.031, 0.035, 0.040)

    grime_c = (0.085, 0.075, 0.062)
    col = b.mixc(b.mul(dust, 0.14), col, (0.24, 0.23, 0.21))
    col = b.mixc(b.mul(pollen, 0.22), col, (0.30, 0.28, 0.20))
    col = b.mixc(b.mul(cav, 0.75), col, (0.05, 0.045, 0.04))
    col = b.mixc(b.mul(streaks, 0.45), col, (0.13, 0.13, 0.12))
    col = b.mixc(b.mul(b.add(tide, tide_line), 0.88), col, grime_c)
    col = b.mixc(b.mul(mud, 0.95), col, (0.17, 0.135, 0.095))
    col = b.mixc(b.mul(bird_ring, 0.5), col, (0.30, 0.31, 0.31))
    col = b.mixc(bird, col, (0.55, 0.54, 0.50))
    col = b.mixc(bird_core, col, (0.06, 0.06, 0.05))

    # ---- driver door key/fingernail scratches below the handle (driver = -X)
    kz = b.mulall(b.mr(x, -0.70, -0.78), b.band(y, -0.12, -0.10, 0.04, 0.07), b.band(z, 0.80, 0.83, 0.88, 0.90))
    ks = b.mr(b.noise(b.scale(P, (40, 400, 900)), 1, 2, 0.5), 0.62, 0.66)
    scr = b.mul(kz, ks)
    col = b.mixc(b.mul(scr, 0.5), col, (0.36, 0.38, 0.40))

    # ---- wash swirl micro-scratches (coat only): concentrated on sides and hood
    swirl_zone = b.add(b.mul(vert, b.band(z, 0.40, 0.50, 0.95, 1.0)), b.mul(b.mr(y, 1.0, 1.2), up))
    sw1 = b.noise(b.scale(P, (900, 900, 30)), 1, 2, 0.5)
    sw2 = b.noise(b.scale(P, (30, 900, 900)), 1, 2, 0.5)
    sw = b.mx(b.mr(sw1, 0.62, 0.66), b.mr(sw2, 0.62, 0.66))
    sw = b.mul(sw, swirl_zone)

    # ---- roughness / metallic / coat
    dirt_all = b.madd(b.mul(tide, 0.9), mud, b.mul(streaks, 0.4), bird, b.mul(pollen, 0.25))
    cw = b.sub(1.0, b.madd(b.mul(ox, 0.75), peel, chip, rust, b.mul(tide, 0.6), mud, bird), clamp=True)
    cr = b.madd(0.13, b.mul(up, 0.13), b.mul(ox_soft, 0.10), b.mul(ox, 0.25), b.mul(sw, 0.10), b.mul(dust, 0.05), b.mul(dirt_all, 0.4))
    rough = b.madd(0.36, b.mul(ox, 0.2), b.mul(chip, 0.25), b.mul(rust, 0.45), b.mul(dirt_all, 0.5), b.mul(tu, -0.2))
    rough = b.mn(rough, 0.95)
    metal = b.mixf(b.madd(chip, rust, b.mul(tide, 0.7), mud, bird, peel), 0.65, 0.0)
    metal = b.mixf(bare, metal, 0.9)

    # ---- normals: oil-canning + flakes + dents + defects for base; orange peel + swirls for coat
    oil = b.mul(b.noise(b.scale(P, 1.7), 1, 0.4), 0.0011)
    oil = b.mul(oil, b.add(vert, b.mul(up, b.mr(z, 0.85, 0.95))))
    peelh = b.mul(b.noise(b.scale(P, 260), 2, 0.5), 0.000025)
    flake = b.voronoi(b.scale(P, 2500), 1, "F1", "Color")
    fx, fy, fz = b.xyz(flake)
    flake_h = b.mul(fx, 0.0000045)
    chip_h = b.mul(chip, -0.00012)
    h_base = b.madd(oil, dent_h, chip_h, b.mul(rust, rh), blis_h, b.mul(tu, 0.00015), b.mul(peel, -0.00004), b.mul(bird, 0.0002))
    n_base = b.bump(b.add(h_base, flake_h), 1.0, 1.0)
    h_coat = b.madd(oil, dent_h, peelh, b.mul(sw, 0.0000035), chip_h)
    n_coat = b.bump(h_coat, 1.0, 1.0)

    sh = b.principled(Base_Color=col, Metallic=metal, Roughness=rough, Normal=n_base,
                      Coat_Weight=cw, Coat_Roughness=cr, Coat_IOR=1.45, Coat_Normal=n_coat,
                      Coat_Tint=(0.97, 0.965, 0.93), Specular_IOR_Level=0.5)
    return b.out(sh)


def paint_inner():
    b = NB("paint_inner")
    P = b.geo("Position"); x, y, z = b.xyz(P)
    n = b.noise(b.scale(P, 8), 5, 0.6)
    col = b.mixc(b.mr(z, 0.45, 0.2), (0.21, 0.25, 0.29), (0.07, 0.06, 0.05))
    col = b.mixc(b.mul(n, 0.3), col, (0.12, 0.11, 0.10))
    # seam sealer / spot-weld dimple feel via fine voronoi bump
    v = b.voronoi(b.scale(P, 60), 1, "F1", "Distance")
    h = b.mul(b.mr(v, 0.12, 0.06), -0.0003)
    sh = b.principled(Base_Color=col, Roughness=b.add(0.5, b.mul(n, 0.3)), Normal=b.bump(h, 1, 1))
    return b.out(sh)


def plastic_black(name="plastic_trim", bleach=1.0, scuff=True, tex_scale=1.0):
    """Unpainted textured PP: sun-bleached grey patches on top faces, scuffs on corners, dust in grain."""
    b = NB(name)
    P = b.geo("Position"); x, y, z = b.xyz(P); nx, ny, nz = b.xyz(b.geo("Normal"))
    ax = b.abs(x)
    up = b.mr(nz, 0.0, 0.8)
    bl = b.mul(b.mul(up, b.mr(b.noise(b.scale(P, 2.2), 5, 0.6), 0.35, 0.65)), bleach)
    col = b.mixc(b.mul(bl, 0.6), (0.008, 0.008, 0.009), (0.040, 0.039, 0.037))
    grain = b.noise(b.scale(P, 1400 * tex_scale), 2, 0.5)
    col = b.mixc(b.mul(b.mr(grain, 0.6, 0.8), 0.15), col, (0.06, 0.058, 0.055))
    rough = b.madd(0.52, b.mul(bl, 0.2), b.mul(grain, 0.08))
    h = b.mul(grain, 0.00003)
    if scuff:
        corner = b.mulall(b.mr(ax, 0.62, 0.76), b.add(b.mr(y, 1.78, 1.88), b.mr(y, -1.72, -1.80)), b.band(z, 0.26, 0.30, 0.44, 0.48))
        sc = b.mr(b.noise(b.scale(P, (6, 6, 520)), 1, 0.5, 0.2), 0.66, 0.69)
        sc = b.mul(sc, corner)
        col = b.mixc(b.mul(sc, 0.6), col, (0.10, 0.098, 0.095))
        rough = b.add(rough, b.mul(sc, 0.25))
        # deeper scrape on the front right corner
        deep = b.mulall(b.mr(x, 0.66, 0.74), b.mr(y, 1.78, 1.86), b.band(z, 0.33, 0.345, 0.385, 0.40))
        gouge = b.mr(b.noise(b.scale(P, (5, 5, 220)), 2, 0.5), 0.55, 0.60)
        g = b.mul(deep, gouge)
        col = b.mixc(g, col, (0.20, 0.195, 0.19))
        h = b.add(h, b.mul(g, -0.0006))
    # mold parting line (horizontal ridge)
    pl = b.mr(b.abs(b.sub(z, 0.335)), 0.0009, 0.0)
    h = b.add(h, b.mul(pl, 0.00015))
    # dirt from below and in cavities
    tide = b.mr(b.add(z, b.mul(b.noise(b.scale(P, 4), 3), 0.07)), 0.36, 0.20)
    cav = b.mr(b.inv(b.ao(0.02, True, 6)), 0.05, 0.5)
    col = b.mixc(b.mul(cav, 0.6), col, (0.06, 0.055, 0.05))
    col = b.mixc(b.mul(tide, 0.5), col, (0.085, 0.072, 0.058))
    rough = b.add(rough, b.mul(tide, 0.25))
    sh = b.principled(Base_Color=col, Roughness=b.mn(rough, 0.92), Normal=b.bump(h, 1, 1),
                      Specular_IOR_Level=0.45)
    return b.out(sh)


def rubber(name="rubber", cracks=True):
    b = NB(name)
    P = b.geo("Position")
    col = (0.018, 0.018, 0.019)
    v = b.voronoi(b.scale(P, 220), 1, "DISTANCE_TO_EDGE", "Distance")
    cr = b.mul(b.mr(v, 0.03, 0.0), b.mr(b.noise(b.scale(P, 15), 2), 0.45, 0.6)) if cracks else b.val(0)
    gr = b.mr(b.noise(b.scale(P, 6), 3), 0.4, 0.7)
    c = b.mixc(b.mul(gr, 0.5), col, (0.06, 0.058, 0.055))
    c = b.mixc(b.mul(cr, 0.4), c, (0.10, 0.10, 0.10))
    sh = b.principled(Base_Color=c, Roughness=b.add(0.72, b.mul(gr, 0.15)), Subsurface_Weight=0.05,
                      Subsurface_Radius=(0.002, 0.002, 0.002), Normal=b.bump(b.mul(cr, -0.0002), 1, 1),
                      Specular_IOR_Level=0.4)
    return b.out(sh)


def glass(name="glass", tint=(0.86, 0.95, 0.89), windshield=False, driver_scratch=False):
    b = NB(name)
    P = b.geo("Position"); x, y, z = b.xyz(P)
    dust_n = b.noise(b.scale(P, 9), 5, 0.6)
    dust = b.add(0.008, b.mul(b.mr(dust_n, 0.4, 0.75), 0.022))
    dust = b.add(dust, b.mul(b.mr(z, 1.05, 0.95), 0.03))
    rough = b.add(0.0, b.mul(dust, 0.15))
    if windshield:
        # wiper sweep: clean arcs around two pivots, dirty outside them and washer streaks
        a1 = b.dist(b.vec(x, y, 0), (-0.38, 0.97, 0))
        a2 = b.dist(b.vec(x, y, 0), (0.18, 0.97, 0))
        swept = b.mx(b.mul(b.mr(a1, 0.62, 0.56), b.mr(a1, 0.10, 0.16)), b.mul(b.mr(a2, 0.60, 0.54), b.mr(a2, 0.10, 0.16)))
        arcs = b.mul(b.mr(b.wave(b.scale(b.vec(b.sub(x, -0.38), b.sub(y, 0.97), 0), 1), 60, 1.5, 2, "RINGS"), 0.75, 1.0), swept)
        dust = b.add(b.mul(dust, b.sub(1.0, b.mul(swept, 0.7))), b.mul(b.inv(swept), 0.05))
        dust = b.add(dust, b.mul(arcs, 0.02))
        rough = b.add(b.mul(dust, 0.18), b.mul(arcs, 0.03))
    if driver_scratch:
        sc = b.mr(b.noise(b.scale(P, (40, 2, 1400)), 1, 2), 0.64, 0.68)
        zone = b.mulall(b.mr(x, -0.6, -0.7), b.band(y, -0.10, -0.05, 0.6, 0.72), b.band(z, 0.97, 0.99, 1.15, 1.25))
        rough = b.add(rough, b.mul(b.mul(sc, zone), 0.25))
    g = b.principled(Base_Color=tint, Roughness=rough, IOR=1.5, Transmission_Weight=1.0, Specular_IOR_Level=0.5)
    d = b.shader("ShaderNodeBsdfDiffuse", Color=(0.22, 0.21, 0.19), Roughness=1.0)
    s = b.mixs(b.mn(dust, 0.4), g, d)
    tr = b.shader("ShaderNodeBsdfTransparent", Color=tint)
    s = b.mixs(b.lightpath("Is Shadow Ray"), s, tr)
    return b.out(s)


def lens(name, tint, rough=0.03, haze=0.0, condens=False, center=(0, 0, 0), flutes=True, emit=None):
    b = NB(name)
    P = b.geo("Position"); x, y, z = b.xyz(P)
    n = b.noise(b.scale(P, 25), 4, 0.6)
    r = b.add(rough, b.mul(b.mul(n, haze), 0.6))
    hh = b.val(0.0)
    if flutes:
        hh = b.mul(b.wave(b.scale(P, 1.0), 260, 0, 0, "BANDS", "Z", "SIN"), 0.00006)
        hh = b.add(hh, b.mul(b.wave(b.scale(P, 1.0), 180, 0, 0, "BANDS", "X", "SIN"), 0.00004))
    cr = b.mr(b.noise(b.scale(P, (80, 80, 3)), 2, 0.5), 0.70, 0.72)
    r = b.add(r, b.mul(cr, 0.3))
    if condens:
        dd = b.dist(P, center)
        ring = b.mul(b.band(dd, 0.050, 0.060, 0.080, 0.088), b.mr(z, center[2] + 0.02, center[2] - 0.03))
        drop = b.mr(b.voronoi(b.scale(P, 900), 1, "F1", "Distance"), 0.35, 0.15)
        r = b.add(r, b.mul(ring, 0.35))
        hh = b.add(hh, b.mulall(ring, drop, 0.00008))
    col = b.mixc(b.mul(haze, 0.6), tint, (tint[0] * 0.85, tint[1] * 0.8, tint[2] * 0.6))
    g = b.principled(Base_Color=col, Roughness=r, IOR=1.49, Transmission_Weight=1.0, Normal=b.bump(hh, 1, 1))
    tr = b.shader("ShaderNodeBsdfTransparent", Color=tint)
    s = b.mixs(b.lightpath("Is Shadow Ray"), g, tr)
    return b.out(s)


def reflector(name="reflector"):
    b = NB(name)
    P = b.geo("Position")
    peel = b.mr(b.noise(b.scale(P, 45), 6, 0.65, 0.3), 0.60, 0.63)
    col = b.mixc(peel, (0.80, 0.80, 0.80), (0.10, 0.10, 0.10))
    sh = b.principled(Base_Color=col, Metallic=b.inv(peel), Roughness=b.add(0.12, b.mul(peel, 0.5)))
    return b.out(sh)


def rusty_steel(name="rusty_steel", amount=0.55, base=(0.18, 0.18, 0.18), scale=1.0):
    b = NB(name)
    P = b.geo("Position")
    n = b.noise(b.scale(P, 6 * scale), 6, 0.6)
    a = b.mr(b.add(b.mul(n, 0.8), amount * 0.6), 0.55, 0.75)
    rc, rr, rh = rust_layers(b, P, a, scale)
    col = b.mixc(a, base, rc)
    sh = b.principled(Base_Color=col, Metallic=b.mixf(a, 0.7, 0.0), Roughness=b.mixf(a, 0.5, 0.9),
                      Normal=b.bump(b.mul(a, rh), 1, 1))
    return b.out(sh)


def bitumen(name="underbody"):
    b = NB(name)
    P = b.geo("Position")
    n = b.noise(b.scale(P, 5), 6, 0.65)
    peel = b.mr(n, 0.66, 0.68)
    salt = b.mr(b.noise(b.scale(P, 50), 4, 0.7), 0.62, 0.72)
    mud = b.mr(b.noise(b.scale(P, 3), 4, 0.6), 0.5, 0.7)
    col = b.mixc(b.mul(mud, 0.7), (0.025, 0.024, 0.022), (0.13, 0.105, 0.075))
    col = b.mixc(b.mul(salt, 0.5), col, (0.40, 0.39, 0.36))
    rc, _, rh = rust_layers(b, P, b.val(0.6))
    col = b.mixc(peel, col, rc)
    h = b.add(b.mul(b.noise(b.scale(P, 300), 2), 0.0003), b.mul(peel, -0.001))
    sh = b.principled(Base_Color=col, Roughness=b.add(0.65, b.mul(salt, 0.25)), Normal=b.bump(h, 1, 1))
    return b.out(sh)


def tire(name="tire"):
    b = NB(name)
    Po = b.tc("Object"); x, y, z = b.xyz(Po)
    r = b.m("SQRT", b.add(b.mul(y, y), b.mul(z, z)))
    tread = b.mr(r, 0.252, 0.258)
    Pw = b.geo("Position")
    n = b.noise(b.scale(Pw, 12), 4, 0.6)
    col = b.mixc(tread, (0.020, 0.020, 0.021), (0.045, 0.043, 0.040))
    dirt = b.mul(b.mr(n, 0.4, 0.7), b.add(0.3, b.mul(tread, 0.5)))
    col = b.mixc(b.mul(dirt, 0.6), col, (0.13, 0.11, 0.085))
    # ozone cracking on the sidewall
    v = b.voronoi(b.scale(Po, (6, 400, 400)), 1, "DISTANCE_TO_EDGE", "Distance")
    crk = b.mulall(b.mr(v, 0.04, 0.0), b.band(r, 0.18, 0.19, 0.245, 0.25), b.mr(b.noise(b.scale(Pw, 20), 2), 0.5, 0.6))
    # molded rings (generic markings, no text)
    ring = b.add(b.band(r, 0.2095, 0.2100, 0.2112, 0.2117), b.band(r, 0.2325, 0.2330, 0.2338, 0.2343))
    h = b.madd(b.mul(crk, -0.00025), b.mul(ring, 0.0003), b.mul(b.noise(b.scale(Pw, 900), 2), 0.00002))
    sh = b.principled(Base_Color=col, Roughness=b.add(0.78, b.mul(tread, 0.1)), Normal=b.bump(h, 1, 1),
                      Subsurface_Weight=0.03, Specular_IOR_Level=0.35)
    return b.out(sh)


def steel_wheel(name="steel_wheel"):
    b = NB(name)
    Po = b.tc("Object"); x, y, z = b.xyz(Po)
    r = b.m("SQRT", b.add(b.mul(y, y), b.mul(z, z)))
    Pw = b.geo("Position")
    lip = b.mr(r, 0.158, 0.172)
    n = b.noise(b.scale(Pw, 40), 6, 0.65)
    rust = b.mul(lip, b.mr(n, 0.42, 0.58))
    rc, _, rh = rust_layers(b, Pw, rust, 1.5)
    col = b.mixc(rust, (0.30, 0.30, 0.31), rc)
    dust = b.mr(b.noise(b.scale(Pw, 9), 4), 0.3, 0.7)
    col = b.mixc(b.mul(dust, 0.75), col, (0.08, 0.065, 0.05))
    sh = b.principled(Base_Color=col, Metallic=b.mixf(b.add(rust, dust), 0.6, 0.0), Roughness=b.add(0.45, b.mul(b.add(rust, dust), 0.4)),
                      Normal=b.bump(b.mul(rust, rh), 1, 1))
    return b.out(sh)


def hubcap(name="hubcap", base=(0.36, 0.37, 0.38), rough=0.38):
    b = NB(name)
    Pw = b.geo("Position"); Po = b.tc("Object"); x, y, z = b.xyz(Po)
    r = b.m("SQRT", b.add(b.mul(y, y), b.mul(z, z)))
    cav = b.mr(b.inv(b.ao(0.02, True, 6)), 0.05, 0.4)
    dust = b.add(b.mul(cav, 0.8), b.mul(b.mr(b.noise(b.scale(Pw, 10), 4), 0.4, 0.75), 0.4))
    sc = b.mul(b.mr(r, 0.14, 0.165), b.mr(b.noise(b.scale(Po, (5, 300, 300)), 2), 0.55, 0.62))
    col = b.mixc(b.mn(dust, 0.9), base, (0.07, 0.06, 0.05))
    col = b.mixc(sc, col, (0.12, 0.12, 0.12))
    sh = b.principled(Base_Color=col, Metallic=b.mixf(dust, 0.6, 0.1), Roughness=b.add(rough, b.mul(dust, 0.4)),
                      Coat_Weight=b.mixf(dust, 0.5, 0.0), Coat_Roughness=0.2)
    return b.out(sh)


def brake_disc(name="brake_disc"):
    b = NB(name)
    Po = b.tc("Object"); x, y, z = b.xyz(Po)
    r = b.m("SQRT", b.add(b.mul(y, y), b.mul(z, z)))
    Pw = b.geo("Position")
    track = b.band(r, 0.075, 0.08, 0.112, 0.116)
    rc, _, rh = rust_layers(b, Pw, b.mr(b.noise(b.scale(Pw, 30), 5), 0.3, 0.6), 2)
    col = b.mixc(track, rc, (0.42, 0.42, 0.42))
    ang = b.m("ARCTAN2", z, y)
    sh = b.principled(Base_Color=col, Metallic=b.mixf(track, 0.2, 1.0), Roughness=b.mixf(track, 0.85, 0.32),
                      Anisotropic=b.mul(track, 0.7), Anisotropic_Rotation=b.mul(ang, 0.159))
    return b.out(sh)


def simple(name, col, rough=0.5, metal=0.0, noise_amt=0.15, dirt=0.3, sheen=0.0, grain=0.0, scale=1.0):
    b = NB(name)
    P = b.geo("Position")
    n = b.noise(b.scale(P, 8 * scale), 5, 0.6)
    c = b.mixc(b.mul(n, noise_amt), col, (col[0] * 0.6, col[1] * 0.6, col[2] * 0.6))
    cav = b.mr(b.inv(b.ao(0.03, True, 6)), 0.05, 0.5)
    c = b.mixc(b.mul(cav, dirt), c, (0.05, 0.045, 0.04))
    h = b.val(0.0)
    if grain:
        g = b.voronoi(b.scale(P, 500 * scale), 1, "F1", "Distance")
        h = b.mul(g, grain)
    kw = {}
    if sheen:
        kw = dict(Sheen_Weight=sheen, Sheen_Roughness=0.5)
    sh = b.principled(Base_Color=c, Roughness=b.add(rough, b.mul(n, 0.1)), Metallic=metal, Normal=b.bump(h, 1, 1), **kw)
    return b.out(sh)


def dash_plastic(name="dash"):
    b = NB(name)
    P = b.geo("Position"); x, y, z = b.xyz(P); nx, ny, nz = b.xyz(b.geo("Normal"))
    up = b.mr(nz, 0.3, 0.9)
    fade = b.mul(up, b.mr(b.noise(b.scale(P, 3), 4), 0.3, 0.7))
    col = b.mixc(fade, (0.030, 0.031, 0.033), (0.075, 0.078, 0.085))
    g = b.voronoi(b.scale(P, 450), 1, "F1", "Distance")
    crk_zone = b.mulall(up, b.band(y, 0.78, 0.82, 0.92, 0.95), b.mr(b.noise(b.scale(P, 4), 3), 0.5, 0.6))
    crk = b.mul(b.mr(b.voronoi(b.scale(P, (30, 6, 30)), 1, "DISTANCE_TO_EDGE", "Distance"), 0.02, 0.0), crk_zone)
    col = b.mixc(crk, col, (0.01, 0.01, 0.01))
    h = b.add(b.mul(g, 0.00012), b.mul(crk, -0.0005))
    sh = b.principled(Base_Color=col, Roughness=b.add(0.62, b.mul(fade, 0.15)), Normal=b.bump(h, 1, 1))
    return b.out(sh)


def seat_cloth(name="seat_cloth"):
    b = NB(name)
    P = b.geo("Position"); x, y, z = b.xyz(P)
    pat = b.mr(b.wave(b.scale(P, 1), 160, 2.0, 1.0, "BANDS", "Z"), 0.4, 0.6)
    dots = b.mr(b.voronoi(b.scale(P, 120), 1, "F1", "Distance"), 0.25, 0.15)
    col = b.mixc(b.mul(pat, 0.35), (0.075, 0.077, 0.082), (0.12, 0.122, 0.13))
    col = b.mixc(b.mul(dots, 0.3), col, (0.17, 0.17, 0.18))
    # driver bolster polished wear (driver at x<0)
    bol = b.mulall(b.mr(x, -0.22, -0.30), b.band(y, -0.55, -0.45, 0.10, 0.18), b.band(z, 0.42, 0.47, 0.56, 0.60),
                   b.add(b.mr(x, -0.50, -0.56), b.mr(x, -0.24, -0.20)))
    stain = b.mr(b.noise(b.scale(P, 6), 4), 0.66, 0.72)
    col = b.mixc(b.mul(stain, 0.4), col, (0.10, 0.09, 0.07))
    col = b.mixc(b.mul(bol, 0.5), col, (0.05, 0.05, 0.055))
    fib = b.noise(b.scale(P, 2000), 2)
    sh = b.principled(Base_Color=col, Roughness=b.sub(0.92, b.mul(bol, 0.45)), Sheen_Weight=b.sub(0.8, b.mul(bol, 0.6)),
                      Sheen_Roughness=0.4, Normal=b.bump(b.add(b.mul(fib, 0.00012), b.mul(pat, 0.0002)), 1, 1))
    return b.out(sh)


def wheel_grip(name="steering"):
    b = NB(name)
    Po = b.tc("Object"); x, y, z = b.xyz(Po)
    ang = b.m("ARCTAN2", z, x)  # object local: wheel in XZ plane
    worn = b.add(b.band(ang, 0.25, 0.4, 0.85, 1.0), b.band(ang, 2.14, 2.29, 2.74, 2.89))
    col = b.mixc(worn, (0.028, 0.028, 0.03), (0.04, 0.04, 0.042))
    g = b.voronoi(b.scale(b.geo("Position"), 600), 1, "F1", "Distance")
    sh = b.principled(Base_Color=col, Roughness=b.sub(0.6, b.mul(worn, 0.35)), Normal=b.bump(b.mul(b.sub(1, worn), b.mul(g, 0.0001)), 1, 1))
    return b.out(sh)


def license_plate(name="plate"):
    b = NB(name)
    P = b.geo("Position")
    n = b.noise(b.scale(P, 20), 4)
    col = b.mixc(b.mul(b.mr(n, 0.5, 0.8), 0.35), (0.62, 0.62, 0.60), (0.48, 0.46, 0.41))
    sh = b.principled(Base_Color=col, Roughness=b.add(0.35, b.mul(n, 0.3)), Coat_Weight=0.3, Coat_Roughness=0.3)
    return b.out(sh)


def corrosion(name="battery_corrosion"):
    b = NB(name)
    P = b.geo("Position")
    n = b.noise(b.scale(P, 120), 6, 0.7)
    col = b.ramp(n, [(0.3, (0.55, 0.58, 0.50)), (0.55, (0.30, 0.45, 0.32)), (0.75, (0.75, 0.77, 0.72))])
    sh = b.principled(Base_Color=col, Roughness=0.95, Normal=b.bump(b.mul(n, 0.002), 1, 1))
    return b.out(sh)


def backdrop(name="backdrop"):
    b = NB(name)
    sh = b.principled(Base_Color=(0.47, 0.47, 0.47), Roughness=0.85, Specular_IOR_Level=0.3)
    return b.out(sh)


def emission_off(name, col):
    b = NB(name)
    sh = b.principled(Base_Color=col, Roughness=0.3)
    return b.out(sh)


def build_all():
    M = {}
    M["paint"] = paint()
    M["paint_inner"] = paint_inner()
    M["trim"] = plastic_black("plastic_trim")
    M["bumper"] = plastic_black("plastic_bumper", 1.0, True)
    M["plastic_int"] = plastic_black("plastic_engine", 0.2, False)
    M["rubber"] = rubber("rubber")
    M["rubber_soft"] = rubber("rubber_seal", True)
    M["glass"] = glass("glass")
    M["glass_ws"] = glass("glass_windshield", windshield=True)
    M["glass_drv"] = glass("glass_driver", driver_scratch=True)
    M["hl_lens_L"] = lens("headlight_lens_L", (0.95, 0.93, 0.82), 0.02, 0.6, True, (-0.515, 1.90, 0.628))
    M["hl_lens_R"] = lens("headlight_lens_R", (0.95, 0.93, 0.84), 0.02, 0.5)
    M["ind_lens"] = lens("indicator_lens", (0.95, 0.55, 0.12), 0.08, 0.8, flutes=True)
    M["tail_red"] = lens("tail_red", (0.62, 0.06, 0.05), 0.06, 0.6)
    M["tail_amber"] = lens("tail_amber", (0.92, 0.50, 0.10), 0.06, 0.6)
    M["tail_clear"] = lens("tail_clear", (0.92, 0.92, 0.90), 0.06, 0.6)
    M["reflector"] = reflector()
    M["rust"] = rusty_steel("rusty_steel", 0.6)
    M["rust_heavy"] = rusty_steel("rusty_heavy", 0.95, (0.10, 0.08, 0.07))
    M["exhaust"] = rusty_steel("exhaust", 0.85, (0.20, 0.19, 0.18), 1.5)
    M["under"] = bitumen()
    M["tire"] = tire()
    M["wheel"] = steel_wheel()
    M["hubcap"] = hubcap("hubcap", (0.20, 0.205, 0.21), 0.38)
    M["hubcap_odd"] = hubcap("hubcap_replacement", (0.25, 0.245, 0.235), 0.30)
    M["disc"] = brake_disc()
    M["caliper"] = simple("caliper", (0.12, 0.11, 0.10), 0.7, 0.3, 0.4, 0.6)
    M["metal_dirty"] = simple("metal_dirty", (0.25, 0.25, 0.25), 0.55, 0.8, 0.4, 0.7)
    M["alu_engine"] = simple("aluminium_cast", (0.33, 0.32, 0.30), 0.62, 0.9, 0.4, 0.8)
    M["engine_black"] = simple("engine_black", (0.03, 0.03, 0.03), 0.55, 0.2, 0.3, 0.8)
    M["hose"] = rubber("hose", True)
    M["reservoir"] = simple("reservoir_pp", (0.55, 0.52, 0.42), 0.45, 0.0, 0.3, 0.6)
    M["battery"] = simple("battery_case", (0.03, 0.03, 0.03), 0.5)
    M["corrosion"] = corrosion()
    M["dash"] = dash_plastic()
    M["int_plastic"] = simple("interior_plastic", (0.045, 0.046, 0.05), 0.6, 0, 0.1, 0.3, grain=0.0001)
    M["int_grey"] = simple("doorcard_grey", (0.10, 0.10, 0.105), 0.6, 0, 0.1, 0.3, grain=0.0001)
    M["seat"] = seat_cloth()
    M["fabric_ins"] = simple("door_fabric", (0.08, 0.08, 0.085), 0.95, 0, 0.2, 0.3, sheen=0.6)
    M["headliner"] = simple("headliner", (0.40, 0.40, 0.39), 0.95, 0, 0.15, 0.4, sheen=0.5)
    M["carpet"] = simple("carpet", (0.03, 0.03, 0.03), 1.0, 0, 0.3, 0.3, sheen=0.7)
    M["mat"] = simple("rubber_mat", (0.03, 0.03, 0.03), 0.75, 0, 0.6, 0.6)
    M["steering"] = wheel_grip()
    M["gauge"] = simple("gauge_face", (0.01, 0.01, 0.01), 0.4)
    M["gauge_mark"] = simple("gauge_marks", (0.75, 0.74, 0.70), 0.5, 0, 0.0, 0.0)
    M["needle"] = simple("needle", (0.7, 0.18, 0.05), 0.4, 0, 0, 0)
    M["lcd"] = simple("lcd", (0.12, 0.14, 0.11), 0.2)
    M["plate"] = license_plate()
    M["freshener"] = simple("air_freshener", (0.15, 0.38, 0.12), 0.9, 0, 0.3, 0.1)
    M["leaf"] = simple("dry_leaf", (0.20, 0.11, 0.04), 0.8, 0, 0.6, 0.1)
    M["bulb"] = simple("bulb_glass", (0.8, 0.8, 0.75), 0.05, 0.3, 0, 0)
    M["backdrop"] = backdrop()
    return M
