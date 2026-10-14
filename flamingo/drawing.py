#!/usr/bin/env python3
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import PolyCollection, LineCollection
import trimesh

import generate as g

HERE = os.path.dirname(os.path.abspath(__file__))

DENSITY = 1.24
FIL_D = 1.75
WALL = 3 * 0.42
SHELL_TB = 0.8
INFILL = 0.15
PRICE_PER_KG = 700.0
FLOW_G_PER_H = 9.0
WASTE = 1.10

Z_ROCKET = g.STAND_H + g.POST_H + g.R - g.BELLY_CUT
DX, DY = -g.PIN_X, g.POST_Y


def tm(man):
    return g.to_trimesh(man)


def assembly_parts():
    off = [DX, DY, Z_ROCKET]
    return {
        "stand": g.stand(),
        "fuselage": g.fuselage_printable().translate(off),
        "wing": g.wing_part().translate([DX, DY, Z_ROCKET + g.WING_Z]),
        "tail": g.tail_shape().translate(off),
    }


def fit_checks(parts):
    res = []
    names = list(parts)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = parts[names[i]], parts[names[j]]
            v = (a ^ b).volume()
            res.append((f"{names[i]} ∩ {names[j]}", v))
    return res


def draw_view(ax, mesh, axes, color="#f8bbd0", edge="#222", angle=25):
    i, j = axes
    v2 = mesh.vertices[:, [i, j]]
    ax.add_collection(PolyCollection(v2[mesh.faces], facecolors=color,
                                     edgecolors="none", zorder=2))
    ang = mesh.face_adjacency_angles
    edges = mesh.face_adjacency_edges[ang > np.radians(angle)]
    k = 3 - i - j
    nrm = mesh.face_normals[:, k]
    fa = mesh.face_adjacency
    sil = mesh.face_adjacency_edges[(nrm[fa[:, 0]] > 0) != (nrm[fa[:, 1]] > 0)]
    allE = np.vstack([edges, sil])
    ax.add_collection(LineCollection(v2[allE], colors=edge, linewidths=0.45, zorder=3))


def dim(ax, p1, p2, off, text=None, horiz=True, fs=8):
    (x1, y1), (x2, y2) = p1, p2
    kw = dict(color="#1565c0", lw=0.6, zorder=5)
    if horiz:
        y = off
        ax.plot([x1, x1], [y1, y], **kw); ax.plot([x2, x2], [y2, y], **kw)
        ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", **{k: v for k, v in kw.items() if k != 'zorder'}, shrinkA=0, shrinkB=0))
        ax.text((x1 + x2) / 2, y + (1.2 if y >= max(y1, y2) else -1.2),
                text or f"{abs(x2 - x1):.1f}", ha="center",
                va="bottom" if y >= max(y1, y2) else "top", fontsize=fs, color="#0d47a1",
                bbox=dict(fc="white", ec="none", pad=0.3), zorder=6)
    else:
        x = off
        ax.plot([x1, x], [y1, y1], **kw); ax.plot([x2, x], [y2, y2], **kw)
        ax.annotate("", (x, y1), (x, y2), arrowprops=dict(arrowstyle="<->", **{k: v for k, v in kw.items() if k != 'zorder'}, shrinkA=0, shrinkB=0))
        ax.text(x + (1.2 if x >= max(x1, x2) else -1.2), (y1 + y2) / 2,
                text or f"{abs(y2 - y1):.1f}", ha="left" if x >= max(x1, x2) else "right",
                va="center", rotation=90, fontsize=fs, color="#0d47a1",
                bbox=dict(fc="white", ec="none", pad=0.3), zorder=6)


def note(ax, xy, txt, dxy=(8, 8), fs=7):
    ax.annotate(txt, xy, (xy[0] + dxy[0], xy[1] + dxy[1]), fontsize=fs,
                arrowprops=dict(arrowstyle="-", color="#555", lw=0.5),
                color="#333", zorder=7, bbox=dict(fc="white", ec="none", pad=0.2))


