# MLGR — Lab Report Generator

**MLGR** is a web application for ХНУРЕ students that turns your raw lab work notes into a properly formatted `.docx` report in seconds, with AI writing the parts you hate most.

---

## What it does

You fill in the basics — discipline, teacher, group, goal, and your section notes — and MLGR handles the rest:

- **AI-written introduction** — one click generates a full introduction based on your stated goal.
- **AI section improvement** — paste rough text into any section and get a polished, academic-sounding version back.
- **AI-streamed conclusion** — the conclusion writes itself in real time as you watch, token by token.
- **One-click `.docx` export** — generates a Word document that follows ХНУРЕ formatting guidelines (Times New Roman 14pt, 1.5 spacing, correct margins, heading hierarchy, table of contents, title page, listings, and image captions).
- **Image uploads** — attach screenshots or diagrams to specific sections; they appear in the document with proper numbered captions.
- **Report dashboard** — all your reports in one place with search and quick download.
- **Disciplines view** — reports grouped by discipline, so finding last semester's OS lab doesn't mean scrolling through everything.

---

## Getting started

You need [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

**1. Clone and configure**

```bash
git clone <repo-url>
cd MLGR
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/lab_report_db
SECRET_KEY=your-secret-key-here
GROQ_API_KEY=your-groq-api-key
REDIS_URL=redis://redis:6379
```

Get a free Groq API key at [console.groq.com](https://console.groq.com).

**2. Start**

```bash
docker compose up --build
```

**3. Open**

| Service   | URL                        |
|-----------|----------------------------|
| Frontend  | http://localhost:3000      |
| API docs  | http://localhost:8000/docs |

Register an account and start writing reports.

---

## The document it produces

Every exported `.docx` includes:

- Title page with university header, discipline, group, teacher, and student name
- Auto-generated table of contents
- **Мета роботи** section
- Numbered sections with text, code listings (Courier New 12pt), and inline images
- **Висновки** section
- All formatted to ДСТУ 3008:2015 / ХНУРЕ department requirements

---

## AI features in detail

| Feature | How to trigger |
|---|---|
| Generate introduction | Click **Згенерувати вступ** in the editor |
| Improve section text | Write rough text → click **Покращити** next to the section |
| Stream conclusion | Click **Згенерувати висновок** — text streams live |

AI responses are cached, so re-generating the same content is instant.

---

## Limits

- AI endpoints: 10 requests / minute per user
- Login attempts: 5 requests / minute per IP

---

## License

MIT
