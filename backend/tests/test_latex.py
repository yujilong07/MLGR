"""Content blocks, formulas, essays (реферат), latexify and the LaTeX mode."""
import io
import zipfile
from types import SimpleNamespace

from docx import Document

from app.services.content import item_blocks, split_inline
from app.services.docx_builder import build_report_docx
from app.services.latex_doc import parse_latex_body, to_latex_body
from app.services.pdf_builder import build_report_html
from app.services.py_latex import PythonFormulaError, python_to_latex
from tests.conftest import make_png

M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def _report(**kw):
    data = dict(
        id=1, kind="lab", title="ЛР 1", discipline="ШІ", teacher="Іваненко І. І.", teacher_gender="f",
        teacher_position="", student_name="Петренко О. О.", student_gender="m", group="КНТ-22-1",
        faculty="", department="", work_date="", goal="Мета.", introduction=None, conclusion="Висновок.",
        bibliography=None,
        sections=[{"title": "Хід роботи", "blocks": [
            {"type": "text", "text": "Формула $E = mc^2$ у тексті."},
            {"type": "code", "code": "print(1)", "language": "python"},
            {"type": "text", "text": "Текст після коду."},
            {"type": "formula", "latex": r"\frac{a}{b}"},
        ]}],
    )
    data.update(kw)
    return SimpleNamespace(**data)


# ── blocks ──

def test_legacy_section_reads_as_blocks():
    assert item_blocks({"text": "t", "code": "c", "language": "sql"}) == [
        {"type": "text", "text": "t"}, {"type": "code", "code": "c", "language": "sql"}]


def test_split_inline_keeps_escaped_dollar():
    assert split_inline(r"Ціна \$5 і $x^2$") == [("text", "Ціна $5 і "), ("math", "x^2")]