def setup(ax, title, xlim, ylim):
    ax.set_aspect("equal"); ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.axis("off"); ax.set_title(title, fontsize=10, loc="left", fontweight="bold")


def frame(fig, sheet, total, title):
    fig.patches.append(plt.Rectangle((0.01, 0.01), 0.98, 0.98, transform=fig.transFigure,
                                     fill=False, lw=1.2, ec="k"))
    x0, y0, w, h = 0.66, 0.015, 0.325, 0.09
    fig.patches.append(plt.Rectangle((x0, y0), w, h, transform=fig.transFigure,
                                     fill=False, lw=1.0, ec="k"))
    fig.text(x0 + 0.01, y0 + h - 0.025, "Пам'ятна модель ракети FP-5 «Фламінго»",
             fontsize=11, fontweight="bold")
    fig.text(x0 + 0.01, y0 + h - 0.05, title, fontsize=9)
    fig.text(x0 + 0.01, y0 + 0.012,
             f"Масштаб: 1:1 (мм)   Матеріал: PLA   Аркуш {sheet}/{total}", fontsize=8)
    fig.text(x0 + w - 0.01, y0 + 0.012, "Розміри в мм, ескіз", fontsize=8, ha="right")


def material(mesh):
    V = mesh.volume / 1000.0
    A = mesh.area / 100.0
    shell = min(V, A * (WALL / 10.0) * 0.75 + A * (SHELL_TB / 10.0) * 0.25)
    infill = max(V - shell, 0) * INFILL
    used = (shell + infill) * WASTE
    mass = used * DENSITY
    length = used / (np.pi * (FIL_D / 20.0) ** 2) / 100.0
    return dict(V=V, mass=mass, length=length, cost=mass / 1000 * PRICE_PER_KG,
                time=mass / FLOW_G_PER_H)


