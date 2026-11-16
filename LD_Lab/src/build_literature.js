const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, BorderStyle,
  ShadingType, TableLayoutType, HeadingLevel, LineRuleType, ExternalHyperlink, VerticalAlign,
} = require("docx");

const OUT = process.argv[2];
const FONT = "Times New Roman";
const W = 9355;

const r = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 26, bold: o.b, italics: o.i, color: o.color });
const link = (t, url, size = 22) => new ExternalHyperlink({ link: url, children: [new TextRun({ text: t, font: FONT, size, color: "0563C1", underline: { type: "single" } })] });
const P = (content, o = {}) => new Paragraph({
  alignment: o.align || AlignmentType.JUSTIFIED,
  indent: o.noIndent ? undefined : { firstLine: 709 },
  spacing: { line: 320, lineRule: LineRuleType.AUTO, before: o.before || 0, after: o.after === undefined ? 100 : o.after },
  keepNext: o.keepNext,
  children: typeof content === "string" ? [r(content, { size: o.size, b: o.b, i: o.i })] : content,
});
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 160 }, keepNext: true, children: [r(t, { b: true, size: 30 })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, keepNext: true, children: [r(t, { b: true, size: 26 })] });

const bd = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: bd, bottom: bd, left: bd, right: bd };
function cell(children, w, hdr) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders, verticalAlign: VerticalAlign.TOP,
    shading: hdr ? { type: ShadingType.CLEAR, fill: "E7E6E6", color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children,
  });
}
const cp = (content, o = {}) => new Paragraph({ spacing: { after: 40 }, alignment: o.align || AlignmentType.LEFT,
  children: typeof content === "string" ? [r(content, { size: 21, b: o.b })] : content });

