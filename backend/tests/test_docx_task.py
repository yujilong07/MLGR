from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.tasks.docx_task import generate_docx_task


def _session_with(report):
    session = MagicMock()
    session.__enter__.return_value = session
    session.exec.return_value.first.return_value = report
    session.exec.return_value.all.return_value = []
    return session


def test_task_renders_pdf_and_applies_pages(tmp_path):
    docx_path = str(tmp_path / "report_1.docx")
    with patch("app.tasks.docx_task.Session", return_value=_session_with(SimpleNamespace(id=1))), \
         patch("app.tasks.docx_task.build_report_docx", return_value=docx_path), \
         patch("app.tasks.docx_task.pdf_available", return_value=True), \
         patch("app.tasks.docx_task.render_pdf", return_value=("x.pdf", {"_Toc00000001": 3})) as render, \
         patch("app.tasks.docx_task.apply_toc_pages") as apply:
        assert generate_docx_task.run(1) == docx_path
    render.assert_called_once_with(docx_path)
    apply.assert_called_once_with(docx_path, {"_Toc00000001": 3})


def test_task_keeps_docx_when_pdf_fails(tmp_path):
    docx_path = str(tmp_path / "report_1.docx")
    stale = tmp_path / "report_1.pdf"
    stale.write_bytes(b"old")
    with patch("app.tasks.docx_task.Session", return_value=_session_with(SimpleNamespace(id=1))), \
         patch("app.tasks.docx_task.build_report_docx", return_value=docx_path), \
         patch("app.tasks.docx_task.pdf_available", return_value=True), \
         patch("app.tasks.docx_task.render_pdf", side_effect=RuntimeError("boom")):
        assert generate_docx_task.run(1) == docx_path
    assert not stale.exists()  # an outdated preview must not be served
