"""Document structure shared by the .docx and .pdf builders, so both number
sections, listings, figures, tables and formulas identically (ДСТУ 3008:2015):
"1 НАЗВА РОЗДІЛУ", "1.1 Назва підрозділу", "1.1.1 Назва пункту"; МЕТА РОБОТИ / ВСТУП,
ВИСНОВКИ and the reference list stay unnumbered; appendices are ДОДАТОК А, Б, ...

How a kind of work is laid out lives in one place — DocStyle below:
  lab     — listings / figures / tables numbered through the document (1, 2, 3);
  essay   — numbered within the section (2.1), every section on a new page;
  course  — like essay, plus the course-project rules of the методичка: 2 blank lines
            after a section heading, 1 before a subsection, right margin 15 mm,
            page numbers in 12 pt, numbering shown from the first page after ЗМІСТ."""
import os
from dataclasses import dataclass, field

from app.services.content import (
    APPENDIX_LETTERS, children, item_blocks, main_and_appendices, table_header_rows, table_rows,
)


@dataclass(frozen=True)
class DocStyle:
    kind: str
    front_title: str                 # unnumbered first section
    local_numbering: bool            # listings / figures / tables: 2.1 instead of 1, 2, 3
    new_page_sections: bool
    h1_space_after: int              # blank lines after a level-1 heading
    sub_space_before: int            # blank lines before a level-2/3 heading that follows text
    spaced_blocks: bool              # blank line around figures, formulas, tables
    right_margin_mm: int
    page_number_pt: int
    numbers_from_body: bool          # title page, task, ЗМІСТ: counted but not numbered
    references_title: str
    always_references: bool


STYLES = {
    "lab": DocStyle("lab", "Мета роботи", False, False, 0, 0, False, 20, 14, False, "Перелік посилань", False),
    "essay": DocStyle("essay", "Вступ", True, True, 1, 0, True, 20, 14, True, "Перелік посилань", True),
    "course": DocStyle("course", "Вступ", True, True, 2, 1, True, 15, 12, True, "Перелік джерел посилання", True),
}


def doc_style(report) -> DocStyle:
    return STYLES.get(getattr(report, "kind", "lab") or "lab", STYLES["lab"])


def is_essay(report) -> bool:
    """Essay-like structure (ВСТУП, sections from a new page): essays and course works."""
    return doc_style(report).kind in ("essay", "course")


def report_meta(report) -> dict:
    meta = getattr(report, "meta", None)
    return meta if isinstance(meta, dict) else {}


@dataclass
class Heading:
    text: str
    level: int
    bookmark: str  # docx bookmark / html anchor the TOC points to
    new_page: bool = False
    space_after: int = 0         # blank lines
    space_before: int = 0
    subtitle: str = ""           # appendix name, on its own line under "ДОДАТОК А"

    @property
    def toc_text(self):
        text = self.text.upper() if self.level == 1 else self.text
        return f"{text} {self.subtitle}" if self.subtitle else text


@dataclass
class Text:
    text: str  # one paragraph per line; inline formulas as $...$


@dataclass
class Listing:
    number: str
    title: str
    code: str


@dataclass
class Figure:
    number: str
    path: str
    caption: str


@dataclass
class Formula:
    number: str
    latex: str


@dataclass
class Table:
    number: str
    caption: str
    rows: list
    header: int = 1


@dataclass
class References:
    items: list = field(default_factory=list)


def text_lines(text):
    """Non-empty lines; each becomes its own paragraph."""
    return [line.strip() for line in (text or "").replace('\r\n', '\n').split('\n') if line.strip()]


