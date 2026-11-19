from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from app.database import get_session
from app.models.report import Report, ReportImage
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.image_store import save_image

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

    image = save_image(session, report_id, await file.read(), section_path,
                       caption=f"Зображення {_human_number(section_path)}")
    return {"url": f"/uploads/{image.filename}", "id": image.id,
            "caption": image.caption, "section_path": image.section_path, "position": image.position}
