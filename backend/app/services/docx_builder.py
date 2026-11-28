from docx import Document
from docx.image.image import Image
from docx.shared import Pt, Cm, Mm, Inches, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime
import math
import os

from app.services.content import split_inline
from app.services.math_render import FormulaError, latex_to_omml
from app.services.report_outline import (
    Figure, Formula, Heading, Listing, References, Text,
    essay_people, is_essay, iter_report_blocks, signature_rows, text_lines,
)

# A4, margins 30/20/20/20 mm (ДСТУ 3008:2015)
TEXT_WIDTH = Mm(160)
TEXT_HEIGHT_PT = (297 - 40) * 72 / 25.4
LINE_PT = 14 * 1.15 * 1.5          # Times New Roman 14 pt, 1.5 line spacing
CHARS_PER_LINE = 68
CODE_LINE_PT = 12 * 1.13           # Courier New 12 pt, single spacing
CODE_CHARS_PER_LINE = 62
IMAGE_WIDTH = Inches(5)
IMAGE_MAX_HEIGHT = Mm(170)


class PageEstimator:
    """Rough layout model, used only for the page numbers cached in the TOC.
    Word recalculates exact numbers itself when it updates fields on open."""

    def __init__(self, start_page):
        self.page = start_page
        self.used = 0.0

    def add(self, height_pt, keep_together=False):
        if self.used + height_pt <= TEXT_HEIGHT_PT:
            self.used += height_pt
        elif keep_together or self.used == 0:
            self.page += 1
            self.used = min(height_pt, TEXT_HEIGHT_PT)
        else:
            total = self.used + height_pt
            self.page += int(total // TEXT_HEIGHT_PT)
            self.used = total % TEXT_HEIGHT_PT

    def text(self, text):
        for line in _lines(text):
            self.add(math.ceil(len(line) / CHARS_PER_LINE) * LINE_PT)

    def heading(self):
        # keep_with_next: heading jumps to the next page together with 2 lines of text
        if self.used + 3 * LINE_PT > TEXT_HEIGHT_PT:
            self.page += 1
            self.used = 0.0
        self.add(LINE_PT)

    def code(self, code):
        rows = sum(max(1, math.ceil(len(l.expandtabs(4)) / CODE_CHARS_PER_LINE)) for l in code.split('\n'))
        self.add(LINE_PT, keep_together=True)
        self.add(rows * CODE_LINE_PT)

    def image(self, height_emu):
        self.add(height_emu / 12700 + LINE_PT, keep_together=True)

    def new_page(self):
        if self.used > 0:
            self.page += 1
            self.used = 0.0


_lines = text_lines


def _insert_before_successors(parent, element, successor_tags):
    """Insert element respecting OOXML schema order (Word rejects out-of-order children)."""
    for child in parent:
        if child.tag in successor_tags:
            child.addprevious(element)
            return
    parent.append(element)


def _add_field(paragraph, instruction, cached_text, size=14):
    """Simple field (PAGE, PAGEREF ...) with a cached value shown until Word updates it."""
    runs = []
    for kind in ('begin', 'instr', 'separate', 'text', 'end'):
        run = paragraph.add_run()
        set_font(run, size=size)
        if kind == 'instr':
            el = OxmlElement('w:instrText')
            el.set(qn('xml:space'), 'preserve')
            el.text = f' {instruction} '
            run._r.append(el)
        elif kind == 'text':
            run.text = cached_text
        else:
            el = OxmlElement('w:fldChar')
            el.set(qn('w:fldCharType'), kind)
            run._r.append(el)
        runs.append(run)
    return runs


def _set_font_name(rpr_owner, name):
    """font.name only sets ascii/hAnsi; also pin eastAsia/cs so theme fonts don't leak in."""
    rpr_owner.font.name = name
    rFonts = rpr_owner.element.rPr.rFonts
    for attr in ('w:eastAsia', 'w:cs'):
        rFonts.set(qn(attr), name)
    for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        rFonts.attrib.pop(qn(attr), None)


def set_font(run, size=14, bold=False, name='Times New Roman'):
    _set_font_name(run, name)
    run.font.size = Pt(size)
    run.bold = bold


def create_base_doc():
    document = Document()

    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Mm(30)
    section.right_margin = Mm(20)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)

    normal = document.styles['Normal']
    _set_font_name(normal, 'Times New Roman')
    normal.font.size = Pt(14)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.first_line_indent = Cm(1.25)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    lang = OxmlElement('w:lang')
    lang.set(qn('w:val'), 'uk-UA')
    normal.element.get_or_add_rPr().append(lang)

    # Default heading styles are blue Calibri Light — make them plain black TNR
    for level in (1, 2, 3):
        style = document.styles[f'Heading {level}']
        _set_font_name(style, 'Times New Roman')
        style.font.size = Pt(14)
        style.font.bold = True
        style.font.italic = False
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.line_spacing = 1.5

    # "toc N" are Word's built-in TOC entry styles; Word reuses them when it rebuilds the TOC
    for level in (1, 2, 3):
        style = document.styles.add_style(f'toc {level}', WD_STYLE_TYPE.PARAGRAPH)
        style.element.set(qn('w:styleId'), f'TOC{level}')
        style.base_style = normal
        style.paragraph_format.first_line_indent = Cm(0)
        style.paragraph_format.left_indent = Cm((level - 1) * 0.5)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        style.paragraph_format.tab_stops.add_tab_stop(TEXT_WIDTH, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

    _add_page_numbers(section)

    # Ask Word to refresh the TOC / page numbers when the file is opened
    update = OxmlElement('w:updateFields')
    update.set(qn('w:val'), 'true')
    _insert_before_successors(document.settings.element, update, {
        qn(f'w:{t}') for t in (
            'hdrShapeDefaults', 'footnotePr', 'endnotePr', 'compat', 'docVars', 'rsids',
            'attachedSchema', 'themeFontLang', 'clrSchemeMapping', 'doNotIncludeSubdocsInStats',
            'doNotAutoCompressPictures', 'forceUpgrade', 'captions', 'readModeInkLockDown',
            'smartTagType', 'shapeDefaults', 'doNotEmbedSmartTags', 'decimalSymbol', 'listSeparator',
        )
    } | {'{http://schemas.openxmlformats.org/officeDocument/2006/math}mathPr',
         '{http://schemas.openxmlformats.org/schemaLibrary/2006/main}schemaLibrary'})

    return document


def _add_page_numbers(section):
    """Page number in the top right corner; the title page is counted but not numbered."""
    section.different_first_page_header_footer = True
    section.first_page_header.is_linked_to_previous = False
    paragraph = section.header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.0
    _add_field(paragraph, 'PAGE', '2')


def _centered(document, text, bold=False, size=14):
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    if text:
        run = p.add_run(text)
        set_font(run, size=size, bold=bold)
    return p


def _remove_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)
    for old in tblPr.findall(qn('w:tblBorders')):
        tblPr.remove(old)
    tblBorders = OxmlElement('w:tblBorders')
    for name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{name}')
        el.set(qn('w:val'), 'none')
        el.set(qn('w:sz'), '0')
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), 'auto')
        tblBorders.append(el)
    _insert_before_successors(tblPr, tblBorders, {
        qn(f'w:{t}') for t in ('shd', 'tblLayout', 'tblCellMar', 'tblLook', 'tblCaption', 'tblDescription')
    })


