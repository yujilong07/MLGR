"""Build queue (services/generation.py): one build per report, limited concurrency, state in
Redis and files in the database so that several server instances can share the work."""
import os
import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import RateLimitError
from sqlmodel import Session, select

from app.models.report import GeneratedFile, Report
from app.services import generation


@pytest.fixture
def gen_dir(tmp_path, monkeypatch):
    path = tmp_path / "generated"
    monkeypatch.setenv("GENERATED_DIR", str(path))
    return path


@pytest.fixture
def report_in_db(engine):
    with Session(engine) as session:
        report = Report(user_id=1, title="T", discipline="D", teacher="T", group="G", goal="G")
        session.add(report)
        session.commit()
        session.refresh(report)
        return report.id


def _fake_builders(out_dirs):
    def docx(report, images=None, out_dir=None):
        out_dirs.append(out_dir)
        path = os.path.join(out_dir, f"report_{report.id}.docx")
        with open(path, "wb") as f:
            f.write(b"PK docx")
        return path

    def pdf(report, images=None, out_dir=None):
        path = os.path.join(out_dir, f"report_{report.id}.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF fake")
        return path, {"_Toc00000001": 3}

    return docx, pdf


def _rows(engine, report_id):
    with Session(engine) as session:
        return {f.format: f for f in session.exec(select(GeneratedFile).where(GeneratedFile.report_id == report_id))}


# ── the build ────────────────────────────────────────────────────────────────

def test_build_stores_files_in_database(engine, report_in_db, gen_dir):
    out_dirs = []
    docx, pdf = _fake_builders(out_dirs)
    with patch.object(generation, "engine", engine), \
         patch.object(generation, "build_report_docx", side_effect=docx), \
         patch.object(generation, "build_report_pdf", side_effect=pdf), \
         patch.object(generation, "apply_toc_pages") as apply:
        assert generation.build_documents(report_in_db, version="v1") is True

    rows = _rows(engine, report_in_db)
    assert rows["docx"].data == b"PK docx" and rows["pdf"].data == b"%PDF fake"
    assert rows["docx"].version == "v1" and rows["docx"].size == 7
    assert apply.call_args.args[1] == {"_Toc00000001": 3}
    # built in a directory of its own, removed afterwards
    assert out_dirs[0] != str(gen_dir) and not os.path.exists(out_dirs[0])
    assert (gen_dir / f"report_{report_in_db}.v1.docx").read_bytes() == b"PK docx"


def test_build_without_pdf_drops_the_old_pdf(engine, report_in_db, gen_dir):
    generation_files = {"docx": b"old", "pdf": b"old pdf"}
    with patch.object(generation, "engine", engine):
        generation.store_files(report_in_db, generation_files, "v0")
    docx, _ = _fake_builders([])
    with patch.object(generation, "engine", engine), \
         patch.object(generation, "build_report_docx", side_effect=docx), \
         patch.object(generation, "build_report_pdf", side_effect=OSError("no pango")):
        assert generation.build_documents(report_in_db, version="v1") is True
    rows = _rows(engine, report_in_db)
    assert set(rows) == {"docx"} and rows["docx"].data == b"PK docx"


def test_build_of_missing_report(engine):
    with patch.object(generation, "engine", engine):
        assert generation.build_documents(9999) is False


def test_old_files_are_removed(engine, report_in_db, gen_dir):
    with Session(engine) as session:
        session.add(GeneratedFile(report_id=777, format="docx", version="old", size=1, data=b"x",
                                  created_at=generation._utcnow() - timedelta(days=3)))
        session.commit()
    with patch.object(generation, "engine", engine):
        generation.store_files(report_in_db, {"docx": b"new", "pdf": None}, "v1")
    assert _rows(engine, 777) == {}
    assert set(_rows(engine, report_in_db)) == {"docx"}


