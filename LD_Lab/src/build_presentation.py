"""Презентация ЛР3 (вариант 9.6, Lens Distortion): python build_presentation.py [выходной.pptx]

Оформление как в презентации ЛР2 (логотипы РУТ, номера слайдов, переход к содержанию).
Данные берутся из ../results (summary.json, *.csv), рисунки строятся здесь же.
"""
import csv
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from pptx import Presentation
from pptx.chart.data import XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from lensdistort import distort, lens_correct, to_uint8

ROOT = HERE.parent
RES = ROOT / "results"
ASSETS = ROOT / "deck_assets"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "ТКИ-441_Буланый_Хоптий_В9.6_Lens_Distortion_Лр3_СМЗИ.pptx"

NAVY, BLUE, SKY = RGBColor(0x0B, 0x25, 0x45), RGBColor(0x1B, 0x5C, 0xB8), RGBColor(0xE6, 0xEF, 0xFB)
ORANGE, GREEN, RED = RGBColor(0xF2, 0x8C, 0x28), RGBColor(0x1E, 0x9E, 0x6A), RGBColor(0xD6, 0x45, 0x45)
GRAY, LIGHT, BORDER = RGBColor(0x5B, 0x6B, 0x7C), RGBColor(0xF4, 0xF7, 0xFB), RGBColor(0xD3, 0xDD, 0xEA)
TEXT, WHITE = RGBColor(0x1B, 0x24, 0x30), RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Arial"
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "axes.unicode_minus": False, "mathtext.fontset": "stix"})

# ------------------------------------------------------------------ данные
summary = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
est_rows = list(csv.reader((RES / "estimate_K_synthetic.csv").open(encoding="utf-8-sig"), delimiter=";"))[1:]
curve_rows = list(csv.reader((RES / "straightness_vs_K.csv").open(encoding="utf-8-sig"), delimiter=";"))[1:]
interp_rows = list(csv.reader((RES / "interpolation.csv").open(encoding="utf-8-sig"), delimiter=";"))[1:]
num = lambda s: float(str(s).replace(",", "."))  # noqa: E731
fmt = lambda x, d=2: f"{x:.{d}f}".replace(".", ",").replace("-", "−")  # noqa: E731
K_EST = {round(num(r[0]), 2): num(r[2]) for r in est_rows}  # Kd -> найденное K
ph = summary["photo"]

# ------------------------------------------------------------------ рисунки
V_COLS = np.linspace(120, 1080, 9)
H_ROWS = np.linspace(110, 790, 7)
grid = np.array(Image.open(RES / "grid_ideal.png").convert("L"), dtype=float)[..., None]


def ref_lines(ax, pad=0):
    for c in V_COLS:
        ax.axvline(c + pad, color="#d62728", lw=0.8, ls="--", alpha=0.9)
    for r in H_ROWS:
        ax.axhline(r + pad, color="#d62728", lw=0.8, ls="--", alpha=0.9)


def make_assets():
    ASSETS.mkdir(exist_ok=True)
    barrel = distort(grid, 0.20, pad=0)
    pincushion = distort(grid, -0.20, pad=0)
    k_fix = K_EST[0.20]
    _, fixed = lens_correct(barrel, k_fix, pad=50)
    _, over = lens_correct(barrel, k_fix - 0.15, pad=50)

    # типы дисторсии (слайд 3)
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.5), dpi=170)
    for ax, im, t in zip(axs, (grid, barrel, pincushion), ("Без дисторсии", "Бочка", "Подушка")):
        ax.imshow(to_uint8(im), cmap="gray", vmin=0, vmax=255)
        ax.set_title(t, fontsize=17, color="#0B2545", pad=8)
        ax.axis("off")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(ASSETS / "types.png", facecolor="#F4F7FB")
    plt.close(fig)

    # опыт 1 (слайд 5)
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.7), dpi=170)
    panels = [(barrel, 0, "Искажённая (бочка, $K_d$ = +0,20)"),
              (fixed, 50, f"Исправленная, K = {fmt(k_fix, 3)}"),
              (over, 50, f"Слишком сильная, K = {fmt(k_fix - 0.15, 3)}")]
    for ax, (im, pad, t) in zip(axs, panels):
        ax.imshow(to_uint8(im), cmap="gray", vmin=0, vmax=255)
        ref_lines(ax, pad)
        ax.set_title(t, fontsize=15, color="#0B2545", pad=8)
        ax.axis("off")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(ASSETS / "exp1.png", facecolor="#F4F7FB")
    plt.close(fig)

    # формула
    fig = plt.figure(figsize=(0.1, 0.1))
    fig.text(0, 0, r"$(x_K,\ y_K)=\left(x\,(1+K r^{2}),\ y\,(1+K r^{2})\right),\quad r=\sqrt{x^{2}+y^{2}}$",
             fontsize=30, color="#0B2545")
    fig.savefig(ASSETS / "formula.png", dpi=300, bbox_inches="tight", pad_inches=0.04, transparent=True)
    plt.close(fig)

    # фото (слайд 7)
    def small(src, dst, width=900):
        im = Image.open(src).convert("RGB")
        im = im.resize((width, int(im.height * width / im.width)), Image.Resampling.LANCZOS)
        im.save(ASSETS / dst, quality=90)
    small(ROOT / "input" / "photo_phone.png", "ph_orig.jpg")
    small(RES / "photo_distorted.png", "ph_dist.jpg")
    small(RES / "photo_corrected.png", "ph_fixed.jpg")


