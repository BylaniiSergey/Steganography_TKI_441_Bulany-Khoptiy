const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  BorderStyle, ShadingType, TableLayoutType, HeadingLevel, TableOfContents, Footer, PageNumber, PageBreak,
  LineRuleType, VerticalAlign,
} = require("docx");

const LAB = "C:/Users/user/Desktop/Учёба ТКИ-441/Стеганография/Задание 3/LD_Lab";
const RES = LAB + "/results";
const OUT = process.argv[2];
const FONT = "Times New Roman";
const CONTENT_W = 9355; // dxa

// ---------------------------------------------------------------- данные
const readCsv = (f) => fs.readFileSync(path.join(RES, f), "utf8").replace(/^\uFEFF/, "").trim().split(/\r?\n/).map((l) => l.split(";"));
const est = readCsv("estimate_K_synthetic.csv").slice(1);
const interp = readCsv("interpolation.csv").slice(1);
const pk = readCsv("photo_psnr_vs_K.csv").slice(1);
const summary = JSON.parse(fs.readFileSync(path.join(RES, "summary.json"), "utf8"));
const fmt = (x, d) => Number(x).toFixed(d).replace(".", ",").replace("-", "−");
const num = (s) => Number(String(s).replace(",", "."));

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

function sliceFunc(src, startMarker, endMarker) {
  const a = src.indexOf(startMarker), b = src.indexOf(endMarker);
  return src.slice(a, b).trimEnd();
}
const expSrc = fs.readFileSync(LAB + "/src/experiments.py", "utf8");
const metricCode = sliceFunc(expSrc, "def straightness(", "def psnr(");
const codeM = fs.readFileSync(LAB + "/src/lensdistort.m", "utf8");
const codePy = fs.readFileSync(LAB + "/src/lensdistort.py", "utf8");

// ---------------------------------------------------------------- хелперы
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 28, bold: o.b, italics: o.i, superScript: o.sup, subScript: o.sub, color: o.color });
function runs(content, size) {
  if (typeof content === "string") return [run(content, { size })];
  return content.map((c) => (typeof c === "string" ? run(c, { size }) : c instanceof TextRun ? c : run(c.t, { ...c, size: c.size || size })));
}
const P = (content, o = {}) =>
  new Paragraph({
    children: runs(content, o.size),
    alignment: o.align || AlignmentType.JUSTIFIED,
    indent: o.noIndent ? undefined : { firstLine: 709 },
    spacing: { line: o.line || 360, lineRule: LineRuleType.AUTO, before: o.before || 0, after: o.after === undefined ? 0 : o.after },
    keepNext: o.keepNext, keepLines: o.keepLines,
  });
const H1 = (t, pb) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: pb, children: [run(t, { b: true })], spacing: { before: 360, after: 200 }, keepNext: true });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(t, { b: true })], spacing: { before: 240, after: 120 }, keepNext: true });
const formula = (t, n) =>
  new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, layout: TableLayoutType.FIXED, columnWidths: [8355, 1000],
    borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }, insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE } },
    rows: [new TableRow({ cantSplit: true, children: [
      new TableCell({ width: { size: 8355, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, borders: noB(), children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 }, children: runs(t, 28) })] }),
      new TableCell({ width: { size: 1000, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, borders: noB(), children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run("(" + n + ")")] })] }),
    ] })],
  });
function noB() { const n = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }; return { top: n, bottom: n, left: n, right: n }; }

let figN = 0, tabN = 0;
function fig(file, width, caption) {
  figN++;
  const f = path.join(RES, file);
  const { w, h } = pngSize(f);
  const height = Math.round((width * h) / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(f), transformation: { width, height }, altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [run(`Рисунок ${figN} – ${caption}`, { size: 26 })] }),
  ];
}
function table(caption, headers, rows, widths, opt = {}) {
  tabN++;
  const bd = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
  const borders = { top: bd, bottom: bd, left: bd, right: bd };
  const cell = (t, w, hdr, align, keep) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders, verticalAlign: VerticalAlign.CENTER,
    shading: hdr ? { type: ShadingType.CLEAR, fill: "E7E6E6", color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    children: [new Paragraph({ keepNext: keep, alignment: align || (hdr ? AlignmentType.CENTER : AlignmentType.CENTER), children: [run(String(t), { size: 24, b: hdr })] })],
  });
  return [
    new Paragraph({ keepNext: true, spacing: { before: 160, after: 80 }, children: [run(`Таблица ${tabN} – ${caption}`, { size: 26 })] }),
    new Table({
      width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, layout: TableLayoutType.FIXED, columnWidths: widths,
      rows: [new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, widths[i], true, undefined, true)) }),
        ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], false, opt.leftCols && opt.leftCols.includes(i) ? AlignmentType.LEFT : undefined, ri < rows.length - 1)) }))],
    }),
    new Paragraph({ spacing: { after: 160 }, children: [] }),
  ];
}
function code(text, size = 18) {
  const bd = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
  const lines = text.replace(/\t/g, "    ").split(/\r?\n/);
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, layout: TableLayoutType.FIXED, columnWidths: [CONTENT_W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: CONTENT_W, type: WidthType.DXA }, borders: { top: bd, bottom: bd, left: bd, right: bd },
      shading: { type: ShadingType.CLEAR, fill: "F5F5F5", color: "auto" }, margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: lines.map((l) => new Paragraph({ spacing: { line: 240, after: 0 }, children: [new TextRun({ text: l === "" ? " " : l, font: "Courier New", size })] })),
    })] })],
  });
}
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// ---------------------------------------------------------------- титульный лист
const T = (t, o = {}) => new Paragraph({ alignment: o.align || AlignmentType.CENTER, spacing: { before: o.before || 0, after: o.after || 0, line: 300 },
  children: [run(t, { size: o.size || 28, b: o.b })] });
