"""PDF version of the report, rendered with WeasyPrint from the same outline as the .docx.

Light enough for a small server (no LibreOffice). WeasyPrint lays the pages out itself,
so the TOC page numbers it reports are also written back into the .docx."""
import os
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.services.docx_builder import IMAGE_WIDTH, image_size
import itertools
import re

from app.services.content import split_inline
from app.services.math_render import FormulaError, latex_to_svg
from app.services.course_pages import (
    calendar_rows, course_words, report_meta_value, supervisors, task_fields, task_heading_lines, wants_task_sheet,
)
from app.services.report_outline import (
    Figure, Formula, Heading, Listing, References, Table, Text,
    doc_style, iter_report_blocks, text_lines,
)
from app.services.templates import resolve_title_page

LINE_PT = 24.15

EMU_PER_MM = 36000

CSS = """
@page {
  size: A4;
  margin: 20mm @@right@@mm 20mm 30mm;
  @top-right {
    content: counter(page);
    vertical-align: top;
    padding-top: 11mm;
    font: @@pagept@@pt "Times New Roman", "Liberation Serif", serif;
  }
}
@page :first { @top-right { content: none; } }

html { font: 14pt/24.15pt "Times New Roman", "Liberation Serif", serif; color: #000; }
body { margin: 0; }
p { margin: 0; text-indent: 1.25cm; text-align: justify; orphans: 2; widows: 2; }

.title p { text-indent: 0; text-align: center; }
.title { break-after: page; }
.signatures { width: 100%; border-collapse: collapse; }
.signatures td { width: 50%; padding: 0; vertical-align: top; }
.signatures p { text-align: left; }

.toc { break-after: page; }
.toc-title { margin: 0; font-size: 14pt; font-weight: bold; text-align: center; }
.toc a { display: block; color: #000; text-decoration: none; }
.toc a.l2 { padding-left: 0.5cm; }
.toc a.l3 { padding-left: 1cm; }
.toc a::after { content: leader('.') target-counter(attr(href), page); }

h1, h2, h3 { margin: 0; font-size: 14pt; font-weight: bold; break-after: avoid; }
h1 { text-align: center; }
h2, h3 { text-align: left; text-indent: 1.25cm; }

.listing-caption { text-indent: 0; text-align: left; break-after: avoid; }
pre {
  margin: 0;
  font: 12pt/13.56pt "Courier New", "Liberation Mono", monospace;
  white-space: pre-wrap;
  tab-size: 4;
}

/* essay / course work: title page, task, plan and ЗМІСТ are counted but carry no page number */
@page front { @top-right { content: none; } }
.from-body .title, .from-body .toc, .from-body .task, .from-body .plan { page: front; }
.title { display: flex; flex-direction: column; height: 257mm; }
.title .push { flex: 1; }
.field { display: flex; text-indent: 0; text-align: left; }
.field .u { flex: 1; border-bottom: 1px solid #000; text-align: center; padding: 0 4px; }
.field .lbl { padding-right: 6px; white-space: pre; }
.hint { font-size: 10pt; line-height: 12pt; }
h1.new-page { break-before: page; }
.spaced .figure { margin: 24.15pt 0; }

.formula { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; margin: 8pt 0; break-inside: avoid; }
.spaced .formula { margin: 24.15pt 0; }
.formula .f { grid-column: 2; }
.formula .n { grid-column: 3; text-align: right; }
.formula svg, p svg { display: inline-block; }
.latex-src { font-family: "Cambria Math", "Liberation Serif", serif; font-style: italic; }
.refs p { text-indent: 1.25cm; }

.table-caption { text-indent: 0; text-align: left; break-after: avoid; }
.spaced .table-caption { margin-top: 24.15pt; }
table.grid { width: 100%; border-collapse: collapse; font-size: 12pt; line-height: 1.2; }
.spaced table.grid { margin-bottom: 24.15pt; }
table.grid td, table.grid th { border: 1px solid #000; padding: 2pt 4pt; vertical-align: top; text-align: left; font-weight: normal; }
table.grid thead th { font-weight: bold; text-align: center; }
table.grid p { text-indent: 0; text-align: inherit; }

.task, .plan { break-after: page; }
.task p, .plan p { text-indent: 0; }
.task .center, .plan .center { text-align: center; }
.task .head { font-weight: bold; text-align: center; }
.uline { display: flex; text-align: left; }
.uline .lbl { white-space: pre; padding-right: 6px; }
.uline .u { flex: 1; border-bottom: 1px solid #000; text-align: center; }
.uline.long { display: block; }
.uline.long .lbl { white-space: normal; }
.uline.long .u { display: inline; border-bottom: none; text-decoration: underline; }
.u-inline { text-decoration: underline; white-space: pre; }
table.sign { width: 100%; margin-top: 12pt; border-collapse: collapse; }
table.sign td { padding: 0 4pt; vertical-align: bottom; text-align: center; }
table.sign td:first-child { text-align: left; white-space: nowrap; }
table.sign .h td { font-size: 10pt; line-height: 12pt; vertical-align: top; }
.plan table.grid td:first-child, .plan table.grid td:nth-child(3) { text-align: center; }

.figure { break-inside: avoid; text-align: center; }
.figure img { display: block; margin: 0 auto; }
.figure p { text-indent: 0; text-align: center; }
"""


