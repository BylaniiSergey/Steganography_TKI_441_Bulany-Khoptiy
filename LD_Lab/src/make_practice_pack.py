"""Материалы практической части ЛР3 (вариант 9.6) для оформления отчёта.

Воспроизводит то, что показывает окно MATLAB-программы lensdistort из книги Фарида: слева исходный кадр с полями,
справа исправленный, в заголовке значение K, внизу ползунок. Расчёт делает Python-версия (lensdistort.py).
Запуск: python make_practice_pack.py   ->   ../../Рисунки для отчёта/*.png  и  ../../Практическая часть ЛР3 - материалы для Пети.docx
"""
import csv
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from PIL import Image

from lensdistort import lens_correct, to_uint8

ROOT = HERE.parent
RES = ROOT / "results"
TASK = ROOT.parent
PICS = TASK / "Рисунки для отчёта"
PICS.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "axes.unicode_minus": True})

summary = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
photo_psnr = {round(float(r[0].replace(",", ".")), 3): float(r[1].replace(",", "."))
              for r in list(csv.reader((RES / "photo_psnr_vs_K.csv").open(encoding="utf-8-sig"), delimiter=";"))[1:]}
K_BEST = summary["photo"]["K_best"]

# входной файл практической части: искажённая фотография (так выглядит снимок, который «подали программе»)
src = Image.open(RES / "photo_distorted.png").convert("RGB")
# уменьшаем для скорости и читаемости окна: ширина кадра 900 пикс.
scale = 900 / src.width
src = src.resize((900, int(src.height * scale)), Image.Resampling.LANCZOS)
SRC_PATH = PICS / "00_исходный_файл_искажённая_фотография.png"
src.save(SRC_PATH)
arr = np.array(src)


def window(K, name):
    """Окно в стиле MATLAB: [im imK], заголовок K, ползунок внизу слева."""
    impad, imK = lens_correct(arr, K, pad=50, order=3)
    both = to_uint8(np.concatenate([impad, imK], axis=1))
    h, w = both.shape[:2]
    fig = plt.figure(figsize=(12.0, 12.0 * 0.98 * h / w / 0.72), dpi=130, facecolor="#F0F0F0")
    ax = fig.add_axes([0.01, 0.17, 0.98, 0.72])
    ax.imshow(both)
    ax.axis("off")
    fig.text(0.5, 0.93, f"{K:.3f}".rstrip("0").rstrip(".") if K != 0 else "0", ha="center", va="center", fontsize=13, color="black")
    # ползунок, как в окне MATLAB (диапазон от −1 до 1)
    sax = fig.add_axes([0.012, 0.035, 0.2, 0.055])
    sax.set_xlim(0, 1)
    sax.set_ylim(0, 1)
    sax.axis("off")
    sax.add_patch(Rectangle((0.0, 0.0), 1, 1, facecolor="#D9D9D9", edgecolor="#9A9A9A", lw=1))
    sax.add_patch(Rectangle((0.0, 0.0), 0.07, 1, facecolor="#F0F0F0", edgecolor="#9A9A9A", lw=1))
    sax.add_patch(Rectangle((0.93, 0.0), 0.07, 1, facecolor="#F0F0F0", edgecolor="#9A9A9A", lw=1))
    pos = 0.07 + 0.80 * (K + 1) / 2
    sax.add_patch(Rectangle((pos - 0.04, 0.05), 0.08, 0.9, facecolor="#F7F7F7", edgecolor="#6A6A6A", lw=1))
    fig.text(0.78, 0.045, "слева – исходный кадр с полями 50 пикс., справа – исправленный", ha="right", fontsize=9, color="#555555")
    fig.savefig(PICS / name, facecolor=fig.get_facecolor())
    plt.close(fig)
    return PICS / name


steps = [
    (0.0, "01_K_0_без_изменений.png", "K = 0", "Ползунок в среднем положении: исправленный кадр совпадает с исходным (только поля по 50 пикс. вокруг изображения). Линии телефона по краям кадра изогнуты наружу – это бочкообразная дисторсия."),
    (-0.05, "02_K_минус_0,05.png", "K = −0,05", "Коррекция начала работать: края выпрямляются, но ещё заметно искривление в углах."),
    (-0.10, "03_K_минус_0,10.png", "K = −0,10", "Края почти прямые, углы всё ещё немного изогнуты."),
    (K_BEST, "04_K_минус_0,168_лучший.png", "K = −0,168", "Лучшее значение: изображение наиболее близко к исходному (до искажения). Прямые края корпуса телефона выпрямлены."),
    (-0.25, "05_K_минус_0,25_слишком_сильно.png", "K = −0,25", "Слишком сильная коррекция: линии выгибаются в обратную сторону (получается подушка), углы вытягиваются за кадр."),
    (0.10, "06_K_плюс_0,10_в_другую_сторону.png", "K = +0,10", "Ползунок вправо (K > 0) усиливает бочку – искажение растёт. Положительный K нужен для исправления подушкообразной дисторсии."),
]
rows = []
for K, fname, label, note in steps:
    p = window(K, fname)
    if abs(K - K_BEST) < 1e-9:
        psnr = summary["photo"]["psnr_corrected"]
    else:
        psnr = photo_psnr.get(round(K, 3))
    rows.append((K, fname, label, note, psnr))
    print("ok", fname)