def main():
    parts = assembly_parts()
    meshes = {k: tm(v) for k, v in parts.items()}
    full = trimesh.util.concatenate(list(meshes.values()))
    bb = full.bounds
    fits = fit_checks(parts)

    pin_top = g.STAND_H + g.POST_H + g.PIN_H
    hole_top = g.STAND_H + g.POST_H + g.HOLE_DEPTH
    checks = [
        ("Штир Ø%.1f в отворі Ø%.1f" % (g.PIN_D, g.PIN_D + 2 * g.FIT), g.FIT, "радіальний зазор"),
        ("Штир %.1f мм / глибина отв. %.1f мм" % (g.PIN_H, g.HOLE_DEPTH), hole_top - pin_top, "запас по глибині"),
        ("Крило %.1f мм у пазу %.1f мм" % (g.WING_T, g.WING_T + 2 * g.FIT), g.FIT, "зазор на бік"),
        ("Оперення %.1f мм у пазу %.1f мм" % (g.TAIL_T, g.TAIL_T + 2 * g.FIT), g.FIT, "зазор на бік"),
    ]
    for name, v in fits:
        assert v < 0.01, f"Перетин деталей: {name} = {v:.3f} мм³"

    print_parts = {
        "Підставка (stand.stl)": tm(g.lay_flat(g.stand())),
        "Фюзеляж (fuselage.stl)": tm(g.lay_flat(g.fuselage_printable())),
        "Крило (wing.stl)": tm(g.lay_flat(g.wing_part())),
        "Оперення (tail.stl)": tm(g.lay_flat(g.tail_shape())),
    }
    rows = []
    for name, m in print_parts.items():
        b = m.bounds; d = b[1] - b[0]
        mt = material(m)
        rows.append((name, f"{d[0]:.1f}×{d[1]:.1f}×{d[2]:.1f}", mt))
    tot = {k: sum(r[2][k] for r in rows) for k in ("V", "mass", "length", "cost", "time")}

    pdf = PdfPages(os.path.join(HERE, "sketch.pdf"))

    fig = plt.figure(figsize=(16.54, 11.69))
    frame(fig, 1, 2, "Складальний ескіз, габаритні розміри")
    zt = bb[1][2]
    ax = fig.add_axes([0.04, 0.50, 0.55, 0.44])
    for k in ("stand", "fuselage", "tail", "wing"):
        draw_view(ax, meshes[k], (0, 2), color="#cfd8dc" if k == "stand" else "#f8bbd0")
    setup(ax, "Вигляд спереду (збоку на ракету)", (-85, 85), (-22, 75))
    dim(ax, (-70, 0), (70, 0), -10, "140 (підставка)")
    dim(ax, (DX, Z_ROCKET), (DX + g.L, Z_ROCKET), zt + 8, f"{g.L:.0f} (довжина ракети)")
    dim(ax, (70, 0), (70, zt), 80, f"{zt:.1f} (загальна висота)", horiz=False)
    dim(ax, (-70, 0), (-70, g.STAND_H), -76, f"{g.STAND_H:.0f}", horiz=False)
    dim(ax, (-8, g.STAND_H), (-8, g.STAND_H + g.POST_H), -14, f"{g.POST_H:.0f}", horiz=False)
    dim(ax, (DX, 0), (0, 0), -18, f"{g.PIN_X:.0f} (ніс → вісь стійки)")
    note(ax, (DX + 95, Z_ROCKET + g.R + 7.5), "мотогондола Ø6.8×30", (-30, 14))
    note(ax, (DX + 116, Z_ROCKET + 6), "кілі H-оперення h=8", (2, 16))

    ax = fig.add_axes([0.04, 0.10, 0.55, 0.40])
    for k in ("stand", "fuselage", "tail", "wing"):
        draw_view(ax, meshes[k], (0, 1), color="#cfd8dc" if k == "stand" else "#f8bbd0")
    setup(ax, "Вигляд згори", (-85, 100), (-40, 45))
    dim(ax, (-70, -23), (-70, 23), -78, "46", horiz=False)
    wx = DX + 58
    dim(ax, (wx, DY - 29), (wx, DY + 29), 92, "58 (розмах крила)", horiz=False)
    dim(ax, (DX + g.L - 3, DY - 15), (DX + g.L - 3, DY + 15), 78, "30 (оперення)", horiz=False)
    dim(ax, (DX + 44, DY + 29), (DX + 58, DY + 29), 40, "14 (хорда)")

    ax = fig.add_axes([0.62, 0.50, 0.35, 0.44])
    for k in ("stand", "tail", "fuselage", "wing"):
        draw_view(ax, meshes[k], (1, 2), color="#cfd8dc" if k == "stand" else "#f8bbd0")
    setup(ax, "Вигляд зліва (з носа)", (-40, 40), (-22, 75))
    dim(ax, (-23, 0), (23, 0), -10, "46")
    dim(ax, (DY - g.R, Z_ROCKET), (DY + g.R, Z_ROCKET), zt + 6, f"Ø{2*g.R:.0f}")
    dim(ax, (DY - 29, Z_ROCKET + g.WING_Z), (DY + 29, Z_ROCKET + g.WING_Z), -16, "58")

    ax = fig.add_axes([0.62, 0.12, 0.35, 0.34]); ax.axis("off")
    txt = [
        "ГАБАРИТИ ЗБІРКИ",
        f"  Д × Ш × В: {bb[1][0]-bb[0][0]:.1f} × {bb[1][1]-bb[0][1]:.1f} × {zt:.1f} мм",
        f"  Ракета: {g.L:.0f} мм, Ø{2*g.R:.0f} мм, розмах 58 мм",
        f"  Вісь ракети над столом: {Z_ROCKET:.1f} мм",
        "",
        "ПЕРЕВІРКА ПОСАДОК",
    ]
    for n, v, d in checks:
        txt.append(f"  {'✔' if v > 0 else '✘'} {n}: {d} {v:.2f} мм")
    worst = max(v for _, v in fits)
    txt.append(f"  ✔ Перетинів деталей немає (макс. {worst:.3f} мм³)")
    txt += ["", "МАТЕРІАЛ (разом, PLA)",
            f"  Маса ≈ {tot['mass']:.0f} г, пруток Ø1.75 ≈ {tot['length']:.1f} м",
            f"  Вартість ≈ {tot['cost']:.0f} грн (при {PRICE_PER_KG:.0f} грн/кг)",
            f"  Час друку ≈ {tot['time']:.1f} год"]
    ax.text(0, 1, "\n".join(txt), va="top", family="DejaVu Sans Mono", fontsize=9)
    fig.savefig(os.path.join(HERE, "sketch.png"), dpi=110)
    pdf.savefig(fig); plt.close(fig)

    fig = plt.figure(figsize=(16.54, 11.69))
    frame(fig, 2, 2, "Деталі: пази, посадки, розрахунок матеріалу")
    fus = tm(g.fuselage_printable())
    ax = fig.add_axes([0.04, 0.66, 0.6, 0.29])
    draw_view(ax, fus, (0, 2))
    setup(ax, "Деталь 1 — Фюзеляж (вигляд збоку)", (-8, 128), (-16, 22))
    zb = -g.R + g.BELLY_CUT
    dim(ax, (0, zb), (g.L, zb), -12, f"{g.L:.0f}")
    dim(ax, (g.L, zb), (g.L, fus.bounds[1][2]), 126, f"{fus.bounds[1][2]-zb:.1f}", horiz=False)
    dim(ax, (0, -g.R), (0, g.R), -5, f"Ø{2*g.R:.0f}", horiz=False)
    ws = g.WING_T + 2 * g.FIT
    note(ax, (51, g.WING_Z), f"паз крила {14+2*g.FIT:.1f}×{ws:.1f} наскрізний", (-30, 14))
    note(ax, (g.L - 7, 0), f"паз оперення {10.5+2*g.FIT:.1f}×{g.TAIL_T+2*g.FIT:.1f} наскрізний", (-30, -14))
    note(ax, (g.PIN_X, zb), f"отв. Ø{g.PIN_D+2*g.FIT:.1f}, глиб. {g.HOLE_DEPTH:.1f}", (12, -8))
    note(ax, (5, zb), f"пласке черевце (зріз {g.BELLY_CUT} мм)", (8, -8))

    wing = tm(g.wing_part())
    ax = fig.add_axes([0.04, 0.33, 0.28, 0.32])
    draw_view(ax, wing, (0, 1))
    setup(ax, f"Деталь 2 — Крило, s={g.WING_T:.0f}", (36, 70), (-34, 34))
    dim(ax, (44, -29), (58, -29), -33, "14")
    dim(ax, (56, -29), (56, 29), 64, "58", horiz=False)
    dim(ax, (47, 29), (56, 29), 32, "9")

    tail = tm(g.tail_shape())
    ax = fig.add_axes([0.34, 0.33, 0.3, 0.32])
    draw_view(ax, tail, (0, 1))
    setup(ax, f"Деталь 3 — Оперення, s={g.TAIL_T}", (g.L - 18, g.L + 6), (-24, 20))
    dim(ax, (g.L - 13, -15), (g.L - 2.5, -15), -18, "10.5")
    dim(ax, (g.L - 1, -15), (g.L - 1, 15), g.L + 3, "30", horiz=False)
    ax2 = fig.add_axes([0.34, 0.19, 0.3, 0.1])
    draw_view(ax2, tail, (0, 2))
    setup(ax2, "вигляд збоку: кілі h=8", (g.L - 18, g.L + 6), (-3, 12))

    st = tm(g.stand())
    ax = fig.add_axes([0.66, 0.55, 0.32, 0.40])
    draw_view(ax, st, (0, 1), color="#cfd8dc", angle=40)
    setup(ax, "Деталь 4 — Підставка (вигляд згори)", (-75, 75), (-30, 30))
    dim(ax, (-70, -23), (70, -23), -28, "140")
    dim(ax, (70, -23), (70, 23), 73, "46", horiz=False)
    note(ax, (0, g.POST_Y), f"стійка Ø12→Ø7, h={g.POST_H:.0f};\nштир Ø{g.PIN_D:.0f}, h={g.PIN_H}", (20, 12))
    note(ax, (0, -11), f"напис {g.TITLE}, h=1", (-60, -12))

    ax = fig.add_axes([0.04, 0.03, 0.6, 0.15]); ax.axis("off")
    head = ["Деталь", "Габарит, мм", "Об'єм, см³", "Маса, г", "Пруток, м", "Ціна, грн", "Час, год"]
    data = [[n, d, f"{m['V']:.2f}", f"{m['mass']:.1f}", f"{m['length']:.2f}",
             f"{m['cost']:.1f}", f"{m['time']:.1f}"] for n, d, m in rows]
    data.append(["РАЗОМ", "", f"{tot['V']:.2f}", f"{tot['mass']:.1f}", f"{tot['length']:.2f}",
                 f"{tot['cost']:.1f}", f"{tot['time']:.1f}"])
    t = ax.table(cellText=data, colLabels=head, loc="upper left", cellLoc="center")
    t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.25)
    for (r, c), cell in t.get_celld().items():
        if r == 0 or r == len(data):
            cell.set_text_props(fontweight="bold")
    ax3 = fig.add_axes([0.66, 0.13, 0.32, 0.38]); ax3.axis("off")
    ax3.text(0, 1, "\n".join([
        "ПРИПУЩЕННЯ РОЗРАХУНКУ",
        f"  PLA, ρ = {DENSITY} г/см³, пруток Ø{FIL_D} мм",
        f"  стінки 3×0.42 мм, верх/низ {SHELL_TB} мм",
        f"  заповнення {INFILL*100:.0f} %, +{(WASTE-1)*100:.0f} % на спідницю/відходи",
        f"  ціна {PRICE_PER_KG:.0f} грн/кг, ~{FLOW_G_PER_H:.0f} г/год (шар 0.16)",
        "  Точні цифри дасть слайсер — розбіжність ±20 %.",
        "",
        "КОЛЬОРИ",
        "  Ракета (дет. 1–3): рожевий PLA",
        "  Підставка: сірий/чорний, напис — зміна",
        f"  кольору на висоті {g.STAND_H:.0f} мм (білий/золотий)",
        "",
        "КРІПЛЕННЯ",
        "  Суперклей (ціакрилат) — 1–2 краплі",
        "  у пази крила та оперення (за бажанням).",
    ]), va="top", family="DejaVu Sans Mono", fontsize=9)
    fig.savefig(os.path.join(HERE, "sketch_page2.png"), dpi=110)
    pdf.savefig(fig); plt.close(fig); pdf.close()

    md = ["# Розрахунок матеріалу та габарити — FP-5 «Фламінго»", "",
          f"Габарит збірки: **{bb[1][0]-bb[0][0]:.1f} × {bb[1][1]-bb[0][1]:.1f} × {zt:.1f} мм** (Д × Ш × В)", "",
          "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    md += ["| " + " | ".join(r) + " |" for r in data]
    md += ["", "## Перевірка посадок", ""]
    md += [f"- {n}: {d} **{v:.2f} мм**" for n, v, d in checks]
    md += [f"- Перетинів деталей у збірці немає (макс. {worst:.3f} мм³)", "",
           "## Припущення", "",
           f"PLA ρ={DENSITY} г/см³, пруток {FIL_D} мм, 3 стінки, заповнення {INFILL*100:.0f} %, "
           f"+{(WASTE-1)*100:.0f} % на відходи, ціна {PRICE_PER_KG:.0f} грн/кг, ~{FLOW_G_PER_H:.0f} г/год. "
           "Точні цифри покаже слайсер (±20 %).", ""]
    open(os.path.join(HERE, "MATERIALS.md"), "w").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