def _uploads_only_fetcher(root):
    """Only local files from the uploads directory may be embedded — never the network."""
    from weasyprint.urls import URLFetcher

    class UploadsOnly(URLFetcher):
        def fetch(self, url, headers=None):
            path = os.path.realpath(unquote(urlparse(url).path))
            if os.path.commonpath([path, root]) != root:
                raise ValueError(f"Blocked resource: {url}")
            return super().fetch(url, headers)

    return UploadsOnly(allowed_protocols={'file'})


_svg_ids = itertools.count()


def _math_svg(latex, inline):
    """Inline <svg>: WeasyPrint draws SVG but not MathML. Symbol ids are made unique per
    formula, otherwise every glyph id would clash with the same glyph in other formulas."""
    try:
        svg, _w, _h, depth = latex_to_svg(latex, inline=inline)
    except FormulaError:
        return f'<span class="latex-src">{escape(latex)}</span>'
    prefix = f"m{next(_svg_ids)}_"
    svg = re.sub(r'(id="|href="#)', lambda m: m.group(1) + prefix, svg)
    if inline:
        svg = svg.replace("<svg ", f'<svg style="vertical-align: -{depth:.2f}px" ', 1)
    return svg


def _inline_html(line):
    return ''.join(_math_svg(v, inline=True) if kind == "math" else escape(v) for kind, v in split_inline(line))


def _paragraphs(text, cls=None):
    attr = f' class="{cls}"' if cls else ''
    return ''.join(f'<p{attr}>{_inline_html(line)}</p>' for line in text_lines(text))


def _title_page(report):
    """Draws the report's title page template (services/templates.py)."""
    blank = '<p>&nbsp;</p>'
    out, last_label = [], ""
    for el in resolve_title_page(report):
        kind = el["t"]
        if kind == "line":
            style = f'text-align:{el["align"]};font-size:{el["size"]}pt;' + ('font-weight:bold;' if el["bold"] else '')
            out.append(f'<p style="{style}">{escape(el["text"]) or "&nbsp;"}</p>')
        elif kind == "blank":
            out.append(blank * el["n"])
        elif kind == "field":
            label = el["label"] or (last_label if el.get("indent") else "")
            hidden = ' style="visibility:hidden"' if el.get("indent") else ''
            last_label = el["label"] or last_label
            out.append(f'<p class="field"><span class="lbl"{hidden}>{escape(label)}</span>'
                       f'<span class="u">{escape(el["value"])}&nbsp;</span></p>')
            if el.get("hint"):
                out.append(f'<p class="hint">{escape(el["hint"])}</p>')
        elif kind == "columns":
            cell = lambda lines: ''.join(f'<p>{escape(t) or "&nbsp;"}</p>' for t in lines)
            out.append(f'<table class="signatures"><tr><td>{cell(el["left"])}</td><td>{cell(el["right"])}</td></tr></table>')
        elif kind == "push":
            out.append('<div class="push"></div>')
    return '<section class="title">' + ''.join(out) + '</section>'


def _task_pages(report):
    """ЗАВДАННЯ and КАЛЕНДАРНИЙ ПЛАН of a course work (services/course_pages.py)."""
    words = course_words(report)
    head = task_heading_lines(report)
    line = lambda label, value: (f'<p class="uline"><span class="lbl">{escape(label)}</span>'
                                 f'<span class="u">{escape(value)}&nbsp;</span></p>')
    long_line = lambda label, value: (f'<p class="uline long"><span class="lbl">{escape(label)}</span>'
                                      f'<span class="u">&nbsp;{escape(value)}&nbsp;</span></p>')
    course_line = ''.join(f'<span class="u-inline">{escape(t)}</span>' if u else escape(t) for t, u in head["course_line"])
    task = ('<section class="task">'
            f'<p class="center">{escape(head["institution"])}</p>'
            + ''.join(line(l, v) for l, v in head["fields"])
            + f'<p>{course_line}</p><p>&nbsp;</p>'
            f'<p class="head">ЗАВДАННЯ</p><p class="head">{escape(words["task_title"])}</p>'
            + line(head["student_label"], head["student_full"])
            + '<p class="hint center">(прізвище, ім’я, по батькові)</p>'
            + ''.join(long_line(f"{n}. {l}", v) for n, (l, v) in enumerate(task_fields(report), start=1))
            + '</section>')
    rows = ''.join(f'<tr><td>{escape(r["no"])}</td><td>{escape(r["stage"])}</td><td>{escape(r["deadline"])}</td>'
                   f'<td>{escape(r["note"])}</td></tr>' for r in calendar_rows(report))
    signers = [("Студент:", (getattr(report, "student_name", "") or "").split("\n")[0].strip(), "(прізвище, ініціали)")]
    signers += [("Керівник роботи:", t, "(посада, прізвище, ініціали)") for t in supervisors(report)]
    sign = ''.join(f'<tr><td>{escape(l)}</td><td>______________</td><td>{escape(n)}</td></tr>'
                   f'<tr class="h"><td></td><td>(підпис)</td><td>{h}</td></tr>' for l, n, h in signers)
    plan = ('<section class="plan"><p class="head center"><b>КАЛЕНДАРНИЙ ПЛАН</b></p><p>&nbsp;</p>'
            '<table class="grid"><thead><tr><th>№</th>'
            f'<th>Назви етапів {escape(words["genitive"])}</th><th>Строк виконання етапів роботи</th><th>Примітка</th>'
            f'</tr></thead><tbody>{rows}</tbody></table><p>&nbsp;</p>'
            + line("Дата видачі завдання:", report_meta_value(report, "issue_date"))
            + f'<table class="sign">{sign}</table></section>')
    return task + plan


