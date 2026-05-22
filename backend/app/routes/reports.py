import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session, select
from app.database import get_session
from app.models.report import Report, ReportImage
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from app.services.auth_service import get_current_user

reports_router = APIRouter()

@reports_router.post('', response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(report_data: ReportCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    new_report = Report(
        user_id=current_user.id,
        title=report_data.title,
        discipline=report_data.discipline,
        teacher=report_data.teacher,
        group=report_data.group,
        goal=report_data.goal,
        sections=report_data.sections,
        conclusion=report_data.conclusion
    )
    session.add(new_report)
    session.commit()
    session.refresh(new_report)
    return new_report

@reports_router.get('', response_model=list[ReportResponse], status_code=status.HTTP_200_OK)
async def get_reports(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    reports = session.exec(select(Report).where(Report.user_id == current_user.id)).all()
    return reports

@reports_router.get('/{id}', response_model=ReportResponse, status_code=status.HTTP_200_OK)
async def get_report_by_id(id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return report

@reports_router.patch('/{id}', response_model=ReportResponse, status_code=status.HTTP_200_OK)
async def update_report_by_id(id: int, report_data: ReportUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    update_fields = report_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(report, field, value)
    from datetime import datetime, timezone
    report.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(report)
    return report

@reports_router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_by_id(id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    session.delete(report)
    session.commit()
    return None

@reports_router.post('/{id}/images', status_code=status.HTTP_201_CREATED)
async def upload_image(
    id: int,
    file: UploadFile = File(...),
    caption: str = Form(...),
    section_path: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    ext = file.filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join("/app/uploads", filename)
    with open(path, "wb") as f:
        f.write(await file.read())

    image = ReportImage(
        report_id=id,
        filename=filename,
        caption=caption,
        section_path=section_path
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return {"id": image.id, "filename": image.filename, "caption": image.caption}