def add_title_page(document, report, student_name=""):
    year = datetime.now().year

    _centered(document, "Міністерство освіти і науки України")
    _centered(document, "Харківський національний університет радіоелектроніки")
    _centered(document, "")
    _centered(document, f"Кафедра {(getattr(report, 'department', '') or 'штучного інтелекту').strip()}")

    for _ in range(4):
        _centered(document, "")

    _centered(document, f"Дисципліна «{report.discipline}»")
    _centered(document, report.title)

    for _ in range(5):
        _centered(document, "")

    # Виконав / Прийняла side-by-side with borderless table
    rows_data = signature_rows(report, student_name)
    table = document.add_table(rows=len(rows_data), cols=2)
    _remove_table_borders(table)

    for row_idx, (left, right) in enumerate(rows_data):
        for col_idx, text in enumerate((left, right)):
            cell = table.cell(row_idx, col_idx)
            para = cell.paragraphs[0]
            para.paragraph_format.first_line_indent = Cm(0)
            para.paragraph_format.space_before = Pt(0)
            para.paragraph_format.space_after = Pt(0)
            run = para.add_run(text)
            set_font(run)

    for _ in range(max(2, 6 - len(rows_data))):
        _centered(document, "")

    _centered(document, f"Харків – {year}")

    document.add_page_break()


