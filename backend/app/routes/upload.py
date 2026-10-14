import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from app.database import get_session
from app.models.report import Report, ReportImage
from app.models.user import User
from app.services.auth_service import get_current_user

upload_router = APIRouter()


def _human_number(section_path: str) -> str:
    """'0.1' -> '1.2', matching the section numbering in the document."""
    return ".".join(str(int(p) + 1) if p.isdigit() else p for p in section_path.split("."))


@upload_router.post('/upload/image')
async def upload_image(
    file: UploadFile = File(...),
    report_id: int = Form(...),
    section_index: Optional[int] = Form(None),
    # "0" for a section, "0.1" for its subsection; section_index kept for older clients
    section_path: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if section_path is None:
        if section_index is None:
            raise HTTPException(status_code=422, detail="section_path is required")
        section_path = str(section_index)

    report = session.exec(select(Report).where(Report.id == report_id, Report.user_id == current_user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
    filename = f"{uuid.uuid4()}.{ext}"
    uploads_dir = os.getenv("UPLOADS_DIR", "/app/uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    path = os.path.join(uploads_dir, filename)
    with open(path, "wb") as f:
        f.write(await file.read())

    image = ReportImage(
        report_id=report_id,
        filename=filename,
        caption=f"Зображення {_human_number(section_path)}",
        section_path=section_path,
    )
    session.add(image)
    session.commit()
    session.refresh(image)

    return {"url": f"/uploads/{filename}", "id": image.id}