make_assets()

# ------------------------------------------------------------------ каркас
prs = Presentation()
prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
BLANK = prs.slide_layouts[6]
LINKS = []


def tb(slide, text, x, y, w, h, size=18, bold=False, color=TEXT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = anchor
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        runs = line if isinstance(line, list) else [(line, {})]
        for t, st in runs:
            r = p.add_run()
            r.text = t
            r.font.name, r.font.size = FONT, Pt(st.get("size", size))
            r.font.bold = st.get("bold", bold)
            r.font.color.rgb = st.get("color", color)
    return box


def card(slide, x, y, w, h, fill=WHITE, border=BORDER, radius=0.05):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = radius
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.color.rgb = border
    s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def pic(slide, path, x, y, w=None, h=None, border=False):
    with Image.open(path) as im:
        ratio = im.width / im.height
    if w and h:
        if w / h > ratio:
            w = h * ratio
        else:
            h = w / ratio
    elif w:
        h = w / ratio
    else:
        w = h * ratio
    p = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    if border:
        p.line.color.rgb = BORDER
        p.line.width = Pt(1)
    return p, w, h


def new_slide(title, notes=""):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = LIGHT
    number = len(prs.slides)
    tb(s, title, 0.6, 0.3, 11.5, 0.8, 28, True, NAVY, anchor=MSO_ANCHOR.MIDDLE)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.65), Inches(1.1), Inches(0.9), Inches(0.07))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ORANGE
    bar.line.fill.background()
    s.shapes.add_picture(str(ASSETS / "logo_coat.png"), Inches(0.35), Inches(6.9), height=Inches(0.5))
    s.shapes.add_picture(str(ASSETS / "logo_text.png"), Inches(0.95), Inches(6.9), height=Inches(0.5))
    tb(s, str(number), 12.2, 7.0, 0.6, 0.3, 12, False, GRAY, PP_ALIGN.RIGHT)
    if number > 2:
        nav = tb(s, "К содержанию", 10.4, 7.0, 1.7, 0.3, 12, False, BLUE, PP_ALIGN.RIGHT)
        LINKS.append((nav, 2))
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def chip(slide, text, x, y, w, h=0.45, fill=SKY, color=NAVY, size=14):
    card(slide, x, y, w, h, fill, fill, 0.5)
    tb(slide, text, x, y, w, h, size, True, color, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, 0)


def kpi(slide, value, label, x, y, w, h=1.5, color=BLUE, vsize=28):
    card(slide, x, y, w, h)
    tb(slide, value, x, y + 0.1, w, 0.75, vsize, True, color, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, 0)
    tb(slide, label, x + 0.12, y + 0.88, w - 0.24, h - 0.9, 13, False, GRAY, PP_ALIGN.CENTER, MSO_ANCHOR.TOP, 0)


