FROM python:3.12-slim-trixie

WORKDIR /app

# WeasyPrint (PDF preview) needs Pango; Liberation fonts are metric-compatible with
# Times New Roman / Courier New, so the PDF lays out like the .docx in Word
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]