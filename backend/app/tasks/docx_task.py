from app.tasks import celery
from app.database import engine
from sqlmodel import Session, select
from app.models.report import Report
from app.services.docx_builder import build_report_docx

@celery.task
def generate_docx_task(report_id: int):
    with Session(engine) as session:
        report = session.exec(select(Report).where(Report.id == report_id)).first()
        if not report:
            return None
        path = build_report_docx(report)
        return path