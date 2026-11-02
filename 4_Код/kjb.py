"""Учебная реализация Куттера–Джордана–Боссена (КДБ).

Модуляция синего канала, повторение битов, крестообразный предиктор.
Позиции выбираются перестановкой без повторений, каждый бит имеет ровно n
копий. Это упрощение схемы распределения из оригинальной статьи.
Два опорных бита 0,1 позволяют вычислить адаптивный порог. Геометрическая
синхронизация и шифрование не реализованы. NumPy PCG64 не криптостойкий ГПСЧ.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def read_rgb(path):
    with Image.open(path) as image:
        return np.array(image.convert("RGB"))


def validate_image(image):
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Нужно RGB-изображение uint8, три канала по 8 бит.")


def positions(shape, bit_count, repeats, radius, key):
    """Одинаковые ключ и параметры воспроизводят одинаковые координаты."""
    h, w = shape[:2]
    if repeats < 1 or radius < 1 or bit_count < 1:
        raise ValueError("Число битов, повторов и радиус должны быть >= 1.")
    if h <= 2 * radius or w <= 2 * radius:
        raise ValueError("Размер изображения слишком мал для окрестности.")
    available = (h - 2 * radius) * (w - 2 * radius)
    needed = (bit_count + 2) * repeats
    if needed > available:
        raise ValueError(f"Не хватает ёмкости: нужно {needed} пикселей, есть {available}.")
    seed = int.from_bytes(hashlib.sha256(str(key).encode("utf-8")).digest()[:16], "big")
    rng = np.random.Generator(np.random.PCG64(seed))
    flat = rng.permutation(available)[:needed].reshape(bit_count + 2, repeats)
    return flat // (w - 2 * radius) + radius, flat % (w - 2 * radius) + radius


def embed(image, bits, key="TKI-441", strength=0.1, repeats=31, radius=3):
    """Встраивание. Возвращает новое RGB-изображение и число обрезаний."""
    validate_image(image)
    raw = np.asarray(bits)
    if raw.ndim != 1 or raw.size == 0 or not np.all((raw == 0) | (raw == 1)):
        raise ValueError("Сообщение должно быть непустым массивом нулей и единиц.")
    if not np.isfinite(strength) or not 0 < strength <= 1:
        raise ValueError("Сила q должна быть в диапазоне (0, 1].")
    bits = np.concatenate(([0, 1], raw)).astype(np.int16)
    y, x = positions(image.shape, raw.size, repeats, radius, key)
    selected = image[y, x].astype(np.float64)
    luminance = selected @ np.array([0.299, 0.587, 0.114])
    values = selected[:, :, 2] + (2 * bits[:, None] - 1) * strength * luminance
    clipped = int(np.count_nonzero((values < 0) | (values > 255)))
    result = image.copy()
    result[y, x, 2] = np.clip(np.rint(values), 0, 255).astype(np.uint8)
    return result, clipped


def extract(image, bit_count, key="TKI-441", repeats=31, radius=3, adaptive=True):
    """Слепое извлечение: исходное изображение и исходные биты не нужны."""
    validate_image(image)
    y, x = positions(image.shape, bit_count, repeats, radius, key)
    blue = image[:, :, 2].astype(np.float64)
    prediction = np.zeros(y.shape, dtype=np.float64)
    for distance in range(1, radius + 1):
        prediction += (blue[y - distance, x] + blue[y + distance, x]
                       + blue[y, x - distance] + blue[y, x + distance])
    prediction /= 4 * radius
    scores = (blue[y, x] - prediction).mean(axis=1)
    threshold = float((scores[0] + scores[1]) / 2) if adaptive else 0.0
    return (scores[2:] > threshold).astype(np.uint8), scores, threshold


def metrics(original, changed):
    """Метрики RGB по всем каналам; доля изменённых пикселей по RGB."""
    if original.shape != changed.shape:
        raise ValueError("Размеры сравниваемых изображений должны совпадать.")
    delta = changed.astype(np.float64) - original.astype(np.float64)
    mse = float(np.mean(delta ** 2))
    return {
        "mse_rgb": mse,
        "mae_rgb": float(np.mean(np.abs(delta))),
        "psnr_rgb_db": float(10 * np.log10(255 ** 2 / mse)) if mse else None,
        "max_abs_change": int(np.abs(delta).max()),
        "changed_pixels_percent": float(np.any(delta != 0, axis=2).mean() * 100),
    }


def channel_stats(image):
    result = {}
    for i, name in enumerate("RGB"):
        values = image[:, :, i].astype(np.float64)
        histogram = np.bincount(image[:, :, i].ravel(), minlength=256)
        p = histogram[histogram > 0] / values.size
        left, right = values[:, :-1].ravel(), values[:, 1:].ravel()
        corr = float(np.corrcoef(left, right)[0, 1]) if left.std() and right.std() else None
        result[name] = {"mean": float(values.mean()), "std": float(values.std()),
                        "entropy_bits": float(-np.sum(p * np.log2(p))),
                        "horizontal_correlation": corr}
    return result


def main():
    parser = argparse.ArgumentParser(description="КДБ: скрытие и извлечение битов из RGB PNG")
    sub = parser.add_subparsers(dest="action", required=True)
    enc = sub.add_parser("embed", help="Спрятать текст или строку битов")
    enc.add_argument("input")
    enc.add_argument("output", help="Выходной файл PNG")
    enc.add_argument("--message", default="TKI-441")
    enc.add_argument("--bits", help="Например, 01001101; имеет приоритет над текстом")
    enc.add_argument("--strength", type=float, default=0.1)
    dec = sub.add_parser("extract", help="Прочитать без исходного контейнера")
    dec.add_argument("input")
    dec.add_argument("--length", type=int, required=True, help="Длина полезного сообщения в битах")
    dec.add_argument("--output", help="Сохранить извлечённые биты в txt")
    for command in (enc, dec):
        command.add_argument("--key", default="TKI-441")
        command.add_argument("--repeats", type=int, default=31)
        command.add_argument("--radius", type=int, default=3)
    args = parser.parse_args()
    try:
        image = read_rgb(args.input)
        if args.action == "embed":
            if Path(args.output).suffix.lower() != ".png":
                raise ValueError("Сохраняйте контейнер в PNG, чтобы не потерять биты при сжатии.")
            if args.bits is not None:
                if not args.bits or any(c not in "01" for c in args.bits):
                    raise ValueError("--bits должен содержать только 0 и 1.")
                bits = np.array([int(c) for c in args.bits], dtype=np.uint8)
            else:
                bits = np.unpackbits(np.frombuffer(args.message.encode("utf-8"), dtype=np.uint8))
            out, clipped = embed(image, bits, args.key, args.strength, args.repeats, args.radius)
            Image.fromarray(out).save(args.output)
            print(json.dumps({"length": len(bits), "repeats": args.repeats,
                              "radius": args.radius, "clipped": clipped,
                              **metrics(image, out)}, ensure_ascii=False, indent=2))
        else:
            bits, scores, threshold = extract(image, args.length, args.key, args.repeats, args.radius)
            line = "".join(map(str, bits))
            print(line)
            if args.output:
                Path(args.output).write_text(line + "\n", encoding="utf-8")
            print(f"Порог: {threshold:.4f}; разность опорных оценок: {scores[1]-scores[0]:.4f}")
            if len(bits) % 8 == 0:
                try:
                    print("Текст UTF-8:", np.packbits(bits).tobytes().decode("utf-8"))
                except UnicodeDecodeError:
                    print("Результат не является корректным текстом UTF-8.")
            print("Без исходных битов или контрольной суммы правильность чтения не гарантируется.")
    except (ValueError, OSError) as error:
        parser.exit(2, f"Ошибка: {error}\n")


if __name__ == "__main__":
    main()
