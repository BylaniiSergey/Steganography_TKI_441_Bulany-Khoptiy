"""Полный цикл на настоящей фотографии: КДБ → программы из задания → параметры и помехи.

Запуск: python src/photo_experiment.py <фото.png|jpg> [каталог_результатов]
По умолчанию результаты кладутся в results/photo. Любое своё фото можно подставить без правки кода.
Нужны NumPy, Pillow, scikit-image, SciPy, OpenCV, Matplotlib (как для src/external_programs.py).
"""
import csv
import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kjb import embed, extract, read_rgb, metrics  # noqa: E402
from experiments import watermark, attacks, KEYS  # noqa: E402
import external_programs as ep  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
plt.rcParams["font.family"] = "Arial"
Q_LIST = [0.02, 0.05, 0.1, 0.15, 0.2]
N_LIST = [1, 5, 11, 21, 31, 63]
RADIUS_LIST = [1, 2, 3, 5, 8]
PAYLOAD_LIST = [64, 256, 1024, 4096, 16384, 32000]
TEXT = "ТКИ-441 Буланый С.Е."
TUNED_Q = 0.2  # на фото сила q = 0,1 из базового опыта недостаточна (см. kjb_q_n_sweep.csv)


def ber(a, b):
    return float(np.mean(np.asarray(a) != np.asarray(b)) * 100)


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_kjb(image, bits, key, q=0.1, n=31, c=3):
    marked, clipped = embed(image, bits, key, q, n, c)
    got, _, _ = extract(marked, len(bits), key, n, c)
    return marked, got, clipped


