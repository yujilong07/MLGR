import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from app.database import get_session
from app.models.report import Report, ReportImage
from app.models.user import User
from app.services.auth_service import get_current_user

upload_router = APIRouter()


@upload_router.post('/upload/image')
async def upload_image(
    file: UploadFile = File(...),
    report_id: int = Form(...),
    section_index: int = Form(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = session.exec(select(Report).where(Report.id == report_id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
    filename = f"{uuid.uuid4()}.{ext}"
    path = os.path.join("/app/uploads", filename)
    with open(path, "wb") as f:
        f.write(await file.read())

    image = ReportImage(
        report_id=report_id,
        filename=filename,
        caption=f"Зображення {section_index + 1}",
        section_path=str(section_index),
    )
    session.add(image)
    session.commit()
    session.refresh(image)

    return {"url": f"/uploads/{filename}", "id": image.id}
