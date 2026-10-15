"""PDF version of the report, rendered with WeasyPrint from the same outline as the .docx.

Light enough for a small server (no LibreOffice). WeasyPrint lays the pages out itself,
so the TOC page numbers it reports are also written back into the .docx."""
import os
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.services.docx_builder import IMAGE_WIDTH, image_size
from app.services.report_outline import Figure, Heading, Listing, Text, iter_report_blocks, text_lines

EMU_PER_MM = 36000

CSS = """
@page {
  size: A4;
  margin: 20mm 20mm 20mm 30mm;
  @top-right {
    content: counter(page);
    vertical-align: top;
    padding-top: 11mm;
    font: 14pt "Times New Roman", "Liberation Serif", serif;
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
.toc a::after { content: leader('.') target-counter(attr(href), page); }

h1, h2 { margin: 0; font-size: 14pt; font-weight: bold; break-after: avoid; }
h1 { text-align: center; }
h2 { text-align: left; text-indent: 1.25cm; }

.listing-caption { text-indent: 0; text-align: left; break-after: avoid; }
pre {
  margin: 0;
  font: 12pt/13.56pt "Courier New", "Liberation Mono", monospace;
  white-space: pre-wrap;
  tab-size: 4;
}

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


def _paragraphs(text, cls=None):
    attr = f' class="{cls}"' if cls else ''
    return ''.join(f'<p{attr}>{escape(line)}</p>' for line in text_lines(text))


def _title_page(report, student_name):
    blank = '<p>&nbsp;</p>'
    line = lambda text: f'<p>{escape(text or "")}</p>' if text else blank
    rows = [("Виконав:", "Прийняла:"), (f"ст. гр. {report.group}", report.teacher), (student_name, "")]
    table = ''.join(f'<tr><td>{line(a)}</td><td>{line(b)}</td></tr>' for a, b in rows)
    return (
        '<section class="title">'
        + line("Міністерство освіти і науки України")
        + line("Харківський національний університет радіоелектроніки")
        + blank + line("Кафедра штучного інтелекту") + blank * 4
        + line(f"Дисципліна «{report.discipline}»") + line(report.title) + blank * 5
        + f'<table class="signatures">{table}</table>' + blank * 5
        + line(f"Харків – {datetime.now().year}")
        + '</section>'
    )


def _figure_style(path):
    size = image_size(path)
    if 'height' in size:
        return f'height: {size["height"] / EMU_PER_MM:.1f}mm'
    return f'width: {IMAGE_WIDTH / EMU_PER_MM:.1f}mm'


def build_report_html(report, images=None, student_name=""):
    toc, body = [], []
    for block in iter_report_blocks(report, images):
        if isinstance(block, Heading):
            tag = 'h1' if block.level == 1 else 'h2'
            toc.append(f'<a class="l{block.level}" href="#{block.bookmark}">{escape(block.toc_text)}</a>')
            body.append(f'<{tag} id="{block.bookmark}">{escape(block.toc_text)}</{tag}>')
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

    return (
        f'<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
        + _title_page(report, student_name)
        + '<section class="toc"><p class="toc-title">ЗМІСТ</p>' + ''.join(toc) + '</section>'
        + ''.join(body)
        + '</body></html>'
    )


def build_report_pdf(report, images=None, student_name=""):
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

    output_dir = os.getenv("GENERATED_DIR", "/app/generated")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"report_{report.id}.pdf")
    document.write_pdf(path)
    return path, pages