def main():
    photo_path = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "results" / "photo"
    out.mkdir(parents=True, exist_ok=True)
    work = out / "_work"
    work.mkdir(exist_ok=True)
    original = ep.load_original()

    cover = read_rgb(photo_path)
    h, w = cover.shape[:2]
    Image.fromarray(cover).save(out / "cover.png")
    bits = watermark()
    summary = {"photo": photo_path.name, "size": [w, h], "base": {"q": 0.1, "n": 31, "radius": 3, "bits": 64}}

    # 1. Базовый опыт КДБ, три ключа
    base_rows = []
    for key in KEYS:
        marked, got, clipped = run_kjb(cover, bits, key)
        base_rows.append({"key": key, "errors": int(np.count_nonzero(got != bits)), "ber_percent": ber(got, bits),
                          "clipped": clipped, **metrics(cover, marked)})
        if key == KEYS[0]:
            kjb_stego, kjb_got = marked, got
    save_csv(out / "kjb_base.csv", base_rows)
    Image.fromarray(kjb_stego).save(out / "kjb_stego.png")
    delta = kjb_stego.astype(np.int16) - cover.astype(np.int16)
    Image.fromarray(np.clip(np.abs(delta) * 8, 0, 255).astype(np.uint8)).save(out / "kjb_difference_x8.png")
    summary["kjb_base"] = base_rows
    summary["kjb_fixed"] = ep.quality_measures(cover, kjb_stego)
    summary["kjb_original_code"] = ep.run_original(original, cover, kjb_stego)

    # Подобранная сила: на фото q = 0,1 даёт ошибки, поэтому те же опыты повторены с q = TUNED_Q
    tuned_rows = []
    for key in KEYS:
        marked, got, clipped = run_kjb(cover, bits, key, q=TUNED_Q)
        tuned_rows.append({"key": key, "errors": int(np.count_nonzero(got != bits)), "ber_percent": ber(got, bits),
                           "clipped": clipped, **metrics(cover, marked)})
        if key == KEYS[0]:
            tuned_stego = marked
    save_csv(out / "kjb_tuned.csv", tuned_rows)
    Image.fromarray(tuned_stego).save(out / "kjb_stego_tuned.png")
    delta_tuned = tuned_stego.astype(np.int16) - cover.astype(np.int16)
    Image.fromarray(np.clip(np.abs(delta_tuned) * 8, 0, 255).astype(np.uint8)).save(out / "kjb_tuned_difference_x8.png")
    summary["tuned_q"] = TUNED_Q
    summary["kjb_tuned"] = tuned_rows
    summary["kjb_tuned_fixed"] = ep.quality_measures(cover, tuned_stego)
    summary["kjb_tuned_original_code"] = ep.run_original(original, cover, tuned_stego)

    # текст вместо знака: прочитанная строка должна совпасть
    text_bits = np.unpackbits(np.frombuffer(TEXT.encode("utf-8"), dtype=np.uint8))
    summary["text"] = {"message": TEXT, "bits": int(text_bits.size)}
    for label, q in (("base", 0.1), ("tuned", TUNED_Q)):
        _, t_got, _ = run_kjb(cover, text_bits, KEYS[0], q=q)
        summary["text"][label] = {"q": q, "errors": int(np.count_nonzero(t_got != text_bits)),
                                  "decoded": np.packbits(t_got).tobytes().decode("utf-8", errors="replace")}

    # 2. Сила q × повторы n
    sweep = []
    for q in Q_LIST:
        for n in N_LIST:
            for key in KEYS:
                marked, got, _ = run_kjb(cover, bits, key, q=q, n=n)
                m = metrics(cover, marked)
                sweep.append({"q": q, "n": n, "key": key, "ber_percent": ber(got, bits),
                              "psnr_db": m["psnr_rgb_db"], "mse": m["mse_rgb"]})
    save_csv(out / "kjb_q_n_sweep.csv", sweep)

    # 3. Радиус
    radius_rows = []
    for c in RADIUS_LIST:
        for key in KEYS:
            marked, got, _ = run_kjb(cover, bits, key, c=c)
            radius_rows.append({"radius": c, "key": key, "ber_percent": ber(got, bits)})
    save_csv(out / "kjb_radius_sweep.csv", radius_rows)

    # 4. Размер сообщения относительно контейнера
    rng = np.random.Generator(np.random.PCG64(20261010))
    payload_rows = []
    for count in PAYLOAD_LIST:
        message = rng.integers(0, 2, count, dtype=np.uint8)
        try:
            marked, got, _ = run_kjb(cover, message, KEYS[0])
            m = metrics(cover, marked)
            payload_rows.append({"bits": count, "used_pixels_percent": (count + 2) * 31 / (w * h) * 100,
                                 "ber_percent": ber(got, message), "psnr_db": m["psnr_rgb_db"], "status": "ok"})
        except ValueError as error:
            payload_rows.append({"bits": count, "used_pixels_percent": None, "ber_percent": None,
                                 "psnr_db": None, "status": str(error)})
    save_csv(out / "kjb_payload.csv", payload_rows)

    # 5. Изменённый ЦВЗ
    variants = {"original": bits, "inverted": 1 - bits, "zeros": np.zeros(64, np.uint8), "ones": np.ones(64, np.uint8),
                "random": rng.integers(0, 2, 64, dtype=np.uint8)}
    wm_rows = []
    for name, message in variants.items():
        for key in KEYS:
            _, got, _ = run_kjb(cover, message, key)
            wm_rows.append({"watermark": name, "key": key, "ber_percent": ber(got, message)})
    save_csv(out / "kjb_watermark.csv", wm_rows)

    # 6. Внешние воздействия на заполненный контейнер КДБ
    attack_rows = []
    for q in (0.1, TUNED_Q):
        for key in KEYS:
            marked, _, _ = run_kjb(cover, bits, key, q=q)
            for name, changed in attacks(marked):
                got, _, _ = extract(changed, 64, key, 31, 3)
                attack_rows.append({"q": q, "key": key, "attack": name, "ber_percent": ber(got, bits)})
    save_csv(out / "kjb_attacks.csv", attack_rows)

    # 7. Программа Антропова и Архипова на той же фотографии: тот же знак «К» 8×8 → 64×64 RGB
    wm = ep.watermark_rgb(8)
    wm_path = work / "wm.png"
    Image.fromarray(wm).save(wm_path)
    stegwm_path = out / "stegwm_stego.png"
    ep.run_stegwm(out / "cover.png", wm_path, stegwm_path)
    ext_path = work / "wm_ext.png"
    ep.run_stegwm_ext(stegwm_path, ext_path, 64, 64)
    sw_stego = read_rgb(stegwm_path)
    d2 = sw_stego.astype(np.int16) - cover.astype(np.int16)
    Image.fromarray(np.clip(np.abs(d2) * 255, 0, 255).astype(np.uint8)).save(out / "stegwm_difference_x255.png")
    summary["stegwm"] = {"watermark_size": [64, 64], "wrong_values": int(np.count_nonzero(read_rgb(ext_path) != wm)),
                         "changed_pixels_percent": float(np.any(d2 != 0, axis=2).mean() * 100),
                         "max_abs_change": int(np.abs(d2).max()),
                         "fixed": ep.quality_measures(cover, sw_stego),
                         "original_code": ep.run_original(original, cover, sw_stego)}
    sw_rows = []
    for name, changed in attacks(sw_stego):
        attacked = work / f"{name}.png"
        Image.fromarray(changed).save(attacked)
        got_path = work / f"{name}_wm.png"
        ep.run_stegwm_ext(attacked, got_path, 64, 64)
        got = read_rgb(got_path)
        sw_rows.append({"attack": name, "ber_percent": ber(np.unpackbits(got), np.unpackbits(wm))})
    save_csv(out / "stegwm_attacks.csv", sw_rows)

    # Таблица характеристик Домашкина/Баурина для обеих программ
    metric_rows = []
    for program, fixed, orig in (("КДБ q=0,1", summary["kjb_fixed"], summary["kjb_original_code"]),
                                 (f"КДБ q={TUNED_Q}".replace(".", ","), summary["kjb_tuned_fixed"],
                                  summary["kjb_tuned_original_code"]),
                                 ("stegwm 64x64", summary["stegwm"]["fixed"], summary["stegwm"]["original_code"])):
        for key, label in ep.METRICS:
            metric_rows.append({"program": program, "metric": key, "name": label, "formula": fixed[key],
                                "original_code": orig.get(key)})
    save_csv(out / "metrics_domashkin_baurin.csv", metric_rows)

    # Рисунки
    def small(a):
        return Image.fromarray(a).resize((w // 3, h // 3), Image.Resampling.LANCZOS)

    x0, y0, size = 520, 170, 140  # фрагмент у кромки горы (если фото меньше — берётся левый верхний угол)
    x0, y0 = min(x0, max(w - size, 0)), min(y0, max(h - size, 0))
    crop = lambda a: a[y0:y0 + size, x0:x0 + size]  # noqa: E731
    fig, axes = plt.subplots(2, 3, figsize=(13, 6.6), dpi=150)
    top = [cover, np.clip(np.abs(delta_tuned) * 8, 0, 255).astype(np.uint8), np.clip(np.abs(d2) * 255, 0, 255).astype(np.uint8)]
    titles = ["Пустой контейнер (фото)", f"КДБ q = {TUNED_Q}: |разница| × 8".replace(".", ","), "stegwm: |разница| × 255"]
    for ax, img, title in zip(axes[0], top, titles):
        ax.imshow(img)
        ax.set_title(title, fontsize=12)
        ax.axis("off")
    for ax, img, title in zip(axes[1], [crop(cover), crop(tuned_stego), crop(sw_stego)],
                              ["Фрагмент: пустой", "Фрагмент: КДБ", "Фрагмент: stegwm"]):
        ax.imshow(img, interpolation="nearest")
        ax.set_title(title, fontsize=12)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out / "photo_comparison.png", facecolor="white")
    plt.close(fig)

    def avg(rows, key, **flt):
        vals = [r[key] for r in rows if all(r[k] == v for k, v in flt.items()) and r[key] is not None]
        return float(np.mean(vals))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), dpi=150)
    for q in (0.05, 0.1, 0.2):
        axes[0].plot(N_LIST, [avg(sweep, "ber_percent", q=q, n=n) for n in N_LIST], marker="o", label=f"q = {q}")
    axes[0].set_xlabel("Повторов на бит n")
    axes[0].set_ylabel("BER, %")
    axes[0].set_title("Ошибки чтения от числа повторов")
    axes[0].legend()
    axes[0].grid(alpha=.3)
    axes[1].plot(Q_LIST, [avg(sweep, "psnr_db", q=q, n=31) for q in Q_LIST], marker="o", color="#a63861")
    axes[1].set_xlabel("Сила встраивания q")
    axes[1].set_ylabel("PSNR, дБ")
    axes[1].set_title("Качество фото от силы q (n = 31)")
    axes[1].grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(out / "photo_q_n.png", facecolor="white")
    plt.close(fig)

    names = [n for n, _ in attacks(cover[:8, :8].repeat(4, 0).repeat(4, 1))]
    kv = [avg(attack_rows, "ber_percent", attack=n, q=0.1) for n in names]
    kt = [avg(attack_rows, "ber_percent", attack=n, q=TUNED_Q) for n in names]
    sv = [next(r["ber_percent"] for r in sw_rows if r["attack"] == n) for n in names]
    fig, ax = plt.subplots(figsize=(13, 4.6), dpi=150)
    pos = np.arange(len(names))
    ax.bar(pos - .27, kv, .27, label="КДБ q = 0,1 (среднее по 3 ключам)", color="#7fb0d8")
    ax.bar(pos, kt, .27, label=f"КДБ q = {TUNED_Q}".replace(".", ","), color="#1866a5")
    ax.bar(pos + .27, sv, .27, label="stegwm (ЦВЗ 64 × 64)", color="#b57900")
    ax.set_xticks(pos)
    ax.set_xticklabels(names, rotation=35, ha="right")
    ax.set_ylabel("BER, %")
    ax.set_title("Влияние воздействий на извлечение")
    ax.legend()
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(out / "photo_attacks.png", facecolor="white")
    plt.close(fig)

    summary["aggregates"] = {
        "sweep_ber_q0.1": {str(n): avg(sweep, "ber_percent", q=0.1, n=n) for n in N_LIST},
        "sweep_ber_n31": {str(q): avg(sweep, "ber_percent", q=q, n=31) for q in Q_LIST},
        "sweep_psnr_n31": {str(q): avg(sweep, "psnr_db", q=q, n=31) for q in Q_LIST},
        "radius": {str(c): avg(radius_rows, "ber_percent", radius=c) for c in RADIUS_LIST},
        "watermark": {k: avg(wm_rows, "ber_percent", watermark=k) for k in variants},
        "kjb_attacks": dict(zip(names, kv)), "kjb_tuned_attacks": dict(zip(names, kt)),
        "stegwm_attacks": dict(zip(names, sv))}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    print("готово:", out)


if __name__ == "__main__":
    main()
