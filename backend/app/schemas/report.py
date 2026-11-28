from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any, Literal, Optional

Gender = Literal["m", "f"]
Kind = Literal["lab", "essay", "course"]
Level = Literal["university", "school"]
EditorMode = Literal["form", "latex"]


class ReportCreate(BaseModel):
    kind: Kind = "lab"
    level: Level = "university"
    title: str
    discipline: str
    teacher: str
    teacher_gender: Gender = "f"
    student_name: str = ""
    student_gender: Gender = "m"
    group: str
    ministry: str = "Міністерство освіти і науки України"
    institution: str = ""
    city: str = ""
    faculty: str = ""
    department: str = ""
    teacher_position: str = ""
    work_date: str = ""
    goal: str = ""
    introduction: Optional[str] = None
    sections: Optional[Any] = None
    conclusion: Optional[str] = None
    bibliography: Optional[list[str]] = None
    meta: Optional[dict] = None
    editor_mode: EditorMode = "form"
    latex_source: Optional[str] = None


class ReportUpdate(BaseModel):
    kind: Optional[Kind] = None
    level: Optional[Level] = None
    title: Optional[str] = None
    discipline: Optional[str] = None
    teacher: Optional[str] = None
    teacher_gender: Optional[Gender] = None
    student_name: Optional[str] = None
    student_gender: Optional[Gender] = None
    group: Optional[str] = None
    ministry: Optional[str] = None
    institution: Optional[str] = None
    city: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    teacher_position: Optional[str] = None
    work_date: Optional[str] = None
    goal: Optional[str] = None
    introduction: Optional[str] = None
    sections: Optional[Any] = None
    conclusion: Optional[str] = None
    bibliography: Optional[list[str]] = None
    meta: Optional[dict] = None
    editor_mode: Optional[EditorMode] = None
    latex_source: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    kind: str
    level: str
    title: str
    discipline: str
    teacher: str
    teacher_gender: str
    student_name: str
    student_gender: str
    group: str
    ministry: str
    institution: str
    city: str
    faculty: str
    department: str
    teacher_position: str
    work_date: str
    goal: str
    introduction: Optional[str]
    sections: Optional[Any]
    conclusion: Optional[str]
    bibliography: Optional[list[str]]
    meta: Optional[dict] = None
    editor_mode: str
    latex_source: Optional[str]
    # problems found while parsing latex_source (only in the PATCH response)
    latex_warnings: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
