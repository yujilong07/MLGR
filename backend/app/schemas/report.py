from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any, Literal, Optional

Gender = Literal["m", "f"]


class ReportCreate(BaseModel):
    title: str
    discipline: str
    teacher: str
    teacher_gender: Gender = "f"
    student_name: str = ""
    student_gender: Gender = "m"
    group: str
    goal: str
    sections: Optional[Any] = None
    conclusion: Optional[str] = None


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    discipline: Optional[str] = None
    teacher: Optional[str] = None
    teacher_gender: Optional[Gender] = None
    student_name: Optional[str] = None
    student_gender: Optional[Gender] = None
    group: Optional[str] = None
    goal: Optional[str] = None
    sections: Optional[Any] = None
    conclusion: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    title: str
    discipline: str
    teacher: str
    teacher_gender: str
    student_name: str
    student_gender: str
    group: str
    goal: str
    sections: Optional[Any]
    conclusion: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