def test_docx_text_code_text_order_and_equations(tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    doc = Document(build_report_docx(_report()))
    texts = [p.text for p in doc.paragraphs]
    assert texts.index("print(1)") < texts.index("Текст після коду.")
    assert len(doc.element.body.findall(f".//{M}oMath")) == 2          # inline + display
    assert any(t.endswith("(1.1)") for t in texts)                     # formula number


def test_broken_formula_does_not_break_the_document(tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    r = _report(sections=[{"title": "A", "blocks": [{"type": "formula", "latex": r"\frac{"}]}])
    doc = Document(build_report_docx(r))
    assert any(r"\frac{" in p.text for p in doc.paragraphs)


def test_pdf_html_has_svg_formulas():
    html = build_report_html(_report())
    assert html.count("<svg") == 2 and "(1.1)" in html


# ── essay ──

def test_essay_structure_and_numbering(tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    r = _report(kind="essay", introduction="Вступ.", bibliography=["Книга. – 2020."],
                student_name="Бабаєв М. О.\nПетренко О. О.", teacher_gender="m", teacher_position="ас. каф. ШІ",
                faculty="Комп’ютерних наук", department="Штучного інтелекту", work_date="13.10.2025")
    doc = Document(build_report_docx(r))
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading ")]
    assert headings == ["ВСТУП", "1 ХІД РОБОТИ", "ВИСНОВКИ", "ПЕРЕЛІК ПОСИЛАНЬ"]
    texts = [p.text for p in doc.paragraphs]
    assert "РЕФЕРАТ" in texts and "1. Книга. – 2020." in texts
    assert any("виконали:" in t for t in texts) and any(t.startswith("перевірив") for t in texts)
    assert "Лістинг 1.1 – Хід роботи" in texts
    assert len(doc.sections) == 2                                      # numbers start at ВСТУП
    assert not doc.sections[0].header.paragraphs[0].text
    body_heading = next(p for p in doc.paragraphs if p.text == "1 ХІД РОБОТИ")
    assert body_heading.paragraph_format.page_break_before


def test_lab_without_references_has_no_reference_heading(tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    doc = Document(build_report_docx(_report()))
    assert "ПЕРЕЛІК ПОСИЛАНЬ" not in [p.text for p in doc.paragraphs]


# ── latexify ──

def test_python_function_to_latex():
    assert python_to_latex("def f(x):\n    return x**2 + 1") == "f(x) = x^{2} + 1"
    assert python_to_latex("y = w * x + b") == "y = w x + b"


def test_python_is_never_executed(tmp_path):
    marker = tmp_path / "pwned"
    src = f"@__import__('pathlib').Path({str(marker)!r}).touch\ndef g(x=__import__('os').getpid()):\n    return x + 1"
    assert python_to_latex(src) == "g(x) = x + 1"
    assert not marker.exists()


def test_python_errors_are_readable():
    for bad in ("def f(:", "while True: pass", ""):
        try:
            python_to_latex(bad)
        except PythonFormulaError as exc:
            assert str(exc)
        else:
            raise AssertionError(bad)


# ── LaTeX source ──

def test_latex_round_trip():
    r = _report(goal="50% & більше_за $x$", bibliography=["Книга."])
    img = SimpleNamespace(id=7, filename="a.png", caption="Скрін", section_path="0", position=0)
    parsed = parse_latex_body(to_latex_body(r, [img]), "lab", {7})
    assert parsed["goal"] == r.goal
    assert parsed["sections"][0]["blocks"] == r.sections[0]["blocks"]
    assert parsed["bibliography"] == ["Книга."]
    assert parsed["figures"] == [{"image_id": 7, "section_path": "0", "position": 0, "caption": "Скрін"}]
    assert parsed["warnings"] == []


def test_parse_hand_written_latex():
    src = r"""\documentclass{article}\begin{document}
\section*{Вступ} Текст~\cite{1} з \textbf{жирним}. % коментар
\section{Теорія}
\[ f(x) = x^2 \]
\begin{align} a &= b \\ c &= d \end{align}
\begin{itemize}\item один\item два\end{itemize}
\begin{minted}{javascript}
const p = 100; // 50%
\end{minted}
\section*{Висновки} Готово.
\end{document}"""
    res = parse_latex_body(src, "essay", set())
    assert res["introduction"] == "Текст [1] з жирним."
    blocks = res["sections"][0]["blocks"]
    assert blocks[0] == {"type": "formula", "latex": "f(x) = x^2"}
    assert blocks[1]["latex"].startswith(r"\begin{aligned}")
    assert blocks[2] == {"type": "text", "text": "– один\n– два"}
    assert blocks[3] == {"type": "code", "code": "const p = 100; // 50%", "language": "javascript"}
    assert res["conclusion"] == "Готово."
    assert any("textbf" in w for w in res["warnings"])


# ── API ──

def test_latex_mode_save_parses_source(client, auth_headers, report_id):
    img = client.post("/upload/image", headers=auth_headers, data={"report_id": report_id, "section_path": "u"},
                      files={"file": ("a.png", make_png(), "image/png")}).json()
    src = (f"\\section*{{Мета роботи}}\nНова мета.\n\\section{{Перший}}\nТекст.\n"
           f"\\begin{{figure}}\\includegraphics{{img-{img['id']}}}\\caption{{Підпис}}\\end{{figure}}\n"
           "\\section*{Висновки}\nКінець. \\unknowncmd{x}")
    r = client.patch(f"/reports/{report_id}", headers=auth_headers,
                     json={"editor_mode": "latex", "latex_source": src}).json()
    assert r["goal"] == "Нова мета." and r["sections"][0]["title"] == "Перший"
    assert r["conclusion"] == "Кінець. x" and r["latex_warnings"]
    images = client.get(f"/reports/{report_id}/images", headers=auth_headers).json()
    assert images[0]["section_path"] == "0" and images[0]["caption"] == "Підпис"

    # dropping the figure from the source takes the image out of the document, but keeps it
    client.patch(f"/reports/{report_id}", headers=auth_headers, json={"latex_source": "\\section{Перший}\nТекст."})
    assert client.get(f"/reports/{report_id}/images", headers=auth_headers).json()[0]["section_path"] == "u"

    # back to the form: the source is dropped, the structure stays
    r = client.patch(f"/reports/{report_id}", headers=auth_headers, json={"editor_mode": "form"}).json()
    assert r["latex_source"] is None and r["sections"][0]["title"] == "Перший"


def test_report_as_latex_and_parse_preview(client, auth_headers, report_id):
    client.patch(f"/reports/{report_id}", headers=auth_headers,
                 json={"sections": [{"title": "A", "blocks": [{"type": "formula", "latex": "x^2"}]}]})
    src = client.get(f"/reports/{report_id}/latex", headers=auth_headers).json()["source"]
    assert "\\begin{equation}" in src
    preview = client.post(f"/reports/{report_id}/latex/parse", headers=auth_headers, json={"source": src}).json()
    assert preview["sections"][0]["blocks"] == [{"type": "formula", "latex": "x^2"}]


def test_from_python_and_check_endpoints(client, auth_headers):
    r = client.post("/latex/from-python", headers=auth_headers, json={"source": "def f(x):\n    return x / 2"})
    assert r.status_code == 200 and r.json()["latex"] == r"f(x) = \frac{x}{2}"
    assert client.post("/latex/from-python", headers=auth_headers, json={"source": "def f(:"}).status_code == 422
    assert client.post("/latex/check", headers=auth_headers, json={"latex": r"\frac{a}{b}"}).json()["error"] is None
    assert client.post("/latex/check", headers=auth_headers, json={"latex": r"\frac{"}).json()["error"]
    assert client.post("/latex/from-python", json={"source": "x"}).status_code == 401


def test_tex_export_zip(client, auth_headers, report_id):
    client.post("/upload/image", headers=auth_headers, data={"report_id": report_id, "section_path": "0"},
                files={"file": ("a.png", make_png(), "image/png")})
    client.patch(f"/reports/{report_id}", headers=auth_headers, json={"kind": "essay", "sections": [{"title": "A"}]})
    r = client.get(f"/reports/{report_id}/download/tex", headers=auth_headers)
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert "main.tex" in names and any(n.startswith("images/img-") for n in names)
    tex = zf.read("main.tex").decode()
    assert "\\begin{document}" in tex and "РЕФЕРАТ" in tex and "\\sectionbreak" in tex