def table(slide, header, rows, x, y, w, h, size=14, col_w=None):
    shape = slide.shapes.add_table(len(rows) + 1, len(header), Inches(x), Inches(y), Inches(w), Inches(h))
    grid_t = shape.table
    if col_w:
        total = sum(col_w)
        for i, part in enumerate(col_w):
            grid_t.columns[i].width = Inches(w * part / total)
    for r, values in enumerate([header] + rows):
        grid_t.rows[r].height = Inches(h / (len(rows) + 1))
        for c, value in enumerate(values):
            cell = grid_t.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = BLUE if r == 0 else (WHITE if r % 2 else RGBColor(0xEE, 0xF4, 0xFB))
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            para = cell.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.CENTER
            run = para.add_run()
            run.text = str(value)
            run.font.name, run.font.size = FONT, Pt(size)
            run.font.bold = r == 0
            run.font.color.rgb = WHITE if r == 0 else TEXT
    return shape


# ------------------------------------------------------------------ 1. титул
s = prs.slides.add_slide(BLANK)
s.background.fill.solid()
s.background.fill.fore_color.rgb = WHITE
tb(s, "Лабораторная работа № 3", 0.8, 0.9, 11.5, 0.5, 20, False, GRAY)
tb(s, "Форензика. Коррекция дисторсии объектива", 0.8, 1.4, 11.8, 1.6, 38, True, NAVY)
tb(s, "Вариант 9.6 – Lens Distortion", 0.8, 3.3, 11.5, 0.6, 24, False, BLUE)
tb(s, "Стеганографические методы защиты информации", 0.8, 4.0, 11.5, 0.5, 18, False, GRAY)
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.85), Inches(3.2), Inches(1.2), Inches(0.07))
bar.fill.solid()
bar.fill.fore_color.rgb = ORANGE
bar.line.fill.background()
tb(s, ["Выполнили: Буланый С. Е., Хоптий П. В.", "Группа ТКИ-441", "Проверил: проф. Сидоренко В. Г.", "Москва, 2026"],
   7.6, 4.6, 5.2, 1.8, 16, False, TEXT, space=4)
s.shapes.add_picture(str(ASSETS / "logo_coat.png"), Inches(0.35), Inches(6.9), height=Inches(0.5))
s.shapes.add_picture(str(ASSETS / "logo_text.png"), Inches(0.95), Inches(6.9), height=Inches(0.5))
s.notes_slide.notes_text_frame.text = "Тема – коррекция радиальной дисторсии объектива по разделу 9.6 книги Фарида."

# ------------------------------------------------------------------ 2. содержание (ссылки расставляются в конце)
s = new_slide("Содержание", "Навигация: щёлкните по пункту, чтобы перейти к слайду.")
TOC = [("Дисторсия объектива и форензика", 3), ("Алгоритм коррекции", 4), ("Опыт 1. Сетка из прямых линий", 5),
       ("Опыт 2. Оценка K вслепую", 6), ("Опыт 3. Фотография и интерполяция", 7), ("Выводы", 8), ("Источники", 9)]
TOC_BOXES = []
for i, (name, n) in enumerate(TOC):
    y = 1.5 + i * 0.7
    card(s, 0.9, y, 8.2, 0.55, WHITE, BORDER, 0.2)
    b = tb(s, f"{name}", 1.1, y, 7.0, 0.55, 20, False, NAVY, anchor=MSO_ANCHOR.MIDDLE, space=0)
    tb(s, str(n), 8.3, y, 0.7, 0.55, 20, True, BLUE, PP_ALIGN.RIGHT, MSO_ANCHOR.MIDDLE, 0)
    TOC_BOXES.append((b, n))

# ------------------------------------------------------------------ 3. дисторсия и форензика
s = new_slide("Дисторсия объектива и форензика",
              "Дисторсия искривляет прямые линии у краёв кадра. Бочка – у широкоугольных объективов и телефонов, подушка – у телеобъективов. "
              "В форензике её используют, чтобы определить камеру, заметить монтаж и подготовить снимок к измерениям.")
pic(s, ASSETS / "types.png", 0.6, 1.35, w=12.1)
cards = [("Что это", ["Увеличение зависит от расстояния до центра кадра, поэтому прямые линии у краёв изгибаются [2]."]),
         ("Виды", ["Бочка – линии выгибаются наружу.", "Подушка – линии прогибаются внутрь."]),
         ("Зачем в форензике", ["Определение камеры по дисторсии [4].", "Несогласованность в кадре – признак монтажа.", "Её убирают перед измерениями."])]
