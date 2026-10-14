#!/usr/bin/env python3
"""Эскиз с габаритами, проверка посадок и расчёт материала для модели FP-5 «Фламинго».

Создаёт:
  * sketch.pdf / sketch.png  — лист 1: сборка (3 вида), лист 2: детали с размерами + расчёт
  * sketch_page2.png
  * MATERIALS.md             — таблица материала, стоимости и времени печати
Запуск: python3 drawing.py (после generate.py, использует его параметры).
"""
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

# ---------- Параметры расчёта материала (FDM, PLA) ----------
DENSITY = 1.24          # г/см³, PLA
FIL_D = 1.75            # мм, диаметр прутка
WALL = 3 * 0.42         # мм, 3 периметра
SHELL_TB = 0.8          # мм, верх/низ (≈5 слоёв по 0.16)
INFILL = 0.15           # заполнение 15 %
PRICE_PER_KG = 1500.0   # руб. за 1 кг катушки
FLOW_G_PER_H = 9.0      # г/ч — средняя производительность для мелких деталей, слой 0.16
WASTE = 1.10            # +10 % на юбку, продувку, брак

# ---------- Геометрия в собранном виде ----------
Z_ROCKET = g.STAND_H + g.POST_H + g.R - g.BELLY_CUT   # ось ракеты над столом
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
    """Пересечения деталей (должны быть ~0) и зазоры."""
    res = []
    names = list(parts)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = parts[names[i]], parts[names[j]]
            v = (a ^ b).volume()
            res.append((f"{names[i]} ∩ {names[j]}", v))
    return res


# ---------- Рисование ----------
def draw_view(ax, mesh, axes, color="#f8bbd0", edge="#222", angle=25):
    """Ортогональная проекция: заливка + рёбра-силуэты/резкие рёбра."""
    i, j = axes
    v2 = mesh.vertices[:, [i, j]]
    ax.add_collection(PolyCollection(v2[mesh.faces], facecolors=color,
                                     edgecolors="none", zorder=2))
    # резкие рёбра
    ang = mesh.face_adjacency_angles
    edges = mesh.face_adjacency_edges[ang > np.radians(angle)]
    # силуэт: смежные грани, одна смотрит на нас, другая — нет
    k = 3 - i - j
    nrm = mesh.face_normals[:, k]
    fa = mesh.face_adjacency
    sil = mesh.face_adjacency_edges[(nrm[fa[:, 0]] > 0) != (nrm[fa[:, 1]] > 0)]
    # открытые границы (у таких моделей нет)
    allE = np.vstack([edges, sil])
    ax.add_collection(LineCollection(v2[allE], colors=edge, linewidths=0.45, zorder=3))


def dim(ax, p1, p2, off, text=None, horiz=True, fs=8):
    """Размерная линия между p1 и p2 со смещением off."""
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
    # штамп
    x0, y0, w, h = 0.66, 0.015, 0.325, 0.09
    fig.patches.append(plt.Rectangle((x0, y0), w, h, transform=fig.transFigure,
                                     fill=False, lw=1.0, ec="k"))
    fig.text(x0 + 0.01, y0 + h - 0.025, "Памятная модель ракеты FP-5 «Фламинго»",
             fontsize=11, fontweight="bold")
    fig.text(x0 + 0.01, y0 + h - 0.05, title, fontsize=9)
    fig.text(x0 + 0.01, y0 + 0.012,
             f"Масштаб: 1:1 (мм)   Материал: PLA   Лист {sheet}/{total}", fontsize=8)
    fig.text(x0 + w - 0.01, y0 + 0.012, "Размеры в мм, эскиз", fontsize=8, ha="right")


# ---------- Расчёт материала ----------
def material(mesh):
    V = mesh.volume / 1000.0                  # см³
    A = mesh.area / 100.0                     # см²
    shell = min(V, A * (WALL / 10.0) * 0.75 + A * (SHELL_TB / 10.0) * 0.25)
    infill = max(V - shell, 0) * INFILL
    used = (shell + infill) * WASTE           # см³ пластика
    mass = used * DENSITY
    length = used / (np.pi * (FIL_D / 20.0) ** 2) / 100.0   # м
    return dict(V=V, mass=mass, length=length, cost=mass / 1000 * PRICE_PER_KG,
                time=mass / FLOW_G_PER_H)


