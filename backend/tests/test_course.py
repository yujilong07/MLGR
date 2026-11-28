"""Course work (курсовий проєкт / курсова робота): title page, task sheet, calendar plan,
three heading levels, tables, appendices, abbreviations (методичка «Оформлення КП»)."""
from types import SimpleNamespace

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm

from app.services.ai_service import build_report_context
from app.services.docx_builder import build_report_docx
from app.services.latex_doc import build_tex_document, parse_latex_body, to_latex_body
from app.services.pdf_builder import build_report_html
from app.services.report_outline import Heading, Table, iter_report_blocks


def _course(**kw):
    data = dict(
        id=7, kind="course", level="university", title="Аналіз навантаженості плоских важільних механізмів",
        discipline="Технічна механіка", ministry="Міністерство освіти і науки України",
        institution="Харківський національний університет радіоелектроніки", city="Харків",
        faculty="Комп’ютерних наук", department="Медіасистем та технологій",
        teacher="проф. Табакова І. С.\nпроф. Ткаченко В. П.\nас. Трунова Т. О.", teacher_gender="f",
        teacher_position="", student_name="Мурзабулатова М. С.", student_gender="f", group="ВПВПС-24-2",
        work_date="2025", goal="", introduction="Плоскі важільні механізми широко застосовуються.",
        conclusion="Встановлено основні параметри.", bibliography=["Методичні вказівки. – Харків: ХНУРЕ, 2025. 74 с."],
        meta={
            "course_type": "project", "task_sheet": True, "specialty": "186 «Видавництво та поліграфія»",
            "year_of_study": "2", "semester": "3", "student_full_dative": "Мурзабулатовій Марії Сергіївні",
            "deadline": "27.12.2025 р.", "input_data": "3-3/9", "contents": "Частина 1: Динамічний аналіз механізму.",
            "graphics": "Лист 1 (Формат А1). Силовий аналіз механізму.", "issue_date": "02.09.2025 р.",
            "calendar": [
                {"stage": "Вибір розрахункової схеми", "deadline": "09.09.2025", "note": "Виконано"},
                {"stage": "Кінематичний аналіз механізму", "deadline": "09.10.2025"},
                {"stage": "побудова плану швидкостей", "sub": True, "deadline": "29.10.2025"},
                {"stage": "побудова плану прискорень", "sub": True},
                {"stage": "Захист курсового проєкту на комісії", "deadline": "з 16.12 по 27.12"},
            ],
            "abbreviations": "КП – курсовий проєкт\nВПС – видавничо-поліграфічна справа",
        },
        sections=[
            {"title": "Метричний синтез механізмів", "blocks": [{"type": "text", "text": "Вихідні дані подано в таблиці 1.1."}],
             "subsections": [
                 {"title": "Вибір вихідного положення механізму", "blocks": [
                     {"type": "table", "caption": "Вихідні дані для варіанта 3-3/9", "header": 1,
                      "rows": [["№", "Параметри", "Варіант 3"], ["1", "Частота обертання $n$, об/хв", "480"],
                               ["2", "LAB, мм", "26"]]},
                     {"type": "formula", "latex": r"\mu_l = \frac{l_{AB}}{AB}"}],
                  "subsections": [{"title": "Остання група Ассура", "blocks": [{"type": "text", "text": "Текст пункту."}]}]},
             ]},
            {"title": "Кінематичне дослідження механізмів", "blocks": [{"type": "text", "text": "Текст."}]},
            {"title": "Креслення", "appendix": True, "blocks": [
                {"type": "table", "caption": "Розміри ланок", "rows": [["Ланка", "Довжина"], ["AB", "26"]]}]},
        ],
    )
    data.update(kw)
    return SimpleNamespace(**data)


def _docx(tmp_path, monkeypatch, **kw):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    return Document(build_report_docx(_course(**kw)))


