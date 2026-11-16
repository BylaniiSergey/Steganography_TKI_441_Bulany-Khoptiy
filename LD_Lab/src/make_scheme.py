"""Схема алгоритма коррекции дисторсии (по ГОСТ 19.701-90) -> ../results/scheme_algorithm.png"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

plt.rcParams.update({"font.family": ["Times New Roman", "DejaVu Serif"], "font.size": 12})
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "scheme_algorithm.png")

fig, ax = plt.subplots(figsize=(8.2, 13.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 20)
ax.axis("off")
CX, BW, BH = 5.0, 6.6, 1.15


def box(y, text, kind="proc", h=BH, w=BW):
    x0, y0 = CX - w / 2, y - h / 2
    if kind == "term":
        ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle=f"round,pad=0,rounding_size={h / 2}",
                                    fc="white", ec="black", lw=1.4))
    elif kind == "io":
        d = 0.45
        ax.add_patch(Polygon([(x0 + d, y0 + h), (x0 + w, y0 + h), (x0 + w - d, y0), (x0, y0)],
                             closed=True, fc="white", ec="black", lw=1.4))
    elif kind == "loop_top":
        d = 0.3
        ax.add_patch(Polygon([(x0 + d, y0 + h), (x0 + w - d, y0 + h), (x0 + w, y0 + h - d), (x0 + w, y0),
                              (x0, y0), (x0, y0 + h - d)], closed=True, fc="white", ec="black", lw=1.4))
    elif kind == "loop_bot":
        d = 0.3
        ax.add_patch(Polygon([(x0, y0 + h), (x0 + w, y0 + h), (x0 + w, y0 + d), (x0 + w - d, y0),
                              (x0 + d, y0), (x0, y0 + d)], closed=True, fc="white", ec="black", lw=1.4))
    else:
        ax.add_patch(Rectangle((x0, y0), w, h, fc="white", ec="black", lw=1.4))
    ax.text(CX, y, text, ha="center", va="center", fontsize=11.5, linespacing=1.25)


def arrow(y1, y2):
    ax.annotate("", xy=(CX, y2), xytext=(CX, y1), arrowprops=dict(arrowstyle="-|>", lw=1.3, color="black"))


ys = [19.0, 17.35, 15.55, 13.65, 11.85, 10.05, 8.3, 6.1, 4.3, 2.75, 1.2]
box(ys[0], "Начало", "term", h=0.9)
box(ys[1], "Ввод: изображение im\n(размер Y×X, Z каналов),\nпараметр дисторсии K", "io", h=1.35)
box(ys[2], "Дополнить im нулевыми полями\nпо 50 пикс. с каждой стороны:\nразмер ydim = Y+100, xdim = X+100", h=1.35)
box(ys[3], "Построить сетку координат и нормировать:\nxramp = (i − xdim/2) / (xdim/2),\nyramp = (j − ydim/2) / (ydim/2)", h=1.35)
box(ys[4], "Радиус до центра изображения:\nr = √(xramp² + yramp²)", h=1.2)
box(ys[5], "Новая сетка:\nxrampK = xramp·(1 + K·r²),\nyrampK = yramp·(1 + K·r²)", h=1.35)
box(ys[6], "Для каждого канала z = 1 … Z", "loop_top", h=0.9)
box(ys[7], "Интерполяция исходного канала im(:,:,z)\nв точках (xrampK, yrampK):\nimK(:,:,z) = interp2(xramp, yramp, im(:,:,z),\nxrampK, yrampK, 'cubic')", h=1.6)
box(ys[8], "Конец цикла по z", "loop_bot", h=0.9)
box(ys[9], "Вывод: im (с полями) и исправленное\nизображение imK; значение K в заголовке", "io", h=1.2)
box(ys[10], "Конец", "term", h=0.9)

tops = [0.45, 0.675, 0.675, 0.675, 0.6, 0.675, 0.45, 0.8, 0.45, 0.6]
bots = [0.45, 0.675, 0.675, 0.675, 0.6, 0.675, 0.45, 0.8, 0.45, 0.6]
for i in range(len(ys) - 1):
    arrow(ys[i] - bots[i], ys[i + 1] + (tops[i + 1] if i + 1 < len(tops) else 0.45))

ax.text(CX + 3.55, ys[6] - 0.0, "", fontsize=9)
ax.text(0.15, 0.1, "K < 0 - коррекция бочки, K > 0 - коррекция подушки; главная точка - центр кадра",
        fontsize=9.5, style="italic")
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("схема сохранена:", os.path.basename(OUT))
