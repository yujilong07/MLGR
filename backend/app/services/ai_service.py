from openai import OpenAI
from app.config import settings

client = OpenAI(
    api_key=settings.groq_api_key,
    base_url="https://api.groq.com/openai/v1"
)

def stream_conclusion(goal: str, sections: dict):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Ти асистент який пише висновки до лабораторних робіт українською мовою."},
            {"role": "user", "content": f"Мета роботи: {goal}\n\nРозділи: {sections}"}
        ],
        stream=True
    )
    for chunk in response:
        text = chunk.choices[0].delta.content
        if text:
            yield text