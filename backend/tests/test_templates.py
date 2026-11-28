"""Title page templates for any institution (university / school), and "Мої дані"."""
from types import SimpleNamespace

import pytest
from docx import Document

from app.services.docx_builder import build_report_docx
from app.services.latex_doc import build_tex_document
from app.services.pdf_builder import build_report_html
from app.services.templates import TEMPLATES, resolve_title_page, template_id


def _report(**kw):
    data = dict(
        id=1, kind="lab", level="university", title="ЛР 1", discipline="Фізика",
        ministry="Міністерство освіти і науки України", institution="Ліцей № 1", city="Львів",
        faculty="", department="", teacher="Іваненко І. І.", teacher_gender="f", teacher_position="",
        student_name="Петренко О. О.", student_gender="m", group="9-А", work_date="", goal="Мета.",
        introduction="Вступ.", conclusion="Висновок.", bibliography=None,
        sections=[{"title": "Хід роботи", "blocks": [{"type": "text", "text": "Текст."}]}],
    )
    data.update(kw)
    return SimpleNamespace(**data)


def _texts(resolved):
    out = []
    for el in resolved:
        if el["t"] == "line":
            out.append(el["text"])
        elif el["t"] == "field":
            out += [el["label"], el["value"]]
        elif el["t"] == "columns":
            out += el["left"] + el["right"]
    return out


@pytest.mark.parametrize("tid", list(TEMPLATES))
def test_every_template_builds_docx_pdf_and_tex(tid, tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    level, kind = tid.split("_")
    r = _report(level=level, kind=kind)
    assert template_id(r) == tid
    texts = [p.text for p in Document(build_report_docx(r)).paragraphs]
    assert "Ліцей № 1" in texts
    assert any(t.startswith("Львів") for t in texts)
    assert "Ліцей № 1" in build_report_html(r)
    assert "Ліцей № 1" in build_tex_document(r, "")
    assert "Харків" not in "".join(texts) and "радіоелектроніки" not in "".join(texts)


def test_school_title_page_words():
    r = _report(level="school", kind="essay", student_gender="f", teacher_gender="m",
                teacher_position="вчитель фізики")
    texts = _texts(resolve_title_page(r))
    assert "Виконала:" in texts and "учениця 9-А класу" in texts
    assert "Перевірив:" in texts and "вчитель фізики" in texts
    assert "з предмета «Фізика»" in texts and "на тему: «ЛР 1»" in texts


def test_several_students_use_plural():
    texts = _texts(resolve_title_page(_report(student_name="А. А.\nБ. Б.")))
    assert "Виконали:" in texts and "А. А." in texts and "Б. Б." in texts
    texts = _texts(resolve_title_page(_report(level="school", student_name="А. А.\nБ. Б.")))
    assert "учні 9-А класу" in texts


def test_empty_optional_lines_are_dropped():
    texts = _texts(resolve_title_page(_report(ministry="", department="", city="")))
    assert "Міністерство освіти і науки України" not in texts
    assert not any(t.startswith("Кафедра") for t in texts)
    assert texts[-1].isdigit()                       # just the year without a city


def test_essay_fields_repeat_per_student():
    r = _report(kind="essay", student_name="А. А.\nБ. Б.", work_date="01.02.2026", group="КН-1")
    fields = [el for el in resolve_title_page(r) if el["t"] == "field" and "студент" in el["value"]]
    assert [f["label"] for f in fields] == ["виконали:", ""]
    assert fields[0]["value"] == "01.02.2026 студент гр. КН-1 А. А."
    assert _texts(resolve_title_page(r))[-1] == "Львів 2026 р."


# ── API ──

def test_templates_endpoint(client):
    data = client.get("/templates").json()
    assert set(data["templates"]) == set(TEMPLATES)
    assert any("Харківський національний університет радіоелектроніки" == i["name"] for i in data["institutions"])


def test_new_report_has_no_built_in_institution(client, auth_headers):
    r = client.post("/reports", headers=auth_headers, json={
        "title": "T", "discipline": "D", "teacher": "X", "group": "G", "level": "school"}).json()
    assert r["level"] == "school" and r["institution"] == "" and r["city"] == ""
    assert r["ministry"] == "Міністерство освіти і науки України"


def test_profile_round_trip(client, auth_headers):
    assert client.get("/auth/profile", headers=auth_headers).json() == {
        k: None for k in ("level", "ministry", "institution", "city", "faculty", "department",
                          "group", "student_name", "student_gender")}
    body = {"level": "school", "institution": "Гімназія № 5", "city": "Київ", "group": "10-Б",
            "student_name": "Коваль І. І.", "student_gender": "f"}
    assert client.put("/auth/profile", headers=auth_headers, json=body).json()["institution"] == "Гімназія № 5"
    got = client.get("/auth/profile", headers=auth_headers).json()
    assert {k: got[k] for k in body} == body
    assert client.put("/auth/profile", headers=auth_headers, json={"level": "kindergarten"}).status_code == 422
    assert client.get("/auth/profile").status_code == 401
