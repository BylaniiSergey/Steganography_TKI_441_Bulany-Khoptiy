"""
Опыты для отчёта по варианту 9.6 (Lens Distortion): python experiments.py
Все результаты пишутся в ../results (рисунки .png, таблицы .csv, сводка summary.json).

Опыт 1. Синтетическая сетка прямых линий: искажаем её известным K_d, исправляем разными K.
Опыт 2. Мера «прямолинейности» линий как функция K - по минимуму оцениваем K вслепую.
Опыт 3. Реальное изображение (фото из ЛР2): искажаем известным K_d, исправляем, PSNR(K).
Опыт 4. Влияние порядка интерполяции (ближайший сосед / билинейная / кубическая).
Опыт 5. Влияние полей из нулей (pad = 0 и 50).
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy import ndimage
from scipy.optimize import minimize_scalar
from scipy.signal import find_peaks

from lensdistort import lens_correct, distort, to_uint8

ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)
plt.rcParams.update({"font.family": ["Times New Roman", "DejaVu Serif"], "font.size": 11,
                     "axes.unicode_minus": False})

W, H = 1200, 900                 # размер синтетической сцены
V_COLS = np.linspace(120, 1080, 9)   # вертикальные линии (центры столбцов)
H_ROWS = np.linspace(110, 790, 7)    # горизонтальные линии (центры строк)


# ---------------------------------------------------------------- сцены и метрики
def scene_lines(kind):
    """Сцена из тонких прямых линий с гауссовым профилем (σ = 1,5 пикс.), чтобы
    положение линии можно было определять с подпиксельной точностью. kind: 'v', 'h' или 'grid'."""
    s = np.zeros((H, W))
    xs, ys = np.arange(W)[None, :], np.arange(H)[:, None]
    if kind in ("v", "grid"):
        for c in V_COLS:
            s = np.maximum(s, 255 * np.exp(-((xs - c) ** 2) / (2 * 1.5 ** 2)) * np.ones((H, 1)))
    if kind in ("h", "grid"):
        for r in H_ROWS:
            s = np.maximum(s, 255 * np.exp(-((ys - r) ** 2) / (2 * 1.5 ** 2)) * np.ones((1, W)))
    return s[..., None]


def straightness(img2d, vertical, hw=8, margin=0.20):
    """Мера прямолинейности линий на изображении, % от расстояния между соседними линиями.

    Линии вдоль оси 0 (при vertical=False изображение транспонируется). Положение каждой линии
    в центральной строке находится по пикам профиля, затем линия прослеживается вверх и вниз
    с подпиксельным центроидом в окне ±hw. По центральной части кадра (margin..1-margin)
    строится наилучшая прямая x = a*y + b; мера - СКО отклонений, делённое на расстояние между
    линиями (поэтому она не зависит от масштаба, который меняет коррекция)."""
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


def line_error(dist_v, dist_h, Kc, order=3):
    """Прямолинейность после коррекции с параметром Kc, % расстояния между линиями
    (среднее для вертикальных и горизонтальных линий)."""
    ev = straightness(lens_correct(dist_v, Kc, pad=0, order=order)[1][..., 0], True)
    eh = straightness(lens_correct(dist_h, Kc, pad=0, order=order)[1][..., 0], False)
    return 0.5 * (ev + eh)


def psnr(a, b, mask):
    mse = np.mean((a[mask] - b[mask]) ** 2)
    return float(10 * np.log10(255.0 ** 2 / mse)) if mse > 0 else float("inf")


def save_img(path, arr):
    Image.fromarray(to_uint8(arr)).save(path)


def overlay_ref(ax, pad=0, color="#d62728"):
    """Рисует идеальные (прямые) линии сетки красным пунктиром поверх изображения."""
    for c in V_COLS:
        ax.axvline(c + pad, color=color, lw=0.7, ls="--", alpha=0.9)
    for r in H_ROWS:
        ax.axhline(r + pad, color=color, lw=0.7, ls="--", alpha=0.9)


summary = {}

# ============================================================ ОПЫТ 1 и 2: синтетическая сетка
grid = scene_lines("grid")
sv, sh = scene_lines("v"), scene_lines("h")

# искажённые копии: K_d > 0 - бочка, K_d < 0 - подушка
Kd_list = [0.10, 0.20, -0.10, -0.20]
dist_grid = {Kd: distort(grid, Kd, pad=0) for Kd in Kd_list}
dist_v = {Kd: distort(sv, Kd, pad=0) for Kd in Kd_list}
dist_h = {Kd: distort(sh, Kd, pad=0) for Kd in Kd_list}

# --- кривые «ошибка прямолинейности - K»
Ks = np.round(np.arange(-0.40, 0.401, 0.025), 3)
curves, rows = {}, []
for Kd in Kd_list:
    e = [line_error(dist_v[Kd], dist_h[Kd], K) for K in Ks]
    curves[Kd] = e
    for K, v in zip(Ks, e):
        rows.append([Kd, K, round(v, 4)])
with open(os.path.join(RES, "straightness_vs_K.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["K_d (искажение)", "K (коррекция)", "Отклонение линий от прямых, % расстояния между линиями"])
    w.writerows([[a, str(b).replace(".", ","), str(c).replace(".", ",")] for a, b, c in rows])

# --- оценка K вслепую: минимизация ошибки прямолинейности
est = {}
for Kd in Kd_list:
    k0 = float(Ks[int(np.argmin(curves[Kd]))])      # грубый минимум по сетке, затем уточнение
    r = minimize_scalar(lambda K: line_error(dist_v[Kd], dist_h[Kd], K), bounds=(k0 - 0.03, k0 + 0.03),
                        method="bounded", options={"xatol": 1e-3})
    base = line_error(dist_v[Kd], dist_h[Kd], 0.0)
    est[Kd] = {"K_est": round(float(r.x), 4), "err_min": round(float(r.fun), 3), "err_at_0": round(base, 3)}
summary["synthetic_estimate"] = {str(k): v for k, v in est.items()}
with open(os.path.join(RES, "estimate_K_synthetic.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["K_d (задано)", "Тип искажения", "K найдено", "Сумма K_d+K", "Отклонение до коррекции, %",
                "Отклонение после коррекции, %"])
    for Kd in Kd_list:
        e = est[Kd]
        w.writerow([str(Kd).replace(".", ","), "бочка" if Kd > 0 else "подушка",
                    str(e["K_est"]).replace(".", ","), str(round(Kd + e["K_est"], 4)).replace(".", ","),
                    str(e["err_at_0"]).replace(".", ","), str(e["err_min"]).replace(".", ",")])

# --- рисунок: ошибка прямолинейности от K
fig, ax = plt.subplots(figsize=(8, 4.6))
cols = {0.10: "#1f77b4", 0.20: "#2ca02c", -0.10: "#ff7f0e", -0.20: "#9467bd"}
for Kd in Kd_list:
    ax.plot(Ks, curves[Kd], "-", color=cols[Kd], lw=1.8,
            label=f"$K_d$ = {Kd:+.2f} ({'бочка' if Kd > 0 else 'подушка'})")
    ax.plot(est[Kd]["K_est"], est[Kd]["err_min"], "o", color=cols[Kd], ms=7, mec="k")
ax.set_xlabel("параметр коррекции K")
ax.set_ylabel("отклонение линий от прямых, % расстояния между линиями")
ax.set_title("Опыт 2. Прямолинейность линий после коррекции (точки - минимум)")
ax.grid(alpha=0.3)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(RES, "fig3_straightness_vs_K.png"), dpi=170)
plt.close(fig)

# --- рисунок 1: идеал / искажённая / исправленная / «перекоррекция»
Kd = 0.20
Kc = est[Kd]["K_est"]
_, fixed = lens_correct(dist_grid[Kd], Kc, pad=50)
_, over = lens_correct(dist_grid[Kd], Kc - 0.15, pad=50)
fig, axs = plt.subplots(2, 2, figsize=(11, 8.4))
panels = [(grid, 0, "Идеальная сцена (прямые линии)"),
          (dist_grid[Kd], 0, f"Искажённая (бочка, $K_d$ = {Kd:+.2f})"),
          (fixed, 50, f"Исправленная, K = {Kc:+.3f} (найдено вслепую)"),
          (over, 50, f"Слишком сильная коррекция, K = {Kc - 0.15:+.3f}")]
for ax, (im, pad, t) in zip(axs.flat, panels):
    ax.imshow(to_uint8(im), cmap="gray", vmin=0, vmax=255)
    overlay_ref(ax, pad)
    ax.set_title(t, fontsize=11)
    ax.axis("off")
fig.suptitle("Опыт 1. Красным пунктиром показаны идеальные прямые", y=0.995)
fig.tight_layout()
fig.savefig(os.path.join(RES, "fig1_grid_before_after.png"), dpi=150)
plt.close(fig)
save_img(os.path.join(RES, "grid_distorted_barrel.png"), dist_grid[Kd])
save_img(os.path.join(RES, "grid_corrected.png"), fixed)
save_img(os.path.join(RES, "grid_ideal.png"), grid)

# --- рисунок 2: перебор K на искажённой сетке (бочка и подушка)
fig, axs = plt.subplots(2, 4, figsize=(15, 6.6))
for row, (Kd2, Kset) in enumerate([(0.20, [-0.30, -0.20, -0.15, 0.00]), (-0.20, [0.00, 0.20, 0.325, 0.45])]):
    for ax, K in zip(axs[row], Kset):
        _, im = lens_correct(dist_grid[Kd2], K, pad=50)
        ax.imshow(to_uint8(im), cmap="gray", vmin=0, vmax=255)
        overlay_ref(ax, 50)
        ax.set_title(f"$K_d$ = {Kd2:+.2f}, K = {K:+.2f}", fontsize=10)
        ax.axis("off")
fig.suptitle("Опыт 1. Перебор параметра коррекции K (верхний ряд - бочка, нижний - подушка)")
fig.tight_layout()
fig.savefig(os.path.join(RES, "fig2_K_sweep_grid.png"), dpi=140)
plt.close(fig)

# ============================================================ ОПЫТ 3: реальное изображение
photo = np.array(Image.open(os.path.join(ROOT, "input", "photo_phone.png")).convert("RGB")).astype(float)
ph, pw = photo.shape[:2]
Kd_photo = 0.20
dist_photo = distort(photo, Kd_photo, pad=0)
# Область сравнения: где исходное содержимое не потеряно при искажении (у бочки углы кадра уходят
# за границу и заменяются чёрным). Определяем по белому кадру: искажаем, исправляем, берём то,
# что осталось белым, и отступаем на 10 пикс. внутрь.
ones = np.ones((ph, pw, 1)) * 255
_, ones_back = lens_correct(distort(ones, Kd_photo, pad=0), -0.75 * Kd_photo, pad=50, order=1)
valid = np.zeros((ph + 100, pw + 100), bool)
valid[50:50 + ph, 50:50 + pw] = True
valid &= ndimage.binary_erosion(ones_back[..., 0] > 250, iterations=10)
mask = np.repeat(valid[..., None], 3, axis=2)
summary_mask_share = float(valid.sum()) / (ph * pw)
padded_orig = np.zeros((ph + 100, pw + 100, 3))
padded_orig[50:50 + ph, 50:50 + pw] = photo

Kp = np.round(np.arange(-0.50, 0.101, 0.025), 4)
pk = []
for K in Kp:
    _, c = lens_correct(dist_photo, K, pad=50)
    pk.append(psnr(np.clip(c, 0, 255), padded_orig, mask))
best = int(np.argmax(pk))
r = minimize_scalar(lambda K: -psnr(np.clip(lens_correct(dist_photo, K, pad=50)[1], 0, 255), padded_orig, mask),
                    bounds=(-0.5, 0.0), method="bounded", options={"xatol": 1e-3})
K_best = float(r.x)
_, corrected = lens_correct(dist_photo, K_best, pad=50)
psnr_dist = psnr(np.clip(lens_correct(dist_photo, 0.0, pad=50)[1], 0, 255), padded_orig, mask)
psnr_fix = psnr(np.clip(corrected, 0, 255), padded_orig, mask)
summary["photo"] = {"valid_area_share": round(summary_mask_share, 3), "K_d": Kd_photo, "K_best": round(K_best, 4), "psnr_distorted": round(psnr_dist, 2),
                    "psnr_corrected": round(psnr_fix, 2), "size": [pw, ph]}
with open(os.path.join(RES, "photo_psnr_vs_K.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["K (коррекция)", "PSNR, дБ"])
    for K, v in zip(Kp, pk):
        w.writerow([str(K).replace(".", ","), str(round(v, 2)).replace(".", ",")])

fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(Kp, pk, "-o", ms=4, color="#1f77b4")
ax.axvline(-Kd_photo, color="#d62728", ls="--", lw=1, label=f"$-K_d$ = {-Kd_photo:+.2f}")
ax.plot(K_best, psnr_fix, "s", color="k", ms=7, label=f"максимум: K = {K_best:+.3f}, {psnr_fix:.1f} дБ")
ax.set_xlabel("параметр коррекции K")
ax.set_ylabel("PSNR исправленного и исходного, дБ")
ax.set_title("Опыт 3. Качество восстановления фото в зависимости от K")
ax.grid(alpha=0.3)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(RES, "fig5_psnr_vs_K.png"), dpi=170)
plt.close(fig)

diff = np.abs(np.clip(corrected, 0, 255) - padded_orig)
fig, axs = plt.subplots(2, 2, figsize=(12, 9))
panels = [(photo, "Исходное изображение"),
          (dist_photo, f"Искажённое (бочка, $K_d$ = {Kd_photo:+.2f})"),
          (corrected, f"Исправленное, K = {K_best:+.3f} ({psnr_fix:.1f} дБ)"),
          (np.clip(diff * 4, 0, 255), "Модуль разности с исходным (×4)")]
for ax, (im, t) in zip(axs.flat, panels):
    ax.imshow(to_uint8(im))
    ax.set_title(t, fontsize=11)
    ax.axis("off")
fig.suptitle("Опыт 3. Реальное изображение: искажение и коррекция", y=0.995)
fig.tight_layout()
fig.savefig(os.path.join(RES, "fig4_photo_before_after.png"), dpi=130)
plt.close(fig)
save_img(os.path.join(RES, "photo_distorted.png"), dist_photo)
save_img(os.path.join(RES, "photo_corrected.png"), corrected)

# ============================================================ ОПЫТ 4: интерполяция
names = {0: "ближайший сосед", 1: "билинейная", 3: "кубическая (B-сплайн)"}
interp = {}
for order in (0, 1, 3):
    _, c = lens_correct(dist_photo, K_best, pad=50, order=order)
    interp[order] = (np.clip(c, 0, 255), psnr(np.clip(c, 0, 255), padded_orig, mask))
summary["interpolation"] = {names[o]: round(v[1], 2) for o, v in interp.items()}
with open(os.path.join(RES, "interpolation.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Интерполяция при коррекции", "PSNR, дБ"])
    for o in (0, 1, 3):
        w.writerow([names[o], str(round(interp[o][1], 2)).replace(".", ",")])

y0, x0 = 50 + int(0.30 * ph), 50 + int(0.30 * pw)      # фрагмент для увеличения
fig, axs = plt.subplots(1, 4, figsize=(15, 4.2))
crop = (slice(y0, y0 + 90), slice(x0, x0 + 120))
axs[0].imshow(to_uint8(padded_orig[crop]), interpolation="nearest"); axs[0].set_title("Исходное")
for ax, o in zip(axs[1:], (0, 1, 3)):
    ax.imshow(to_uint8(interp[o][0][crop]), interpolation="nearest")
    ax.set_title(f"{names[o]}\n{interp[o][1]:.1f} дБ", fontsize=10)
for ax in axs:
    ax.axis("off")
fig.suptitle("Опыт 4. Фрагмент 120×90 пикс. при разной интерполяции")
fig.tight_layout()
fig.savefig(os.path.join(RES, "fig6_interpolation.png"), dpi=150)
plt.close(fig)

# ============================================================ ОПЫТ 5: поля из нулей
dd = dist_grid[0.20]
Kc5 = est[0.20]["K_est"]
_, p0 = lens_correct(dd, Kc5, pad=0)
_, p50 = lens_correct(dd, Kc5, pad=50)
# доля «белых» пикселей линий, которые после коррекции оказались в 50-пиксельных полях, т.е. за исходным кадром
inner = np.zeros(p50.shape[:2], bool)
inner[50:-50, 50:-50] = True
white = p50[..., 0] > 127
out_share = 100.0 * float((white & ~inner).sum()) / float(white.sum())
summary["padding"] = {"K": Kc5, "percent_of_line_pixels_outside_original_frame": round(out_share, 2)}
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
axs[0].imshow(to_uint8(p0), cmap="gray"); axs[0].set_title("Без полей (pad = 0)")
axs[1].imshow(to_uint8(p50), cmap="gray"); axs[1].set_title("С полями 50 пикс. (как в книге)")
for ax in axs:
    ax.axis("off")
fig.suptitle("Опыт 5. Что теряется при коррекции бочки без полей")
fig.tight_layout()
fig.savefig(os.path.join(RES, "fig7_padding.png"), dpi=150)
plt.close(fig)

with open(os.path.join(RES, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(json.dumps(summary, ensure_ascii=False, indent=2))