// ---------------------------------------------------------------- литература
const widths = [420, 3700, 2735, 2500];
const lit = [
  // [№, описание, зачем нужно, ссылка[текст,url], статус]
  ["Farid H., Popescu A. C. Blind removal of lens distortion // J. Opt. Soc. Am. A. 2001. Vol. 18, No. 9. P. 2072–2078.",
    "Авторы книги из вашего источника: дисторсия порождает в спектре изображения высшие корреляции, K находят, минимизируя их. Про форензику и автоматическую оценку K.",
    ["DOI 10.1364/JOSAA.18.002072", "https://doi.org/10.1364/JOSAA.18.002072"], "данные подтверждены"],
  ["Devernay F., Faugeras O. Straight lines have to be straight: automatic calibration and removal of distortion from scenes of structured environments // Machine Vision and Applications. 2001. Vol. 13, No. 1. P. 14–24.",
    "Метод «прямые линии должны быть прямыми» – именно этот критерий использован в опыте 2 отчёта.",
    ["Springer, DOI 10.1007/PL00013269", "https://link.springer.com/doi/10.1007/PL00013269"], "данные подтверждены"],
  ["Brown D. C. Close-range camera calibration // Photogrammetric Engineering. 1971. Vol. 37, No. 8. P. 855–866.",
    "Классика: полиномиальная модель радиальной и тангенциальной дисторсии, метод «отвеса» (plumb line). Основа формулы (1) отчёта.",
    ["полный текст нужно искать через библиотеку / ASPRS", "https://asprs.org"], "данные подтверждены"],
  ["Choi K. S., Lam E. Y., Wong K. K. Y. Automatic source camera identification using the intrinsic lens radial distortion // Optics Express. 2006. Vol. 14, No. 24. P. 11551–11565.",
    "Форензика: определение камеры по радиальной дисторсии объектива (классификатор SVM, 5 камер). Подтверждает пункт 2.4 отчёта.",
    ["DOI 10.1364/oe.14.011551", "https://doi.org/10.1364/oe.14.011551"], "DOI подтверждён; страницы сверьте"],
  ["Zhang Z. A flexible new technique for camera calibration // IEEE Trans. Pattern Analysis and Machine Intelligence. 2000. Vol. 22, No. 11. P. 1330–1334.",
    "Стандартная калибровка по шахматной доске с учётом радиальной дисторсии; на ней построен cv2.calibrateCamera.",
    ["DOI 10.1109/34.888718", "https://doi.org/10.1109/34.888718"], "данные подтверждены"],
  ["Fan J., Zhang J., Maybank S. J., Tao D. Wide-angle image rectification: a survey. arXiv:2011.12108, 2020 (v2 – 2021).",
    "Свежий обзор методов исправления дисторсии (на геометрии и на нейросетях) – для раздела «современное состояние».",
    ["arXiv:2011.12108", "https://arxiv.org/abs/2011.12108"], "данные подтверждены"],
  ["OpenCV: Camera Calibration (документация, модель k1, k2, p1, p2, k3).",
    "Как та же дисторсия описывается в практических библиотеках (коэффициенты k1, k2, k3 при r², r⁴, r⁶).",
    ["docs.opencv.org", "https://docs.opencv.org/3.4/dc/dbb/tutorial_py_calibration.html"], "страница существует"],
  ["Keys R. G. Cubic convolution interpolation for digital image processing // IEEE Trans. ASSP. 1981. Vol. 29, No. 6. P. 1153–1160.",
    "Кубическая свёртка – та интерполяция, которая стоит в interp2(...,'cubic') из книги.",
    ["DOI 10.1109/TASSP.1981.1163711", "https://doi.org/10.1109/TASSP.1981.1163711"], "данные подтверждены"],
  ["Unser M. Splines: a perfect fit for signal and image processing // IEEE Signal Processing Magazine. 1999. Vol. 16, No. 6. P. 22–38.",
    "Кубические B-сплайны – интерполяция, использованная в Python-версии.",
    ["DOI 10.1109/79.799930", "https://doi.org/10.1109/79.799930"], "данные подтверждены"],
  ["Conrady A. E. Decentred lens-systems // Monthly Notices of the Royal Astronomical Society. 1919. Vol. 79, No. 5. P. 384–390.",
    "Историческая работа о тангенциальной дисторсии (децентрировка линз). Название в оригинале пишется «Decentred».",
    ["DOI 10.1093/mnras/79.5.384", "https://doi.org/10.1093/mnras/79.5.384"], "данные подтверждены"],
];
const rus = [
  ["Титов Д. В., Ширабакина Т. А. Модуль цифровой коррекции дисторсии изображения // Известия вузов. Приборостроение. 2009. Т. 52, № 2.",
    "На русском: автоматический выбор объектов, оценка коэффициента радиальной дисторсии, перенос координат пикселей и яркостная коррекция.",
    ["pribor.ifmo.ru (PDF)", "https://pribor.ifmo.ru/file/article/4706.pdf"], "авторов и страницы сверьте по PDF"],
  ["Kunina I. A., Gladilin S. A., Nikolaev D. P. Blind radial distortion compensation in a single image using fast Hough transform // Компьютерная оптика. 2016. Т. 40, № 3. С. 395–403.",
    "На русском журнале: оценка параметров дисторсии по одному снимку без калибровки (преобразование Хафа). Ближе всего к автоматической оценке K из вашего опыта 2.",
    ["DOI 10.18287/2412-6179-2016-40-3-395-403", "https://www.computeroptics.ru/eng/KO/Annot/KO40-3/400312.html"], "данные подтверждены"],
  ["Дисторсия в оптике // Большая российская энциклопедия.",
    "Определение дисторсии по-русски: подушкообразная считается положительной, бочкообразная – отрицательной; для аэросъёмки допуск порядка 0,01 %.",
    ["bigenc.ru", "https://bigenc.ru/c/distorsiia-v-optike-57966a"], "страница существует"],
];
function litTable(rows, startN) {
  return new Table({
    width: { size: W, type: WidthType.DXA }, layout: TableLayoutType.FIXED, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: ["№", "Источник", "Зачем нужен", "Ссылка / статус"].map((h, i) => cell([cp(h, { b: true, align: AlignmentType.CENTER })], widths[i], true)) }),
      ...rows.map((x, i) => new TableRow({ cantSplit: true, children: [
        cell([cp(String(startN + i), { align: AlignmentType.CENTER })], widths[0]),
        cell([cp(x[0])], widths[1]),
        cell([cp(x[1])], widths[2]),
        cell([new Paragraph({ spacing: { after: 40 }, children: [link(x[2][1].replace(/^https?:\/\//, ""), x[2][1], 18)] }), cp([r(x[3], { size: 19, i: true })])], widths[3]),
      ] })),
    ],
  });
}

// ---------------------------------------------------------------- код
const codeText = `function [imK] = lensdistort( filename )
if( isempty( get( gcf, 'UserData' ) ) )
  h = uicontrol;   % элемент интерфейса: ползунок величины дисторсии
  set( h, 'Style', 'slider' );
  set( h, 'Position', [20 20 200 20] );
  set( h, 'Value', 0, 'Min', -1, 'Max', 1 );
  set( h, 'SliderStep', [0.001 0.01] );
  set( h, 'Callback', sprintf( 'lensdistort(''%s'');', filename ) );
  set( gcf, 'UserData', h );
end
h = get( gcf, 'UserData' );
K = get( h, 'Value' );
% дисторсия объектива
im = double( imread( filename ) );
[ydim,xdim,zdim] = size( im );
impad = zeros( ydim+100, xdim+100, zdim );
impad(51:ydim+50,51:xdim+50,:) = im;   % дополнить нулями
im = impad;                            % дополнить нулями
[ydim,xdim,zdim] = size( im );
[xramp,yramp] = meshgrid( [1:xdim]-xdim/2, [1:ydim]-ydim/2 );  % сетка координат
xramp = xramp / (xdim/2);              % нормировка
yramp = yramp / (ydim/2);              % нормировка
rad = sqrt( xramp.^2 + yramp.^2 );     % расстояние до центра
xrampK = xramp .* (1 + K*rad.^2);      % новая сетка координат
yrampK = yramp .* (1 + K*rad.^2);      % новая сетка координат
imK = zeros( ydim, xdim, zdim );       % заготовка нового изображения
for z = 1 : zdim                       % убрать дисторсию по каждому каналу
  imK(:,:,z) = interp2( xramp, yramp, im(:,:,z), xrampK, yrampK, 'cubic' );
end
imshow( uint8([im imK]) );             % слева исходное, справа исправленное
title( K );                            % значение K в заголовке`;
function code(text) {
  return new Table({
    width: { size: W, type: WidthType.DXA }, layout: TableLayoutType.FIXED, columnWidths: [W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: W, type: WidthType.DXA }, borders, shading: { type: ShadingType.CLEAR, fill: "F5F5F5", color: "auto" },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: text.split("\n").map((l) => new Paragraph({ spacing: { line: 240, after: 0 }, children: [new TextRun({ text: l === "" ? " " : l, font: "Courier New", size: 18 })] })),
    })] })],
  });
}

