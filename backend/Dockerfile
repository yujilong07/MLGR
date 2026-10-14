FROM python:3.12-slim-trixie

WORKDIR /app

# LibreOffice renders the PDF preview; Liberation fonts are metric-compatible with
# Times New Roman / Courier New, so page breaks match Word
RUN apt-get update \
 && apt-get install -y --no-install-recommends libreoffice-writer-nogui python3-uno fonts-liberation \
 && rm -rf /var/lib/apt/lists/*
ENV UNO_PYTHON=/usr/bin/python3 SOFFICE=soffice

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]