for i, (head, lines) in enumerate(cards):
    x = 0.6 + i * 4.1
    card(s, x, 4.75, 3.95, 2.0)
    tb(s, head, x + 0.15, 4.82, 3.6, 0.4, 17, True, BLUE, space=2)
    tb(s, ["• " + t for t in lines], x + 0.15, 5.25, 3.65, 1.5, 14, False, TEXT, space=3)

# ------------------------------------------------------------------ 4. алгоритм
s = new_slide("Алгоритм коррекции (раздел 9.6 книги Фарида)",
              "Пиксель результата берётся из исходного изображения в точке, сдвинутой по радиусу в (1 плюс K на r в квадрате) раз. "
              "K один: минус исправляет бочку, плюс – подушку. Перед расчётом добавляем поля по 50 пикселей, чтобы углы не терялись.")
steps = ["Ввод: изображение и параметр K [1]", "Поля из нулей по 50 пикс. со всех сторон",
         "Сетка координат, нормировка в диапазон [−1; 1]", "Радиус r – расстояние до центра кадра",
         "Новая сетка: x·(1 + K·r²), y·(1 + K·r²) [3]", "Интерполяция каждого канала [7, 8] → результат"]
for i, t in enumerate(steps):
    y = 1.45 + i * 0.86
    card(s, 0.6, y, 5.9, 0.66, WHITE, BLUE, 0.15)
    tb(s, str(i + 1), 0.7, y, 0.5, 0.66, 20, True, ORANGE, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, 0)
    tb(s, t, 1.25, y, 5.2, 0.66, 15, False, TEXT, anchor=MSO_ANCHOR.MIDDLE, space=0)
    if i < len(steps) - 1:
        a = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(3.55), Inches(y + 0.66), Inches(3.55), Inches(y + 0.86))
        a.line.color.rgb = BLUE
        a.line.width = Pt(2)
card(s, 6.9, 1.45, 5.8, 1.55, WHITE, BORDER)
tb(s, "Формула преобразования", 7.05, 1.5, 5.5, 0.4, 16, True, BLUE, space=2)
pic(s, ASSETS / "formula.png", 7.1, 2.0, w=5.4)
tb(s, "Знак параметра K", 6.9, 3.25, 5.8, 0.4, 16, True, BLUE)
chip(s, "K < 0 – исправляет бочку", 6.9, 3.75, 5.8)
chip(s, "K > 0 – исправляет подушку", 6.9, 4.3, 5.8)
chip(s, "K = 0 – без изменений", 6.9, 4.85, 5.8, fill=RGBColor(0xEE, 0xF1, 0xF5), color=GRAY)
card(s, 6.9, 5.5, 5.8, 1.2)
tb(s, ["Код с MATLAB перенесён на Python и проверен 5 тестами.", "Точки вне кадра – чёрные; центр кадра = главная точка."],
   7.05, 5.55, 5.5, 1.1, 14, False, TEXT, space=3)

# ------------------------------------------------------------------ 5. опыт 1
s = new_slide("Опыт 1. Сетка из прямых линий",
              "Мы взяли сетку из девяти вертикальных и семи горизонтальных прямых, исказили её известным K и исправили. "
              "Красным показаны идеальные прямые. При подобранном K линии почти совпадают с ними, при слишком сильной коррекции выгибаются в другую сторону.")
pic(s, ASSETS / "exp1.png", 0.6, 1.3, w=12.1)
dev0 = [num(r[4]) for r in est_rows]
dev1 = [num(r[5]) for r in est_rows]
kpi(s, f"{fmt(min(dev0), 1)}–{fmt(max(dev0), 1)} % → {fmt(min(dev1))}–{fmt(max(dev1), 1)} %",
    "отклонение линий от прямых до и после коррекции, % расстояния между линиями", 0.6, 5.25, 4.9, 1.5, vsize=24)
kpi(s, "0,1–0,6 пикс.", "остаточное отклонение на сетке 1200×900 пикс.", 5.7, 5.25, 3.4, 1.5, GREEN)
kpi(s, f"K = {fmt(K_EST[0.20], 3)}", "найдено вслепую при заданном K_d = +0,20", 9.3, 5.25, 3.4, 1.5, ORANGE)

# ------------------------------------------------------------------ 6. опыт 2
s = new_slide("Опыт 2. Оценка K вслепую по прямолинейности линий",
              "K подбирается без знания исходной сцены: после коррекции прямые линии должны стать прямыми [5]. "
              "Мера – отклонение линий от наилучшей прямой в процентах расстояния между линиями. У каждой кривой один минимум. "
              "Найденное K близко к минус Kd, но не равно ему: одной степени r в квадрате для точного обращения не хватает.")
