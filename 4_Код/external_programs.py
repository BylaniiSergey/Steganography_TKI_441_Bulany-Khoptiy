"""Запуск двух программ из задания и сравнение с КДБ.

1. Домашкин и Баурин — набор из 13 «числовых характеристик» пустого и заполненного
   контейнера (external/domashkin_baurin/Kod_programmy.py, файл не изменён).
2. Антропов и Архипов — программа встраивания цветного ЦВЗ в младший бит синего
   канала (external/antropov_arkhipov/stegwm.py, stegwm_ext.py, файлы не изменены).

Запуск: python src/external_programs.py
"""
import csv
import importlib.machinery
import importlib.util
import io
import json
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kjb import read_rgb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = RES / "external"
EXT = ROOT / "external"
STEGWM = EXT / "antropov_arkhipov" / "stegwm.py"
STEGWM_EXT = EXT / "antropov_arkhipov" / "stegwm_ext.py"
ORIGINAL = EXT / "domashkin_baurin" / "Kod_programmy.py"
CONTAINERS = ["uniform", "gradient", "edges", "texture", "black"]
NAMES = {"uniform": "Однотонный", "gradient": "Градиент", "edges": "Резкие границы",
         "texture": "Пёстрая текстура", "black": "Чёрный"}

METRICS = [  # ключ, русское название (как в программе Домашкина/Баурина)
    ("MD", "Максимальная разность"),
    ("AD", "Средняя абсолютная разность"),
    ("NAD", "Нормированная средняя абсолютная разность"),
    ("MSE", "Среднеквадратичная ошибка"),
    ("NMSE", "Нормированная среднеквадратическая ошибка"),
    ("Lp", "L^p-норма (p = 1)"),
    ("LMSE", "Лапласова среднеквадратическая ошибка"),
    ("SNR", "Отношение «сигнал/шум»"),
    ("PSNR_ratio", "Максимальное отношение «сигнал/шум»"),
    ("IF", "Качество изображения"),
    ("NCC", "Нормированная взаимная корреляция"),
    ("CQ", "Качество корреляции"),
    ("SC", "Структурное содержание"),
    ("PSNR_dB", "PSNR, дБ"),
]


# ------------------------------------------------------------------ формулы
def _laplacian(a):
    """O(f) = f(x+1,y)+f(x-1,y)+f(x,y+1)+f(x,y-1)-4f(x,y) по каждому каналу, без краёв."""
    return (a[2:, 1:-1] + a[:-2, 1:-1] + a[1:-1, 2:] + a[1:-1, :-2] - 4 * a[1:-1, 1:-1])


def _ratio(a, b):
    return float(a / b) if b else float("inf")


def quality_measures(cover, stego):
    """Те же 13 характеристик, но с правильными типами и нормировкой.

    Суммы берутся по всем M*N*3 значениям RGB, «средние» — деление на M*N*3.
    """
    c = cover.astype(np.float64)
    s = stego.astype(np.float64)
    d = c - s
    count = c.size
    sq = float(np.sum(d ** 2))
    sum_c, sum_c2, sum_s2 = float(np.sum(c)), float(np.sum(c ** 2)), float(np.sum(s ** 2))
    lc, ls = _laplacian(c), _laplacian(s)
    mse = sq / count
    return {
        "MD": float(np.max(np.abs(d))),
        "AD": float(np.mean(np.abs(d))),
        "NAD": _ratio(float(np.sum(np.abs(d))), sum_c),
        "MSE": mse,
        "NMSE": _ratio(sq, sum_c2),
        "Lp": float(np.mean(np.abs(d))),  # p = 1
        "LMSE": _ratio(float(np.sum((lc - ls) ** 2)), float(np.sum(lc ** 2))),
        "SNR": _ratio(sum_c2, sq),
        "PSNR_ratio": _ratio(count * float(np.max(c)) ** 2, sq),
        "IF": 1 - _ratio(sq, sum_c2) if sum_c2 else float("nan"),
        "NCC": _ratio(float(np.sum(c * s)), sum_c2),
        "CQ": _ratio(float(np.sum(c * s)), sum_c),
        "SC": _ratio(sum_c2, sum_s2),
        "PSNR_dB": float(10 * np.log10(255 ** 2 / mse)) if mse else float("inf"),
    }


