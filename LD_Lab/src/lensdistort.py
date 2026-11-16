"""
Коррекция радиальной дисторсии объектива (вариант 9.6, Lens Distortion).

Перенос на Python MATLAB-функции lensdistort из книги
H. Farid, "Digital Image Forensics" (Dartmouth, 2012), раздел 9.6, стр. 157-158.

Модель: главная точка совпадает с центром изображения. Координаты пикселя
нормируются в [-1, 1] по каждой оси, r - расстояние до центра.
Пиксель исправленного изображения в точке (x, y) берётся из исходного изображения
в точке (x*(1 + K*r^2), y*(1 + K*r^2)).

    K < 0  - исправляет бочкообразную дисторсию (типична для широкоугольных объективов);
    K > 0  - исправляет подушкообразную дисторсию (типична для телеобъективов);
    K = 0  - изображение не меняется.

Отличия от оригинала (сознательные):
  * интерполяция - кубический B-сплайн scipy (order=3) вместо кубической свёртки
    MATLAB interp2(...,'cubic'); порядок интерполяции можно менять параметром order;
  * точки вне исходного кадра заполняются чёрным (в MATLAB - NaN, при uint8 тоже 0).

Запуск из командной строки:
    python lensdistort.py вход.png выход.png -K -0.2 [--order 3] [--pad 50]
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates


def lens_correct(im, K, pad=50, order=3):
    """Возвращает (im_pad, imK): исходное изображение с полями pad пикселей
    по каждой стороне и исправленное изображение того же размера (как im, imK в MATLAB)."""
    im = np.asarray(im, dtype=np.float64)
    if im.ndim == 2:
        im = im[..., None]
    ydim0, xdim0, zdim = im.shape

    # поля из нулей, чтобы углы изображения не обрезались при растяжении
    impad = np.zeros((ydim0 + 2 * pad, xdim0 + 2 * pad, zdim))
    impad[pad:pad + ydim0, pad:pad + xdim0, :] = im
    ydim, xdim = impad.shape[:2]

    # [xramp,yramp] = meshgrid([1:xdim]-xdim/2, [1:ydim]-ydim/2); нормировка на половину размера
    xramp = (np.arange(1, xdim + 1) - xdim / 2.0) / (xdim / 2.0)
    yramp = (np.arange(1, ydim + 1) - ydim / 2.0) / (ydim / 2.0)
    xramp, yramp = np.meshgrid(xramp, yramp)

    rad = np.sqrt(xramp ** 2 + yramp ** 2)
    xrampK = xramp * (1 + K * rad ** 2)
    yrampK = yramp * (1 + K * rad ** 2)

    # обратно в индексы массива (0-based): индекс MATLAB = x*(xdim/2) + xdim/2
    col = xrampK * (xdim / 2.0) + xdim / 2.0 - 1.0
    row = yrampK * (ydim / 2.0) + ydim / 2.0 - 1.0

    imK = np.empty_like(impad)
    for z in range(zdim):
        imK[..., z] = map_coordinates(impad[..., z], [row, col], order=order,
                                      mode="constant", cval=0.0)
    return impad, imK


def distort(im, K, pad=0, order=3):
    """Искусственная дисторсия: та же формула, что и коррекция, но применяется к
    идеальному изображению. K > 0 даёт бочку, K < 0 - подушку (обратный знак к коррекции)."""
    return lens_correct(im, K, pad=pad, order=order)[1]


def to_uint8(a):
    a = np.clip(np.rint(a), 0, 255).astype(np.uint8)
    return a[..., 0] if a.shape[-1] == 1 else a


def main():
    ap = argparse.ArgumentParser(description="Коррекция радиальной дисторсии (раздел 9.6 книги Farid)")
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("-K", type=float, required=True, help="параметр дисторсии, обычно от -1 до 1")
    ap.add_argument("--order", type=int, default=3, help="порядок интерполяции: 0, 1 или 3")
    ap.add_argument("--pad", type=int, default=50, help="ширина полей из нулей, пикс.")
    a = ap.parse_args()
    im = np.array(Image.open(a.src).convert("RGB"))
    _, imK = lens_correct(im, a.K, pad=a.pad, order=a.order)
    Image.fromarray(to_uint8(imK)).save(a.dst)
    print("сохранено:", os.path.basename(a.dst), "размер", imK.shape[1], "x", imK.shape[0])


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
