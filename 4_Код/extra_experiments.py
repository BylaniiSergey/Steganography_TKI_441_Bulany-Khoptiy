"""Дополнительные опыты: типы контейнеров, разные сообщения, форматы файлов, разница, подбор V на горах.

Запуск: python src/extra_experiments.py <фото_варианта_8.png> <фото_гор.png> <заполненный_вариант8_КДБ.png>
Результаты: results/extra (CSV, JSON, картинки), консольные снимки — results/extra/console.
"""
import csv
import html
import io
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diff_report  # noqa: E402
from kjb import embed, extract, read_rgb, metrics  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = RES / "extra"
CONSOLE = OUT / "console"
for d in (OUT, CONSOLE, OUT / "types", OUT / "variant8", OUT / "mountain"):
    d.mkdir(parents=True, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
KEY = "TKI-441"
TEXT = "ТКИ-441 Буланый С.Е."
photo8, mountain, stego8_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
cover8, coverm = read_rgb(photo8), read_rgb(mountain)


def text_bits(t):
    return np.unpackbits(np.frombuffer(t.encode("utf-8"), dtype=np.uint8))


def decode(bits):
    try:
        return np.packbits(bits).tobytes().decode("utf-8")
    except UnicodeDecodeError:
        return "(не текст UTF-8)"


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render(blocks, name, title, width=1180):
    rows = []
    for command, output in blocks:
        rows.append(f'<div class="cmd"><span class="p">C:\\KJB_Lab&gt;</span> {html.escape(command)}</div>')
        if output:
            rows.append(f"<pre>{html.escape(output)}</pre>")
    page = f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#1e1e1e;font:15px/1.45 Consolas,'Courier New',monospace;color:#d8d8d8}}
.bar{{background:#2d2d30;color:#ddd;padding:8px 14px;font:14px Arial}}.wrap{{padding:14px 18px}}
.cmd{{color:#fff;margin-top:12px;white-space:pre-wrap;word-break:break-all}}.p{{color:#7ec16e}}
pre{{margin:4px 0 0;white-space:pre-wrap;word-break:break-all;font:inherit}}</style>
<div class="bar">{html.escape(title)}</div><div class="wrap">{''.join(rows)}</div>"""
    tmp = Path(tempfile.gettempdir()) / "claude_stego"
    tmp.mkdir(exist_ok=True)
    page_path = tmp / (name + ".html")
    page_path.write_text(page, encoding="utf-8")
    lines = sum(1 + (len(o) // 120 + o.count("\n") + 1 if o else 0) for _, o in blocks)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{90 + lines * 22 + 30 * len(blocks)}",
                    f"--screenshot={tmp / 'tmp.png'}", page_path.as_uri()], capture_output=True)
    shutil.copy(tmp / "tmp.png", CONSOLE / (name + ".png"))


def capture_stats(empty, filled, out):
    buf = io.StringIO()
    stats = diff_report.compare(empty, filled, 50, out)
    saved = sys.stdout
    sys.stdout = buf
    diff_report.print_stats(stats, Path(empty).name, Path(filled).name)
    sys.stdout = saved
    return stats, buf.getvalue().rstrip("\n")


summary = {}

# ---------------------------------------------------------------- 1. Разные сообщения
messages = [("Короткое слово", "Привет"), ("Фраза", "Метод КДБ, вариант 8, ТКИ-441"), ("Цифры", "89991234567"), ("Сообщение варианта", TEXT)]
rows = []
for label, photo, cover in (("Фото варианта 8", "variant8", cover8), ("Контрольное «горы»", "mountain", coverm)):
    h, w = cover.shape[:2]
    for name, message in messages:
        bits = text_bits(message)
        for v in (0.1, 0.2, 0.25):
            marked, _ = embed(cover, bits, KEY, v, 31, 3)
            got, _, _ = extract(marked, len(bits), KEY, 31, 3)
            m = metrics(cover, marked)
            rows.append({"container": label, "message_kind": name, "message": message, "bytes": len(message.encode("utf-8")),
                         "bits": int(len(bits)), "container_bytes": int(h * w * 3), "V": v,
                         "errors": int(np.count_nonzero(got != bits)), "ber_percent": float(np.mean(got != bits) * 100),
                         "psnr_db": m["psnr_rgb_db"], "decoded": decode(got)})
save_csv(OUT / "messages.csv", rows)

# ---------------------------------------------------------------- 2. Форматы файлов и сжатие
bits = text_bits(TEXT)
fmt_rows = []


def reload(buf):
    buf.seek(0)
    return np.array(Image.open(buf).convert("RGB"))


def transforms(stego):
    img = Image.fromarray(stego)
    out = {"PNG (исходный)": stego}
    b = io.BytesIO()
    img.save(b, format="PNG", compress_level=9)
    out["PNG пересохранён"] = reload(b)
    b = io.BytesIO()
    img.save(b, format="BMP")
    out["BMP 24 бита"] = reload(b)
    b = io.BytesIO()
    img.save(b, format="TIFF", compression="tiff_adobe_deflate")
    out["TIFF без потерь"] = reload(b)
    png = io.BytesIO()
    img.save(png, format="PNG")
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("stego.png", png.getvalue())
    with zipfile.ZipFile(zb) as z:
        out["ZIP-архив"] = np.array(Image.open(io.BytesIO(z.read("stego.png"))).convert("RGB"))
    b = io.BytesIO()
    img.save(b, format="WEBP", lossless=True)
    out["WebP без потерь"] = reload(b)
    for q in (95, 75):
        b = io.BytesIO()
        img.save(b, format="JPEG", quality=q, subsampling=2)
        out[f"JPEG {q}"] = reload(b)
    b = io.BytesIO()
    img.save(b, format="WEBP", quality=90)
    out["WebP с потерями 90"] = reload(b)
    out["GIF 256 цветов"] = np.array(img.convert("P", palette=Image.ADAPTIVE, colors=256).convert("RGB"))
    return out


for label, cover in (("Фото варианта 8", cover8), ("Контрольное «горы»", coverm)):
    marked, _ = embed(cover, bits, KEY, 0.25, 31, 3)
    for name, arr in transforms(marked).items():
        got, _, _ = extract(arr, len(bits), KEY, 31, 3)
        fmt_rows.append({"container": label, "format": name, "errors": int(np.count_nonzero(got != bits)),
                         "ber_percent": float(np.mean(got != bits) * 100), "readable": bool(np.array_equal(got, bits))})
save_csv(OUT / "formats.csv", fmt_rows)

# ---------------------------------------------------------------- 3. Горы: подбор V для текста
mt_rows = []
for v in (0.1, 0.15, 0.2, 0.25, 0.3):
    marked, clipped = embed(coverm, bits, KEY, v, 31, 3)
    got, _, _ = extract(marked, len(bits), KEY, 31, 3)
    m = metrics(coverm, marked)
    mt_rows.append({"V": v, "errors": int(np.count_nonzero(got != bits)), "psnr_db": m["psnr_rgb_db"], "clipped": clipped,
                    "changed_percent": m["changed_pixels_percent"], "max_change": m["max_abs_change"], "decoded": decode(got)})
save_csv(OUT / "mountain_v_text.csv", mt_rows)

# ---------------------------------------------------------------- 4. Программа разницы для обоих фото
stego8 = stego8_path
stego_m = OUT / "mountain" / "stego_text_q0.25.png"
Image.fromarray(embed(coverm, bits, KEY, 0.25, 31, 3)[0]).save(stego_m)
stego_m1 = OUT / "mountain" / "stego_text_q0.1.png"
Image.fromarray(embed(coverm, bits, KEY, 0.1, 31, 3)[0]).save(stego_m1)
diff_stats = {}
for label, empty, filled in (("variant8", photo8, stego8), ("mountain", mountain, stego_m)):
    stats, text = capture_stats(empty, filled, OUT / label / "diff")
    diff_stats[label] = stats
    cmd = f"python src/diff_report.py {'photo.png'} {'stego.png'} --amplify 50"
    render([(cmd, text + "\n\n[+] Бинарная маска: diff_binary.png\n[+] Усиленная карта: diff_amplified.png\n[+] Список пикселей: changed_pixels.csv")],
           f"20_программа_разницы_{label}", f"Командная строка — программа разницы ({'фото варианта 8' if label == 'variant8' else 'контрольное фото «горы»'})")
summary["diff"] = diff_stats

# ---------------------------------------------------------------- 5. Контейнеры разных типов: сетка (пустой, заполненный, разница)
for t in ("uniform", "gradient", "edges", "texture", "black"):
    folder = RES / t
    delta = np.load(folder / "signed_difference.npy")
    mask = (np.abs(delta).max(axis=2) > 0).astype(np.uint8) * 255
    img = Image.fromarray(mask).filter(ImageFilter.MaxFilter(3))
    Image.merge("RGB", (img.point(lambda v: 0), img.point(lambda v: v // 2), img)).resize((512, 512), Image.Resampling.NEAREST).save(OUT / "types" / f"{t}_diff.png")
    for kind in ("cover", "stego"):
        Image.open(folder / f"{kind}.png").convert("RGB").resize((512, 512), Image.Resampling.NEAREST).save(OUT / "types" / f"{t}_{kind}.png")

(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("готово", OUT)
