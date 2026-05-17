from openai import OpenAI
from app.config import settings

client = OpenAI(
    api_key=settings.groq_api_key,
    base_url="https://api.groq.com/openai/v1"
)

_LANG_RULE = "Відповідай ВИКЛЮЧНО українською мовою. Не використовуй жодних слів іншими мовами."


def generate_introduction(goal: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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
    return response.choices[0].message.content


def improve_section_text(text: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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
    return response.choices[0].message.content


def stream_conclusion(goal: str, sections: dict):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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