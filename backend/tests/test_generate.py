from unittest.mock import MagicMock, patch


# ── generate-introduction ────────────────────────────────────────────────────

def test_generate_introduction_no_auth(client):
    response = client.post("/reports/1/generate-introduction")
    assert response.status_code == 401


def test_generate_introduction_not_found(client, auth_headers):
    with patch("app.routes.generate.generate_introduction", return_value="text"):
        response = client.post("/reports/9999/generate-introduction", headers=auth_headers)
    assert response.status_code == 404


def test_generate_introduction_success(client, auth_headers, report_id):
    with patch("app.routes.generate.generate_introduction", return_value="Generated intro") as mock_fn:
        response = client.post(f"/reports/{report_id}/generate-introduction", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["introduction"] == "Generated intro"
    mock_fn.assert_called_once()


def test_generate_introduction_cached(client, auth_headers, report_id, mock_cache):
    mock_cache.get.side_effect = lambda key: "Cached intro" if key.startswith("introduction:") else None
    with patch("app.routes.generate.generate_introduction") as mock_fn:
        response = client.post(f"/reports/{report_id}/generate-introduction", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["introduction"] == "Cached intro"
    mock_fn.assert_not_called()


# ── improve-section ──────────────────────────────────────────────────────────

def test_improve_section_no_auth(client):
    response = client.post("/reports/1/improve-section", json={"text": "hello"})
    assert response.status_code == 401


def test_improve_section_not_found(client, auth_headers):
    with patch("app.routes.generate.improve_section_text", return_value="x"):
        response = client.post("/reports/9999/improve-section", headers=auth_headers, json={"text": "hello"})
    assert response.status_code == 404


def test_improve_section_success(client, auth_headers, report_id):
    with patch("app.routes.generate.improve_section_text", return_value="Improved text"):
        response = client.post(f"/reports/{report_id}/improve-section",
            headers=auth_headers, json={"text": "original text"})
    assert response.status_code == 200
    assert response.json()["improved_text"] == "Improved text"


# ── stream-conclusion (SSE, token via query param) ───────────────────────────

def test_stream_conclusion_no_auth(client):
    response = client.get("/reports/1/stream-conclusion?token=bad")
    assert response.status_code == 401


def test_stream_conclusion_missing_token(client):
    response = client.get("/reports/1/stream-conclusion")
    assert response.status_code == 422


def test_stream_conclusion_not_found(client, auth_token):
    with patch("app.routes.generate.stream_conclusion", return_value=iter([])):
        response = client.get(f"/reports/9999/stream-conclusion?token={auth_token}")
    assert response.status_code == 404


def test_stream_conclusion_success(client, auth_token, report_id):
    with patch("app.routes.generate.stream_conclusion", return_value=iter(["tok1", " tok2"])):
        response = client.get(f"/reports/{report_id}/stream-conclusion?token={auth_token}")
    assert response.status_code == 200
    assert "tok1" in response.text
    assert " tok2" in response.text


def test_stream_conclusion_cached(client, auth_token, report_id, mock_cache):
    mock_cache.get.side_effect = lambda key: "Cached conclusion" if key.startswith("conclusion:") else None
    with patch("app.routes.generate.stream_conclusion") as mock_fn:
        response = client.get(f"/reports/{report_id}/stream-conclusion?token={auth_token}")
    assert response.status_code == 200
    assert "Cached conclusion" in response.text
    mock_fn.assert_not_called()


# ── generate docx (Celery task) ───────────────────────────────────────────────

def test_generate_docx_no_auth(client):
    response = client.post("/reports/1/generate")
    assert response.status_code == 401


def test_generate_docx_not_found(client, auth_headers):
    mock_task = MagicMock()
    mock_task.id = "fake-id"
    with patch("app.routes.generate.generate_docx_task") as mock_celery:
        mock_celery.delay.return_value = mock_task
        response = client.post("/reports/9999/generate", headers=auth_headers)
    assert response.status_code == 404


def test_generate_docx_success(client, auth_headers, report_id):
    mock_task = MagicMock()
    mock_task.id = "fake-task-id"
    with patch("app.routes.generate.generate_docx_task") as mock_celery:
        mock_celery.delay.return_value = mock_task
        response = client.post(f"/reports/{report_id}/generate", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["task_id"] == "fake-task-id"


# ── generate status (SSE, token via query param) ──────────────────────────────

def test_generate_status_no_auth(client):
    response = client.get("/reports/1/generate/status?task_id=abc&token=bad")
    assert response.status_code == 401


def test_generate_status_missing_token(client):
    response = client.get("/reports/1/generate/status?task_id=abc")
    assert response.status_code == 422


def test_generate_status_pending(client, auth_token, report_id):
    mock_result = MagicMock()
    # First poll → pending, second poll → done so the stream terminates
    mock_result.successful.side_effect = [False, True]
    mock_result.failed.return_value = False
    with patch("app.routes.generate.celery.AsyncResult", return_value=mock_result), \
         patch("app.routes.generate.asyncio.sleep"):
        response = client.get(
            f"/reports/{report_id}/generate/status?task_id=abc&token={auth_token}")
    assert response.status_code == 200
    assert "pending" in response.text


def test_generate_status_done(client, auth_token, report_id):
    mock_result = MagicMock()
    mock_result.successful.return_value = True
    mock_result.failed.return_value = False
    with patch("app.routes.generate.celery.AsyncResult", return_value=mock_result):
        response = client.get(
            f"/reports/{report_id}/generate/status?task_id=abc&token={auth_token}")
    assert response.status_code == 200
    assert "done" in response.text


# ── download ──────────────────────────────────────────────────────────────────

def test_download_no_auth(client):
    response = client.get("/reports/1/download")
    assert response.status_code == 401


def test_download_report_not_found(client, auth_headers):
    response = client.get("/reports/9999/download", headers=auth_headers)
    assert response.status_code == 404


def test_download_file_not_found(client, auth_headers, report_id):
    with patch("app.routes.generate.os.path.exists", return_value=False):
        response = client.get(f"/reports/{report_id}/download", headers=auth_headers)
    assert response.status_code == 404


def test_download_success(client, auth_headers, report_id, tmp_path):
    fake_file = tmp_path / f"report_{report_id}.docx"
    fake_file.write_bytes(b"PK fake docx content")
    with patch("app.routes.generate.os.path.join", return_value=str(fake_file)), \
         patch("app.routes.generate.os.path.exists", return_value=True):
        response = client.get(f"/reports/{report_id}/download", headers=auth_headers)
    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
