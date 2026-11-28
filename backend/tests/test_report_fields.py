"""Student name / gender fields, title page wording and report image management."""
from types import SimpleNamespace

from app.services.templates import resolve_title_page
from tests.conftest import make_png


def test_create_report_defaults_keep_old_title_page(client, auth_headers, report_id):
    data = client.get(f"/reports/{report_id}", headers=auth_headers).json()
    assert data["student_name"] == ""
    assert data["student_gender"] == "m"
    assert data["teacher_gender"] == "f"


def test_update_student_and_genders(client, auth_headers, report_id):
    response = client.patch(f"/reports/{report_id}", headers=auth_headers, json={
        "student_name": "Петренко О. О.", "student_gender": "f", "teacher_gender": "m",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["student_name"] == "Петренко О. О."
    assert data["student_gender"] == "f"
    assert data["teacher_gender"] == "m"


def test_invalid_gender_rejected(client, auth_headers, report_id):
    response = client.patch(f"/reports/{report_id}", headers=auth_headers, json={"student_gender": "x"})
    assert response.status_code == 422


def _report(**kw):
    data = dict(kind="lab", level="university", group="КНТ-22-1", teacher="Іваненко І. І.",
                student_name="Петренко О. О.", student_gender="m", teacher_gender="f")
    data.update(kw)
    return SimpleNamespace(**data)


def _signatures(report):
    return next(el for el in resolve_title_page(report) if el["t"] == "columns")


def test_signature_rows_by_gender():
    cols = _signatures(_report())
    assert (cols["left"][0], cols["right"][0]) == ("Виконав:", "Прийняла:")
    cols = _signatures(_report(student_gender="f", teacher_gender="m"))
    assert (cols["left"][0], cols["right"][0]) == ("Виконала:", "Прийняв:")
    assert _signatures(_report())["left"][2] == "Петренко О. О."


def _upload(client, auth_headers, report_id, tmp_path=None, monkeypatch=None, path="0", **png):
    return client.post("/upload/image", headers=auth_headers,
                       data={"report_id": report_id, "section_path": path},
                       files={"file": ("img.png", make_png(**png), "image/png")}).json()


def test_list_update_delete_images(client, auth_headers, report_id, tmp_path, monkeypatch, uploads_tmp):
    uploaded = _upload(client, auth_headers, report_id, tmp_path, monkeypatch)

    listed = client.get(f"/reports/{report_id}/images", headers=auth_headers).json()
    assert [i["id"] for i in listed] == [uploaded["id"]]
    assert listed[0]["section_path"] == "0"

    r = client.patch(f"/reports/{report_id}/images/{uploaded['id']}", headers=auth_headers,
                     json={"caption": "Результат роботи програми"})
    assert r.status_code == 200 and r.json()["caption"] == "Результат роботи програми"

    r = client.delete(f"/reports/{report_id}/images/{uploaded['id']}", headers=auth_headers)
    assert r.status_code == 204
    assert client.get(f"/reports/{report_id}/images", headers=auth_headers).json() == []
    assert not any(uploads_tmp.iterdir())


def test_images_of_other_users_report_not_found(client, auth_headers, report_id, tmp_path, monkeypatch):
    uploaded = _upload(client, auth_headers, report_id, tmp_path, monkeypatch)
    r = client.delete(f"/reports/{report_id + 1}/images/{uploaded['id']}", headers=auth_headers)
    assert r.status_code == 404


def test_move_image_to_other_section(client, auth_headers, report_id, tmp_path, monkeypatch):
    uploaded = _upload(client, auth_headers, report_id, tmp_path, monkeypatch)
    r = client.patch(f"/reports/{report_id}/images/{uploaded['id']}", headers=auth_headers,
                     json={"section_path": "2.1"})
    assert r.status_code == 200 and r.json()["section_path"] == "2.1"
    r = client.patch(f"/reports/{report_id}/images/{uploaded['id']}", headers=auth_headers,
                     json={"section_path": "../x"})
    assert r.status_code == 422



def test_image_survives_wiped_disk(client, auth_headers, report_id, uploads_tmp):
    """Render wipes the container disk on restart — the image must come back from the DB."""
    uploaded = _upload(client, auth_headers, report_id)
    for f in uploads_tmp.iterdir():
        f.unlink()
    listed = client.get(f"/reports/{report_id}/images", headers=auth_headers).json()
    assert listed[0]["available"] is True
    r = client.get(uploaded["url"])
    assert r.status_code == 200
    assert r.content.startswith(b"\x89PNG")


def test_docx_task_restores_images(client, auth_headers, report_id, uploads_tmp, session, tmp_path, monkeypatch):
    from unittest.mock import patch
    from app.tasks.docx_task import generate_docx_task
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path / "gen"))
    client.patch(f"/reports/{report_id}", headers=auth_headers, json={"sections": [{"title": "A", "text": "t"}]})
    _upload(client, auth_headers, report_id)
    for f in uploads_tmp.iterdir():
        f.unlink()
    with patch("app.tasks.docx_task.Session", return_value=session), \
         patch("app.tasks.docx_task.build_report_pdf", side_effect=RuntimeError("no pdf")), \
         patch.object(session, "close"):
        path = generate_docx_task(report_id)
    from docx import Document
    assert len(Document(path).inline_shapes) == 1


def test_big_image_is_downscaled(client, auth_headers, report_id):
    uploaded = _upload(client, auth_headers, report_id, width=3000, height=1000)
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(client.get(uploaded["url"]).content))
    assert img.width == 2000


def test_image_order_in_section(client, auth_headers, report_id):
    a = _upload(client, auth_headers, report_id)
    b = _upload(client, auth_headers, report_id)
    other = _upload(client, auth_headers, report_id, path="1")
    assert (a["position"], b["position"], other["position"]) == (0, 1, 0)
    client.patch(f"/reports/{report_id}/images/{a['id']}", headers=auth_headers, json={"position": 1})
    client.patch(f"/reports/{report_id}/images/{b['id']}", headers=auth_headers, json={"position": 0})
    listed = [i["id"] for i in client.get(f"/reports/{report_id}/images", headers=auth_headers).json()
              if i["section_path"] == "0"]
    assert listed == [b["id"], a["id"]]


def test_delete_report_with_images(client, auth_headers, report_id, uploads_tmp):
    _upload(client, auth_headers, report_id)
    assert client.delete(f"/reports/{report_id}", headers=auth_headers).status_code == 204
    assert not any(uploads_tmp.iterdir())