def _table_html(block):
    head = block.rows[:block.header]
    rest = block.rows[block.header:]
    cell = lambda tag, text: f'<{tag}>{_inline_html(text)}</{tag}>'
    thead = ''.join('<tr>' + ''.join(cell('th', c) for c in row) + '</tr>' for row in head)
    tbody = ''.join('<tr>' + ''.join(cell('td', c) for c in row) + '</tr>' for row in rest)
    caption = f"Таблиця {block.number}" + (f" – {escape(block.caption)}" if block.caption else "")
    return (f'<p class="table-caption">{caption}</p><table class="grid">'
            + (f'<thead>{thead}</thead>' if thead else '') + f'<tbody>{tbody}</tbody></table>')


def _figure_style(path):
    size = image_size(path)
    if 'height' in size:
        return f'height: {size["height"] / EMU_PER_MM:.1f}mm'
    return f'width: {IMAGE_WIDTH / EMU_PER_MM:.1f}mm'


def build_report_html(report, images=None, student_name=""):
    style = doc_style(report)
    toc, body = [], []
    for block in iter_report_blocks(report, images):
        if isinstance(block, Heading):
            tag = f'h{block.level}'
            cls_attr = ' class="new-page"' if block.new_page else ''
            spacing = f'margin-top:{LINE_PT * block.space_before}pt;margin-bottom:{LINE_PT * block.space_after}pt'
            toc.append(f'<a class="l{block.level}" href="#{block.bookmark}">{escape(block.toc_text)}</a>')
            text = escape(block.text.upper() if block.level == 1 else block.text)
            if block.subtitle:
                text += f'<br>{escape(block.subtitle)}'
            body.append(f'<{tag}{cls_attr} style="{spacing}" id="{block.bookmark}">{text}</{tag}>')
        elif isinstance(block, Text):
            body.append(_paragraphs(block.text))
        elif isinstance(block, Listing):
            body.append(
                f'<p class="listing-caption">Лістинг {block.number} – {escape(block.title)}</p>'
                f'<pre>{escape(block.code.replace(chr(13), "").rstrip())}</pre>'
            )
        elif isinstance(block, Figure):
            body.append(
                f'<div class="figure"><img src="{Path(block.path).as_uri()}" style="{_figure_style(block.path)}" alt="">'
                f'<p>Рисунок {block.number} – {escape(block.caption)}</p></div>'
            )
        elif isinstance(block, Formula):
            body.append(f'<div class="formula"><span class="f">{_math_svg(block.latex, inline=False)}</span>'
                        f'<span class="n">({block.number})</span></div>')
        elif isinstance(block, Table):
            body.append(_table_html(block))
        elif isinstance(block, References):
            body.append('<div class="refs">' + ''.join(
                f'<p>{n}. {escape(item)}</p>' for n, item in enumerate(block.items, start=1)) + '</div>')

    css = CSS.replace("@@right@@", str(style.right_margin_mm)).replace("@@pagept@@", str(style.page_number_pt))
    classes = " ".join(c for c, on in (("from-body", style.numbers_from_body), ("spaced", style.spaced_blocks), (style.kind, True)) if on)
    return (
        f'<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8"><style>{css}</style></head>'
        f'<body class="{classes}">'
        + _title_page(report)
        + (_task_pages(report) if wants_task_sheet(report) else '')
        + '<section class="toc"><p class="toc-title">ЗМІСТ</p>' + ''.join(toc) + '</section>'
        + ''.join(body)
        + '</body></html>'
    )


def build_report_pdf(report, images=None, student_name="", out_dir=None):
    """Returns (pdf_path, {toc_bookmark: page}) — pages are taken from the actual layout."""
    from weasyprint import HTML  # imported lazily: needs Pango from the system

    uploads_dir = os.path.realpath(os.getenv("UPLOADS_DIR", "/app/uploads"))
    html = build_report_html(report, images, student_name)
    document = HTML(string=html, url_fetcher=_uploads_only_fetcher(uploads_dir)).render()

    pages = {}
    for number, page in enumerate(document.pages, start=1):
        for anchor in page.anchors:
            if anchor.startswith('_Toc'):
                pages.setdefault(anchor, number)

    output_dir = out_dir or os.getenv("GENERATED_DIR", "/app/generated")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"report_{report.id}.pdf")
    document.write_pdf(path)
    return path, pages