const title = [
  T("МИНИСТЕРСТВО ТРАНСПОРТА РОССИЙСКОЙ ФЕДЕРАЦИИ", { size: 26 }),
  T("Федеральное государственное автономное образовательное учреждение высшего образования", { size: 26 }),
  T("«РОССИЙСКИЙ УНИВЕРСИТЕТ ТРАНСПОРТА»", { size: 26, b: true, after: 120 }),
  T("Институт транспортной техники и систем управления", { size: 26 }),
  T("Кафедра «Интеллектуальное управление и информационная безопасность в высокоавтоматизированных транспортных системах»", { size: 26, after: 1500 }),
  T("ОТЧЁТ", { size: 36, b: true, after: 120 }),
  T("по лабораторной работе № 3", { size: 30 }),
  T("«Форензика. Коррекция дисторсии объектива»", { size: 30, b: true }),
  T("(вариант 9.6, Lens Distortion)", { size: 28, after: 120 }),
  T("по дисциплине «Стеганографические методы защиты информации»", { size: 28, after: 1700 }),
  new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 4800 }, spacing: { after: 60 }, children: [run("Выполнили: ст. гр. ТКИ-441", { size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 4800 }, spacing: { after: 60 }, children: [run("Буланый С. Е.", { size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 4800 }, spacing: { after: 240 }, children: [run("Хоптий П. В.", { size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 4800 }, spacing: { after: 60 }, children: [run("Проверил: проф., д.т.н.", { size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.LEFT, indent: { left: 4800 }, spacing: { after: 1500 }, children: [run("Сидоренко В. Г.", { size: 28 })] }),
  T("Москва – 2026", { size: 28 }),
  pageBreak(),
];

// ---------------------------------------------------------------- тело отчёта
const body = [];
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [run("СОДЕРЖАНИЕ", { b: true })] }));
body.push(new TableOfContents("Содержание", { hyperlink: true, headingStyleRange: "1-2" }));
body.push(pageBreak());

// 1
body.push(H1("1 ПОСТАНОВКА ЗАДАЧИ"));
body.push(P("Вариант 9.6 соответствует разделу 9.6 «Lens Distortion» учебных материалов Х. Фарида «Digital Image Forensics» (Dartmouth College, 2012) [1]. В этом разделе приведена MATLAB-функция lensdistort, которая убирает радиальную дисторсию объектива с изображения, принимая за главную точку центр кадра."));
body.push(P("Цель работы – изучить радиальную дисторсию объектива как признак, используемый в цифровой форензике, реализовать алгоритм коррекции, исследовать его поведение при разных значениях параметра дисторсии и оценить пределы его применимости."));
body.push(P("Для достижения цели необходимо:", { keepNext: true }));
for (const t of [
  "изучить модель радиальной дисторсии и алгоритм из раздела 9.6;",
  "построить схему алгоритма и перенести программу из MATLAB на Python;",
  "проверить правильность переноса автоматическими тестами;",
  "исследовать на синтетическом изображении из прямых линий, как параметр K влияет на прямолинейность линий, и найти K без знания исходной сцены;",
  "исследовать работу алгоритма на фотографии и влияние порядка интерполяции и полей из нулей;",
  "составить три тестовых задания и сделать выводы.",
]) body.push(P("– " + t, { noIndent: false }));

// 2
body.push(H1("2 ТЕОРЕТИЧЕСКАЯ ЧАСТЬ"));
body.push(H2("2.1 Дисторсия объектива и её виды"));
body.push(P("Дисторсия – это геометрическая аберрация объектива, при которой изображение передаётся без искажения резкости, но с нарушением подобия: линейное увеличение зависит от расстояния до оптической оси. Прямые линии сцены, не проходящие через центр кадра, в результате получаются изогнутыми [2, 3]. В отечественной литературе подушкообразную дисторсию принято считать положительной, а бочкообразную – отрицательной [2]; тот же знак имеет параметр K в п. 2.2."));
body.push(P("Для большинства объективов дисторсия почти осесимметрична, поэтому её называют радиальной. Различают три основных вида:", { keepNext: true }));
body.push(P("– бочкообразная: увеличение убывает при удалении от центра, линии выгибаются наружу, углы изображения «втягиваются» к центру; типична для широкоугольных объективов и камер смартфонов;"));
body.push(P("– подушкообразная: увеличение растёт при удалении от центра, линии прогибаются внутрь, углы «растягиваются» наружу; типична для телеобъективов;"));
body.push(P("– усообразная (комбинированная): вблизи центра бочка, у краёв подушка; описывается членами более высокого порядка."));
body.push(P("Кроме радиальной бывает тангенциальная дисторсия, вызванная несоосностью линз (децентрировкой) [4]; в работе она не рассматривается."));

body.push(H2("2.2 Радиальная модель"));
body.push(P("Пусть центр кадра совпадает с главной точкой, ru – расстояние от центра до точки идеального изображения (без дисторсии), rd – расстояние до той же точки на реальном изображении. Классическая полиномиальная модель Брауна [3] записывается так:", { keepNext: true }));
body.push(formula([run("r"), run("d", { sub: true }), run(" = r"), run("u", { sub: true }), run(" · (1 + k"), run("1", { sub: true }), run("r"), run("u", { sub: true }), run("2", { sup: true }), run(" + k"), run("2", { sub: true }), run("r"), run("u", { sub: true }), run("4", { sup: true }), run(" + …),")], 1));
body.push(P("где k1, k2, … – коэффициенты дисторсии. При k1 < 0 получается бочка, при k1 > 0 – подушка. На практике часто хватает одного коэффициента k1. В библиотеке OpenCV модель записывается так же, с коэффициентами k1, k2, k3 при r², r⁴, r⁶ [15]; параметры находят калибровкой по изображениям шахматной доски [11, 15]."));
body.push(P("В разделе 9.6 книги [1] используется однопараметрическая модель в нормированных координатах. Координаты пикселя приводятся к диапазону [−1, 1] делением на половину размера кадра по каждой оси, радиус считается как r = √(x² + y²) (в углу кадра r² = 2). Исправленное изображение получается обратным отображением: значение в точке (x, y) берётся из исходного изображения в точке"));
body.push(formula([run("(x"), run("K", { sub: true }), run(", y"), run("K", { sub: true }), run(") = (x · (1 + K·r"), run("2", { sup: true }), run("), y · (1 + K·r"), run("2", { sup: true }), run(")).")], 2));
body.push(P("Параметр K выбирается вручную ползунком от −1 до 1. Если K < 0, то точка берётся ближе к центру, чем она лежит в исправленном кадре, – так исправляется бочка; если K > 0, исправляется подушка; при K = 0 изображение не меняется. Знак проверен в п. 5.1 расчётом. Пример из книги [1] согласуется с этим: для снимка кирпичной стены с бочкообразной дисторсией линии выпрямляются при K = −0,084."));
body.push(P("Если искажённое изображение получено по той же формуле с параметром Kd, то для исправления нужно решить уравнение q·(1 + Kd·|q|²) = p относительно q. В первом приближении q ≈ p·(1 − Kd·r²), то есть Kc ≈ −Kd. Точного решения в классе той же формулы нет, поэтому для сильной дисторсии значение Kc, лучше всего выпрямляющее линии, отличается от −Kd (п. 5.3)."));

body.push(H2("2.3 Коррекция как обратное отображение и интерполяция"));
body.push(P("Алгоритм использует обратное (backward) отображение: для каждого пикселя результата вычисляется, из какой точки исходного изображения он должен быть взят. Такой подход не оставляет «дыр» в результате, в отличие от переноса пикселей вперёд. Координаты (xK, yK) в общем случае не целые, поэтому значение находят интерполяцией соседних пикселей. В MATLAB используется кубическая свёртка [5] (interp2 с параметром 'cubic'). В Python-версии применён кубический B-сплайн [6]; допустимы также билинейная интерполяция и выбор ближайшего пикселя."));
body.push(P("Если источником оказывается точка вне исходного кадра, пиксель результата получает значение 0 (чёрный). Бочка исправляется растяжением кадра наружу, поэтому её углы выходят за исходные границы. Чтобы они не терялись, изображение предварительно дополняется нулевыми полями по 50 пикс. с каждой стороны."));

body.push(H2("2.4 Роль дисторсии в цифровой форензике"));
body.push(P("Параметры дисторсии зависят от оптики конкретной модели камеры, а у зум-объективов – ещё и от фокусного расстояния. Это позволяет использовать их как признак: в [7] предложено определять источник снимка по радиальной дисторсии его объектива. Кроме того, дисторсия должна быть согласованной по всему кадру: фрагмент, вставленный из другого снимка, может иметь другие параметры. Наконец, в форензике и измерениях по снимкам дисторсию надо убирать до анализа геометрии, иначе прямые линии (здания, разметка, оконные рамы) нельзя использовать как эталон прямизны. Критерий «прямые линии должны быть прямыми» лежит в основе методов автоматической оценки дисторсии по линиям сцены [8]; иной подход, не требующий линий в кадре, использует статистические признаки самого изображения [9]. Обзор современных методов исправления дисторсии, включая нейросетевые, дан в [14], а цифровая коррекция с автоматическим выбором объектов для оценки дисторсии описана в [13]."));

body.push(H2("2.5 Автоматическая оценка параметра K"));
body.push(P("В книге [1] K подбирается вручную. В работе добавлена автоматическая оценка по критерию [8]: после коррекции прямые линии сцены должны снова стать прямыми. В качестве меры используется среднее отклонение пикселей линии от наилучшей прямой, нормированное на расстояние между линиями. Нормировка нужна потому, что при K > 0 коррекция сжимает кадр и абсолютные отклонения в пикселях уменьшаются сами по себе, а не из-за выпрямления линий. Параметр K выбирается как минимум этой меры (п. 5.3). Оценка по одному снимку возможна и без явного выделения линий: в [12] для этого применено быстрое преобразование Хафа, оценивающее общую кривизну линий."));

// 3
body.push(H1("3 АЛГОРИТМ"));
body.push(H2("3.1 Схема алгоритма"));
body.push(P("Схема алгоритма коррекции дисторсии, составленная по ГОСТ 19.701-90, приведена на рисунке 1. Схема строится программой make_scheme.py (matplotlib), которую можно править и перезапускать; результат сохраняется в файле scheme_algorithm.png."));
body.push(...fig("scheme_algorithm.png", 300, "Схема алгоритма коррекции радиальной дисторсии"));
body.push(H2("3.2 Описание шагов"));
for (const [i, t] of [
  "Ввод изображения im размера Y×X с Z цветовыми каналами и параметра дисторсии K.",
  "Изображение дополняется нулевыми полями по 50 пикс. с каждой стороны, размер становится (Y + 100)×(X + 100).",
  "Строится сетка координат пикселей и нормируется: xramp = (i − xdim/2)/(xdim/2), yramp = (j − ydim/2)/(ydim/2).",
  "Для каждого узла сетки вычисляется радиус r = √(xramp² + yramp²).",
  "Строится новая сетка xrampK = xramp·(1 + K·r²), yrampK = yramp·(1 + K·r²).",
  "Для каждого канала изображение интерполируется в точках новой сетки; точки вне кадра получают значение 0.",
  "Выводятся изображение с полями и исправленное изображение.",
].entries()) body.push(P(`${i + 1}. ${t}`));
body.push(H2("3.3 Отличия реализации на Python от кода MATLAB"));
body.push(P("Логика вычислений сохранена. Отличия: во-первых, интерполяция выполняется функцией scipy.ndimage.map_coordinates [10] (B-сплайн порядка 3) вместо interp2 с кубической свёрткой, поэтому значения пикселей совпадают с MATLAB не побитно; во-вторых, вместо ползунка используется параметр K командной строки или аргумент функции; в-третьих, порядок интерполяции вынесен в параметр order (0, 1 или 3), что нужно для опыта 4."));

// 4
body.push(H1("4 ПРОГРАММНАЯ РЕАЛИЗАЦИЯ"));
body.push(P("Программа написана на Python 3.14 с использованием библиотек numpy, scipy, Pillow и matplotlib. Состав файлов приведён в таблице 1. Полные тексты программ lensdistort.m и lensdistort.py даны в приложениях А и Б, функция оценки прямолинейности – в приложении В; остальные файлы прилагаются к отчёту отдельно."));
body.push(...table("Состав программного комплекса", ["Файл", "Назначение"], [
  ["lensdistort.m", "оригинальный код MATLAB из книги [1] (редактируемый файл с кодом)"],
  ["lensdistort.py", "перенос на Python: функции lens_correct (коррекция), distort (искусственная дисторсия) и командная строка"],
  ["selftest.py", "автоматическая проверка переноса (5 проверок)"],
  ["experiments.py", "опыты 1–5: расчёт, таблицы .csv, рисунки .png, сводка summary.json"],
  ["make_scheme.py", "построение схемы алгоритма"],
], [2600, 6755], { leftCols: [0, 1] }));
body.push(P("Запуск коррекции одного изображения: python lensdistort.py вход.png выход.png -K -0.15. Для воспроизведения результатов отчёта выполняют по очереди selftest.py, experiments.py и make_scheme.py."));

// 5
body.push(H1("5 РЕЗУЛЬТАТЫ И АНАЛИЗ"));
body.push(H2("5.1 Проверка правильности переноса"));
body.push(P("Пять автоматических проверок из selftest.py выполнены успешно (таблица 2). Проверка знака K выполнена на вертикальной линии правее центра: у бочки концы линии ближе к центру, чем середина; у подушки – дальше."));
body.push(...table("Результаты самопроверки lensdistort.py", ["Проверка", "Результат"], [
  ["K = 0 не меняет изображение", "максимальная ошибка 1,6·10⁻¹²"],
  ["размер результата = исходный + поля по 50 пикс.", "120×160 → 220×260, 3 канала"],
  ["K = +0,3 (бочка)", "столбец линии в строке 100: 289, в середине: 295 – концы ближе к центру"],
  ["K = −0,3 (подушка)", "столбец линии в строке 100: 324, в середине: 311 – концы дальше от центра"],
  ["круговая проверка: искажение K = 0,15, затем коррекция K = −0,15", "СКО в центре кадра 2,08 из 255"],
], [4400, 4955], { leftCols: [0, 1] }));

body.push(H2("5.2 Опыт 1. Синтетическая сетка линий"));
body.push(P("Сцена – белые линии с гауссовым профилем (σ = 1,5 пикс.) на чёрном фоне, размер 1200×900: 9 вертикальных линий (шаг 120 пикс.) и 7 горизонтальных (шаг около 113 пикс.). Искажение создавалось той же функцией с параметрами Kd = ±0,10 и ±0,20 (Kd > 0 даёт бочку, Kd < 0 – подушку). На рисунке 2 показаны идеальная сцена, искажённая сетка (Kd = +0,20), результат коррекции с найденным K = −0,145 и слишком сильная коррекция K = −0,295. Красным пунктиром нанесены положения идеальных прямых."));
body.push(...fig("fig1_grid_before_after.png", 560, "Коррекция бочкообразной дисторсии на сетке (Kd = +0,20)"));
body.push(P("Центральные линии после коррекции совпадают с пунктиром, крайние остаются слегка изогнутыми: одного параметра K недостаточно, чтобы точно обратить преобразование. При K = −0,295 коррекция чрезмерна, и линии выгибаются в противоположную сторону."));
body.push(P("Тот же опыт выполнен на фотографии: поверх снимка нарисована такая же сетка прямых линий (рисунок 3). Фотография искажена бочкой с Kd = +0,20, значение K найдено тем же способом, по прямолинейности линий: K = −0,144, что близко к результату на чёрной сетке (−0,145). Отклонение линий от прямых упало с 3,85 % до 0,25 % расстояния между линиями. Вместе с линиями искажается и сама фотография, а после коррекции фигура обезьяны выглядит естественно; при K = −0,294 коррекция снова чрезмерна."));
body.push(...fig("monkey_grid_before_after.png", 560, "Коррекция бочкообразной дисторсии на фотографии с сеткой (Kd = +0,20)"));
body.push(P("Результаты перебора K для бочки и подушки показаны на рисунке 4."));
body.push(...fig("fig2_K_sweep_grid.png", 600, "Результат коррекции при разных значениях K (верхний ряд – бочка, нижний – подушка)"));

body.push(H2("5.3 Опыт 2. Оценка K по прямолинейности линий"));
body.push(P("Для каждой линии положение определялось по строкам (столбцам) с подпиксельным центроидом в окне ±8 пикс.; анализировалась центральная часть кадра (от 20 до 80 % длины). Через найденные точки проводилась наилучшая прямая, мерой служило среднеквадратичное отклонение от неё, нормированное на расстояние между соседними линиями и выраженное в процентах; по линиям бралась медиана, по двум направлениям – среднее. Значение K, дающее минимум меры, принималось за оценку (сетка с шагом 0,025 и уточнение в окрестности минимума). Код функции приведён в приложении В."));
body.push(...fig("fig3_straightness_vs_K.png", 540, "Прямолинейность линий после коррекции в зависимости от K"));
body.push(P("На графике (рисунок 5) у каждой кривой есть чёткий минимум; правее него мера растёт почти линейно. Левые ветви неровные: при сильном растяжении кадра часть линий выходит из окна анализа, и состав линий, по которым считается медиана, меняется. Результаты оценки приведены в таблице 3."));
body.push(...table("Оценка параметра K по прямолинейности линий", ["Kd (задано)", "Вид", "K (найдено)", "Kd + K", "Отклонение до коррекции, %", "Отклонение после, %"],
  est.map((r) => [fmt(num(r[0]), 2), r[1], fmt(num(r[2]), 3), fmt(num(r[3]), 3), fmt(num(r[4]), 2), fmt(num(r[5]), 2)]),
  [1350, 1300, 1450, 1200, 2205, 1850]));
body.push(P("Отклонение линий от прямых снижается с 2,0–3,8 % до 0,08–0,5 % расстояния между линиями, то есть примерно с 2,4–4,5 пикс. до 0,1–0,6 пикс. Найденное K по модулю близко к Kd, но равенства Kd + K = 0 нет: сумма растёт с силой искажения (0,017 для Kd = 0,10 и 0,124 для Kd = −0,20). Причина – в упрощении формулы (2): точное обратное преобразование содержит члены более высоких степеней r, а модель их не учитывает. Для подушки отличие больше, чем для бочки. В одномерной записи обратное преобразование – решение уравнения q + Kd·q³ = p, то есть q = p − Kd·p³ + 3·Kd²·p⁵ − …; при Kd > 0 члены ряда чередуют знак и частично гасят друг друга, а при Kd < 0 все они одного знака, поэтому отбрасывание старших членов даёт большую ошибку."));

body.push(H2("5.4 Опыт 3. Фотография"));
body.push(P(`В качестве реального изображения взята фотография размером ${summary.photo.size[0]}×${summary.photo.size[1]} пикс. (то же изображение, что и в лабораторной работе № 2). Оно искажено функцией distort с Kd = +0,20, затем исправлено при разных K; качество оценивалось пиковым отношением сигнал/шум (PSNR) между исправленным и исходным изображениями на участке, где при искажении не потеряно содержимое (${fmt(summary.photo.valid_area_share * 100, 1)} % площади кадра).`));
body.push(...fig("fig4_photo_before_after.png", 560, "Искажение фотографии (Kd = +0,20) и её коррекция"));
body.push(P(`Без коррекции PSNR равен ${fmt(summary.photo.psnr_distorted, 1)} дБ, при оптимальном K = ${fmt(summary.photo.K_best, 3)} – ${fmt(summary.photo.psnr_corrected, 1)} дБ. Зависимость PSNR от K показана на рисунке 7 и в таблице 4. Максимум достигается при K = ${fmt(summary.photo.K_best, 3)}, а не при −0,200: действует то же ограничение однопараметрической модели, что и в опыте 2. Остаточная разность (рисунок 6, правый нижний снимок) сосредоточена на контурах и в углах, где смещение точек наибольшее. Края исправленного кадра остаются чёрными (содержимое, потерянное при искажении, не восстанавливается). Фотография является студийным изображением без реальной дисторсии, поэтому опыт проверяет обратимость преобразования, а не работу с реальным объективом.`));
body.push(...fig("fig5_psnr_vs_K.png", 460, "Зависимость PSNR исправленной фотографии от K"));
const pickK = ["-0,25", "-0,2", "-0,175", "-0,15", "-0,125", "-0,1", "-0,05", "0,0", "0,05"];
body.push(...table("PSNR исправленной фотографии при разных значениях K (Kd = +0,20)", ["K", "PSNR, дБ"],
  pk.filter((r) => pickK.includes(r[0])).map((r) => [fmt(num(r[0]), 3), r[1]]), [3000, 3000]));

body.push(H2("5.5 Опыт 4. Порядок интерполяции"));
body.push(P(`При оптимальном K = ${fmt(summary.photo.K_best, 3)} коррекция выполнена с тремя способами интерполяции (таблица 5, рисунок 8).`));
body.push(...table("Влияние интерполяции на PSNR исправленной фотографии", ["Интерполяция", "PSNR, дБ"], interp.map((r) => [r[0], r[1]]), [5000, 3000], { leftCols: [0] }));
body.push(...fig("fig6_interpolation.png", 600, "Фрагмент исправленного изображения при разной интерполяции"));
body.push(P("Разница между способами не превышает 0,4 дБ; билинейная интерполяция в этом опыте даёт лучшее значение, чем кубическая, ближайший сосед – худшее и заметен ступеньками на наклонных контурах. Искажение в опыте создавалось кубической интерполяцией, а вероятно, билинейная слегка сглаживает остаточные ошибки, что и повышает PSNR; на резкость контуров она при этом влияет в худшую сторону. Вывод: на качество коррекции порядок интерполяции влияет заметно меньше, чем ошибка в параметре K."));

body.push(H2("5.6 Опыт 5. Поля из нулей"));
body.push(P(`Опыт показывает, зачем нужны поля по 50 пикс. На искажённой сетке (Kd = +0,20) выполнена коррекция с K = ${fmt(summary.padding.K, 3)} без полей и с полями (рисунок 9). Без полей концы линий, выходящие за исходный кадр, обрезаются. С полями ${fmt(summary.padding.percent_of_line_pixels_outside_original_frame, 1)} % пикселей линий оказываются за границей исходного кадра. Для этого значения K доля мала, но она растёт с ростом |K|, поскольку у бочки именно углы выходят за кадр больше всего.`));
body.push(...fig("fig7_padding.png", 560, "Коррекция без полей и с полями по 50 пикс."));

// 6
body.push(H1("6 ТЕСТОВЫЕ ЗАДАНИЯ"));
const opt = (t) => P(t, { noIndent: true, line: 300 });
body.push(P("Задание 1 (один правильный ответ). На рисунке 10 показана сетка с дисторсией. Какое значение параметра K в функции lensdistort следует задать, чтобы выпрямить её линии?", { keepNext: true, noIndent: true }));
body.push(...fig("grid_distorted_barrel.png", 300, "Сетка с бочкообразной дисторсией"));
body.push(opt("А) K < 0;"), opt("Б) K > 0;"), opt("В) K = 0;"), opt("Г) знак K не имеет значения, важен только модуль."));
body.push(P("Правильный ответ: А. У бочки точки лежат ближе к центру, чем в идеальной картине, поэтому в формуле (2) нужен множитель 1 + K·r² < 1, то есть K < 0.", { noIndent: true, before: 80, after: 160 }));

body.push(P("Задание 2 (несколько правильных ответов). Какие утверждения об алгоритме из раздела 9.6 верны? Выберите все верные.", { keepNext: true, noIndent: true }));
body.push(opt("А) главной точкой считается центр изображения;"));
body.push(opt("Б) перед преобразованием изображение дополняется нулевыми полями, чтобы при растяжении не терялись углы;"));
body.push(opt("В) алгоритм изменяет яркость пикселей, а не их положение;"));
body.push(opt("Г) параметр K автоматически определяется по спектру Фурье изображения."));
body.push(P("Правильные ответы: А и Б. В – неверно: алгоритм перемещает пиксели (меняет координаты выборки), яркости получаются интерполяцией. Г – неверно: в книге K задаётся вручную ползунком.", { noIndent: true, before: 80, after: 160 }));

body.push(P("Задание 3 (один правильный ответ). Мера прямолинейности линий (п. 2.5) делится на расстояние между соседними линиями. Для чего это сделано?", { keepNext: true, noIndent: true }));
body.push(opt("А) чтобы ускорить расчёт;"));
body.push(opt("Б) потому что линии имеют разную толщину;"));
body.push(opt("В) коррекция при K > 0 сжимает кадр, и отклонения в пикселях уменьшались бы сами по себе, а не из-за выпрямления линий;"));
body.push(opt("Г) так требует стандарт ГОСТ 19.701."));
body.push(P("Правильный ответ: В. Деление на расстояние между линиями делает меру независимой от масштаба изображения после коррекции.", { noIndent: true, before: 80, after: 160 }));

// 7
body.push(H1("7 ВЫВОДЫ"));
for (const t of [
  "Изучена радиальная дисторсия объектива и однопараметрическая модель из раздела 9.6 книги Фарида. Алгоритм построен на обратном отображении с интерполяцией; знак K подтверждён расчётом: K < 0 исправляет бочку, K > 0 – подушку.",
  "Программа с MATLAB перенесена на Python, правильность проверена пятью автоматическими проверками, включая круговую проверку «искажение – коррекция» (СКО 2,08 из 255).",
  "На синтетической сетке параметр K найден без знания исходной сцены по минимуму непрямолинейности линий: отклонение падает с 2,0–3,8 % до 0,08–0,5 % расстояния между линиями (до 0,1–0,6 пикс.). Найденное K близко к −Kd, но не равно ему, поскольку одной степени r² недостаточно для точного обращения преобразования; расхождение больше для подушки и для сильных искажений.",
  "На фотографии коррекция повышает PSNR с 11,0 до 21,7 дБ при K = −0,168 (искажение Kd = +0,20). Остаточные ошибки сосредоточены в углах и на контурах.",
  "Порядок интерполяции влияет на результат слабо (разброс PSNR до 0,4 дБ); нулевые поля нужны, чтобы при коррекции бочки не терялись крайние области кадра.",
  "Ограничения работы: алгоритм предполагает, что главная точка находится в центре кадра, и использует один коэффициент; опыты на реальных снимках с оптической дисторсией не проводились (фотография искажена искусственно). Следующий шаг – проверка на снимках с реальной камерой и добавление второго коэффициента k2.",
]) body.push(P("– " + t));

// Источники
body.push(H1("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"));
const src = [
  "Farid H. Digital Image Forensics [Электронный ресурс]. – Dartmouth College, 2012. – 199 p. – URL: www.cs.dartmouth.edu/farid (дата обращения: 09.11.2026).",
  "Дисторсия в оптике // Большая российская энциклопедия [Электронный ресурс]. – URL: https://bigenc.ru/c/distorsiia-v-optike-57966a (дата обращения: 09.11.2026).",
  "Brown D. C. Close-range camera calibration // Photogrammetric Engineering. – 1971. – Vol. 37, No. 8. – P. 855–866.",
  "Conrady A. E. Decentred lens-systems // Monthly Notices of the Royal Astronomical Society. – 1919. – Vol. 79, No. 5. – P. 384–390.",
  "Keys R. G. Cubic convolution interpolation for digital image processing // IEEE Transactions on Acoustics, Speech, and Signal Processing. – 1981. – Vol. 29, No. 6. – P. 1153–1160.",
  "Unser M. Splines: a perfect fit for signal and image processing // IEEE Signal Processing Magazine. – 1999. – Vol. 16, No. 6. – P. 22–38.",
  "Choi K. S., Lam E. Y., Wong K. K. Y. Automatic source camera identification using the intrinsic lens radial distortion // Optics Express. – 2006. – Vol. 14, No. 24. – P. 11551–11565.",
  "Devernay F., Faugeras O. Straight lines have to be straight: automatic calibration and removal of distortion from scenes of structured environments // Machine Vision and Applications. – 2001. – Vol. 13, No. 1. – P. 14–24.",
  "Farid H., Popescu A. C. Blind removal of lens distortion // Journal of the Optical Society of America A. – 2001. – Vol. 18, No. 9. – P. 2072–2078.",
  "SciPy documentation: scipy.ndimage.map_coordinates [Электронный ресурс]. – URL: docs.scipy.org (дата обращения: 09.11.2026).",
  "Zhang Z. A flexible new technique for camera calibration // IEEE Transactions on Pattern Analysis and Machine Intelligence. – 2000. – Vol. 22, No. 11. – P. 1330–1334.",
  "Kunina I. A., Gladilin S. A., Nikolaev D. P. Blind radial distortion compensation in a single image using fast Hough transform // Computer Optics. – 2016. – Vol. 40, No. 3. – P. 395–403. – DOI: 10.18287/2412-6179-2016-40-3-395-403.",
  "Титов Д. В., Ширабакина Т. А. Модуль цифровой коррекции дисторсии изображения // Известия высших учебных заведений. Приборостроение. – 2009. – Т. 52, № 2. – URL: https://pribor.ifmo.ru/file/article/4706.pdf (дата обращения: 09.11.2026).",
  "Fan J., Zhang J., Maybank S. J., Tao D. Wide-angle image rectification: a survey [Электронный ресурс] // arXiv:2011.12108. – 2020. – URL: https://arxiv.org/abs/2011.12108 (дата обращения: 09.11.2026).",
  "OpenCV: Camera Calibration [Электронный ресурс]. – URL: https://docs.opencv.org/3.4/dc/dbb/tutorial_py_calibration.html (дата обращения: 09.11.2026).",
];
src.forEach((t, i) => body.push(P(`${i + 1}. ${t}`, { noIndent: true, after: 60 })));

// Приложения
body.push(H1("ПРИЛОЖЕНИЕ А. Листинг lensdistort.m (MATLAB, оригинал из книги [1])", true));
body.push(code(codeM));
body.push(H1("ПРИЛОЖЕНИЕ Б. Листинг lensdistort.py (перенос на Python)", true));
body.push(code(codePy));
body.push(H1("ПРИЛОЖЕНИЕ В. Листинг функций оценки прямолинейности (фрагмент experiments.py)", true));
body.push(code(metricCode));

// ---------------------------------------------------------------- документ
const doc = new Document({
  creator: "Буланый С. Е.", title: "Отчёт по ЛР3. Форензика. Коррекция дисторсии объектива (вариант 9.6)",
  styles: {
    default: { document: { run: { font: FONT, size: 28 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: { titlePage: true, page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1701, right: 850 } } },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 24 })] })] }),
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
    },
    children: [...title, ...body],
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("записано", OUT, buf.length); });
