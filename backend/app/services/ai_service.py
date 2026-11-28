import os
import time
import structlog
from openai import OpenAI
from app.config import settings
from app.services.content import item_blocks, strip_inline_math

client = OpenAI(
    api_key=settings.groq_api_key,
    base_url="https://api.groq.com/openai/v1"
)

logger = structlog.get_logger().bind(service="ai")

# Groq retires models periodically: list available ones via GET /openai/v1/models
_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
_LANG_RULE = (
    "Відповідай ВИКЛЮЧНО українською мовою. Не використовуй жодних слів іншими мовами. "
    # Text goes straight into a .docx, so markdown symbols would show up literally
    "Пиши звичайним суцільним текстом без Markdown: без **, #, `, таблиць і маркованих списків."
)


_ESSAY_INTRO_PROMPT = (
    "Ти досвідчений викладач, який допомагає написати розділ «Вступ» до реферату студента або учня "
    "(рівень закладу зазначено в описі). "
    "Тобі дають тему, дисципліну та назви розділів (і, можливо, їхній зміст). "
    "Напиши 2–3 абзаци (120–220 слів): актуальність теми, мета реферату та коротко — які питання "
    "розглянуто в розділах. Не вигадуй фактів, чисел і джерел, яких немає у матеріалі. "
    "Безособова форма, академічний стиль. Не додавай заголовок «Вступ». "
    + _LANG_RULE
)


def generate_introduction(goal: str, essay_context: str | None = None) -> str:
    """Lab: a short introduction from the goal. Essay: the ВСТУП section from the topic and outline."""
    t0 = time.perf_counter()
    logger.info("ai_request_start", fn="generate_introduction", model=_MODEL, essay=bool(essay_context))
    if essay_context:
        messages = [
            {"role": "system", "content": _ESSAY_INTRO_PROMPT},
            {"role": "user", "content": essay_context},
        ]
    else:
        messages = [
            {
                "role": "system",
                "content": (
                    "Ти асистент який пише вступ до лабораторної роботи на основі її мети. "
                    "Напиши один короткий абзац вступу. "
                    + _LANG_RULE
                ),
            },
            {"role": "user", "content": f"Мета роботи: {goal}"},
        ]
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            temperature=0.3,
            messages=messages,
        )
        logger.info(
            "ai_request_done",
            fn="generate_introduction",
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
            total_tokens=response.usage.total_tokens,
        )
        return _strip_markdown(response.choices[0].message.content)
    except Exception:
        logger.error(
            "ai_request_failed",
            fn="generate_introduction",
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
            exc_info=True,
        )
        raise


def improve_section_text(text: str) -> str:
    t0 = time.perf_counter()
    logger.info("ai_request_start", fn="improve_section_text", model=_MODEL)
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ти науковий редактор. Покращуй академічний стиль і формулювання "
                        "наданого тексту. "
                        "Суворо заборонено додавати нові факти, дані або інформацію, "
                        "яких немає в оригіналі — лише покращуй подачу того що вже є. "
                        "Повертай виключно відредагований текст без пояснень і коментарів. "
                        + _LANG_RULE
                    ),
                },
                {"role": "user", "content": text},
            ]
        )
        logger.info(
            "ai_request_done",
            fn="improve_section_text",
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
            total_tokens=response.usage.total_tokens,
        )
        return response.choices[0].message.content
    except Exception:
        logger.error(
            "ai_request_failed",
            fn="improve_section_text",
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
            exc_info=True,
        )
        raise


# Keeps the prompt within model limits on long reports
_MAX_CODE_CHARS = 1500
_MAX_CONTEXT_CHARS = 14000

CONCLUSION_PROMPT_VERSION = "5"

