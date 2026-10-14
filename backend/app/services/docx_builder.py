from docx import Document
from docx.image.image import Image
from docx.shared import Pt, Cm, Mm, Inches, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime
import math
import os

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


def _lines(text):
    return [l.strip() for l in (text or "").replace('\r\n', '\n').split('\n') if l.strip()]


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
    _centered(document, "Кафедра штучного інтелекту")

    for _ in range(4):
        _centered(document, "")

    _centered(document, f"Дисципліна «{report.discipline}»")
    _centered(document, report.title)

    for _ in range(5):
        _centered(document, "")

    # Виконав / Прийняла side-by-side with borderless table
    table = document.add_table(rows=3, cols=2)
    _remove_table_borders(table)

    rows_data = [
        ("Виконав:", "Прийняла:"),
        (f"ст. гр. {report.group}", report.teacher),
        (student_name, ""),
    ]
    for row_idx, (left, right) in enumerate(rows_data):
        for col_idx, text in enumerate((left, right)):
            cell = table.cell(row_idx, col_idx)
            para = cell.paragraphs[0]
            para.paragraph_format.first_line_indent = Cm(0)
            para.paragraph_format.space_before = Pt(0)
            para.paragraph_format.space_after = Pt(0)
            run = para.add_run(text)
            set_font(run)

    for _ in range(5):
        _centered(document, "")

    _centered(document, f"Харків – {year}")

    document.add_page_break()


def add_table_of_contents(document):
    """Adds the ЗМІСТ title and returns a placeholder paragraph; entries are filled in by
    fill_table_of_contents() once the body is built and heading pages are known."""
    _centered(document, "ЗМІСТ", bold=True)
    placeholder = document.add_paragraph()
    document.add_page_break()
    return placeholder


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


def add_heading(document, text, level=1, bookmark=None):
    """Use Word built-in heading styles so the TOC field picks them up."""
    paragraph = document.add_paragraph(style=f'Heading {level}')
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)

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


def add_paragraph_text(document, text):
    """Each non-empty line becomes its own paragraph: manual line breaks inside a
    justified paragraph make Word stretch the line across the full width."""
    paragraph = None
    for line in _lines(text):
        paragraph = document.add_paragraph()
        set_font(paragraph.add_run(line))
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


def add_image(document, image_path, image_number, caption_text):
    img_paragraph = document.add_paragraph()
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
    return caption

def build_report_docx(report, images=None, student_name=""):
    """Sections are numbered per ДСТУ 3008:2015: "1 НАЗВА РОЗДІЛУ", "1.1 Назва підрозділу".
    МЕТА РОБОТИ and ВИСНОВКИ are structural elements and stay unnumbered."""
    document = create_base_doc()
    add_title_page(document, report, student_name)
    toc_placeholder = add_table_of_contents(document)

    sections = report.sections or []
    # Body starts after the title page and the TOC page(s)
    toc_lines = 3 + sum(1 + len(sec.get('subsections') or []) for sec in sections)
    toc_pages = math.ceil(toc_lines * LINE_PT / TEXT_HEIGHT_PT)
    pages = PageEstimator(start_page=2 + toc_pages)
    toc_headings = []

    def heading(text, level=1):
        bookmark = f'_Toc{len(toc_headings) + 1:08d}'
        pages.heading()
        toc_headings.append((text.upper() if level == 1 else text, level, bookmark, pages.page))
        add_heading(document, text, level=level, bookmark=bookmark)

    images_by_section = {}
    for img in images or []:
        images_by_section.setdefault(img.section_path, []).append(img)

    counters = {'listing': 1, 'image': 1}

    def content(block, title, section_path):
        if block.get('text'):
            add_paragraph_text(document, block['text'])
            pages.text(block['text'])
        if block.get('code'):
            add_listing(document, block['code'], counters['listing'], title)
            pages.code(block['code'])
            counters['listing'] += 1
        for img in images_by_section.get(section_path, []):
            img_path = os.path.join(os.getenv("UPLOADS_DIR", "/app/uploads"), img.filename)
            if os.path.exists(img_path):
                add_image(document, img_path, counters['image'], img.caption)
                pages.image(image_height(img_path))
                counters['image'] += 1

    heading("Мета роботи")
    add_paragraph_text(document, report.goal)
    pages.text(report.goal)

    for idx, section in enumerate(sections):
        title = (section.get('title') or '').strip() or f'Розділ {idx + 1}'
        heading(f"{idx + 1} {title}")
        content(section, title, str(idx))

        for sub_idx, sub in enumerate(section.get('subsections') or []):
            sub_title = (sub.get('title') or '').strip() or f'Підрозділ {idx + 1}.{sub_idx + 1}'
            heading(f"{idx + 1}.{sub_idx + 1} {sub_title}", level=2)
            content(sub, sub_title, f"{idx}.{sub_idx}")

    heading("Висновки")
    add_paragraph_text(document, report.conclusion)

    fill_table_of_contents(toc_placeholder, toc_headings)

    output_dir = os.getenv("GENERATED_DIR", "/app/generated")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"report_{report.id}.docx")
    document.save(path)
    return path