def _year(report):
    """Year from the essay date ("13.10.2025"), else the current one."""
    digits = (getattr(report, "work_date", "") or "").strip()[-4:]
    return digits if digits.isdigit() else str(datetime.now().year)


def _hint(document, text):
    """Small caption under a title page field: "(тема реферату)"."""
    p = _centered(document, text, size=10)
    p.paragraph_format.line_spacing = 1.0
    return p


def _field_line(document, label, value):
    """«label ______value______» — the value underlined to the right margin, as in the
    методичка template (underlined tabs make the line)."""
    p = document.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    stops = p.paragraph_format.tab_stops
    stops.add_tab_stop(Mm(92) if label else Mm(80), WD_TAB_ALIGNMENT.CENTER)
    stops.add_tab_stop(TEXT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    if label:
        set_font(p.add_run(f"{label} "))
    for text in ("\t", value or "", "\t"):
        run = p.add_run(text)
        set_font(run)
        run.underline = True
    return p


def add_title_page_essay(document, report, student_name=""):
    """Title page of a реферат (template ФШІ ІТШ)."""
    _centered(document, "Міністерство освіти і науки України")
    _centered(document, "Харківський національний університет радіоелектроніки")
    for _ in range(2):
        _centered(document, "")
    _field_line(document, "Факультет", (getattr(report, "faculty", "") or "").strip())
    _field_line(document, "Кафедра", (getattr(report, "department", "") or "").strip())
    for _ in range(3):
        _centered(document, "")
    _centered(document, "РЕФЕРАТ", bold=True, size=16)
    _centered(document, "")
    _field_line(document, "на тему:", report.title)
    _hint(document, "(тема реферату)")
    _centered(document, "")
    _field_line(document, "", report.discipline)
    _hint(document, "(дисципліна)")
    for _ in range(2):
        _centered(document, "")

    did, lines, checked, teacher = essay_people(report, student_name)
    for k, line in enumerate(lines):
        _field_line(document, did if k == 0 else " " * len(did), line)
        _hint(document, "(дата, група, прізвище, ініціали)")
    _centered(document, "")
    _field_line(document, checked, teacher)
    _hint(document, "(посада, прізвище, ініціали)")

    # Push "Харків 2025 р." to the bottom of the page
    for _ in range(max(1, 6 - 2 * len(lines))):
        _centered(document, "")
    _centered(document, f"Харків {_year(report)} р.")
    document.add_page_break()


def add_table_of_contents(document, page_break=True):
    """Adds the ЗМІСТ title and returns a placeholder paragraph; entries are filled in by
    fill_table_of_contents() once the body is built and heading pages are known."""
    _centered(document, "ЗМІСТ", bold=True)
    placeholder = document.add_paragraph()
    if page_break:
        document.add_page_break()
    return placeholder


def start_numbered_section(document):
    """Essay: the title page and ЗМІСТ are counted but not numbered — numbers start
    with ВСТУП. A new section without the page number field before it does that."""
    first = document.sections[0]
    for p in first.header.paragraphs:
        for r in list(p._p):
            if r.tag == qn('w:r'):
                p._p.remove(r)
    first.different_first_page_header_footer = False
    body = document.add_section(WD_SECTION.NEW_PAGE)
    body.header.is_linked_to_previous = False
    body.different_first_page_header_footer = False
    paragraph = body.header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.0
    _add_field(paragraph, 'PAGE', '3')


def fill_table_of_contents(placeholder, headings):
    """headings: list of (text, level, bookmark, page). Mirrors the XML Word itself writes:
    one TOC field spanning all entry paragraphs, each entry a hyperlink with a PAGEREF."""
    entries = []
    for text, level, bookmark, page in headings:
        p = placeholder.insert_paragraph_before(style=f'toc {level}')
        runs = [p.add_run(text), p.add_run('\t')]
        for run in runs:
            set_font(run)
        runs += _add_field(p, f'PAGEREF {bookmark} \\h', str(page))

        link = OxmlElement('w:hyperlink')
        link.set(qn('w:anchor'), bookmark)
        link.set(qn('w:history'), '1')
        for run in runs:
            link.append(run._r)
        p._p.append(link)
        entries.append(p)

    first, last = entries[0], entries[-1]
    field_start = []
    for kind in ('begin', 'instr', 'separate'):
        r = OxmlElement('w:r')
        if kind == 'instr':
            el = OxmlElement('w:instrText')
            el.set(qn('xml:space'), 'preserve')
            el.text = ' TOC \\o "1-3" \\h \\z \\u '
        else:
            el = OxmlElement('w:fldChar')
            el.set(qn('w:fldCharType'), kind)
        r.append(el)
        field_start.append(r)
    hyperlink = first._p.find(qn('w:hyperlink'))
    for r in field_start:
        hyperlink.addprevious(r)

    r_end = OxmlElement('w:r')
    fc = OxmlElement('w:fldChar')
    fc.set(qn('w:fldCharType'), 'end')
    r_end.append(fc)
    last._p.append(r_end)

    placeholder._p.getparent().remove(placeholder._p)


def add_heading(document, text, level=1, bookmark=None, new_page=False, space_after=False):
    """Use Word built-in heading styles so the TOC field picks them up."""
    paragraph = document.add_paragraph(style=f'Heading {level}')
    paragraph.paragraph_format.space_before = Pt(0)
    # Essay: "між заголовком і текстом має бути пустий рядок"
    paragraph.paragraph_format.space_after = Pt(LINE_PT) if space_after else Pt(0)
    paragraph.paragraph_format.page_break_before = new_page
    paragraph.paragraph_format.keep_with_next = True

    if level == 1:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Cm(0)
        run = paragraph.add_run(text.upper())
    else:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.first_line_indent = Cm(1.25)
        run = paragraph.add_run(text)

    set_font(run, bold=True)

    if bookmark:
        bm_id = str(int(bookmark.removeprefix('_Toc')))
        start = OxmlElement('w:bookmarkStart')
        start.set(qn('w:id'), bm_id)
        start.set(qn('w:name'), bookmark)
        end = OxmlElement('w:bookmarkEnd')
        end.set(qn('w:id'), bm_id)
        run._r.addprevious(start)
        run._r.addnext(end)
    return paragraph


def _append_math(paragraph, latex):
    """Inline Word equation; a formula that cannot be converted is kept as LaTeX text."""
    try:
        paragraph._p.append(latex_to_omml(latex))
    except FormulaError:
        run = paragraph.add_run(latex)
        set_font(run, name='Cambria Math')
        run.italic = True


def add_paragraph_text(document, text):
    """Each non-empty line becomes its own paragraph: manual line breaks inside a
    justified paragraph make Word stretch the line across the full width.
    $...$ inside a line becomes an inline Word equation."""
    paragraph = None
    for line in _lines(text):
        paragraph = document.add_paragraph()
        for kind, value in split_inline(line):
            if kind == "math":
                _append_math(paragraph, value)
            elif value:
                set_font(paragraph.add_run(value))
    return paragraph


def add_formula(document, latex, number, spaced=True):
    """Display formula: centred, its number "(2.1)" at the right margin (методичка)."""
    p = document.add_paragraph()
    fmt = p.paragraph_format
    fmt.first_line_indent = Cm(0)
    fmt.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fmt.space_before = Pt(LINE_PT) if spaced else Pt(6)
    fmt.space_after = Pt(LINE_PT) if spaced else Pt(6)
    fmt.tab_stops.add_tab_stop(Mm(80), WD_TAB_ALIGNMENT.CENTER)
    fmt.tab_stops.add_tab_stop(TEXT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    set_font(p.add_run("\t"))
    _append_math(p, latex)
    set_font(p.add_run(f"\t({number})"))
    return p


def add_references(document, items):
    paragraph = None
    for n, item in enumerate(items, start=1):
        paragraph = document.add_paragraph()
        set_font(paragraph.add_run(f"{n}. {item}"))
    return paragraph

def add_listing(document, code, listing_number, title):
    caption = document.add_paragraph()
    caption_run = caption.add_run(f"Лістинг {listing_number} – {title}")
    set_font(caption_run)
    caption.paragraph_format.first_line_indent = Cm(0)
    caption.paragraph_format.keep_with_next = True

    code_paragraph = document.add_paragraph()
    code_run = code_paragraph.add_run(code.replace('\r\n', '\n').rstrip('\n'))
    set_font(code_run, size=12, name='Courier New')
    code_paragraph.paragraph_format.first_line_indent = Cm(0)
    code_paragraph.paragraph_format.line_spacing = 1.0
    code_paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return code_paragraph


def image_size(image_path):
    """5 inches wide, but tall screenshots are capped so they fit on one page."""
    img = Image.from_file(image_path)
    height = int(IMAGE_WIDTH * img.px_height / img.px_width)
    if height > IMAGE_MAX_HEIGHT:
        return {'height': IMAGE_MAX_HEIGHT}
    return {'width': IMAGE_WIDTH}


def image_height(image_path):
    img = Image.from_file(image_path)
    size = image_size(image_path)
    return size.get('height') or int(IMAGE_WIDTH * img.px_height / img.px_width)


def add_image(document, image_path, image_number, caption_text, spaced=False):
    img_paragraph = document.add_paragraph()
    if spaced:  # essay: blank line before the figure and after its caption
        img_paragraph.paragraph_format.space_before = Pt(LINE_PT)
    img_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    img_paragraph.paragraph_format.first_line_indent = Cm(0)
    img_paragraph.paragraph_format.line_spacing = 1.0
    img_paragraph.paragraph_format.keep_with_next = True
    run = img_paragraph.add_run()
    run.add_picture(image_path, **image_size(image_path))

    caption = document.add_paragraph()
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.first_line_indent = Cm(0)
    caption_run = caption.add_run(f"Рисунок {image_number} – {caption_text}")
    set_font(caption_run)
    if spaced:
        caption.paragraph_format.space_after = Pt(LINE_PT)
    return caption

def apply_toc_pages(docx_path, pages):
    """Replace the estimated page numbers cached in the TOC with the ones from the
    PDF layout (pdf_builder), so Word no longer needs to update fields."""
    document = Document(docx_path)
    for instr in document.element.body.iter(qn('w:instrText')):
        parts = (instr.text or '').split()
        if len(parts) < 2 or parts[0] != 'PAGEREF' or parts[1] not in pages:
            continue
        # The cached result is the first text run after the field's "separate" mark
        run, separated = instr.getparent().getnext(), False
        while run is not None:
            fld = run.find(qn('w:fldChar'))
            kind = fld.get(qn('w:fldCharType')) if fld is not None else None
            if kind == 'end':
                break
            if kind == 'separate':
                separated = True
            elif separated and run.find(qn('w:t')) is not None:
                run.find(qn('w:t')).text = str(pages[parts[1]])
                break
            run = run.getnext()

    for update in document.settings.element.findall(qn('w:updateFields')):
        document.settings.element.remove(update)
    document.save(docx_path)


def build_report_docx(report, images=None, student_name=""):
    essay = is_essay(report)
    document = create_base_doc()
    if essay:
        add_title_page_essay(document, report, student_name)
        toc_placeholder = add_table_of_contents(document, page_break=False)
        start_numbered_section(document)
    else:
        add_title_page(document, report, student_name)
        toc_placeholder = add_table_of_contents(document)

    # Body starts after the title page and the TOC page(s)
    toc_lines = 4 + sum(1 + len(sec.get('subsections') or []) for sec in report.sections or [])
    toc_pages = math.ceil(toc_lines * LINE_PT / TEXT_HEIGHT_PT)
    pages = PageEstimator(start_page=2 + toc_pages)
    toc_headings = []

    for block in iter_report_blocks(report, images):
        if isinstance(block, Heading):
            if block.new_page:
                pages.new_page()
            pages.heading()
            if block.space_after:
                pages.add(LINE_PT)
            toc_headings.append((block.toc_text, block.level, block.bookmark, pages.page))
            add_heading(document, block.text, level=block.level, bookmark=block.bookmark,
                        new_page=block.new_page, space_after=block.space_after)
        elif isinstance(block, Text):
            add_paragraph_text(document, block.text)
            pages.text(block.text)
        elif isinstance(block, Listing):
            add_listing(document, block.code, block.number, block.title)
            pages.code(block.code)
        elif isinstance(block, Figure):
            add_image(document, block.path, block.number, block.caption, spaced=essay)
            pages.image(image_height(block.path))
        elif isinstance(block, Formula):
            add_formula(document, block.latex, block.number, spaced=essay)
            pages.add(3 * LINE_PT if essay else 2 * LINE_PT, keep_together=True)
        elif isinstance(block, References):
            add_references(document, block.items)
            pages.text("\n".join(block.items))

    fill_table_of_contents(toc_placeholder, toc_headings)

    output_dir = os.getenv("GENERATED_DIR", "/app/generated")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"report_{report.id}.docx")
    document.save(path)
    return path