cd = XyChartData()
names = {0.1: "K_d = +0,10 (бочка)", 0.2: "K_d = +0,20 (бочка)", -0.1: "K_d = −0,10 (подушка)", -0.2: "K_d = −0,20 (подушка)"}
colors = {0.1: "1B5CB8", 0.2: "1E9E6A", -0.1: "F28C28", -0.2: "8E5BC4"}
for kd in (0.1, 0.2, -0.1, -0.2):
    ser = cd.add_series(names[kd])
    for r in curve_rows:
        if abs(num(r[0]) - kd) < 1e-9:
            ser.add_data_point(num(r[1]), num(r[2]))
gf = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, Inches(0.5), Inches(1.4), Inches(7.4), Inches(5.35), cd)
ch = gf.chart
ch.has_legend = True
ch.legend.position = XL_LEGEND_POSITION.BOTTOM
ch.legend.include_in_layout = False
ch.legend.font.size = Pt(12)
ch.font.name = FONT
for kd, ser in zip((0.1, 0.2, -0.1, -0.2), ch.series):
    ser.smooth = False
    ser.format.line.color.rgb = RGBColor.from_string(colors[kd])
    ser.format.line.width = Pt(2.5)
va, ca = ch.value_axis, ch.category_axis
va.has_major_gridlines = True
va.major_gridlines.format.line.color.rgb = BORDER
va.tick_labels.font.size = Pt(12)
va.has_title = True
va.axis_title.text_frame.text = "отклонение линий, % расстояния между линиями"
va.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
va.tick_label_position = XL_TICK_LABEL_POSITION.LOW
ca.has_title = True
ca.axis_title.text_frame.text = "параметр коррекции K"
ca.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
ca.tick_labels.font.size = Pt(12)
ca.tick_labels.number_format = "0.0"
ca.tick_labels.number_format_is_linked = False
ca.minimum_scale, ca.maximum_scale = -0.4, 0.4
ca.has_major_gridlines = False
rows = [[fmt(num(r[0])), fmt(num(r[2]), 3), fmt(num(r[3]), 3), fmt(num(r[5]))] for r in est_rows]
table(s, ["K_d", "K найдено", "K_d + K", "Откл. после, %"], rows, 8.15, 1.5, 4.6, 2.6, size=13, col_w=[1, 1.3, 1.1, 1.5])
card(s, 8.15, 4.35, 4.6, 2.4)
tb(s, [[("Выводы опыта", {"bold": True, "color": BLUE, "size": 16})], "• K ≈ −K_d, но не равно: сумма растёт с силой искажения.",
       "• Для подушки расхождение больше, чем для бочки.", "• Отклонение падает до долей процента.",
       "• Другой подход – по спектру, без линий [6]."],
   8.3, 4.4, 4.35, 2.3, 14, False, TEXT, space=4)

# ------------------------------------------------------------------ 7. фото
s = new_slide("Опыт 3. Фотография и интерполяция",
              "Фотографию мы исказили известным K_d = +0,20 и исправили. Без коррекции PSNR 11,0 дБ, при лучшем K = минус 0,168 – 21,7 дБ. "
              "Порядок интерполяции влияет слабо, до 0,4 дБ. Снимок искажён искусственно, настоящих снимков с оптической дисторсией мы пока не проверяли.")
for i, (img, cap) in enumerate((("ph_orig.jpg", "Исходное"), ("ph_dist.jpg", "Искажённое (K_d = +0,20)"),
                                ("ph_fixed.jpg", f"Исправленное, K = {fmt(ph['K_best'], 3)}"))):
    x = 0.6 + i * 4.1
    pic(s, ASSETS / img, x, 1.4, w=3.95, border=True)
    tb(s, cap, x, 4.45, 3.95, 0.4, 15, True, NAVY, PP_ALIGN.CENTER)
