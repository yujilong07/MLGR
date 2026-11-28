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


def test_stream_conclusion_saved_to_report(client, auth_token, auth_headers, report_id):
    with patch("app.routes.generate.stream_conclusion", return_value=iter(["Висновок", " готовий"])):
        client.get(f"/reports/{report_id}/stream-conclusion?token={auth_token}")
    report = client.get(f"/reports/{report_id}", headers=auth_headers).json()
    assert report["conclusion"] == "Висновок готовий"


def test_stream_conclusion_cached_saved_to_report(client, auth_token, auth_headers, report_id, mock_cache):
    mock_cache.get.side_effect = lambda key: "Cached conclusion" if key.startswith("conclusion:") else None
    client.get(f"/reports/{report_id}/stream-conclusion?token={auth_token}")
    report = client.get(f"/reports/{report_id}", headers=auth_headers).json()
    assert report["conclusion"] == "Cached conclusion"


# ── generate docx (queued build) ─────────────────────────────────────────────

def test_generate_docx_no_auth(client):
    response = client.post("/reports/1/generate")
    assert response.status_code == 401


def test_generate_docx_not_found(client, auth_headers):
    with patch("app.routes.generate.generation.submit", return_value="fake-id") as submit:
        response = client.post("/reports/9999/generate", headers=auth_headers)
    assert response.status_code == 404
    submit.assert_not_called()


def test_generate_docx_success(client, auth_headers, report_id):
    with patch("app.routes.generate.generation.submit", return_value="fake-task-id") as submit:
        response = client.post(f"/reports/{report_id}/generate", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["task_id"] == "fake-task-id"
    submit.assert_called_once_with(report_id, 1)


# ── generate status (SSE, token via query param) ──────────────────────────────

def test_generate_status_no_auth(client):
    response = client.get("/reports/1/generate/status?task_id=abc&token=bad")
    assert response.status_code == 401


def test_generate_status_missing_token(client):
    response = client.get("/reports/1/generate/status?task_id=abc")
    assert response.status_code == 422


def test_generate_status_unknown_job(client, auth_token, report_id):
    with patch("app.routes.generate.generation.get_job", return_value=None):
        response = client.get(f"/reports/{report_id}/generate/status?task_id=abc&token={auth_token}")
    assert response.status_code == 404


def _job(report_id, state):
    return {"report_id": report_id, "user_id": 1, "state": state, "ts": 0}


def test_generate_status_pending(client, auth_token, report_id):
    with patch("app.routes.generate.generation.get_job", return_value=_job(report_id, "queued")), \
         patch("app.routes.generate.generation.progress",
               side_effect=[(_job(report_id, "running"), 0), (_job(report_id, "done"), 0)]), \
         patch("app.routes.generate.asyncio.sleep"):
        response = client.get(f"/reports/{report_id}/generate/status?task_id=abc&token={auth_token}")
    assert response.status_code == 200
    assert "pending" in response.text
    assert "done" in response.text


def test_generate_status_done(client, auth_token, report_id):
    with patch("app.routes.generate.generation.get_job", return_value=_job(report_id, "done")), \
         patch("app.routes.generate.generation.progress", return_value=(_job(report_id, "done"), 0)):
        response = client.get(f"/reports/{report_id}/generate/status?task_id=abc&token={auth_token}")
    assert response.status_code == 200
    assert "done" in response.text


# ── download (files are in the database) ─────────────────────────────────────

def test_download_no_auth(client):
    response = client.get("/reports/1/download")
    assert response.status_code == 401


def test_download_report_not_found(client, auth_headers):
    response = client.get("/reports/9999/download", headers=auth_headers)
    assert response.status_code == 404


def test_download_file_not_found(client, auth_headers, report_id):
    response = client.get(f"/reports/{report_id}/download", headers=auth_headers)
    assert response.status_code == 404


def _store(session, report_id, fmt, data):
    from app.models.report import GeneratedFile
    session.add(GeneratedFile(report_id=report_id, format=fmt, version="v1", size=len(data), data=data))
    session.commit()


def test_download_success(client, auth_headers, report_id, session, tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    _store(session, report_id, "docx", b"PK fake docx content")
    response = client.get(f"/reports/{report_id}/download", headers=auth_headers)
    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
    assert response.content == b"PK fake docx content"


def test_download_pdf_success(client, auth_headers, report_id, session, tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    _store(session, report_id, "pdf", b"%PDF-1.7 fake")
    response = client.get(f"/reports/{report_id}/download?format=pdf", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_download_pdf_missing(client, auth_headers, report_id, session, tmp_path, monkeypatch):
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    _store(session, report_id, "docx", b"PK")
    response = client.get(f"/reports/{report_id}/download?format=pdf", headers=auth_headers)
    assert response.status_code == 404


def test_download_unknown_format(client, auth_headers, report_id):
    response = client.get(f"/reports/{report_id}/download?format=exe", headers=auth_headers)
    assert response.status_code == 422


# ── long reports: conclusion is written from per-part summaries ──────────────

def _many_sections(n):
    return [{"title": f"Розділ {i}", "text": f"Зроблено крок {i}."} for i in range(n)]


def test_needs_chunking_and_split():
    from types import SimpleNamespace
    from app.services.ai_service import needs_chunking, split_report_parts
    small = SimpleNamespace(title="T", discipline="D", goal="G", sections=_many_sections(4))
    big = SimpleNamespace(title="T", discipline="D", goal="G", sections=_many_sections(7))
    assert not needs_chunking(small)
    assert needs_chunking(big)
    parts = split_report_parts(big)
    assert len(parts) == 3                      # 3 + 3 + 1 sections
    assert "Розділ 6" in parts[-1]


def test_stream_conclusion_long_report_uses_parts(client, auth_token, auth_headers, report_id):
    client.patch(f"/reports/{report_id}", headers=auth_headers, json={"sections": _many_sections(7)})
    with patch("app.routes.generate.summarize_part", side_effect=lambda r, part, n, total: f"підсумок {n}") as summ, \
         patch("app.routes.generate.stream_conclusion", return_value=iter(["Висновок"])) as final:
        response = client.get(f"/reports/{report_id}/stream-conclusion?token={auth_token}")
    assert summ.call_count == 3
    context = final.call_args.args[0]
    assert "підсумок 1" in context and "підсумок 3" in context
    assert "Аналізуємо частину 1 з 3" in response.text
    assert client.get(f"/reports/{report_id}", headers=auth_headers).json()["conclusion"] == "Висновок"


def test_stream_conclusion_empty_answer_is_error(client, auth_token, auth_headers, report_id):
    client.patch(f"/reports/{report_id}", headers=auth_headers, json={"conclusion": "старий"})
    with patch("app.routes.generate.stream_conclusion", return_value=iter([])):
        response = client.get(f"/reports/{report_id}/stream-conclusion?token={auth_token}")
    assert '"error"' in response.text
    assert client.get(f"/reports/{report_id}", headers=auth_headers).json()["conclusion"] == "старий"


def test_stream_conclusion_model_failure_is_error(client, auth_token, report_id):
    def boom(_):
        raise RuntimeError("413")
        yield
    with patch("app.routes.generate.stream_conclusion", side_effect=boom):
        response = client.get(f"/reports/{report_id}/stream-conclusion?token={auth_token}")
    assert response.status_code == 200
    assert '"error"' in response.text
