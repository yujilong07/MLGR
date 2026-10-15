"""Document structure shared by the .docx and .pdf builders, so both number
sections, listings and figures identically (ДСТУ 3008:2015):
"1 НАЗВА РОЗДІЛУ", "1.1 Назва підрозділу"; МЕТА РОБОТИ and ВИСНОВКИ stay unnumbered."""
import os
from dataclasses import dataclass


@dataclass
class Heading:
    text: str
    level: int
    bookmark: str  # docx bookmark / html anchor the TOC points to

    @property
    def toc_text(self):
        return self.text.upper() if self.level == 1 else self.text


@dataclass
class Text:
    text: str


@dataclass
class Listing:
    number: int
    title: str
    code: str


@dataclass
class Figure:
    number: int
    path: str
    caption: str


def text_lines(text):
    """Non-empty lines; each becomes its own paragraph."""
    return [line.strip() for line in (text or "").replace('\r\n', '\n').split('\n') if line.strip()]


def iter_report_blocks(report, images=None):
    uploads_dir = os.getenv("UPLOADS_DIR", "/app/uploads")
    images_by_section = {}
    for img in images or []:
        images_by_section.setdefault(img.section_path, []).append(img)

    headings = 0
    listings = 0
    figures = 0

    def heading(text, level=1):
        nonlocal headings
        headings += 1
        return Heading(text, level, f'_Toc{headings:08d}')

    def content(block, title, section_path):
        nonlocal listings, figures
        if block.get('text'):
            yield Text(block['text'])
        if block.get('code'):
            listings += 1
            yield Listing(listings, title, block['code'])
        for img in images_by_section.get(section_path, []):
            path = os.path.join(uploads_dir, img.filename)
            if os.path.exists(path):
                figures += 1
                yield Figure(figures, path, img.caption)

    yield heading("Мета роботи")
    yield Text(report.goal or "")

    for idx, section in enumerate(report.sections or []):
        title = (section.get('title') or '').strip() or f'Розділ {idx + 1}'
        yield heading(f"{idx + 1} {title}")
        yield from content(section, title, str(idx))

        for sub_idx, sub in enumerate(section.get('subsections') or []):
            sub_title = (sub.get('title') or '').strip() or f'Підрозділ {idx + 1}.{sub_idx + 1}'
            yield heading(f"{idx + 1}.{sub_idx + 1} {sub_title}", level=2)
            yield from content(sub, sub_title, f"{idx}.{sub_idx}")

    yield heading("Висновки")
    yield Text(report.conclusion or "")
