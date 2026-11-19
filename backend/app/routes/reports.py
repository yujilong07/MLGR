from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from app.database import get_session
from app.models.report import Report, ReportImage
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from app.services.auth_service import get_current_user
from app.services.image_store import delete_image as remove_image, is_available, ordered, save_image

reports_router = APIRouter()

@reports_router.post('', response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(report_data: ReportCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    new_report = Report(
        user_id=current_user.id,
        title=report_data.title,
        discipline=report_data.discipline,
        teacher=report_data.teacher,
        teacher_gender=report_data.teacher_gender,
        student_name=report_data.student_name,
        student_gender=report_data.student_gender,
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
    for image in session.exec(select(ReportImage).where(ReportImage.report_id == id)).all():
        remove_image(session, image, commit=False)
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

    image = save_image(session, id, await file.read(), section_path, caption)
    return {"id": image.id, "filename": image.filename, "caption": image.caption}

class ImageUpdate(BaseModel):
    caption: Optional[str] = None
    # moves the image when sections are deleted or reordered: "0" / "0.1"
    section_path: Optional[str] = Field(default=None, pattern=r"^\d+(\.\d+)?$")
    position: Optional[int] = Field(default=None, ge=0)


def _image_out(image: ReportImage, available: bool = True):
    return {
        "id": image.id,
        "url": f"/uploads/{image.filename}",
        "caption": image.caption,
        "section_path": image.section_path,
        "position": image.position,
        # False for old uploads whose file was wiped from the server before bytes went to the DB
        "available": available,
    }


def _own_image(report_id: int, image_id: int, user: User, session: Session) -> ReportImage:
    image = session.exec(
        select(ReportImage)
        .join(Report, Report.id == ReportImage.report_id)
        .where(ReportImage.id == image_id, ReportImage.report_id == report_id, Report.user_id == user.id)
    ).first()
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return image


@reports_router.get('/{id}/images')
async def list_images(id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    images = ordered(session.exec(select(ReportImage).where(ReportImage.report_id == id)).all())
    return [_image_out(img, is_available(session, img)) for img in images]


@reports_router.patch('/{id}/images/{image_id}')
async def update_image(id: int, image_id: int, body: ImageUpdate,
                               current_user: User = Depends(get_current_user),
                               session: Session = Depends(get_session)):
    image = _own_image(id, image_id, current_user, session)
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(image, field, value)
    session.add(image)
    session.commit()
    session.refresh(image)
    return _image_out(image)


@reports_router.delete('/{id}/images/{image_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(id: int, image_id: int, current_user: User = Depends(get_current_user),
                       session: Session = Depends(get_session)):
    image = _own_image(id, image_id, current_user, session)
    remove_image(session, image)
    return None
