"""Content of a section / subsection as an ordered list of blocks:

    {"type": "text",    "text": "...one paragraph per line, inline formulas as $...$"}
    {"type": "code",    "code": "...", "language": "python"}
    {"type": "formula", "latex": "E = mc^2"}

Older reports store one "text" and one "code" field per section instead; item_blocks()
reads both shapes, so everything downstream only deals with blocks."""
import re

BLOCK_TYPES = ("text", "code", "formula")

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
    key = {"text": "text", "code": "code", "formula": "latex"}[block["type"]]
    return not (block.get(key) or "").strip()


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