def iter_report_blocks(report, images=None):
    style = doc_style(report)
    uploads_dir = os.getenv("UPLOADS_DIR", "/app/uploads")
    images_by_section = {}
    for img in sorted(images or [], key=lambda i: (getattr(i, "position", 0) or 0, i.id or 0)):
        images_by_section.setdefault(img.section_path, []).append(img)

    headings = 0
    counters = {"listing": 0, "figure": 0, "formula": 0, "table": 0}
    last_was_heading = False

    def heading(text, level=1, new_page=False, subtitle=""):
        nonlocal headings, last_was_heading
        headings += 1
        before = style.sub_space_before if level > 1 and not last_was_heading else 0
        after = style.h1_space_after if level == 1 else (1 if style.kind == "essay" else 0)
        last_was_heading = True
        return Heading(text, level, f'_Toc{headings:08d}', new_page=new_page and style.new_page_sections,
                       space_after=after, space_before=before, subtitle=subtitle)

    def body(block):
        nonlocal last_was_heading
        last_was_heading = False
        return block

    def number(kind, section_label, local):
        counters[kind] += 1
        # formulas always "(розділ.номер)"; the rest too in an essay, a course work and appendices
        if local or kind == "formula":
            return f"{section_label}.{counters[kind]}"
        return str(counters[kind])

    def content(item, title, path, section_label, local):
        for block in item_blocks(item):
            kind = block["type"]
            if kind == "text" and (block.get("text") or "").strip():
                yield body(Text(block["text"]))
            elif kind == "code" and (block.get("code") or "").strip():
                yield body(Listing(number("listing", section_label, local), title, block["code"]))
            elif kind == "formula" and (block.get("latex") or "").strip():
                yield body(Formula(number("formula", section_label, local), block["latex"].strip()))
            elif kind == "table":
                rows = table_rows(block)
                if rows:
                    yield body(Table(number("table", section_label, local), (block.get("caption") or "").strip(),
                                     rows, table_header_rows(block, rows)))
        for img in images_by_section.get(path, []):
            img_path = os.path.join(uploads_dir, img.filename)
            if os.path.exists(img_path):
                yield body(Figure(number("figure", section_label, local), img_path, img.caption))

    def walk(item, path, label, depth, local, section_label):
        """Content of item, then its sub-items (1.1, 1.1.1)."""
        title = (item.get('title') or '').strip() or f'Підрозділ {label}'
        yield from content(item, title, path, section_label, local)
        for k, sub in enumerate(children(item) if depth < 3 else []):
            sub_label = f"{label}.{k + 1}"
            sub_title = (sub.get('title') or '').strip() or f'{"Підрозділ" if depth == 1 else "Пункт"} {sub_label}'
            yield heading(f"{sub_label} {sub_title}", level=depth + 1)
            yield from walk(sub, f"{path}.{k}", sub_label, depth + 1, local, section_label)

    abbreviations = text_lines(report_meta(report).get("abbreviations"))
    if abbreviations and style.kind != "lab":
        yield heading("Скорочення та умовні познаки")
        yield body(Text("\n".join(abbreviations)))

    if style.kind == "lab":
        yield heading("Мета роботи")
        yield body(Text(report.goal or ""))
    else:
        yield heading("Вступ", new_page=bool(abbreviations))
        yield body(Text(getattr(report, "introduction", "") or ""))

    main, appendices = main_and_appendices(report.sections)
    for n, (idx, section) in enumerate(main, start=1):
        if style.local_numbering:  # numbering restarts in every section
            counters.update(listing=0, figure=0, table=0)
        counters["formula"] = 0
        title = (section.get('title') or '').strip() or f'Розділ {n}'
        yield heading(f"{n} {title}", new_page=True)
        yield from walk(section, str(idx), str(n), 1, style.local_numbering, str(n))

    yield heading("Висновки", new_page=True)
    yield body(Text(report.conclusion or ""))

    references = [r.strip() for r in (getattr(report, "bibliography", None) or []) if (r or "").strip()]
    if style.always_references or references:
        yield heading(style.references_title, new_page=True)
        yield body(References(references))

    for k, (idx, section) in enumerate(appendices):
        letter = APPENDIX_LETTERS[k % len(APPENDIX_LETTERS)]
        counters.update(listing=0, figure=0, table=0, formula=0)
        title = (section.get('title') or '').strip()
        # an appendix always starts on a new page, whatever the kind of work
        h = heading(f"Додаток {letter}", subtitle=title)
        h.new_page = True
        yield h
        yield from walk(section, str(idx), letter, 1, True, letter)
