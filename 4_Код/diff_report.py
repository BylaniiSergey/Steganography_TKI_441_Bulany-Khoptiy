"""Программа разницы: сравнивает пустой и заполненный контейнеры и сохраняет результаты.

Запуск: python src/diff_report.py <пустой.png> <заполненный.png> [--amplify 50] [--out папка]

Создаёт: маску изменённых пикселей (красные точки на чёрном), усиленную карту разницы (по каналам),
список изменённых пикселей в CSV и печатает статистику по пикселям и по каналам.
"""
import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image


def compare(empty, filled, amplify=50, out=None, threshold=0):
    a = np.array(Image.open(empty).convert("RGB")).astype(np.int16)
    b = np.array(Image.open(filled).convert("RGB")).astype(np.int16)
    if a.shape != b.shape:
        raise ValueError("Размеры изображений не совпадают, сравнение невозможно.")
    d = np.abs(b - a)
    per_pixel = d.sum(axis=2)
    mask = per_pixel > threshold
    h, w = mask.shape
    stats = {
        "total_pixels": int(h * w),
        "changed_pixels": int(mask.sum()),
        "changed_percent": float(mask.mean() * 100),
        "total_deviation": int(per_pixel[mask].sum()),
        "max_deviation": int(per_pixel.max()),
        "mean_deviation": float(per_pixel[mask].mean()) if mask.any() else 0.0,
        "changed_by_channel": {name: int((d[:, :, i] > 0).sum()) for i, name in enumerate("RGB")},
    }
    if out is not None:
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        binary = np.zeros((h, w, 3), dtype=np.uint8)
        binary[mask] = (255, 0, 0)
        Image.fromarray(binary).save(out / "diff_binary.png")
        Image.fromarray(np.clip(d * amplify, 0, 255).astype(np.uint8)).save(out / "diff_amplified.png")
        ys, xs = np.nonzero(mask)
        with (out / "changed_pixels.csv").open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["X", "Y", "R_old", "G_old", "B_old", "R_new", "G_new", "B_new", "Diff"])
            for y, x in zip(ys, xs):
                writer.writerow([x, y, *a[y, x], *b[y, x], int(per_pixel[y, x])])
    return stats


def print_stats(stats, empty="", filled=""):
    print(f"Сравнение:\n  Пустой:      {empty}\n  Заполненный: {filled}\n")
    print("--- СТАТИСТИКА ПО ПИКСЕЛЯМ ---")
    print(f"Всего пикселей:          {stats['total_pixels']}")
    print(f"Изменённых пикселей:     {stats['changed_pixels']} ({stats['changed_percent']:.4f}%)")
    print(f"Суммарное отклонение:    {stats['total_deviation']}")
    print(f"Максимальное отклонение: {stats['max_deviation']}")
    print(f"Среднее отклонение:      {stats['mean_deviation']:.2f}")
    print("\n--- ИЗМЕНЕНИЯ ПО КАНАЛАМ ---")
    for name, count in stats["changed_by_channel"].items():
        print(f"Канал {name}: изменено значений {count}")


def main():
    parser = argparse.ArgumentParser(description="Сравнение пустого и заполненного контейнеров")
    parser.add_argument("empty")
    parser.add_argument("filled")
    parser.add_argument("--amplify", type=int, default=50)
    parser.add_argument("--threshold", type=int, default=0)
    parser.add_argument("--out", default="diff_result")
    args = parser.parse_args()
    stats = compare(args.empty, args.filled, args.amplify, args.out, args.threshold)
    print_stats(stats, args.empty, args.filled)
    print(f"\n[+] Результаты сохранены в папке: {args.out}")


if __name__ == "__main__":
    main()
