"""Content of a section / subsection as an ordered list of blocks:

    {"type": "text",    "text": "...one paragraph per line, inline formulas as $...$"}
    {"type": "code",    "code": "...", "language": "python"}
    {"type": "formula", "latex": "E = mc^2"}
    {"type": "table",   "caption": "...", "rows": [["Заголовок", ...], ["1", ...]], "header": 1}

Sections nest three levels deep (section -> subsections -> subsections: 1, 1.1, 1.1.1).
A top-level section with "appendix": true is an appendix (ДОДАТОК А, Б, ...).

Older reports store one "text" and one "code" field per section instead; item_blocks()
reads both shapes, so everything downstream only deals with blocks."""
import re

BLOCK_TYPES = ("text", "code", "formula", "table")

# ДСТУ 3008:2015: appendices use the Ukrainian alphabet without Ґ, Є, З, І, Ї, Й, О, Ч, Ь
APPENDIX_LETTERS = "АБВГДЕЖИКЛМНПРСТУФХЦШЩЮЯ"
MAX_DEPTH = 3

# $...$ — an inline formula; \$ is a literal dollar sign
_INLINE_MATH = re.compile(r"(?<!\\)\$(.+?)(?<!\\)\$")


def item_blocks(item: dict) -> list[dict]:
    blocks = item.get("blocks")
    if isinstance(blocks, list):
        return [b for b in blocks if isinstance(b, dict) and b.get("type") in BLOCK_TYPES]
    legacy = []
    if (item.get("text") or "").strip():
        legacy.append({"type": "text", "text": item["text"]})
    if (item.get("code") or "").strip():
        legacy.append({"type": "code", "code": item["code"], "language": item.get("language") or "python"})
    return legacy


def block_is_empty(block: dict) -> bool:
    if block["type"] == "table":
        return not any((c or "").strip() for row in table_rows(block) for c in row)
    key = {"text": "text", "code": "code", "formula": "latex"}[block["type"]]
    return not (block.get(key) or "").strip()


def table_rows(block: dict) -> list[list[str]]:
    """Rows padded to the same number of columns; fully empty trailing rows dropped."""
    rows = [[str(c if c is not None else "") for c in row] for row in (block.get("rows") or []) if isinstance(row, list)]
    while rows and not any(c.strip() for c in rows[-1]):
        rows.pop()
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def table_header_rows(block: dict, rows: list) -> int:
    try:
        n = int(block.get("header", 1))
    except (TypeError, ValueError):
        n = 1
    return max(0, min(n, len(rows)))


def main_and_appendices(sections) -> tuple[list, list]:
    """[(index, section)] of the numbered sections and of the appendices; indexes are the
    positions in report.sections, which image section_paths refer to."""
    main, apps = [], []
    for idx, s in enumerate(sections or []):
        (apps if s.get("appendix") else main).append((idx, s))
    return main, apps


def children(item: dict) -> list:
    return [c for c in (item.get("subsections") or []) if isinstance(c, dict)]


def split_inline(text: str) -> list[tuple[str, str]]:
    """[("text", "Маса "), ("math", "m"), ("text", " тіла")] — for one paragraph."""
    parts, pos = [], 0
    for m in _INLINE_MATH.finditer(text):
        if m.start() > pos:
            parts.append(("text", text[pos:m.start()]))
        parts.append(("math", m.group(1).strip()))
        pos = m.end()
    if pos < len(text):
        parts.append(("text", text[pos:]))
    return [(kind, value.replace("\\$", "$") if kind == "text" else value) for kind, value in parts]


def strip_inline_math(text: str) -> str:
    """Plain text for the AI prompt: keeps the LaTeX of inline formulas readable."""
    return _INLINE_MATH.sub(lambda m: m.group(1), text or "").replace("\\$", "$")
