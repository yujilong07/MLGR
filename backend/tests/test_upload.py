from unittest.mock import patch


def test_upload_image_no_auth(client):
    response = client.post("/reports/1/images",
        data={"caption": "cap", "section_path": "s.1"},
        files={"file": ("img.png", b"data", "image/png")})
    assert response.status_code == 401


def test_upload_image_report_not_found(client, auth_headers):
    with patch("app.routes.reports.os.path.join", return_value="/tmp/test.png"):
        response = client.post("/reports/9999/images", headers=auth_headers,
            data={"caption": "cap", "section_path": "s.1"},
            files={"file": ("img.png", b"data", "image/png")})
    assert response.status_code == 404


def test_upload_image_success(client, auth_headers, report_id, tmp_path):
    with patch("app.routes.reports.os.path.join", return_value=str(tmp_path / "img.png")):
        response = client.post(f"/reports/{report_id}/images", headers=auth_headers,
            data={"caption": "My figure", "section_path": "section.results"},
            files={"file": ("img.png", b"fake image bytes", "image/png")})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["caption"] == "My figure"
    assert "filename" in data