def test_course_structure_and_numbering(tmp_path, monkeypatch):
    doc = _docx(tmp_path, monkeypatch)
    headings = [(p.style.name, p.text) for p in doc.paragraphs if p.style.name.startswith("Heading ")]
    assert headings == [
        ("Heading 1", "СКОРОЧЕННЯ ТА УМОВНІ ПОЗНАКИ"),
        ("Heading 1", "ВСТУП"),
        ("Heading 1", "1 МЕТРИЧНИЙ СИНТЕЗ МЕХАНІЗМІВ"),
        ("Heading 2", "1.1 Вибір вихідного положення механізму"),
        ("Heading 3", "1.1.1 Остання група Ассура"),
        ("Heading 1", "2 КІНЕМАТИЧНЕ ДОСЛІДЖЕННЯ МЕХАНІЗМІВ"),
        ("Heading 1", "ВИСНОВКИ"),
        ("Heading 1", "ПЕРЕЛІК ДЖЕРЕЛ ПОСИЛАННЯ"),
        ("Heading 1", "ДОДАТОК А\nКреслення"),
    ]
    texts = [p.text for p in doc.paragraphs]
    assert "Таблиця 1.1 – Вихідні дані для варіанта 3-3/9" in texts
    assert "Таблиця А.1 – Розміри ланок" in texts                       # numbering inside an appendix
    assert any(t.endswith("(1.1)") for t in texts)
    toc = [p.text for p in doc.paragraphs if p.style.name.startswith("toc ")]
    assert any(t.startswith("1.1.1 Остання група Ассура") for t in toc)
    assert any(t.startswith("ДОДАТОК А Креслення") for t in toc)


def test_course_spacing_and_page_setup(tmp_path, monkeypatch):
    doc = _docx(tmp_path, monkeypatch)
    by_text = {p.text: p for p in doc.paragraphs}
    h1 = by_text["1 МЕТРИЧНИЙ СИНТЕЗ МЕХАНІЗМІВ"]
    assert h1.paragraph_format.page_break_before
    assert round(h1.paragraph_format.space_after.pt) == round(2 * 24.15)   # 2 blank lines after a section heading
    h2 = by_text["1.1 Вибір вихідного положення механізму"]
    assert round(h2.paragraph_format.space_before.pt) == round(24.15)      # 1 blank line before a subsection
    assert all(abs(s.right_margin - Mm(15)) < Mm(0.1) for s in doc.sections)
    page_run = [r for r in doc.sections[-1].header.paragraphs[0].runs if r.font.size]
    assert page_run and page_run[0].font.size.pt == 12
    assert len(doc.sections) == 2                                            # numbers from the first page after ЗМІСТ


def test_course_title_task_and_plan(tmp_path, monkeypatch):
    doc = _docx(tmp_path, monkeypatch)
    texts = [p.text for p in doc.paragraphs]
    assert "КУРСОВИЙ ПРОЄКТ" in texts and "ПОЯСНЮВАЛЬНА ЗАПИСКА" in texts
    supervisors = [t for t in texts if t.startswith("Керівник")]
    assert len(supervisors) == 3 and "Табакова" in supervisors[0]
    assert any(t.startswith("Студент") and "ВПВПС-24-2" in t and "Мурзабулатова" in t for t in texts)
    assert "ЗАВДАННЯ" in texts and "НА КУРСОВИЙ ПРОЄКТ" in texts and "КАЛЕНДАРНИЙ ПЛАН" in texts
    assert any("Студентці" in t and "Мурзабулатовій Марії Сергіївні" in t for t in texts)
    assert any(t.startswith("4. Зміст розрахунково-пояснювальної записки") for t in texts)
    plan = next(t for t in doc.tables if t.cell(0, 1).text.startswith("Назви етапів"))
    rows = [[c.text for c in r.cells] for r in plan.rows]
    assert rows[1][:3] == ["1", "Вибір розрахункової схеми", "09.09.2025"]
    assert rows[3][:2] == ["", "а) побудова плану швидкостей"] and rows[4][1] == "б) побудова плану прискорень"
    assert rows[5][0] == "3"


def test_course_work_wording_and_no_task(tmp_path, monkeypatch):
    meta = {**_course().meta, "course_type": "work", "task_sheet": False}
    texts = [p.text for p in _docx(tmp_path, monkeypatch, meta=meta).paragraphs]
    assert "КУРСОВА РОБОТА" in texts and "(тема роботи)" in texts
    assert "ЗАВДАННЯ" not in texts


def test_table_header_repeats_on_new_pages(tmp_path, monkeypatch):
    doc = _docx(tmp_path, monkeypatch)
    data = next(t for t in doc.tables if t.cell(0, 1).text == "Параметри")
    assert data.rows[0]._tr.trPr.find(qn("w:tblHeader")) is not None
    assert data.cell(0, 0).paragraphs[0].runs[0].bold
    # inline formula inside a cell is a Word equation
    assert data.cell(1, 1)._tc.find(".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath") is not None