def test_load_file_from_disk_copy_or_database(engine, report_in_db, gen_dir):
    with patch.object(generation, "engine", engine):
        generation.store_files(report_in_db, {"docx": b"v1 bytes", "pdf": None}, "v1")
        generation.store_files(report_in_db, {"docx": b"v2 bytes", "pdf": None}, "v2")
    # the older copy on disk is gone, so it can never be served
    assert sorted(p.name for p in gen_dir.iterdir()) == [f"report_{report_in_db}.v2.docx"]
    with Session(engine) as session:
        path, data = generation.load_file(session, report_in_db, "docx")
        assert open(path, "rb").read() == b"v2 bytes" and data is None
        # another instance (empty disk) takes the bytes from the database
        os.remove(path)
        path, _ = generation.load_file(session, report_in_db, "docx")
        assert open(path, "rb").read() == b"v2 bytes"
        assert generation.load_file(session, report_in_db, "pdf") == (None, None)


# ── the queue ────────────────────────────────────────────────────────────────

def test_second_click_gets_the_same_job(fake_redis):
    with patch.object(generation, "_dispatch") as dispatch:
        first = generation.submit(1, user_id=5)
        assert generation.submit(1, user_id=5) == first
        other = generation.submit(2, user_id=5)
    assert other != first and dispatch.call_count == 2
    job, ahead = generation.progress(other)
    assert job["state"] == generation.QUEUED and ahead == 1


def test_finished_job_lets_a_new_build_start(fake_redis):
    with patch.object(generation, "_dispatch"):
        first = generation.submit(1, user_id=5)
        with patch.object(generation, "build_documents", return_value=True):
            assert generation.run_job(first, 1) is True
        assert generation.get_job(first)["state"] == generation.DONE
        assert generation.submit(1, user_id=5) != first


def test_failed_build_is_reported(fake_redis):
    with patch.object(generation, "_dispatch"):
        job_id = generation.submit(1, user_id=5)
    with patch.object(generation, "build_documents", side_effect=RuntimeError("boom")):
        assert generation.run_job(job_id, 1) is False
    job = generation.get_job(job_id)
    assert job["state"] == generation.ERROR and job["error"] == generation.FAILED_MESSAGE
    assert fake_redis.get("gen:report:1") is None


def test_queue_is_bounded(fake_redis, monkeypatch):
    monkeypatch.setattr(generation, "MAX_QUEUE", 2)
    with patch.object(generation, "_dispatch"):
        generation.submit(1, user_id=5)
        generation.submit(2, user_id=5)
        with pytest.raises(generation.QueueFull):
            generation.submit(3, user_id=5)
    assert fake_redis.get("gen:report:3") is None


def test_job_of_a_dead_instance_is_not_waited_for_forever(fake_redis):
    with patch.object(generation, "_dispatch"):
        job_id = generation.submit(1, user_id=5)
    generation._save_job(job_id, report_id=1, user_id=5, state=generation.RUNNING,
                         ts=time.time() - generation.STALE_RUNNING - 1)
    assert generation.get_job(job_id)["state"] == generation.ERROR
    with patch.object(generation, "_dispatch"):
        assert generation.submit(1, user_id=5) != job_id  # a new build can start


def test_without_worker_builds_run_in_this_process(fake_redis, monkeypatch):
    from app.tasks import celery
    monkeypatch.setattr(celery.conf, "task_always_eager", True)
    with patch.object(generation, "build_documents", return_value=True) as build:
        job_id = generation.submit(3, user_id=5)
        for _ in range(100):
            if generation.get_job(job_id)["state"] == generation.DONE:
                break
            time.sleep(0.02)
    assert generation.get_job(job_id)["state"] == generation.DONE
    build.assert_called_once_with(3, version=job_id)


def test_with_worker_builds_go_to_celery(fake_redis, monkeypatch):
    from app.tasks import celery
    monkeypatch.setattr(celery.conf, "task_always_eager", False)
    with patch("app.tasks.docx_task.generate_docx_task.apply_async") as apply_async:
        job_id = generation.submit(3, user_id=5)
    apply_async.assert_called_once_with(args=[3, job_id], task_id=job_id)


# ── routes ───────────────────────────────────────────────────────────────────

def test_generate_returns_queued_job(client, auth_headers, report_id, fake_redis):
    with patch.object(generation, "_dispatch"):
        response = client.post(f"/reports/{report_id}/generate", headers=auth_headers)
    assert response.status_code == 200
    assert generation.get_job(response.json()["task_id"])["state"] == generation.QUEUED