def load_original():
    loader = importlib.machinery.SourceFileLoader("domashkin_original", str(ORIGINAL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def as_bgr_uint8(rgb):
    """cv2.imread отдаёт BGR uint8; программа Домашкина/Баурина работает именно с ним."""
    return np.ascontiguousarray(rgb[:, :, ::-1])


def run_original(module, cover, stego):
    """Функции программы вызываются как есть, на массивах uint8 (как делает cv2.imread)."""
    c, s = as_bgr_uint8(cover), as_bgr_uint8(stego)
    calls = {
        "AD": module.mid_abs_sub, "MSE": module.middle_errore, "NMSE": module.norm_middle_errore,
        "Lp": module.l_norm, "LMSE": module.lapplace_middle_errore, "SNR": module.ratio_sing_shum,
        "PSNR_ratio": module.max_ratio_sign_shum, "IF": module.quality_img,
        "NCC": module.norm_vz_corr, "CQ": module.quality_vz_corr, "SC": module.struct_soder,
        "PSNR_dB": module.PSNR, "NAD": module.norm_mid_abs_sub,
    }
    result = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result["MD"] = float(np.max(module.max_sub_img(c, s)))  # функция возвращает РАЗНОСТЬ-картинку
        for key, func in calls.items():
            try:
                result[key] = float(func(c, s))
            except Exception as error:  # noqa: BLE001
                result[key] = f"ошибка: {type(error).__name__}"
    return result


# ------------------------------------------------------------------ программа Антропова/Архипова
def watermark_rgb(scale):
    """Тот же знак «К» 8×8 из КДБ, но как цветное изображение (0 или 255 в каждом канале)."""
    bits = np.array([[int(ch) for ch in row] for row in
                     ["00000000", "01100110", "01101100", "01111000",
                      "01111000", "01101100", "01100110", "00000000"]], dtype=np.uint8) * 255
    wm = np.repeat(np.repeat(bits, scale, axis=0), scale, axis=1)
    return np.stack([wm] * 3, axis=2)


def run_stegwm(image_path, wm_path, out_path):
    process = subprocess.run([sys.executable, "-I", str(STEGWM), str(image_path), str(wm_path), str(out_path)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    if process.returncode or not Path(out_path).exists():
        raise RuntimeError(process.stdout + process.stderr)
    return process.stdout.strip()


def run_stegwm_ext(image_path, out_path, width, height):
    process = subprocess.run([sys.executable, "-I", str(STEGWM_EXT), str(image_path), str(out_path),
                              str(width), str(height)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if process.returncode or not Path(out_path).exists():
        raise RuntimeError(process.stdout + process.stderr)
    return process.stdout.strip()


def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)


def attacks(image):
    pil = Image.fromarray(image)
    yield "none", image
    for sigma in (2, 5):
        noise = np.random.Generator(np.random.PCG64(917 + sigma)).normal(0, sigma, image.shape)
        yield f"noise_sigma_{sigma}", np.clip(np.rint(image.astype(float) + noise), 0, 255).astype(np.uint8)
    for quality in (95, 75):
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=quality, subsampling=2)
        buf.seek(0)
        yield f"jpeg_{quality}_420", np.array(Image.open(buf).convert("RGB"))
    yield "blur_0.5", np.array(pil.filter(ImageFilter.GaussianBlur(0.5)))
    yield "median_3", np.array(pil.filter(ImageFilter.MedianFilter(3)))
    moved = np.zeros_like(image)
    moved[:, 1:] = image[:, :-1]
    yield "shift_right_1", moved
    yield "brightness_plus_15", np.clip(image.astype(np.int16) + 15, 0, 255).astype(np.uint8)


def main():
    OUT.mkdir(exist_ok=True)
    original = load_original()
    summary = {"rows": []}
    rows = []

    # 1. Свой пример авторов: image.png + watermark.png (взяты из архива 1049-stegwm)
    example = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if example and example.exists():
        folder = OUT / "stegwm_example"
        folder.mkdir(exist_ok=True)
        image, wm = example / "image.png", example / "watermark.png"
        produced = folder / "result_recomputed.png"
        run_stegwm(image, wm, produced)
        got_wm = folder / "watermark_extracted.png"
        wm_arr = np.array(Image.open(wm).convert("RGB"))
        run_stegwm_ext(produced, got_wm, wm_arr.shape[1], wm_arr.shape[0])
        cover, stego = read_rgb(image), read_rgb(produced)
        reference = read_rgb(example / "result.png")
        extracted = read_rgb(got_wm)
        delta = stego.astype(np.int16) - cover.astype(np.int16)
        Image.fromarray(np.clip(np.abs(delta) * 255, 0, 255).astype(np.uint8)).save(folder / "difference_x255.png")
        summary["example"] = {
            "image_size": list(cover.shape[:2]), "watermark_size": list(wm_arr.shape[:2]),
            "result_matches_authors_result_png": bool(np.array_equal(stego, reference)),
            "watermark_restored_exactly": bool(np.array_equal(extracted, wm_arr)),
            "watermark_wrong_values": int(np.count_nonzero(extracted != wm_arr)),
            "changed_pixels_percent": float(np.any(delta != 0, axis=2).mean() * 100),
            "changed_blue_pixels_percent": float((delta[:, :, 2] != 0).mean() * 100),
            "changed_red_green_values": int(np.count_nonzero(delta[:, :, :2])),
            "max_abs_change": int(np.abs(delta).max()),
            "values_ours": quality_measures(cover, stego),
            "values_original_program": run_original(original, cover, stego),
        }

    # 2. Наши пять контейнеров 256×256: КДБ (уже готово) против программы Антропова/Архипова
    work = OUT / "_work"
    work.mkdir(exist_ok=True)
    bad_attack_rows = []
    sheet_rows = []
    for name in CONTAINERS:
        cover = read_rgb(RES / name / "cover.png")
        kjb_stego = read_rgb(RES / name / "stego.png")
        folder = OUT / name
        folder.mkdir(exist_ok=True)
        entries = [("КДБ", kjb_stego, None)]
        for scale in (1, 4):  # 8×8 (занимает 1/16 контейнера) и 32×32 (весь контейнер)
            wm = watermark_rgb(scale)
            wm_path = work / f"wm_{scale}.png"
            Image.fromarray(wm).save(wm_path)
            stego_path = folder / f"stegwm_{wm.shape[1]}x{wm.shape[0]}.png"
            run_stegwm(RES / name / "cover.png", wm_path, stego_path)
            ext_path = folder / f"stegwm_{wm.shape[1]}x{wm.shape[0]}_extracted.png"
            run_stegwm_ext(stego_path, ext_path, wm.shape[1], wm.shape[0])
            stego = read_rgb(stego_path)
            entries.append((f"stegwm {wm.shape[1]}x{wm.shape[0]}", stego, (wm, read_rgb(ext_path))))
            d = stego.astype(np.int16) - cover.astype(np.int16)
            Image.fromarray(np.clip(np.abs(d) * 255, 0, 255).astype(np.uint8)).save(
                folder / f"stegwm_{wm.shape[1]}x{wm.shape[0]}_difference_x255.png")
        for program, stego, wm_pair in entries:
            d = stego.astype(np.int16) - cover.astype(np.int16)
            row = {"container": name, "program": program,
                   "changed_pixels_percent": float(np.any(d != 0, axis=2).mean() * 100),
                   "changed_values_percent": float((d != 0).mean() * 100),
                   "max_abs_change": int(np.abs(d).max()),
                   "blue_only": bool(not np.any(d[:, :, :2])),
                   "wm_wrong_values": (int(np.count_nonzero(wm_pair[0] != wm_pair[1])) if wm_pair else None)}
            row.update({f"fixed_{k}": v for k, v in quality_measures(cover, stego).items()})
            row.update({f"orig_{k}": v for k, v in run_original(original, cover, stego).items()})
            rows.append(row)
        sheet_rows.append((name, cover, entries))

        # устойчивость программы Антропова/Архипова к воздействиям (32×32 ЦВЗ)
        wm = watermark_rgb(4)
        stego = read_rgb(folder / "stegwm_32x32.png")
        for attack, changed in attacks(stego):
            attacked = work / f"{name}_{attack}.png"
            Image.fromarray(changed).save(attacked)
            out = work / f"{name}_{attack}_wm.png"
            run_stegwm_ext(attacked, out, 32, 32)
            got = read_rgb(out)
            wrong_bits = int(np.count_nonzero(np.unpackbits(got) != np.unpackbits(wm)))
            bad_attack_rows.append({"container": name, "attack": attack,
                                    "wrong_values": int(np.count_nonzero(got != wm)),
                                    "wrong_values_percent": float(np.mean(got != wm) * 100),
                                    "wrong_bits": wrong_bits,
                                    "ber_percent": wrong_bits / (wm.size * 8) * 100,
                                    "wm_restored_exactly": bool(np.array_equal(got, wm))})

    def save_csv(path, data):
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)

    save_csv(OUT / "domashkin_baurin_metrics.csv", rows)
    save_csv(OUT / "stegwm_attacks.csv", bad_attack_rows)

    # Лист сравнения: контейнер / КДБ ×8 / stegwm 8×8 ×255 / stegwm 32×32 ×255
    left, step, tile_size = 170, 270, 256
    sheet = Image.new("RGB", (left + 4 * step, 300 * len(sheet_rows) + 60), "white")
    draw = ImageDraw.Draw(sheet)
    for j, title in enumerate(["Контейнер", "КДБ: разница ×8", "stegwm 8×8: ×255", "stegwm 32×32: ×255"]):
        draw.text((left + j * step, 15), title, fill="black", font=font(18))
    for i, (name, cover, entries) in enumerate(sheet_rows):
        top = 50 + i * 300
        draw.text((10, top + 115), NAMES[name], fill="black", font=font(17))
        tiles = [cover,
                 np.clip(np.abs(entries[0][1].astype(np.int16) - cover.astype(np.int16)) * 8, 0, 255).astype(np.uint8)]
        for _, stego, _ in entries[1:]:
            tiles.append(np.clip(np.abs(stego.astype(np.int16) - cover.astype(np.int16)) * 255, 0, 255).astype(np.uint8))
        for j, tile in enumerate(tiles):
            sheet.paste(Image.fromarray(tile).resize((tile_size, tile_size), Image.Resampling.NEAREST),
                        (left + j * step, top))
    sheet.save(OUT / "comparison_programs.png")

    summary["rows"] = rows
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("готово:", OUT)


if __name__ == "__main__":
    main()

