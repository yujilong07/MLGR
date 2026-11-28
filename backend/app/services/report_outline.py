"""Document structure shared by the .docx and .pdf builders, so both number
sections, listings, figures and formulas identically (ДСТУ 3008:2015):
"1 НАЗВА РОЗДІЛУ", "1.1 Назва підрозділу"; МЕТА РОБОТИ / ВСТУП, ВИСНОВКИ and
ПЕРЕЛІК ПОСИЛАНЬ stay unnumbered.

Lab report: listings and figures are numbered through the whole document (1, 2, 3).
Essay (реферат, методичка ФШІ): everything is numbered within its section (2.1, 2.2),
every section starts on a new page and a blank line separates a heading from the text."""
import os
from dataclasses import dataclass, field

from app.services.content import item_blocks


@dataclass
class Heading:
    text: str
    level: int
    bookmark: str  # docx bookmark / html anchor the TOC points to
    new_page: bool = False
    space_after: bool = False

    @property
    def toc_text(self):
        return self.text.upper() if self.level == 1 else self.text


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
class References:
    items: list = field(default_factory=list)


def is_essay(report) -> bool:
    return getattr(report, "kind", "lab") == "essay"


def student_lines(report, student_name=""):
    text = (getattr(report, "student_name", "") or student_name or "")
    return [line.strip() for line in text.replace("\r\n", "\n").split("\n") if line.strip()]


def signature_rows(report, student_name=""):
    """Rows of the "Виконав / Прийняв" block on the lab title page, with verb forms by gender."""
    students = student_lines(report, student_name)
    if len(students) > 1:
        did = "Виконали:"
    else:
        did = "Виконала:" if getattr(report, "student_gender", "m") == "f" else "Виконав:"
    took = "Прийняв:" if getattr(report, "teacher_gender", "f") == "m" else "Прийняла:"
    rows = [(did, took), (f"ст. гр. {report.group}", report.teacher)]
    rows += [(name, "") for name in students] or [("", "")]
    return rows


def essay_people(report, student_name=""):
    """Essay title page (методичка): ("виконав:", ["13.10.2025  студент гр. ІТШІ-23-1  Іваненко І. І."]),
    ("перевірив", "ас. каф. ШІ Гриньов С. А.")."""
    students = student_lines(report, student_name) or [""]
    if len(students) > 1:
        did = "виконали:"
    else:
        did = "виконала:" if getattr(report, "student_gender", "m") == "f" else "виконав:"
    date = (getattr(report, "work_date", "") or "").strip()
    group = (report.group or "").strip()
    lines = ["   ".join(p for p in (date, f"студент гр. {group}" if group else "", name) if p) for name in students]
    checked = "перевірив" if getattr(report, "teacher_gender", "f") == "m" else "перевірила"
    teacher = " ".join(p for p in ((getattr(report, "teacher_position", "") or "").strip(), (report.teacher or "").strip()) if p)
    return did, lines, checked, teacher


def text_lines(text):
    """Non-empty lines; each becomes its own paragraph."""
    return [line.strip() for line in (text or "").replace('\r\n', '\n').split('\n') if line.strip()]


def iter_report_blocks(report, images=None):
    uploads_dir = os.getenv("UPLOADS_DIR", "/app/uploads")
    essay = is_essay(report)
    images_by_section = {}
    for img in sorted(images or [], key=lambda i: (getattr(i, "position", 0) or 0, i.id or 0)):
        images_by_section.setdefault(img.section_path, []).append(img)

    headings = 0
    counters = {"listing": 0, "figure": 0, "formula": 0}

    def heading(text, level=1, new_page=False):
        nonlocal headings
        headings += 1
        return Heading(text, level, f'_Toc{headings:08d}', new_page=new_page and essay, space_after=essay)

    def number(kind, section_no):
        counters[kind] += 1
        # formulas always "(розділ.номер)"; listings / figures too in an essay
        if essay or kind == "formula":
            return f"{section_no}.{counters[kind]}"
        return str(counters[kind])

    def content(item, title, section_path, section_no):
        for block in item_blocks(item):
            kind = block["type"]
            if kind == "text" and (block.get("text") or "").strip():
                yield Text(block["text"])
            elif kind == "code" and (block.get("code") or "").strip():
                yield Listing(number("listing", section_no), title, block["code"])
            elif kind == "formula" and (block.get("latex") or "").strip():
                yield Formula(number("formula", section_no), block["latex"].strip())
        for img in images_by_section.get(section_path, []):
            path = os.path.join(uploads_dir, img.filename)
            if os.path.exists(path):
                yield Figure(number("figure", section_no), path, img.caption)

    if essay:
        yield heading("Вступ")
        yield Text(getattr(report, "introduction", "") or "")
    else:
        yield heading("Мета роботи")
        yield Text(report.goal or "")

    for idx, section in enumerate(report.sections or []):
        if essay:  # numbering restarts in every section
            counters.update(listing=0, figure=0)
        counters["formula"] = 0
        title = (section.get('title') or '').strip() or f'Розділ {idx + 1}'
        yield heading(f"{idx + 1} {title}", new_page=True)
        yield from content(section, title, str(idx), idx + 1)

        for sub_idx, sub in enumerate(section.get('subsections') or []):
            sub_title = (sub.get('title') or '').strip() or f'Підрозділ {idx + 1}.{sub_idx + 1}'
            yield heading(f"{idx + 1}.{sub_idx + 1} {sub_title}", level=2)
            yield from content(sub, sub_title, f"{idx}.{sub_idx}", idx + 1)

    yield heading("Висновки", new_page=True)
    yield Text(report.conclusion or "")

    references = [r.strip() for r in (getattr(report, "bibliography", None) or []) if (r or "").strip()]
    if essay or references:
        yield heading("Перелік посилань", new_page=True)
        yield References(references)