# рисунки опытов из results
extra = [("fig1_grid_before_after.png", "07_опыт_сетка_до_и_после.png"), ("fig2_K_sweep_grid.png", "08_опыт_сетка_перебор_K.png"),
         ("fig3_straightness_vs_K.png", "09_опыт_оценка_K_график.png"), ("fig4_photo_before_after.png", "10_опыт_фото_до_и_после.png"),
         ("fig5_psnr_vs_K.png", "11_опыт_фото_PSNR_от_K.png"), ("fig6_interpolation.png", "12_опыт_интерполяция.png"),
         ("fig7_padding.png", "13_опыт_поля_из_нулей.png"), ("scheme_algorithm.png", "14_схема_алгоритма.png")]
for a, b in extra:
    shutil.copy(RES / a, PICS / b)

# ------------------------------------------------------------------ документ
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(1.5), Cm(2), Cm(2)
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
for name, size in (("Heading 1", 15), ("Heading 2", 13)):
    h = doc.styles[name]
    h.font.name = "Times New Roman"
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = None
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")


def para(text, bold=False, italic=False, align=None, after=4):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    p.paragraph_format.space_after = Pt(after)
    if align:
        p.alignment = align
    return p


def figure(path, caption, width=16.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.add_run(caption).italic = True
    c.paragraph_format.space_after = Pt(8)


def table(header, data, widths):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, htxt in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(htxt)
        r.bold = True
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in data:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            cells[i].paragraphs[0].add_run(str(v))
            cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


doc.add_heading("Практическая часть ЛР3 (вариант 9.6, коррекция дисторсии) – материалы для отчёта", level=1)
para("Что это: готовые рисунки, цифры и пояснения. Из них можно собрать практическую часть отчёта: вставить рисунок, взять подпись и 1–2 предложения «что видно». "
     "Полный готовый отчёт тоже есть (файл ТКИ-441_Буланый_С_Е_В9.6_Lens_Distortion_Форензика_СМЗИ.docx, 23 страницы) – им можно пользоваться как образцом.", after=8)

doc.add_heading("1. Программа и как запустить", level=2)
para("Программа: MATLAB. Код практической части – функция lensdistort из книги Х. Фарида «Digital Image Forensics», раздел 9.6 (стр. 157–158). "
     "Она убирает радиальную дисторсию объектива с изображения, считая главной точкой центр кадра. Ползунок в левом нижнем углу окна задаёт величину дисторсии K "
     "(от −1 до 1), значение K показано в заголовке. Слева показан исходный кадр, справа – исправленный.")
para("Запуск в MATLAB:", bold=True, after=2)
for s in ["Положить файл lensdistort.m (LD_Lab\\src\\lensdistort.m) и картинку (например, 00_исходный_файл_искажённая_фотография.png) в одну папку и сделать её текущей (Current Folder).",
          "В Command Window набрать: lensdistort('00_исходный_файл_искажённая_фотография.png')",
          "Двигать ползунок и делать скриншоты окна при значениях K из таблицы 1 – это и есть практическая часть.",
          "Если MATLAB нет – подходит бесплатный GNU Octave (тот же код). Тот же результат даёт и Python-версия: python lensdistort.py вход.png выход.png -K -0.168."]:
    para("• " + s, after=2)
para("Важно: рисунки 1–6 ниже воспроизводят окно MATLAB-программы (слева кадр с полями, справа результат, заголовок K, ползунок) и посчитаны Python-версией, "
     "которая повторяет код книги. Если у Пети есть MATLAB, лучше сделать настоящие скриншоты окна при тех же K и подставить вместо рисунков 1–6; значения и подписи те же.", italic=True, after=8)

doc.add_heading("2. Исходные данные", level=2)
para("Файл на входе: фотография, искажённая бочкообразной дисторсией (параметр искажения K_d = +0,20). Размер 900×675 пикс. (для окна программы уменьшена до ширины 900). "
     "Исходная фотография – та же, что в ЛР2. Файл: 00_исходный_файл_искажённая_фотография.png.")
figure(SRC_PATH, "Рисунок 0 – Исходный файл для программы (бочкообразная дисторсия)", 11)

doc.add_heading("3. Ход работы: окно программы при разных K", level=2)
para("Ползунок устанавливается на разные значения K. Ниже – окно программы при шести значениях. PSNR – сходство исправленного кадра с исходной фотографией до искажения "
     "(больше – лучше).", after=6)
for i, (K, fname, label, note, psnr) in enumerate(rows, start=1):
    ps = f" PSNR = {str(round(psnr, 1)).replace('.', ',')} дБ." if psnr is not None else ""
    figure(PICS / fname, f"Рисунок {i} – Окно программы lensdistort, {label}", 16.5)
    para(note + ps, after=10)

doc.add_heading("Таблица 1 – Значения K и результат", level=2)
tbl = [[label.replace("K = ", ""), f"{round(psnr, 1)}".replace(".", ",") if psnr is not None else "–", note.split(":")[0].split(".")[0]] for K, fname, label, note, psnr in rows]
table(["K (ползунок)", "PSNR, дБ", "Что видно"], tbl, [3.2, 3.0, 11.0])

doc.add_heading("4. Опыты на сетке из прямых линий (доказательство, что алгоритм выпрямляет линии)", level=2)
para("Чтобы проверить алгоритм объективно, взяли сетку из прямых линий, исказили её известным K_d и исправили. Красным пунктиром показаны идеальные прямые.")
figure(PICS / "07_опыт_сетка_до_и_после.png", "Рисунок 7 – Сетка: искажённая, исправленная (K = −0,145) и слишком сильная коррекция (K = −0,295)", 16.0)
figure(PICS / "08_опыт_сетка_перебор_K.png", "Рисунок 8 – Результат при разных K (верхний ряд – бочка, нижний – подушка)", 16.5)
para("K можно найти автоматически: после коррекции линии должны стать прямыми. Мера – отклонение линий от прямых в процентах расстояния между линиями; у каждой кривой один минимум.")
figure(PICS / "09_опыт_оценка_K_график.png", "Рисунок 9 – Отклонение линий от прямых в зависимости от K (точки – найденный минимум)", 14.0)
est = list(csv.reader((RES / "estimate_K_synthetic.csv").open(encoding="utf-8-sig"), delimiter=";"))[1:]
doc.add_heading("Таблица 2 – Оценка K по прямолинейности линий", level=2)
table(["K_d (задано)", "Вид", "K (найдено)", "Откл. до, %", "Откл. после, %"],
      [[r[0], r[1], r[2], r[4], r[5]] for r in est], [2.8, 2.6, 3.0, 3.0, 3.4])
para("Вывод по таблице 2: отклонение линий падает с 2–4 % до 0,08–0,5 % расстояния между линиями. Найденное K близко к −K_d, но не равно ему: одного параметра для точного обращения преобразования не хватает.")

doc.add_heading("5. Опыты на фотографии, интерполяция, поля", level=2)
figure(PICS / "10_опыт_фото_до_и_после.png", "Рисунок 10 – Исходное, искажённое (K_d = +0,20) и исправленное фото, модуль разности", 15.0)
figure(PICS / "11_опыт_фото_PSNR_от_K.png", "Рисунок 11 – Сходство с исходной фотографией (PSNR) в зависимости от K", 12.5)
interp = list(csv.reader((RES / "interpolation.csv").open(encoding="utf-8-sig"), delimiter=";"))[1:]
doc.add_heading("Таблица 3 – Влияние интерполяции на PSNR", level=2)
table(["Интерполяция", "PSNR, дБ"], [[r[0], r[1]] for r in interp], [8.0, 4.0])
figure(PICS / "12_опыт_интерполяция.png", "Рисунок 12 – Фрагмент исправленного изображения при разной интерполяции", 16.5)
figure(PICS / "13_опыт_поля_из_нулей.png", "Рисунок 13 – Коррекция без полей и с полями 50 пикс. (как в программе из книги)", 15.0)
para("Выводы по разделу: без коррекции PSNR 11,0 дБ, при лучшем K = −0,168 – 21,7 дБ. Порядок интерполяции влияет слабо (до 0,4 дБ). Поля из нулей нужны, чтобы при исправлении бочки не терялись углы кадра.")

doc.add_heading("6. Схема алгоритма", level=2)
figure(PICS / "14_схема_алгоритма.png", "Рисунок 14 – Схема алгоритма коррекции радиальной дисторсии", 8.5)

doc.add_heading("7. Где что лежит", level=2)
for line in ["Рисунки для вставки – папка «Рисунки для отчёта» (файлы пронумерованы 00–14).",
             "Код MATLAB из книги – LD_Lab\\src\\lensdistort.m; перенос на Python – LD_Lab\\src\\lensdistort.py.",
             "Готовый отчёт – ТКИ-441_Буланый_С_Е_В9.6_Lens_Distortion_Форензика_СМЗИ.docx (.pdf).",
             "Презентация – ТКИ-441_Буланый_Хоптий_В9.6_Lens_Distortion_Лр3_СМЗИ.pptx; текст выступления – Сообщение для защиты ЛР3.docx.",
             "Перевод раздела 9.6 и список литературы – Литература и перевод раздела 9.6.docx."]:
    para("• " + line, after=2)

out = TASK / "Практическая часть ЛР3 - материалы для Пети.docx"
doc.save(str(out))
print("сохранено:", out.name)