def main():
    parts = assembly_parts()
    meshes = {k: tm(v) for k, v in parts.items()}
    full = trimesh.util.concatenate(list(meshes.values()))
    bb = full.bounds
    fits = fit_checks(parts)

    # зазоры (из параметров) и проверки
    pin_top = g.STAND_H + g.POST_H + g.PIN_H
    hole_top = g.STAND_H + g.POST_H + g.HOLE_DEPTH
    checks = [
        ("Штырь Ø%.1f в отверстии Ø%.1f" % (g.PIN_D, g.PIN_D + 2 * g.FIT), g.FIT, "радиальный зазор"),
        ("Штырь %.1f мм / глубина отв. %.1f мм" % (g.PIN_H, g.HOLE_DEPTH), hole_top - pin_top, "запас по глубине"),
        ("Крыло %.1f мм в пазу %.1f мм" % (g.WING_T, g.WING_T + 2 * g.FIT), g.FIT, "зазор на сторону"),
        ("Оперение %.1f мм в пазу %.1f мм" % (g.TAIL_T, g.TAIL_T + 2 * g.FIT), g.FIT, "зазор на сторону"),
    ]
    for name, v in fits:
        assert v < 0.01, f"Пересечение деталей: {name} = {v:.3f} мм³"

    # материал по деталям для печати
    print_parts = {
        "Подставка (stand.stl)": tm(g.lay_flat(g.stand())),
        "Фюзеляж (fuselage.stl)": tm(g.lay_flat(g.fuselage_printable())),
        "Крыло (wing.stl)": tm(g.lay_flat(g.wing_part())),
        "Оперение (tail.stl)": tm(g.lay_flat(g.tail_shape())),
    }
    rows = []
    for name, m in print_parts.items():
        b = m.bounds; d = b[1] - b[0]
        mt = material(m)
        rows.append((name, f"{d[0]:.1f}×{d[1]:.1f}×{d[2]:.1f}", mt))
    tot = {k: sum(r[2][k] for r in rows) for k in ("V", "mass", "length", "cost", "time")}

    pdf = PdfPages(os.path.join(HERE, "sketch.pdf"))

    # ===== Лист 1: сборка =====
    fig = plt.figure(figsize=(16.54, 11.69))  # A3
    frame(fig, 1, 2, "Сборочный эскиз, габаритные размеры")
    zt = bb[1][2]
    # Вид спереди (XZ)
    ax = fig.add_axes([0.04, 0.50, 0.55, 0.44])
    for k in ("stand", "fuselage", "tail", "wing"):
        draw_view(ax, meshes[k], (0, 2), color="#cfd8dc" if k == "stand" else "#f8bbd0")
    setup(ax, "Вид спереди (сбоку на ракету)", (-85, 85), (-22, 75))
    dim(ax, (-70, 0), (70, 0), -10, "140 (подставка)")
    dim(ax, (DX, Z_ROCKET), (DX + g.L, Z_ROCKET), zt + 8, f"{g.L:.0f} (длина ракеты)")
    dim(ax, (70, 0), (70, zt), 80, f"{zt:.1f} (общая высота)", horiz=False)
    dim(ax, (-70, 0), (-70, g.STAND_H), -76, f"{g.STAND_H:.0f}", horiz=False)
    dim(ax, (-8, g.STAND_H), (-8, g.STAND_H + g.POST_H), -14, f"{g.POST_H:.0f}", horiz=False)
    dim(ax, (DX, 0), (0, 0), -18, f"{g.PIN_X:.0f} (нос → ось стойки)")
    note(ax, (DX + 95, Z_ROCKET + g.R + 7.5), "мотогондола Ø6.8×30", (-30, 14))
    note(ax, (DX + 116, Z_ROCKET + 6), "кили H-оперения h=8", (2, 16))

    # Вид сверху (XY)
    ax = fig.add_axes([0.04, 0.10, 0.55, 0.40])
    for k in ("stand", "fuselage", "tail", "wing"):
        draw_view(ax, meshes[k], (0, 1), color="#cfd8dc" if k == "stand" else "#f8bbd0")
    setup(ax, "Вид сверху", (-85, 100), (-40, 45))
    dim(ax, (-70, -23), (-70, 23), -78, "46", horiz=False)
    wx = DX + 58
    dim(ax, (wx, DY - 29), (wx, DY + 29), 92, "58 (размах крыла)", horiz=False)
    dim(ax, (DX + g.L - 3, DY - 15), (DX + g.L - 3, DY + 15), 78, "30 (оперение)", horiz=False)
    dim(ax, (DX + 44, DY + 29), (DX + 58, DY + 29), 40, "14 (хорда)")

    # Вид сбоку (YZ)
    ax = fig.add_axes([0.62, 0.50, 0.35, 0.44])
    for k in ("stand", "tail", "fuselage", "wing"):
        draw_view(ax, meshes[k], (1, 2), color="#cfd8dc" if k == "stand" else "#f8bbd0")
    setup(ax, "Вид слева (с носа)", (-40, 40), (-22, 75))
    dim(ax, (-23, 0), (23, 0), -10, "46")
    dim(ax, (DY - g.R, Z_ROCKET), (DY + g.R, Z_ROCKET), zt + 6, f"Ø{2*g.R:.0f}")
    dim(ax, (DY - 29, Z_ROCKET + g.WING_Z), (DY + 29, Z_ROCKET + g.WING_Z), -16, "58")

    # Сводка
    ax = fig.add_axes([0.62, 0.12, 0.35, 0.34]); ax.axis("off")
    txt = [
        "ГАБАРИТЫ СБОРКИ",
        f"  Д × Ш × В: {bb[1][0]-bb[0][0]:.1f} × {bb[1][1]-bb[0][1]:.1f} × {zt:.1f} мм",
        f"  Ракета: {g.L:.0f} мм, Ø{2*g.R:.0f} мм, размах 58 мм",
        f"  Ось ракеты над столом: {Z_ROCKET:.1f} мм",
        "",
        "ПРОВЕРКА ПОСАДОК",
    ]
    for n, v, d in checks:
        txt.append(f"  {'✔' if v > 0 else '✘'} {n}: {d} {v:.2f} мм")
    worst = max(v for _, v in fits)
    txt.append(f"  ✔ Пересечений деталей нет (макс. {worst:.3f} мм³)")
    txt += ["", "МАТЕРИАЛ (итого, PLA)",
            f"  Масса ≈ {tot['mass']:.0f} г, пруток Ø1.75 ≈ {tot['length']:.1f} м",
            f"  Стоимость ≈ {tot['cost']:.0f} руб. (при {PRICE_PER_KG:.0f} руб./кг)",
            f"  Время печати ≈ {tot['time']:.1f} ч"]
    ax.text(0, 1, "\n".join(txt), va="top", family="DejaVu Sans Mono", fontsize=9)
    fig.savefig(os.path.join(HERE, "sketch.png"), dpi=110)
    pdf.savefig(fig); plt.close(fig)

    # ===== Лист 2: детали =====
    fig = plt.figure(figsize=(16.54, 11.69))
    frame(fig, 2, 2, "Детали: пазы, посадки, расчёт материала")
    fus = tm(g.fuselage_printable())
    # Фюзеляж сбоку
    ax = fig.add_axes([0.04, 0.66, 0.6, 0.29])
    draw_view(ax, fus, (0, 2))
    setup(ax, "Деталь 1 — Фюзеляж (вид сбоку)", (-8, 128), (-16, 22))
    zb = -g.R + g.BELLY_CUT
    dim(ax, (0, zb), (g.L, zb), -12, f"{g.L:.0f}")
    dim(ax, (g.L, zb), (g.L, fus.bounds[1][2]), 126, f"{fus.bounds[1][2]-zb:.1f}", horiz=False)
    dim(ax, (0, -g.R), (0, g.R), -5, f"Ø{2*g.R:.0f}", horiz=False)
    ws = g.WING_T + 2 * g.FIT
    note(ax, (51, g.WING_Z), f"паз крыла {14+2*g.FIT:.1f}×{ws:.1f} сквозной", (-30, 14))
    note(ax, (g.L - 7, 0), f"паз оперения {10.5+2*g.FIT:.1f}×{g.TAIL_T+2*g.FIT:.1f} сквозной", (-30, -14))
    note(ax, (g.PIN_X, zb), f"отв. Ø{g.PIN_D+2*g.FIT:.1f}, гл. {g.HOLE_DEPTH:.1f}", (12, -8))
    note(ax, (5, zb), f"плоское брюхо (срез {g.BELLY_CUT} мм)", (8, -8))

    # Крыло сверху
    wing = tm(g.wing_part())
    ax = fig.add_axes([0.04, 0.33, 0.28, 0.32])
    draw_view(ax, wing, (0, 1))
    setup(ax, f"Деталь 2 — Крыло, s={g.WING_T:.0f}", (36, 70), (-34, 34))
    dim(ax, (44, -29), (58, -29), -33, "14")
    dim(ax, (56, -29), (56, 29), 64, "58", horiz=False)
    dim(ax, (47, 29), (56, 29), 32, "9")

    # Оперение
    tail = tm(g.tail_shape())
    ax = fig.add_axes([0.34, 0.33, 0.3, 0.32])
    draw_view(ax, tail, (0, 1))
    setup(ax, f"Деталь 3 — Оперение, s={g.TAIL_T}", (g.L - 18, g.L + 6), (-24, 20))
    dim(ax, (g.L - 13, -15), (g.L - 2.5, -15), -18, "10.5")
    dim(ax, (g.L - 1, -15), (g.L - 1, 15), g.L + 3, "30", horiz=False)
    ax2 = fig.add_axes([0.34, 0.19, 0.3, 0.1])
    draw_view(ax2, tail, (0, 2))
    setup(ax2, "вид сбоку: кили h=8", (g.L - 18, g.L + 6), (-3, 12))

    # Подставка сверху
    st = tm(g.stand())
    ax = fig.add_axes([0.66, 0.55, 0.32, 0.40])
    draw_view(ax, st, (0, 1), color="#cfd8dc", angle=40)
    setup(ax, "Деталь 4 — Подставка (вид сверху)", (-75, 75), (-30, 30))
    dim(ax, (-70, -23), (70, -23), -28, "140")
    dim(ax, (70, -23), (70, 23), 73, "46", horiz=False)
    note(ax, (0, g.POST_Y), f"стойка Ø12→Ø7, h={g.POST_H:.0f};\nштырь Ø{g.PIN_D:.0f}, h={g.PIN_H}", (20, 12))
    note(ax, (0, -11), f"надпись «{g.TITLE}», h=1", (-60, -12))

    # Таблица материала
    ax = fig.add_axes([0.04, 0.03, 0.6, 0.15]); ax.axis("off")
    head = ["Деталь", "Габарит, мм", "Объём, см³", "Масса, г", "Пруток, м", "Цена, руб.", "Время, ч"]
    data = [[n, d, f"{m['V']:.2f}", f"{m['mass']:.1f}", f"{m['length']:.2f}",
             f"{m['cost']:.0f}", f"{m['time']:.1f}"] for n, d, m in rows]
    data.append(["ИТОГО", "", f"{tot['V']:.2f}", f"{tot['mass']:.1f}", f"{tot['length']:.2f}",
                 f"{tot['cost']:.0f}", f"{tot['time']:.1f}"])
    t = ax.table(cellText=data, colLabels=head, loc="upper left", cellLoc="center")
    t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.25)
    for (r, c), cell in t.get_celld().items():
        if r == 0 or r == len(data):
            cell.set_text_props(fontweight="bold")
    ax3 = fig.add_axes([0.66, 0.13, 0.32, 0.38]); ax3.axis("off")
    ax3.text(0, 1, "\n".join([
        "ДОПУЩЕНИЯ РАСЧЁТА",
        f"  PLA, ρ = {DENSITY} г/см³, пруток Ø{FIL_D} мм",
        f"  стенки 3×0.42 мм, верх/низ {SHELL_TB} мм",
        f"  заполнение {INFILL*100:.0f} %, +{(WASTE-1)*100:.0f} % на юбку/отходы",
        f"  цена {PRICE_PER_KG:.0f} руб./кг, ~{FLOW_G_PER_H:.0f} г/ч (слой 0.16)",
        "  Слайсер даст точные цифры — расхождение ±20 %.",
        "",
        "ЦВЕТА",
        "  Ракета (дет. 1–3): розовый PLA",
        "  Подставка: серый/чёрный, надпись — смена",
        f"  цвета на высоте {g.STAND_H:.0f} мм (белый/золотой)",
        "",
        "КРЕПЁЖ",
        "  Суперклей (циакрилат) — 1–2 капли",
        "  в пазы крыла и оперения (по желанию).",
    ]), va="top", family="DejaVu Sans Mono", fontsize=9)
    fig.savefig(os.path.join(HERE, "sketch_page2.png"), dpi=110)
    pdf.savefig(fig); plt.close(fig); pdf.close()

    # MATERIALS.md
    md = ["# Расчёт материала и габариты — FP-5 «Фламинго»", "",
          f"Габарит сборки: **{bb[1][0]-bb[0][0]:.1f} × {bb[1][1]-bb[0][1]:.1f} × {zt:.1f} мм** (Д × Ш × В)", "",
          "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    md += ["| " + " | ".join(r) + " |" for r in data]
    md += ["", "## Проверка посадок", ""]
    md += [f"- {n}: {d} **{v:.2f} мм**" for n, v, d in checks]
    md += [f"- Пересечений деталей в сборке нет (макс. {worst:.3f} мм³)", "",
           "## Допущения", "",
           f"PLA ρ={DENSITY} г/см³, пруток {FIL_D} мм, 3 стенки, заполнение {INFILL*100:.0f} %, "
           f"+{(WASTE-1)*100:.0f} % на отходы, цена {PRICE_PER_KG:.0f} руб./кг, ~{FLOW_G_PER_H:.0f} г/ч. "
           "Точные цифры покажет слайсер (±20 %).", ""]
    open(os.path.join(HERE, "MATERIALS.md"), "w").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
