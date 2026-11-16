"""Рисунок как «Опыт 1» из отчёта, но на фотографии: поверх фото нарисована сетка прямых линий,
затем кадр искажается бочкой, исправляется найденным K и «слишком сильной» коррекцией.
Красным пунктиром показаны идеальные прямые.

Запуск: python make_monkey_grid.py [фото.png]  ->  ../results/monkey_grid_before_after.png
(и копия в ../../Рисунки для отчёта)
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.optimize import minimize_scalar
from scipy.signal import find_peaks

from lensdistort import lens_correct, distort, to_uint8

ROOT = HERE.parent
RES = ROOT / "results"
PICS = ROOT.parent / "Рисунки для отчёта"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input" / "monkey.png"
plt.rcParams.update({"font.family": ["Times New Roman", "DejaVu Serif"], "axes.unicode_minus": False})

KD = 0.20                      # заданное искажение (бочка)
W, H = 1200, 800               # размер кадра
photo = Image.open(SRC).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
photo = np.asarray(photo, dtype=float)

V_COLS = np.linspace(0.10 * W, 0.90 * W, 9)
H_ROWS = np.linspace(0.12 * H, 0.88 * H, 7)
xs, ys = np.arange(W)[None, :], np.arange(H)[:, None]


def line_layer(kind, sigma):
    a = np.zeros((H, W))
    if kind in ("v", "grid"):
        for c in V_COLS:
            a = np.maximum(a, np.exp(-((xs - c) ** 2) / (2 * sigma ** 2)) * np.ones((H, 1)))
    if kind in ("h", "grid"):
        for r in H_ROWS:
            a = np.maximum(a, np.exp(-((ys - r) ** 2) / (2 * sigma ** 2)) * np.ones((1, W)))
    return a


# --- фото с сеткой: тёмно-синие линии шириной около 4 пикс. поверх снимка
alpha = np.clip(line_layer("grid", 2.0) * 1.15, 0, 1)[..., None]
LINE_COLOR = np.array([11.0, 37.0, 150.0])
scene = photo * (1 - alpha) + LINE_COLOR * alpha


# --- мера прямолинейности (как в опыте 2 отчёта)
def straightness(img2d, vertical, hw=8, margin=0.20):
    a2 = img2d if vertical else img2d.T
    Hh, Ww = a2.shape
    r0 = Hh // 2
    prof = ndimage.gaussian_filter1d(a2[r0], 2)
    pk, _ = find_peaks(prof, height=60, distance=30)
    if len(pk) < 3:
        return 100.0
    spacing = float(np.median(np.diff(pk)))
    lo, hi = int(margin * Hh), int((1 - margin) * Hh)
    errs = []
    for x0 in pk:
        pts, ok = {}, True
        for direction in (1, -1):
            x = float(x0)
            r = r0
            while lo <= r <= hi:
                a, b = max(int(round(x)) - hw, 0), min(int(round(x)) + hw + 1, Ww)
                w = a2[r, a:b]
                if w.size == 0 or w.max() < 60:
                    ok = False
                    break
                x = float((w * np.arange(a, b)).sum() / w.sum())
                pts[r] = x
                r += direction
            if not ok:
                break
        if not ok or len(pts) < (hi - lo) * 0.95:
            continue
        rr = np.array(sorted(pts))
        xx = np.array([pts[k] for k in rr])
        p = np.polyfit(rr, xx, 1)
        errs.append(np.sqrt(np.mean((xx - np.polyval(p, rr)) ** 2)))
    if len(errs) < 2:
        return 100.0
    return float(100.0 * np.median(errs) / spacing)


metric_v = (line_layer("v", 1.5) * 255)[..., None]
metric_h = (line_layer("h", 1.5) * 255)[..., None]
dv, dh = distort(metric_v, KD, pad=0), distort(metric_h, KD, pad=0)


def line_error(K):
    ev = straightness(lens_correct(dv, K, pad=0)[1][..., 0], True)
    eh = straightness(lens_correct(dh, K, pad=0)[1][..., 0], False)
    return 0.5 * (ev + eh)


Ks = np.round(np.arange(-0.40, 0.001, 0.025), 3)
errs = [line_error(K) for K in Ks]
k0 = float(Ks[int(np.argmin(errs))])
res = minimize_scalar(line_error, bounds=(k0 - 0.03, k0 + 0.03), method="bounded", options={"xatol": 1e-3})
K_EST = float(res.x)
print(f"K_d = {KD:+.2f}, найдено K = {K_EST:+.3f}, отклонение: до {line_error(0.0):.2f} %, после {res.fun:.2f} %")

# --- искажение и коррекция
dist_img = distort(scene, KD, pad=0)
_, fixed = lens_correct(dist_img, K_EST, pad=50)
_, over = lens_correct(dist_img, K_EST - 0.15, pad=50)


def ref_lines(ax, pad=0, color="#d62728"):
    for c in V_COLS:
        ax.axvline(c + pad, color=color, lw=0.8, ls="--", alpha=0.95)
    for r in H_ROWS:
        ax.axhline(r + pad, color=color, lw=0.8, ls="--", alpha=0.95)


def kfmt(k):
    return f"{k:+.3f}".replace(".", ",").replace("-", "−")


fig, axs = plt.subplots(2, 2, figsize=(11, 7.6), dpi=150)
panels = [(scene, 0, "Исходное фото с сеткой (прямые линии)"),
          (dist_img, 0, f"Искажённое (бочка, $K_d$ = +{KD:.2f})".replace(".", ",")),
          (fixed, 50, f"Исправленное, K = {kfmt(K_EST)} (найдено вслепую)"),
          (over, 50, f"Слишком сильная коррекция, K = {kfmt(K_EST - 0.15)}")]
for ax, (im, pad, t) in zip(axs.flat, panels):
    ax.imshow(to_uint8(im))
    ref_lines(ax, pad)
    ax.set_title(t, fontsize=11)
    ax.axis("off")
fig.suptitle("Опыт 1. Красным пунктиром показаны идеальные прямые", y=0.995)
fig.tight_layout()
out = RES / "monkey_grid_before_after.png"
fig.savefig(out)
plt.close(fig)
PICS.mkdir(exist_ok=True)
shutil.copy(out, PICS / "15_опыт_обезьяна_сетка_до_и_после.png")
print("сохранено:", out.name)