const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [r("ЛР3, вариант 9.6 (Lens Distortion)", { b: true, size: 32 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [r("Дополнительная литература и перевод раздела 9.6", { size: 28 })] }),

  H1("1. Дополнительная литература"),
  P("Ниже – источники, найденные по теме «радиальная дисторсия объектива и её применение в форензике». Выходные данные сверялись с каталогами и страницами издателей; в последнем столбце указано, что подтверждено. Полные тексты я не скачивал: у большинства статей доступ платный или через библиотеку университета, у открытых (arXiv, «Компьютерная оптика», «Приборостроение») ссылки ведут прямо на страницу.", {}),
  H2("1.1. Зарубежные источники"),
  litTable(lit, 1),
  H2("1.2. Источники на русском языке"),
  litTable(rus, lit.length + 1),
  H2("1.3. Что стоит исправить в уже сданном отчёте"),
  P("В списке источников отчёта пункт 2 – Ландсберг Г. С. «Оптика» (Физматлит, 2003). Поиск не нашёл страницы этого издания: в справочниках встречается 4-е издание 1957 г. (общий курс физики, т. 3). Либо проверьте книгу по каталогу библиотеки, либо замените пункт 2 на статью «Дисторсия в оптике» (Большая российская энциклопедия) и на работу Титова и Ширабакиной. Остальные источники отчёта (3–9) совпали с найденными данными: Brown, Conrady, Keys, Unser, Choi и др., Devernay и Faugeras, Farid и Popescu.", {}),
  P("Дополнительно можно добавить в отчёт Zhang (2000), Kunina и др. (2016) и обзор Fan и др. (2020) – они закрывают разделы 2.4 и 2.5.", {}),

  new Paragraph({ children: [], pageBreakBefore: true }),
  H1("2. Перевод раздела 9.6 «Lens Distortion» (Farid H. Digital Image Forensics, стр. 157–158)"),
  P([r("Оригинал: ", { b: true }), r("Hany Farid. Digital Image Forensics. Dartmouth College, 2012. Раздел 9.6, стр. 157–158. Файл «Digital Image Forensics.pdf» в вашей папке «Загрузки»."), ], { noIndent: true }),
  H2("9.6 Дисторсия объектива"),
  P("Этот код убирает дисторсию объектива с изображения, считая главной точкой центр изображения. Ползунок в левом нижнем углу задаёт величину дисторсии (K); числовое значение выводится в заголовке изображения. Слева показано исходное изображение, справа – исправленное."),
  P([r("[Рисунок в книге: фотография кирпичной стены. Слева – исходный снимок с искривлёнными линиями кладки, справа – исправленный; в заголовке изображения указано значение K = −0,084. После исправления кладка прямая, а края кадра растянуты и по краям появились чёрные участки.]", { i: true })], { noIndent: true }),
  P("Код функции (стр. 158). Логика кода не менялась; комментарии в оригинале на английском, здесь переведены:", { noIndent: true, keepNext: true }),
  code(codeText),
  H2("Пояснения к переводу"),
  P("1. Теории в разделе нет: книга содержит один абзац описания и код. Теорию (виды дисторсии, формула, интерполяция) приходится брать из других источников; в отчёте она написана в разделе 2 на основе литературы выше.", {}),
  P("2. Комментарий оригинала «normalize into [0,1]» неточен: после вычитания xdim/2 и деления на xdim/2 координаты лежат в диапазоне [−1, 1]. В переводе оставлено «нормировка».", {}),
  P("3. Пример из книги подтверждает знак параметра: у снимка с бочкообразной дисторсией выпрямление получено при отрицательном K (−0,084), как и в нашей работе.", {}),
  P("4. Размер «50 пикселей» в строке impad(51:ydim+50, …) – это поля, которые добавляются, чтобы углы исправленного изображения не обрезались.", {}),
];

const doc = new Document({
  creator: "Буланый С. Е.", title: "ЛР3, вариант 9.6: литература и перевод",
  styles: {
    default: { document: { run: { font: FONT, size: 26 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 30, bold: true, color: "000000" }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 26, bold: true, color: "000000" }, paragraph: { outlineLevel: 1 } },
    ],
  },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1701, right: 850 } } }, children: body }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("записано", b.length); });
