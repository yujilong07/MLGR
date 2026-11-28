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
    Figure, Formula, Heading, Listing, References, Table, Text,
    doc_style, iter_report_blocks, text_lines,
)
from app.services.course_pages import (
    calendar_rows, course_words, report_meta_value, supervisors, task_fields, task_heading_lines, wants_task_sheet,
)
from app.services.templates import resolve_title_page

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


def create_base_doc(style=None):
    document = Document()
    right = style.right_margin_mm if style else 20
    page_pt = style.page_number_pt if style else 14

    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Mm(30)
    section.right_margin = Mm(right)
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
    # "забороняється переносити останній рядок абзацу на наступну сторінку"
    normal.paragraph_format.widow_control = True
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
        style.paragraph_format.tab_stops.add_tab_stop(Mm(210 - 30 - right), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

    _add_page_numbers(section, page_pt)

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


def _add_page_numbers(section, size=14):
    """Page number in the top right corner; the title page is counted but not numbered."""
    section.different_first_page_header_footer = True
    section.first_page_header.is_linked_to_previous = False
    paragraph = section.header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.0
    _add_field(paragraph, 'PAGE', '2', size=size)


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


def _hint(document, text):
    """Small caption under a title page field: "(тема реферату)"."""
    p = _centered(document, text, size=10)
    p.paragraph_format.line_spacing = 1.0
    return p


def _field_line(document, label, value, aligned=False):
    """«label ______value______» — the value underlined to the right margin
    (underlined tabs draw the line, as in the usual Word templates)."""
    p = document.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    stops = p.paragraph_format.tab_stops
    stops.add_tab_stop(Mm(92) if label or aligned else Mm(80), WD_TAB_ALIGNMENT.CENTER)
    stops.add_tab_stop(TEXT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    if label:
        set_font(p.add_run(f"{label} "))
    for text in ("\t", value or "", "\t"):
        run = p.add_run(text)
        set_font(run)
        run.underline = True
    return p


def _aligned(document, text, align="center", size=14, bold=False):
    p = _centered(document, text, bold=bold, size=size)
    if align == "left":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return p


# Lines of 14 pt / 1.5 that fit on the title page before its last line
_TITLE_PAGE_LINES = 27


def add_title_page(document, report, student_name=""):
    """Draws the report's title page template (services/templates.py)."""
    used, push = 0.0, None
    for el in resolve_title_page(report):
        kind = el["t"]
        if kind == "line":
            _aligned(document, el["text"], el["align"], el["size"], el["bold"])
            used += el["size"] / 14
        elif kind == "blank":
            for _ in range(el["n"]):
                _centered(document, "")
            used += el["n"]
        elif kind == "field":
            _field_line(document, el["label"], el["value"], aligned=el.get("indent", False))
            used += 1
            if el.get("hint"):
                _hint(document, el["hint"])
                used += 0.5
        elif kind == "columns":
            rows = max(len(el["left"]), len(el["right"]))
            table = document.add_table(rows=rows, cols=2)
            _remove_table_borders(table)
            for col, lines in enumerate((el["left"], el["right"])):
                for row, text in enumerate(lines):
                    para = table.cell(row, col).paragraphs[0]
                    para.paragraph_format.first_line_indent = Cm(0)
                    para.paragraph_format.space_before = Pt(0)
                    para.paragraph_format.space_after = Pt(0)
                    set_font(para.add_run(text))
            used += rows
        elif kind == "push":
            push = _centered(document, "")
            used += 1
    # "push": blank lines so that what follows ends up at the bottom of the page
    if push is not None:
        for _ in range(max(0, int(_TITLE_PAGE_LINES - used))):
            filler = push.insert_paragraph_before()
            filler.paragraph_format.first_line_indent = Cm(0)
    document.add_page_break()


def _underlined_line(document, label, value, hint=None, center_value=True):
    """«label ___value___» with the value underlined to the right margin; long values wrap."""
    p = document.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.tab_stops.add_tab_stop(TEXT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    if label:
        set_font(p.add_run(f"{label} "))
    for text in ((" ", value or "", "\t") if not center_value else ("\t", value or "", "\t")):
        run = p.add_run(text)
        set_font(run)
        run.underline = True
    if center_value:
        p.paragraph_format.tab_stops.add_tab_stop(Mm(95), WD_TAB_ALIGNMENT.CENTER)
    if hint:
        _hint(document, hint)
    return p


def add_task_sheet(document, report):
    """ЗАВДАННЯ НА КУРСОВИЙ ПРОЄКТ — the page after the title page (методичка, додаток А)."""
    words = course_words(report)
    head = task_heading_lines(report)
    _centered(document, head["institution"])
    for label, value in head["fields"]:
        _underlined_line(document, label, value)
    p = document.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    for text, underline in head["course_line"]:
        run = p.add_run(text)
        set_font(run)
        run.underline = underline
    _centered(document, "")
    _centered(document, "ЗАВДАННЯ", bold=True)
    _centered(document, words["task_title"], bold=True)
    _underlined_line(document, head["student_label"], head["student_full"], hint="(прізвище, ім’я, по батькові)")
    for n, (label, value) in enumerate(task_fields(report), start=1):
        _underlined_line(document, f"{n}. {label}", value, center_value=False)
    document.add_page_break()


def add_calendar_plan(document, report):
    words = course_words(report)
    _centered(document, "КАЛЕНДАРНИЙ ПЛАН", bold=True)
    _centered(document, "")
    rows = calendar_rows(report)
    table = document.add_table(rows=len(rows) + 1, cols=4)
    table.style = document.styles['Table Grid']
    for c, text in enumerate(("№", f"Назви етапів {words['genitive']}", "Строк виконання етапів роботи", "Примітка")):
        _cell_text(table.cell(0, c), text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _repeat_header(table.rows[0])
    for r, row in enumerate(rows, start=1):
        for c, text in enumerate((row["no"], row["stage"], row["deadline"], row["note"])):
            _cell_text(table.cell(r, c), text, align=WD_ALIGN_PARAGRAPH.CENTER if c in (0, 2) else WD_ALIGN_PARAGRAPH.LEFT)
    _centered(document, "")
    _underlined_line(document, "Дата видачі завдання:", (report_meta_value(report, "issue_date")))
    _centered(document, "")
    signers = [("Студент:", (getattr(report, "student_name", "") or "").split("\n")[0].strip())]
    signers += [("Керівник роботи:", t) for t in supervisors(report)]
    sign = document.add_table(rows=len(signers) * 2, cols=3)
    _remove_table_borders(sign)
    for k, (label, name) in enumerate(signers):
        _cell_text(sign.cell(2 * k, 0), label, size=14)
        _cell_text(sign.cell(2 * k, 1), "______________", size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(sign.cell(2 * k, 2), name, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(sign.cell(2 * k + 1, 1), "(підпис)", size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(sign.cell(2 * k + 1, 2), "(посада, прізвище, ініціали)" if k else "(прізвище, ініціали)",
                   size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
    document.add_page_break()


def add_table_of_contents(document, page_break=True):
    """Adds the ЗМІСТ title and returns a placeholder paragraph; entries are filled in by
    fill_table_of_contents() once the body is built and heading pages are known."""
    _centered(document, "ЗМІСТ", bold=True)
    placeholder = document.add_paragraph()
    if page_break:
        document.add_page_break()
    return placeholder


def start_numbered_section(document, size=14):
    """Essay / course work: the title page (task, calendar plan) and ЗМІСТ are counted
    but not numbered — numbers start with the first page after ЗМІСТ. A new section
    without the page number field before it does that."""
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
    _add_field(paragraph, 'PAGE', '3', size=size)


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


def add_heading(document, text, level=1, bookmark=None, new_page=False, space_after=0, space_before=0, subtitle=""):
    """Use Word built-in heading styles so the TOC field picks them up.
    space_after / space_before are blank lines (essay: 1 after; course: 2 after a section
    heading, 1 before a subsection)."""
    paragraph = document.add_paragraph(style=f'Heading {level}')
    paragraph.paragraph_format.space_before = Pt(LINE_PT * int(space_before))
    paragraph.paragraph_format.space_after = Pt(LINE_PT * int(space_after))
    paragraph.paragraph_format.page_break_before = new_page
    paragraph.paragraph_format.keep_with_next = True

    if level == 1:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Cm(0)
        run = paragraph.add_run(text.upper())
        if subtitle:  # appendix: "ДОДАТОК А" and its name on the next line
            run.add_break()
            set_font(paragraph.add_run(subtitle), bold=True)
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


def _cell_text(cell, text, bold=False, size=12, align=WD_ALIGN_PARAGRAPH.LEFT):
    para = cell.paragraphs[0]
    para.paragraph_format.first_line_indent = Cm(0)
    para.paragraph_format.line_spacing = 1.0
    para.paragraph_format.alignment = align
    for kind, value in split_inline(text or ""):
        if kind == "math":
            _append_math(para, value)
        elif value:
            set_font(para.add_run(value), size=size, bold=bold)
    return para


def _repeat_header(row):
    """Header row repeats on every page the table continues to."""
    tr_pr = row._tr.get_or_add_trPr()
    el = OxmlElement('w:tblHeader')
    el.set(qn('w:val'), 'true')
    tr_pr.append(el)


def add_table(document, number, caption, rows, header=1, spaced=False):
    """«Таблиця 1.1 – Назва» above the table on the left (методичка), header row bold
    and repeated on continuation pages."""
    cap = document.add_paragraph()
    cap.paragraph_format.first_line_indent = Cm(0)
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    cap.paragraph_format.keep_with_next = True
    if spaced:
        cap.paragraph_format.space_before = Pt(LINE_PT)
    set_font(cap.add_run(f"Таблиця {number}" + (f" – {caption}" if caption else "")))

    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = document.styles['Table Grid']
    for r, row in enumerate(rows):
        is_head = r < header
        for c, text in enumerate(row):
            _cell_text(table.cell(r, c), text, bold=is_head,
                       align=WD_ALIGN_PARAGRAPH.CENTER if is_head else WD_ALIGN_PARAGRAPH.LEFT)
        if is_head:
            _repeat_header(table.rows[r])
    if spaced:  # "після таблиці — пустий рядок"
        after = document.add_paragraph()
        after.paragraph_format.line_spacing = 1.0
    return table


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


def build_report_docx(report, images=None, student_name="", out_dir=None):
    style = doc_style(report)
    spaced = style.spaced_blocks
    document = create_base_doc(style)
    add_title_page(document, report, student_name)
    front_pages = 1
    if wants_task_sheet(report):
        add_task_sheet(document, report)
        add_calendar_plan(document, report)
        front_pages += 2
    if style.numbers_from_body:
        toc_placeholder = add_table_of_contents(document, page_break=False)
        start_numbered_section(document, style.page_number_pt)
    else:
        toc_placeholder = add_table_of_contents(document)

    # Body starts after the front pages and the TOC page(s)
    blocks = list(iter_report_blocks(report, images))
    toc_lines = 2 + sum(1 for b in blocks if isinstance(b, Heading))
    toc_pages = math.ceil(toc_lines * LINE_PT / TEXT_HEIGHT_PT)
    pages = PageEstimator(start_page=front_pages + 1 + toc_pages)
    toc_headings = []

    for block in blocks:
        if isinstance(block, Heading):
            if block.new_page:
                pages.new_page()
            if block.space_before:
                pages.add(LINE_PT * block.space_before)
            pages.heading()
            if block.space_after:
                pages.add(LINE_PT * block.space_after)
            toc_headings.append((block.toc_text, block.level, block.bookmark, pages.page))
            add_heading(document, block.text, level=block.level, bookmark=block.bookmark,
                        new_page=block.new_page, space_after=block.space_after,
                        space_before=block.space_before, subtitle=block.subtitle)
        elif isinstance(block, Text):
            add_paragraph_text(document, block.text)
            pages.text(block.text)
        elif isinstance(block, Listing):
            add_listing(document, block.code, block.number, block.title)
            pages.code(block.code)
        elif isinstance(block, Figure):
            add_image(document, block.path, block.number, block.caption, spaced=spaced)
            pages.image(image_height(block.path))
        elif isinstance(block, Formula):
            add_formula(document, block.latex, block.number, spaced=spaced)
            pages.add(3 * LINE_PT if spaced else 2 * LINE_PT, keep_together=True)
        elif isinstance(block, Table):
            add_table(document, block.number, block.caption, block.rows, block.header, spaced=spaced)
            pages.add(LINE_PT * (len(block.rows) + (2 if spaced else 1)))
        elif isinstance(block, References):
            add_references(document, block.items)
            pages.text("\n".join(block.items))

    fill_table_of_contents(toc_placeholder, toc_headings)

    output_dir = out_dir or os.getenv("GENERATED_DIR", "/app/generated")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"report_{report.id}.docx")
    document.save(path)
    return path
