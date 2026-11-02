"""Воспроизводимый набор опытов. Запуск: python src/experiments.py."""
import csv
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from kjb import embed, extract, metrics, channel_stats, read_rgb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
KEYS = ["TKI-441", "trial-2", "trial-3"]
NAMES = {"uniform": "Однотонный", "gradient": "Градиент", "edges": "Резкие границы",
         "texture": "Пёстрая текстура", "black": "Чёрный"}


def containers(size=256):
    y, x = np.mgrid[0:size, 0:size]
    u, v = x / (size - 1), y / (size - 1)
    grad = np.stack([50 + 150*u, 60 + 130*v, 70 + 100*(u+v)/2], axis=2)
    tiles = ((x // max(1, size//8) + y // max(1, size//8)) % 2).astype(bool)
    edges = np.where(tiles[:, :, None], np.array([220, 190, 210]), np.array([35, 65, 40]))
    rng = np.random.Generator(np.random.PCG64(20260929))
    return {"uniform": np.full((size, size, 3), 128, dtype=np.uint8),
            "gradient": np.rint(grad).astype(np.uint8), "edges": edges.astype(np.uint8),
            "texture": rng.integers(25, 231, (size, size, 3), dtype=np.uint8),
            "black": np.zeros((size, size, 3), dtype=np.uint8)}


def watermark():
    return np.array([[int(c) for c in row] for row in
                     ["00000000", "01100110", "01101100", "01111000",
                      "01111000", "01101100", "01100110", "00000000"]], dtype=np.uint8).ravel()


def wm_image(bits):
    return Image.fromarray((np.asarray(bits).reshape(8, 8)*255).astype(np.uint8)).resize((192, 192), Image.Resampling.NEAREST)


def save_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def experiment(image, bits, key, q=.1, n=31, c=3):
    marked, clipped = embed(image, bits, key, q, n, c)
    got, scores, threshold = extract(marked, len(bits), key, n, c)
    return {"q": q, "repeats": n, "radius": c, "bits": len(bits),
            "size": image.shape[0], "key": key, "errors": int(np.count_nonzero(got != bits)),
            "ber_percent": float(np.mean(got != bits)*100),
            "used_pixels_percent": (len(bits)+2)*n / (image.shape[0]*image.shape[1])*100,
            "clipped": clipped, **metrics(image, marked)}, marked, got


def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)


def comparison_sheet(images):
    sheet = Image.new("RGB", (1140, 310 * len(images) + 65), "white")
    draw = ImageDraw.Draw(sheet)
    for x, title in [(20, "Контейнер"), (300, "Исходный"), (575, "Заполненный"), (850, "Разница ×8")]:
        draw.text((x, 20), title, fill="black", font=font(22))
    for row, (name, original, marked) in enumerate(images):
        top = 65 + row*310
        draw.text((20, top+110), NAMES[name], fill="black", font=font(21))
        delta = np.abs(marked.astype(np.int16)-original.astype(np.int16))
        for left, a in [(300, original), (575, marked), (850, np.clip(delta*8,0,255).astype(np.uint8))]:
            sheet.paste(Image.fromarray(a).resize((256,256)), (left,top))
    sheet.save(OUT / "comparison.png")


def attacks(image):
    pil = Image.fromarray(image)
    yield "none", image
    for sigma in (2, 5, 10, 20):
        noise = np.random.Generator(np.random.PCG64(917+sigma)).normal(0,sigma,image.shape)
        yield f"noise_sigma_{sigma}", np.clip(np.rint(image.astype(float)+noise),0,255).astype(np.uint8)
    for quality in (95, 75, 50):
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=quality, subsampling=2)
        buf.seek(0)
        yield f"jpeg_{quality}_420", np.array(Image.open(buf).convert("RGB"))
    for radius in (.5, 1, 2):
        yield f"blur_{radius}", np.array(pil.filter(ImageFilter.GaussianBlur(radius)))
    yield "median_3", np.array(pil.filter(ImageFilter.MedianFilter(3)))
    yield "resize_half_back", np.array(pil.resize((image.shape[1]//2,image.shape[0]//2),Image.Resampling.BILINEAR).resize(pil.size,Image.Resampling.BILINEAR))
    moved = np.zeros_like(image)
    moved[:,1:] = image[:,:-1]
    yield "shift_right_1", moved
    yield "brightness_plus_15", np.clip(image.astype(np.int16)+15,0,255).astype(np.uint8)


def main():
    OUT.mkdir(exist_ok=True)
    bits = watermark()
    wm_image(bits).save(OUT / "watermark.png")
    (OUT / "message_bits.txt").write_text("".join(map(str,bits)),encoding="utf-8")
    imgs = containers()
    demo, stats, sheets = [], {}, []
    for name, original in imgs.items():
        folder = OUT / name
        folder.mkdir(exist_ok=True)
        row, marked, got = experiment(original,bits,KEYS[0])
        demo.append({"container":name, **row})
        Image.fromarray(original).save(folder / "cover.png")
        Image.fromarray(marked).save(folder / "stego.png")
        # Проверяется именно повторно открытый файл, а не массив в памяти.
        recovered, _, _ = extract(read_rgb(folder/"stego.png"),len(bits),KEYS[0])
        assert np.array_equal(got,recovered)
        (folder/"extracted_bits.txt").write_text("".join(map(str,recovered)),encoding="utf-8")
        wm_image(recovered).save(folder / "extracted_watermark.png")
        delta = marked.astype(np.int16)-original.astype(np.int16)
        np.save(folder / "signed_difference.npy",delta)
        Image.fromarray(np.abs(delta).astype(np.uint8)).save(folder / "difference.png")
        Image.fromarray(np.clip(np.abs(delta)*8,0,255).astype(np.uint8)).save(folder / "difference_x8.png")
        # Серый 128 означает нулевое изменение, светлее: +B, темнее: -B.
        Image.fromarray(np.clip(128+delta[:,:,2]*4,0,255).astype(np.uint8)).save(folder/"signed_blue_x4.png")
        stats[name]={"cover":channel_stats(original),"stego":channel_stats(marked)}
        hist=[]
        for value in range(256):
            hist.append({"level":value,"cover_blue":int(np.count_nonzero(original[:,:,2]==value)),
                         "stego_blue":int(np.count_nonzero(marked[:,:,2]==value))})
        save_csv(folder/"histogram_blue.csv",hist)
        sheets.append((name,original,marked))
    comparison_sheet(sheets)
    save_csv(OUT/"demo.csv",demo)
    (OUT/"channel_stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8")
    rows=[]
    for name,image in imgs.items():
        for q in (.01,.03,.05,.1,.2):
            for n in (1,5,15,31,63):
                for key in KEYS:
                    row,_,_=experiment(image,bits,key,q,n)
                    rows.append({"container":name,**row})
    save_csv(OUT/"parameter_sweep.csv",rows)
    radius_rows=[]
    for name,image in imgs.items():
        for c in (1,2,3,5,8):
            for key in KEYS:
                row,_,_=experiment(image,bits,key,c=c)
                radius_rows.append({"container":name,**row})
    save_csv(OUT/"radius_sweep.csv",radius_rows)
    loads=[]
    for size in (128,256,512):
        for name,image in containers(size).items():
            for length in (16,64,256,1024):
                payload=np.random.Generator(np.random.PCG64(400+length)).integers(0,2,length,dtype=np.uint8)
                for key in KEYS:
                    if (length+2)*31 > (size-6)**2:
                        loads.append({"container":name,"size":size,"bits":length,"key":key,
                                      "status":"capacity_exceeded","ber_percent":None,"psnr_rgb_db":None,
                                      "used_pixels_percent":None})
                        continue
                    row,_,_=experiment(image,payload,key)
                    loads.append({"container":name,"size":size,"bits":length,"key":key,
                                  "status":"ok", **{k:row[k] for k in ("ber_percent","psnr_rgb_db","used_pixels_percent")}})
    save_csv(OUT/"payload_sweep.csv",loads)
    attacked_rows=[]
    for name,image in imgs.items():
        for key in KEYS:
            for q in (.05,.1,.2):
                marked,_=embed(image,bits,key,q)
                for attack,a in attacks(marked):
                    got,_,_=extract(a,len(bits),key)
                    attacked_rows.append({"container":name,"key":key,"q":q,"attack":attack,
                                          "errors":int(np.count_nonzero(got!=bits)),
                                          "ber_percent":float(np.mean(got!=bits)*100),
                                          **metrics(marked,a)})
                    if name=="gradient" and key==KEYS[0] and q==.1:
                        folder=OUT/"attacks"
                        folder.mkdir(exist_ok=True)
                        Image.fromarray(a).save(folder/f"{attack}.png")
                        wm_image(got).save(folder/f"{attack}_watermark.png")
    save_csv(OUT/"attacks.csv",attacked_rows)
    wm_rows=[]
    for label,payload in [("original",bits),("inverted",1-bits),("zeros",np.zeros(64,dtype=np.uint8)),
                          ("ones",np.ones(64,dtype=np.uint8)),
                          ("random",np.random.Generator(np.random.PCG64(50)).integers(0,2,64,dtype=np.uint8))]:
        for name,image in imgs.items():
            for key in KEYS:
                row,_,_=experiment(image,payload,key)
                wm_rows.append({"watermark":label,"container":name,**row})
    save_csv(OUT/"watermark_sweep.csv",wm_rows)
    negative=[]
    for name,image in imgs.items():
        marked,_=embed(image,bits,KEYS[0])
        for label,a,key in [("empty_cover",image,KEYS[0]),("wrong_key",marked,"wrong-key")]:
            got,_,_=extract(a,len(bits),key)
            negative.append({"container":name,"condition":label,"ber_percent":float(np.mean(got!=bits)*100)})
    save_csv(OUT/"negative_controls.csv",negative)
    summary={"demo":demo,"experiment_rows":{"parameters":len(rows),"radius":len(radius_rows),
             "payload":len(loads),"attacks":len(attacked_rows),"watermarks":len(wm_rows),"negative":len(negative)},
             "baseline":{"q":.1,"repeats":31,"radius":3,"payload_bits":64,"pilot_bits":2,"keys":KEYS},
             "numpy":np.__version__,"source":"synthetic controlled test images; no external photographs"}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