def test_outline_tables_and_lab_numbering():
    blocks = list(iter_report_blocks(_course(kind="lab")))
    tables = [b for b in blocks if isinstance(b, Table)]
    assert [t.number for t in tables] == ["1", "А.1"]        # lab: through the document; appendix: А.1
    assert not any(isinstance(b, Heading) and b.text == "Скорочення та умовні познаки" for b in blocks)


def test_course_pdf_html():
    html = build_report_html(_course())
    assert 'class="task"' in html and 'class="plan"' in html
    assert "Таблиця 1.1 – Вихідні дані" in html and "<thead>" in html
    assert "<h3" in html and "ДОДАТОК А<br>Креслення" in html
    assert "margin: 20mm 15mm 20mm 30mm" in html and "font: 12pt" in html


def test_course_latex_round_trip():
    r = _course()
    src = to_latex_body(r, [])
    assert "\\subsubsection{Остання група Ассура}" in src and "\\appendix" in src and "\\begin{tabular}" in src
    parsed = parse_latex_body(src, "course", set())
    assert parsed["warnings"] == []
    assert parsed["abbreviations"] == r.meta["abbreviations"]
    assert parsed["introduction"] == r.introduction
    first = parsed["sections"][0]
    table = first["subsections"][0]["blocks"][0]
    assert table["type"] == "table" and table["caption"] == "Вихідні дані для варіанта 3-3/9"
    assert table["rows"][1] == ["1", "Частота обертання $n$, об/хв", "480"]
    assert first["subsections"][0]["subsections"][0]["title"] == "Остання група Ассура"
    assert parsed["sections"][-1].get("appendix") is True and parsed["sections"][-1]["title"] == "Креслення"
    tex = build_tex_document(r, src)
    assert "КУРСОВИЙ ПРОЄКТ" in tex and "\\ukrappendix" in tex and "\\renewcommand{\\sectionbreak}" in tex


def test_parse_hand_written_table():
    res = parse_latex_body(r"""\section{A}
\begin{table}[h]\caption{Ланки механізму}
\begin{tabular}{|c|l|}\hline № & Найменування \\ \hline 1 & Стійка \\ \hline\end{tabular}\end{table}
\begin{tabularx}{\textwidth}{XX} a & b \\ c & d \end{tabularx}""", "lab", set())
    blocks = res["sections"][0]["blocks"]
    assert blocks[0] == {"type": "table", "caption": "Ланки механізму", "rows": [["№", "Найменування"], ["1", "Стійка"]], "header": 1}
    assert blocks[1]["rows"] == [["a", "b"], ["c", "d"]]


def test_ai_context_sees_tables_and_appendices():
    ctx = build_report_context(_course(images=[]), limit=None)
    assert "курсова робота" in ctx
    assert "1.1.1 Остання група Ассура" in ctx
    assert "Таблиця «Вихідні дані для варіанта 3-3/9»" in ctx and "480" in ctx
    assert "Додаток А Креслення" in ctx


# ── API ──

def test_course_report_api(client, auth_headers):
    body = {"kind": "course", "title": "T", "discipline": "D", "teacher": "проф. А. А.\nас. Б. Б.", "group": "G",
            "meta": {"task_sheet": True, "course_type": "work", "calendar": [{"stage": "Етап"}]}}
    r = client.post("/reports", headers=auth_headers, json=body)
    assert r.status_code == 201 and r.json()["kind"] == "course" and r.json()["meta"]["course_type"] == "work"
    rid = r.json()["id"]
    r = client.patch(f"/reports/{rid}", headers=auth_headers, json={"meta": {"abbreviations": "КП – курсовий проєкт"}})
    assert r.json()["meta"] == {"abbreviations": "КП – курсовий проєкт"}
    assert client.patch(f"/reports/{rid}", headers=auth_headers, json={"kind": "thesis"}).status_code == 422


def test_image_in_a_level_three_item(client, auth_headers, report_id):
    from tests.conftest import make_png
    img = client.post("/upload/image", headers=auth_headers, data={"report_id": report_id, "section_path": "0"},
                      files={"file": ("a.png", make_png(), "image/png")}).json()
    r = client.patch(f"/reports/{report_id}/images/{img['id']}", headers=auth_headers, json={"section_path": "1.0.2"})
    assert r.status_code == 200 and r.json()["section_path"] == "1.0.2"
    assert client.patch(f"/reports/{report_id}/images/{img['id']}", headers=auth_headers,
                        json={"section_path": "1.0.2.3"}).status_code == 422