kpi(s, f"{fmt(ph['psnr_distorted'], 1)} → {fmt(ph['psnr_corrected'], 1)} дБ", "PSNR к исходному: до и после коррекции", 0.6, 5.0, 4.0, 1.75, vsize=26)
kpi(s, f"K = {fmt(ph['K_best'], 3)}", "лучшее по PSNR при K_d = +0,20 (не ровно −0,20)", 4.75, 5.0, 3.4, 1.75, GREEN)
table(s, ["Интерполяция", "PSNR, дБ"], [[r[0], r[1]] for r in interp_rows], 8.3, 5.0, 4.4, 1.75, size=13, col_w=[2.4, 1.2])

# ------------------------------------------------------------------ 8. выводы
s = new_slide("Выводы",
              "Главное: алгоритм работает, K можно подобрать без знания исходной сцены, но одного параметра хватает не для точного, а для приближённого обращения. "
              "Следующий шаг – снимки с реальной оптической дисторсией и второй коэффициент.")
items = [("Алгоритм", "Однопараметрическая модель из раздела 9.6 перенесена на Python и проверена; K < 0 исправляет бочку, K > 0 – подушку."),
         ("Оценка K", "По прямолинейности линий K находится вслепую: отклонение падает с 2–4 % до 0,08–0,5 % расстояния между линиями."),
         ("Точность", "K ≈ −K_d, но не равно ему: модель с одним коэффициентом приближённо обращает само преобразование."),
         ("Фото и интерполяция", "PSNR вырос с 11,0 до 21,7 дБ; порядок интерполяции влияет слабо (до 0,4 дБ).")]
for i, (head, body) in enumerate(items):
    x, y = 0.6 + (i % 2) * 6.15, 1.45 + (i // 2) * 1.95
    card(s, x, y, 5.95, 1.75)
    tb(s, head, x + 0.15, y + 0.08, 5.6, 0.4, 18, True, BLUE, space=2)
    tb(s, body, x + 0.15, y + 0.55, 5.65, 1.15, 14, False, TEXT)
card(s, 0.6, 5.4, 12.1, 1.3, RGBColor(0xFF, 0xF4, 0xE6), ORANGE)
tb(s, [[("Ограничения. ", {"bold": True, "color": ORANGE}),
        ("Главная точка принята в центре кадра, используется один коэффициент; фотография искажена искусственно, снимки с реальной "
         "оптической дисторсией не проверялись. Дальше: реальные снимки и второй коэффициент k₂.", {})]],
   0.8, 5.5, 11.7, 1.1, 15, False, TEXT)

# ------------------------------------------------------------------ 9. источники
s = new_slide("Использованные источники", "Основной источник задания – книга Фарида; остальное – литература по дисторсии и интерполяции.")
src = ["Farid H. Digital Image Forensics. – Dartmouth College, 2012. – 199 p. – www.cs.dartmouth.edu/farid.",
       "Дисторсия в оптике // Большая российская энциклопедия. – https://bigenc.ru/c/distorsiia-v-optike-57966a.",
       "Brown D. C. Close-range camera calibration // Photogrammetric Engineering. – 1971. – Vol. 37, No. 8. – P. 855–866.",
       "Choi K. S., Lam E. Y., Wong K. K. Y. Automatic source camera identification using the intrinsic lens radial distortion // Optics Express. – 2006. – Vol. 14, No. 24.",
       "Devernay F., Faugeras O. Straight lines have to be straight // Machine Vision and Applications. – 2001. – Vol. 13, No. 1. – P. 14–24.",
       "Farid H., Popescu A. C. Blind removal of lens distortion // J. Opt. Soc. Am. A. – 2001. – Vol. 18, No. 9. – P. 2072–2078.",
       "Keys R. G. Cubic convolution interpolation for digital image processing // IEEE Trans. ASSP. – 1981. – Vol. 29, No. 6. – P. 1153–1160.",
       "Unser M. Splines: a perfect fit for signal and image processing // IEEE Signal Processing Magazine. – 1999. – Vol. 16, No. 6. – P. 22–38."]
tb(s, [f"{i + 1}. {t}" for i, t in enumerate(src)], 0.7, 1.45, 12.0, 5.3, 15, False, TEXT, space=8)
tb(s, "Дата обращения к электронным источникам: 09.11.2026.", 0.7, 6.5, 8, 0.3, 12, False, GRAY)

# ------------------------------------------------------------------ ссылки
for box, n in TOC_BOXES + LINKS:
    box.click_action.target_slide = prs.slides[n - 1]
prs.save(str(OUT))
print("сохранено:", OUT.name, "слайдов:", len(prs.slides))