_CONCLUSION_SYSTEM_PROMPT = (
    "Ти досвідчений викладач, який пише розділ «Висновки» до навчальної роботи студента "
    "університету чи коледжу або учня школи (лабораторної, практичної або реферату). "
    "Рівень і стиль висновків відповідай рівню закладу, зазначеному в описі роботи. "
    "Тобі дають повний зміст роботи: тему, дисципліну, мету, розділи з текстом, "
    "фрагменти коду та підписи рисунків.\n\n"
    "Спочатку мовчки проаналізуй роботу: визначи її тип (практична робота з кодом чи "
    "теоретичний реферат), що саме було зроблено, які методи, алгоритми, технології, "
    "інструменти використано, які результати, числа чи спостереження наведено, "
    "і чи досягнуто поставленої мети.\n\n"
    "Потім напиши висновки, які стосуються саме цієї роботи:\n"
    "- згадуй конкретні речі з роботи: назви алгоритмів, бібліотек, методів, структур даних, "
    "отримані результати та числа; для коду — що саме він реалізує;\n"
    "- для реферату підсумуй ключові положення та думки, розкриті в розділах;\n"
    "- співвіднеси результати з метою роботи;\n"
    "- НЕ вигадуй фактів, чисел, результатів чи умов експерименту (тип даних, обладнання тощо), "
    "яких немає в матеріалі, і не переказуй код неточно — якщо не впевнений, пиши загальніше;\n"
    "- уникай загальних фраз без змісту на кшталт «набуто практичних навичок» або "
    "«робота є актуальною», якщо за ними не стоїть щось конкретне з роботи.\n\n"
    "Перед відповіддю перевір кожне твердження висновку: якщо його немає в матеріалі "
    "або воно не випливає з нього напряму — прибери його.\n\n"
    "Формат: 1–3 абзаци (120–250 слів), безособова форма, академічний стиль, наприклад "
    "«У ході виконання лабораторної роботи було...». Не додавай заголовок «Висновки». "
    + _LANG_RULE
)


def _strip_markdown(text):
    """The text goes into Word as-is; drop inline markdown marks the model may still emit."""
    return text.replace('`', '').replace('*', '') if text else text


def _report_header(report) -> str:
    lines = [
        f"Тип роботи: {'реферат' if getattr(report, 'kind', 'lab') == 'essay' else 'лабораторна / практична робота'}",
        f"Заклад: {'школа (учнівська робота)' if getattr(report, 'level', 'university') == 'school' else 'університет / коледж'}",
        f"Тема роботи: {report.title}",
        f"Дисципліна: {report.discipline}",
    ]
    if (report.goal or "").strip():
        lines.append(f"Мета роботи: {report.goal}")
    if (getattr(report, "introduction", None) or "").strip():
        lines.append(f"Вступ: {strip_inline_math(report.introduction)}")
    return "\n".join(lines)


def report_section_blocks(report) -> list[str]:
    """One plain-text block per top-level section (with its subsections, code and figure captions)."""
    images_by_path = {}
    for img in getattr(report, "images", None) or []:
        images_by_path.setdefault(img.section_path, []).append(img.caption)

    def block(number, item, path):
        title = (item.get("title") or "").strip() or "(без назви)"
        lines = [f"\n{number} {title}"]
        for b in item_blocks(item):
            if b["type"] == "text" and (b.get("text") or "").strip():
                lines.append(strip_inline_math(b["text"].strip()))
            elif b["type"] == "formula" and (b.get("latex") or "").strip():
                lines.append(f"Формула (LaTeX): {b['latex'].strip()}")
            elif b["type"] == "code" and (b.get("code") or "").strip():
                code = b["code"].strip()
                if len(code) > _MAX_CODE_CHARS:
                    code = code[:_MAX_CODE_CHARS] + "\n... (код скорочено)"
                lines.append(f"Код ({b.get('language') or 'code'}):\n{code}")
        for caption in images_by_path.get(path, []):
            lines.append(f"Рисунок: {caption}")
        return "\n".join(lines)

    blocks = []
    for i, section in enumerate(report.sections or []):
        parts = [block(f"{i + 1}", section, str(i))]
        for j, sub in enumerate(section.get("subsections") or []):
            parts.append(block(f"{i + 1}.{j + 1}", sub, f"{i}.{j}"))
        blocks.append("\n".join(parts))
    return blocks


def build_report_context(report, limit: int | None = _MAX_CONTEXT_CHARS) -> str:
    """Readable plain-text view of the whole report for the model (instead of a raw dict dump)."""
    context = "\n".join([_report_header(report), *report_section_blocks(report)])
    if limit and len(context) > limit:
        context = context[:limit] + "\n... (решту роботи скорочено)"
    return context


# ── Long reports: summarise in parts first ───────────────────────────────────
# One request with the whole of a big report sometimes comes back empty (the model
# spends its budget reasoning, or the request hits the provider's token limit).
# Above these limits each part is condensed separately and the conclusion is
# written from the condensed parts.
CHUNK_SECTIONS_THRESHOLD = 4
_MAX_PART_CHARS = 6000
_MAX_SECTIONS_PER_PART = 3

