"""Самопроверка lensdistort.py: четыре быстрых проверки (запуск: python selftest.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from lensdistort import lens_correct, distort

ok_all = True


def check(name, cond, info=""):
    global ok_all
    ok_all &= bool(cond)
    print(("ПРОЙДЕНО " if cond else "ОШИБКА   ") + name + (" - " + info if info else ""))


rng = np.random.default_rng(1)
img = rng.integers(0, 256, (120, 160, 3)).astype(float)

# 1. K = 0 не меняет изображение (внутри полей)
pad, out = lens_correct(img, 0.0, pad=50, order=3)
err = np.abs(out - pad).max()
check("K=0 - тождественное преобразование", err < 1e-6, f"макс. ошибка {err:.2e}")

# 2. Размер результата = исходный + 2*pad
check("размер с полями", out.shape == (120 + 100, 160 + 100, 3), str(out.shape))

# 3. Знак: линия x = const правее центра при K>0 (бочка) должна прогибаться наружу в середине
scene = np.zeros((401, 401, 1))
scene[:, 300:303, 0] = 255                      # вертикальная линия правее центра
d = distort(scene, +0.3, pad=0, order=1)[..., 0]
col_mid = np.argmax(d[200]); col_top = np.argmax(d[100])
check("K>0 даёт бочку (концы линии ближе к центру, чем середина)",
      d[100].max() > 100 and col_top < col_mid, f"столбец в строке 100: {col_top}, в середине: {col_mid}")
d = distort(scene, -0.3, pad=0, order=1)[..., 0]
col_mid = np.argmax(d[200]); col_top = np.argmax(d[100])
check("K<0 даёт подушку (концы линии дальше от центра, чем середина)",
      d[100].max() > 100 and col_top > col_mid, f"столбец в строке 100: {col_top}, в середине: {col_mid}")

# 4. Круговая проверка: distort(K) затем коррекция (-K) возвращает изображение почти точно
smooth = np.fromfunction(lambda y, x, z: 128 + 100 * np.sin(x / 25.0) * np.cos(y / 31.0), (300, 400, 1))
dist = distort(smooth, 0.15, pad=0, order=3)
_, back = lens_correct(dist, -0.15, pad=0, order=3)
c = (slice(60, 240), slice(80, 320))
rmse = np.sqrt(np.mean((back[c] - smooth[c]) ** 2))
check("круговая проверка distort(K) + correct(-K)", rmse < 3.0, f"СКО в центре {rmse:.2f} из 255")

print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if ok_all else "ЕСТЬ ОШИБКИ")
