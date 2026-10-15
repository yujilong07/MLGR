from types import SimpleNamespace

import pytest

from app.services.pdf_builder import build_report_html


def _report(**overrides):
    data = dict(
        id=1,
        title="Лабораторна робота №1",
        discipline="Алгоритми",
        teacher="Іваненко І.І.",
        group="КНТ-22-1",
        goal="Мета.",
        sections=[{"title": "Хід роботи", "text": "Текст <script>", "code": "print(1)",
                   "subsections": [{"title": "Деталі", "text": "Ще текст."}]}],
        conclusion="Висновок.",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_html_toc_links_every_heading():
    html = build_report_html(_report())
    for anchor, text in [("_Toc00000001", "МЕТА РОБОТИ"), ("_Toc00000002", "1 ХІД РОБОТИ"),
                         ("_Toc00000003", "1.1 Деталі"), ("_Toc00000004", "ВИСНОВКИ")]:
        assert f'href="#{anchor}">{text}</a>' in html
        assert f'id="{anchor}">{text}</' in html
    assert "Лістинг 1 – Хід роботи" in html


def test_html_escapes_user_content():
    html = build_report_html(_report())
    assert "<script>" not in html
    assert "Текст &lt;script&gt;" in html


def test_pdf_pages_match_toc_anchors(tmp_path, monkeypatch):
    try:
        import weasyprint  # noqa: F401  (needs Pango from the system)
    except (ImportError, OSError):
        pytest.skip("WeasyPrint is not available")
    from app.services.pdf_builder import build_report_pdf

    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    path, pages = build_report_pdf(_report())
    assert open(path, "rb").read(5) == b"%PDF-"
    assert pages == {"_Toc00000001": 3, "_Toc00000002": 3, "_Toc00000003": 3, "_Toc00000004": 3}
