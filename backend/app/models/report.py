from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import Column, LargeBinary, Text
from sqlalchemy.dialects.postgresql import JSON

class Report(SQLModel,table = True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    # "lab" — лабораторна / практична, "essay" — реферат, "course" — курсова робота / проєкт
    kind: str = Field(default="lab", max_length=8)
    # "university" (also college) or "school" — picks the title page template (services/templates.py)
    level: str = Field(default="university", max_length=16)
    title :str
    discipline: str
    teacher : str
    # "m" / "f": picks Виконав/Виконала and Прийняв/Прийняла on the title page
    teacher_gender: str = Field(default="f", max_length=1)
    student_name: str = Field(default="")
    student_gender: str = Field(default="m", max_length=1)
    group: str
    ministry: str = Field(default="Міністерство освіти і науки України")
    institution: str = Field(default="")
    city: str = Field(default="")
    faculty: str = Field(default="")
    department: str = Field(default="")
    teacher_position: str = Field(default="")
    work_date: str = Field(default="")
    goal: str
    introduction: Optional[str] = Field(default=None, sa_column=Column(Text))
    # Each section / subsection: {title, blocks: [{type: text|code|formula, ...}], subsections}
    sections: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    conclusion : Optional[str] = None
    bibliography: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    # "latex": the content is edited as LaTeX; latex_source is kept verbatim and
    # sections / conclusion / ... are parsed from it on every save
    # Course project data: course_type (project / work), doc_code, specialty, year_of_study, semester,
    # student_full_dative, deadline, input_data, contents, graphics, issue_date, task_sheet (bool),
    # calendar [{stage, deadline, note, sub}], abbreviations
    meta: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    editor_mode: str = Field(default="form", max_length=8)
    latex_source: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReportImage(SQLModel, table=True):
    id : Optional[int] = Field(default=None, primary_key=True)
    report_id : int = Field(foreign_key="report.id")
    filename : str
    caption : str
    section_path : str
    # order of the figures inside one section (lower first)
    position : int = Field(default=0)
    created_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImageBlob(SQLModel, table=True):
    """Image bytes live in the database: the container disk (Render) is wiped on every
    restart, so files in UPLOADS_DIR are only a cache. Separate table so that listing
    images never loads the bytes."""
    image_id : int = Field(foreign_key="reportimage.id", primary_key=True)
    data : bytes = Field(sa_column=Column(LargeBinary, nullable=False))

class GeneratedFile(SQLModel, table=True):
    """The last built .docx / .pdf of a report. In the database (not on the local disk) so that
    whichever server instance answers the download has it. Rows older than GENERATED_TTL_HOURS
    are removed: the editor rebuilds the files before every download anyway."""
    report_id : int = Field(foreign_key="report.id", primary_key=True)
    format : str = Field(primary_key=True, max_length=8)
    # id of the build; names the copy cached on the local disk, so a stale copy is never served
    version : str = Field(max_length=32)
    size : int = Field(default=0)
    data : bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    # naive UTC
    created_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                                  index=True)
