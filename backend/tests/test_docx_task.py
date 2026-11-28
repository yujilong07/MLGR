from unittest.mock import patch

from app.tasks.docx_task import generate_docx_task


def test_task_runs_the_queued_job():
    with patch("app.tasks.docx_task.generation.run_job", return_value=True) as run_job:
        assert generate_docx_task.run(7, "job1") is True
    run_job.assert_called_once_with("job1", 7)


def test_task_without_job_just_builds():
    with patch("app.tasks.docx_task.generation.build_documents", return_value=True) as build:
        assert generate_docx_task.run(7) is True
    build.assert_called_once_with(7)
