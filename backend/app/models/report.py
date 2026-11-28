from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import Column, LargeBinary, Text
from sqlalchemy.dialects.postgresql import JSON

class Report(SQLModel,table = True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    # "lab" — лабораторна / практична, "essay" — реферат (other title page and structure)
    kind: str = Field(default="lab", max_length=8)
    title :str
    discipline: str
    teacher : str
    # "m" / "f": picks Виконав/Виконала and Прийняв/Прийняла on the title page
    teacher_gender: str = Field(default="f", max_length=1)
    student_name: str = Field(default="")
    student_gender: str = Field(default="m", max_length=1)
    group: str
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