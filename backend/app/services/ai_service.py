import time
import structlog
from openai import OpenAI
from app.config import settings

client = OpenAI(
    api_key=settings.groq_api_key,
    base_url="https://api.groq.com/openai/v1"
)

logger = structlog.get_logger().bind(service="ai")

_MODEL = "llama-3.3-70b-versatile"
_LANG_RULE = "Відповідай ВИКЛЮЧНО українською мовою. Не використовуй жодних слів іншими мовами."


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


def stream_conclusion(goal: str, sections: dict):
    t0 = time.perf_counter()
    logger.info("ai_stream_start", fn="stream_conclusion", model=_MODEL)
    try:
        response = client.chat.completions.create(
            model=_MODEL,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ти асистент який пише висновки до лабораторних робіт. "
                        + _LANG_RULE
                    ),
                },
                {"role": "user", "content": f"Мета роботи: {goal}\n\nРозділи: {sections}"},
            ],
            stream=True,
        )
        for chunk in response:
            text = chunk.choices[0].delta.content
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
