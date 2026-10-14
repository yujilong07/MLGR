import os

import structlog
from app.tasks import celery
from app.database import engine
from sqlmodel import Session, select
from app.models.report import Report, ReportImage
from app.services.docx_builder import build_report_docx, apply_toc_pages
from app.services.pdf_service import pdf_available, render_pdf

logger = structlog.get_logger().bind(service="docx_task")


@celery.task
def generate_docx_task(report_id: int):
    logger.info("docx_task_started", report_id=report_id)
    try:
        with Session(engine) as session:
            report = session.exec(select(Report).where(Report.id == report_id)).first()
            if not report:
                logger.warning("docx_task_report_not_found", report_id=report_id)
                return None
            images = session.exec(select(ReportImage).where(ReportImage.report_id == report_id)).all()
            path = build_report_docx(report, images=images)

        # PDF for preview/download; LibreOffice also gives the real TOC page numbers.
        # A failure here must not cost the user the .docx itself.
        stale_pdf = os.path.splitext(path)[0] + ".pdf"
        if os.path.exists(stale_pdf):
            os.remove(stale_pdf)
        if pdf_available():
            try:
                _, pages = render_pdf(path)
                apply_toc_pages(path, pages)
            except Exception:
                logger.warning("pdf_render_failed", report_id=report_id, exc_info=True)
        else:
            logger.info("pdf_render_skipped", report_id=report_id, reason="LibreOffice not installed")

        logger.info("docx_task_completed", report_id=report_id, path=path)
        return path
    except Exception:
        logger.error("docx_task_failed", report_id=report_id, exc_info=True)
        raise
