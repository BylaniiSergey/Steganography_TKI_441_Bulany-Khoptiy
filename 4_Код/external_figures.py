"""Рисунки для раздела «Проверка в программах из задания». Запуск: python src/external_figures.py"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = RES / "external"
plt.rcParams["font.family"] = "Arial"


def block_scheme():
    """Что программа Антропова/Архипова пишет в один блок 8×8 синего канала."""
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=170)
    colors = {0: "#d9d9d9", 1: "#9ec5e8", 2: "#efefef", 3: "#d9d9d9", 4: "#9ed8b4",
              5: "#efefef", 6: "#d9d9d9", 7: "#f2b8b8"}
    for a in range(8):
        for b in range(8):
            ax.add_patch(Rectangle((b, 7 - a), 1, 1, facecolor=colors[b], edgecolor="#333", linewidth=1))
    labels = {1: "R", 4: "G", 7: "B"}
    for a in range(8):
        for b in (1, 4, 7):
            ax.text(b + .5, 7 - a + .5, f"{labels[b]}{a}", ha="center", va="center", fontsize=11)
        for b, text in ((0, "ДКП0 R"), (3, "ДКП0 G"), (6, "ДКП0 B"), (2, "ДКП1 R"), (5, "ДКП1 G")):
            ax.text(b + .5, 7 - a + .5, text, ha="center", va="center", fontsize=8, color="#444")
    for b in range(8):
        ax.text(b + .5, 8.2, f"b = {b}", ha="center", fontsize=10)
    for a in range(8):
        ax.text(-.2, 7 - a + .5, f"a = {a}", ha="right", va="center", fontsize=10)
    ax.set_xlim(-1.7, 14.2)
    ax.set_ylim(-.8, 9.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(8.5, 7.3, "Блок 8 × 8 синего канала\n(один пиксель ЦВЗ на блок)", fontsize=13, fontweight="bold",
            va="top")
    notes = ["В каждый из 64 пикселей блока пишется только\nмладший бит синего канала: B* = (B & 254) + m.",
             "Столбцы 1, 4, 7: m = бит a значения R, G, B\nпикселя ЦВЗ (24 бита на блок).",
             "Остальные столбцы: m = знак коэффициента ДКП\nвсего изображения (0, если < 0; иначе 1).",
             "Красный и зелёный каналы контейнера\nне меняются; изменение каждого пикселя ≤ 1."]
    for i, text in enumerate(notes):
        ax.text(8.5, 5.4 - i * 1.55, text, fontsize=10.5, va="top")
    fig.savefig(OUT / "stegwm_block.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def comparison_two_rows(names=("gradient", "texture"), labels=("Градиент", "Пёстрая текстура")):
    titles = ["Пустой контейнер", "КДБ: |разница| × 8", "stegwm 8 × 8: × 255", "stegwm 32 × 32: × 255"]
    fig, axes = plt.subplots(len(names), 4, figsize=(11.5, 3.1 * len(names) + .5), dpi=170)
    for row, (name, label) in enumerate(zip(names, labels)):
        cover = np.array(Image.open(RES / name / "cover.png").convert("RGB")).astype(np.int16)
        kjb = np.array(Image.open(RES / name / "stego.png").convert("RGB")).astype(np.int16)
        s8 = np.array(Image.open(OUT / name / "stegwm_8x8.png").convert("RGB")).astype(np.int16)
        s32 = np.array(Image.open(OUT / name / "stegwm_32x32.png").convert("RGB")).astype(np.int16)
        tiles = [cover.astype(np.uint8)] + [np.clip(np.abs(x - cover) * k, 0, 255).astype(np.uint8)
                                            for x, k in ((kjb, 8), (s8, 255), (s32, 255))]
        for col, tile in enumerate(tiles):
            ax = axes[row, col]
            ax.imshow(tile, interpolation="nearest")
            ax.set_xticks([])
            ax.set_yticks([])
            if row == 0:
                ax.set_title(titles[col], fontsize=11)
            if col == 0:
                ax.set_ylabel(label, fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "comparison_two_rows.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    block_scheme()
    comparison_two_rows()
    print("готово")
