from tests.conftest import make_png


def test_upload_image_no_auth(client):
    response = client.post("/reports/1/images",
        data={"caption": "cap", "section_path": "0"},
        files={"file": ("img.png", make_png(), "image/png")})
    assert response.status_code == 401


def test_upload_image_report_not_found(client, auth_headers):
    response = client.post("/reports/9999/images", headers=auth_headers,
        data={"caption": "cap", "section_path": "0"},
        files={"file": ("img.png", make_png(), "image/png")})
    assert response.status_code == 404


def test_upload_image_success(client, auth_headers, report_id):
    response = client.post(f"/reports/{report_id}/images", headers=auth_headers,
        data={"caption": "My figure", "section_path": "0"},
        files={"file": ("img.png", make_png(), "image/png")})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["caption"] == "My figure"
    assert data["filename"].endswith(".png")


def test_upload_not_an_image_rejected(client, auth_headers, report_id):
    response = client.post("/upload/image", headers=auth_headers,
        data={"report_id": report_id, "section_path": "0"},
        files={"file": ("img.png", b"definitely not a png", "image/png")})
    assert response.status_code == 400
