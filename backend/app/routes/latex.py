"""LaTeX helpers for the editor: Python -> formula (latexify), formula check, the report
as LaTeX source, a parse preview of LaTeX source and the .tex export for Overleaf."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.database import get_session
from app.limiter import limiter, get_user_email
from app.models.report import Report, ReportImage
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.image_store import ensure_all_local
from app.services.latex_doc import export_tex_zip, parse_latex_body, to_latex_body
from app.services.math_render import check_latex
from app.services.py_latex import PythonFormulaError, python_to_latex
from app.services.templates import public_templates

latex_router = APIRouter()
# Routes with database or CPU work are plain `def`: FastAPI runs them in its thread pool.


@latex_router.get('/templates')
async def templates():
    """Title page templates (drawn the same way by the browser preview and the builders)
    and suggestions for the institution field."""
    return public_templates()


class PythonSource(BaseModel):
    source: str = Field(max_length=5000)


class FormulaSource(BaseModel):
    latex: str = Field(max_length=4000)


class LatexSource(BaseModel):
    source: str = Field(max_length=500_000)


def _own_report(id: int, user: User, session: Session) -> Report:
    report = session.exec(select(Report).where(Report.id == id, Report.user_id == user.id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Not found")
    return report


@latex_router.post('/latex/from-python')
@limiter.limit("30/minute", key_func=get_user_email)
def latex_from_python(request: Request, body: PythonSource, current_user: User = Depends(get_current_user)):
    """The code is only parsed (ast), never executed."""
    try:
        latex = python_to_latex(body.source)
    except PythonFormulaError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"latex": latex, "error": check_latex(latex)}


@latex_router.post('/latex/check')
@limiter.limit("120/minute", key_func=get_user_email)
def latex_check(request: Request, body: FormulaSource, current_user: User = Depends(get_current_user)):
    """Whether the formula converts for Word / PDF (the browser preview uses KaTeX, which
    accepts a bit more)."""
    return {"error": check_latex(body.latex)}


@latex_router.get('/reports/{id}/latex')
def report_as_latex(id: int, current_user: User = Depends(get_current_user),
                          session: Session = Depends(get_session)):
    report = _own_report(id, current_user, session)
    if report.editor_mode == "latex" and report.latex_source is not None:
        return {"source": report.latex_source}
    images = session.exec(select(ReportImage).where(ReportImage.report_id == id)).all()
    return {"source": to_latex_body(report, [i for i in images if i.section_path != "u"])}


@latex_router.post('/reports/{id}/latex/parse')
@limiter.limit("120/minute", key_func=get_user_email)
def parse_preview(request: Request, id: int, body: LatexSource,
                        current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Parsed structure for the live preview — nothing is saved."""
    report = _own_report(id, current_user, session)
    images = session.exec(select(ReportImage).where(ReportImage.report_id == id)).all()
    return parse_latex_body(body.source, report.kind, {i.id for i in images})


@latex_router.get('/reports/{id}/download/tex')
def download_tex(id: int, current_user: User = Depends(get_current_user),
                       session: Session = Depends(get_session)):
    report = _own_report(id, current_user, session)
    images = ensure_all_local(session, [
        i for i in session.exec(select(ReportImage).where(ReportImage.report_id == id)).all() if i.section_path != "u"
    ])
    data = export_tex_zip(report, images)
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="report_{id}_latex.zip"'})