def test_generate_when_queue_is_full(client, auth_headers, report_id):
    with patch.object(generation, "submit", side_effect=generation.QueueFull):
        response = client.post(f"/reports/{report_id}/generate", headers=auth_headers)
    assert response.status_code == 503
    assert "завантажений" in response.json()["detail"]


def test_status_shows_place_in_queue_then_done(client, auth_token, report_id, fake_redis):
    with patch.object(generation, "_dispatch"):
        job_id = generation.submit(report_id, user_id=1)
    queued = generation.get_job(job_id)
    with patch.object(generation, "progress", side_effect=[
            (queued, 2), ({**queued, "state": "running"}, 0), ({**queued, "state": "done"}, 0)]), \
         patch("app.routes.generate.asyncio.sleep"):
        response = client.get(f"/reports/{report_id}/generate/status?task_id={job_id}&token={auth_token}")
    assert "перед вами 2 документи" in response.text
    assert "Складаємо документ" in response.text
    assert '"done"' in response.text


def test_status_passes_the_error_on(client, auth_token, report_id, fake_redis):
    with patch.object(generation, "_dispatch"):
        job_id = generation.submit(report_id, user_id=1)
    with patch.object(generation, "build_documents", side_effect=RuntimeError):
        generation.run_job(job_id, report_id)
    response = client.get(f"/reports/{report_id}/generate/status?task_id={job_id}&token={auth_token}")
    assert '"error"' in response.text and generation.FAILED_MESSAGE in response.text


def test_status_of_someone_elses_job(client, auth_token, report_id, fake_redis):
    with patch.object(generation, "_dispatch"):
        job_id = generation.submit(report_id, user_id=999)
    response = client.get(f"/reports/{report_id}/generate/status?task_id={job_id}&token={auth_token}")
    assert response.status_code == 404


def test_download_from_database(client, auth_headers, report_id, session, gen_dir):
    session.add(GeneratedFile(report_id=report_id, format="pdf", version="abc", size=9, data=b"%PDF data"))
    session.commit()
    response = client.get(f"/reports/{report_id}/download?format=pdf", headers=auth_headers)
    assert response.status_code == 200
    assert response.content == b"%PDF data"
    assert response.headers["content-type"] == "application/pdf"
    assert client.get(f"/reports/{report_id}/download?format=docx", headers=auth_headers).status_code == 404


def test_deleting_report_removes_its_files(client, auth_headers, report_id, session):
    session.add(GeneratedFile(report_id=report_id, format="docx", version="abc", size=1, data=b"x"))
    session.commit()
    assert client.delete(f"/reports/{report_id}", headers=auth_headers).status_code == 204
    assert session.exec(select(GeneratedFile).where(GeneratedFile.report_id == report_id)).all() == []


def test_health_endpoints(client):
    assert client.get("/health").json() == {"status": "ok"}
    with patch("app.main.cache_service.r") as r:
        assert client.get("/health/ready").status_code == 200
        r.ping.side_effect = ConnectionError
        assert client.get("/health/ready").status_code == 503


# ── AI: Groq limits every model separately ───────────────────────────────────

def _rate_limit_error():
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com/x"))
    return RateLimitError("rate limited", response=response, body=None)


def test_rate_limited_model_falls_back():
    from app.services import ai_service
    api = MagicMock()
    api.chat.completions.create.side_effect = [_rate_limit_error(), "answer"]
    with patch.object(ai_service, "client", api):
        assert ai_service._complete(temperature=0) == "answer"
    models = [call.kwargs["model"] for call in api.chat.completions.create.call_args_list]
    assert models == [ai_service._MODEL, ai_service._FALLBACK_MODEL]


def test_ai_overloaded_is_a_clear_503(client, auth_headers, report_id):
    with patch("app.routes.generate.generate_introduction", side_effect=_rate_limit_error()):
        response = client.post(f"/reports/{report_id}/generate-introduction", headers=auth_headers)
    assert response.status_code == 503
    assert "перевантажений" in response.json()["detail"]
