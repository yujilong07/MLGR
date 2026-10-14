import os
import time
import structlog
from openai import OpenAI
from app.config import settings

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


def generate_introduction(goal: str) -> str:
    t0 = time.perf_counter()
    logger.info("ai_request_start", fn="generate_introduction", model=_MODEL)
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            temperature=0.3,
            messages=[
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
        )
        logger.info(
            "ai_request_done",
            fn="generate_introduction",
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
            total_tokens=response.usage.total_tokens,
        )
        return response.choices[0].message.content
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

CONCLUSION_PROMPT_VERSION = "3"

_CONCLUSION_SYSTEM_PROMPT = (
    "Ти досвідчений викладач технічного університету, який пише розділ «Висновки» "
    "до студентської роботи (лабораторної, практичної або реферату). "
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


def build_report_context(report) -> str:
    """Readable plain-text view of the whole report for the model (instead of a raw dict dump)."""
    parts = [
        f"Тема роботи: {report.title}",
        f"Дисципліна: {report.discipline}",
        f"Мета роботи: {report.goal}",
    ]
    images_by_path = {}
    for img in getattr(report, "images", None) or []:
        images_by_path.setdefault(img.section_path, []).append(img.caption)

    def block(number, item, path):
        title = (item.get("title") or "").strip() or "(без назви)"
        lines = [f"\n{number} {title}"]
        if (item.get("text") or "").strip():
            lines.append(item["text"].strip())
        code = (item.get("code") or "").strip()
        if code:
            if len(code) > _MAX_CODE_CHARS:
                code = code[:_MAX_CODE_CHARS] + "\n... (код скорочено)"
            lines.append(f"Код ({item.get('language') or 'code'}):\n{code}")
        for caption in images_by_path.get(path, []):
            lines.append(f"Рисунок: {caption}")
        return "\n".join(lines)

    for i, section in enumerate(report.sections or []):
        parts.append(block(f"{i + 1}", section, str(i)))
        for j, sub in enumerate(section.get("subsections") or []):
            parts.append(block(f"{i + 1}.{j + 1}", sub, f"{i}.{j}"))

    context = "\n".join(parts)
    if len(context) > _MAX_CONTEXT_CHARS:
        context = context[:_MAX_CONTEXT_CHARS] + "\n... (решту роботи скорочено)"
    return context


def stream_conclusion(report_context: str):
    t0 = time.perf_counter()
    logger.info("ai_stream_start", fn="stream_conclusion", model=_MODEL)
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            temperature=0.2,
            reasoning_effort="high",
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
            elapsed_ms=round((time.perf_counter() - t0) * 1000),
        )
