"""Student name / gender fields, title page wording and report image management."""
from types import SimpleNamespace

from app.services.report_outline import signature_rows


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
    data = dict(group="КНТ-22-1", teacher="Іваненко І. І.", student_name="Петренко О. О.",
                student_gender="m", teacher_gender="f")
    data.update(kw)
    return SimpleNamespace(**data)


def test_signature_rows_by_gender():
    assert signature_rows(_report())[0] == ("Виконав:", "Прийняла:")
    assert signature_rows(_report(student_gender="f", teacher_gender="m"))[0] == ("Виконала:", "Прийняв:")
    assert signature_rows(_report())[2] == ("Петренко О. О.", "")


def _upload(client, auth_headers, report_id, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    return client.post("/upload/image", headers=auth_headers,
                       data={"report_id": report_id, "section_path": "0"},
                       files={"file": ("img.png", b"fake", "image/png")}).json()


def test_list_update_delete_images(client, auth_headers, report_id, tmp_path, monkeypatch):
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
    assert not any(tmp_path.iterdir())


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