_PART_SYSTEM_PROMPT = (
    "Ти допомагаєш викладачу підготувати висновки до студентської роботи. "
    "Тобі дають тему й мету роботи та ОДНУ її частину (кілька розділів). "
    "Стисло випиши, що саме зроблено в цій частині: конкретні методи, алгоритми, технології, "
    "що реалізує код, отримані результати й числа, спостереження. "
    "Лише факти з тексту — нічого не вигадуй і не оцінюй. "
    "Обсяг: 60–150 слів, суцільний текст. "
    + _LANG_RULE
)


def needs_chunking(report) -> bool:
    sections = report.sections or []
    return (
        len(sections) > CHUNK_SECTIONS_THRESHOLD
        or len(build_report_context(report, limit=None)) > _MAX_CONTEXT_CHARS
    )


def split_report_parts(report) -> list[str]:
    """Groups consecutive sections into parts of at most _MAX_SECTIONS_PER_PART
    sections / _MAX_PART_CHARS characters (a single huge section is cut)."""
    parts, current, size = [], [], 0
    for block in report_section_blocks(report):
        if len(block) > _MAX_PART_CHARS:
            block = block[:_MAX_PART_CHARS] + "\n... (розділ скорочено)"
        if current and (len(current) >= _MAX_SECTIONS_PER_PART or size + len(block) > _MAX_PART_CHARS):
            parts.append("\n".join(current))
            current, size = [], 0
        current.append(block)
        size += len(block)
    if current:
        parts.append("\n".join(current))
    return parts


def summarize_part(report, part_text: str, index: int, total: int) -> str:
    t0 = time.perf_counter()
    logger.info("ai_request_start", fn="summarize_part", part=index, total=total, model=_MODEL)
    try:
        response = client.with_options(max_retries=4).chat.completions.create(
            model=_MODEL,
            temperature=0.2,
            reasoning_effort="low",
            messages=[
                {"role": "system", "content": _PART_SYSTEM_PROMPT},
                {"role": "user", "content": f"{_report_header(report)}\n\nЧастина {index} з {total}:\n{part_text}"},
            ],
        )
        logger.info(
            "ai_request_done",
            fn="summarize_part",
            part=index,
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
            total_tokens=response.usage.total_tokens if response.usage else None,
        )
        return _strip_markdown((response.choices[0].message.content or "").strip())
    except Exception:
        logger.error("ai_request_failed", fn="summarize_part", part=index, exc_info=True)
        raise


def condensed_report_context(report, summaries: list[str]) -> str:
    """What the conclusion model sees for a long report: header + section titles + part summaries."""
    titles = [
        f"{i + 1} {(s.get('title') or '').strip() or '(без назви)'}"
        for i, s in enumerate(report.sections or [])
    ]
    body = "\n\n".join(f"Частина {i + 1}. Що зроблено:\n{text}" for i, text in enumerate(summaries))
    return (
        f"{_report_header(report)}\n\nРозділи роботи:\n" + "\n".join(titles)
        + "\n\nРобота велика, тому нижче — стислий виклад її частин по порядку.\n\n" + body
    )


def _conclusion_stream(report_context: str, effort: str):
    response = client.chat.completions.create(
        model=_MODEL,
        temperature=0.2,
        reasoning_effort=effort,
        messages=[
            {"role": "system", "content": _CONCLUSION_SYSTEM_PROMPT},
            {"role": "user", "content": report_context},
        ],
        stream=True,
    )
    for chunk in response:
        if not chunk.choices:
            continue
        text = _strip_markdown(chunk.choices[0].delta.content)
        if text:
            yield text


def stream_conclusion(report_context: str):
    t0 = time.perf_counter()
    logger.info("ai_stream_start", fn="stream_conclusion", model=_MODEL)
    produced = False
    try:
        # With "high" reasoning a long input sometimes ends with no text at all;
        # in that case ask again with less reasoning instead of returning nothing
        for effort in ("high", "medium"):
            for text in _conclusion_stream(report_context, effort):
                produced = True
                yield text
            if produced:
                break
            logger.warning("ai_stream_empty", fn="stream_conclusion", effort=effort)
    except Exception:
        logger.error(
            "ai_stream_failed",
            fn="stream_conclusion",
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
            exc_info=True,
        )
        raise
    else:
        logger.info(
            "ai_stream_done",
            fn="stream_conclusion",
            produced=produced,
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
        )
