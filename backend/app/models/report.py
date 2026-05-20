from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON

class Report(SQLModel,table = True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title :str
    discipline: str
    teacher : str
    group: str
    goal: str
    sections : Optional[dict] = Field(default=None,sa_column=Column(JSON))
    conclusion : Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReportImage(SQLModel, table=True):
    id : Optional[int] = Field(default=None, primary_key=True)
    report_id : int = Field(foreign_key="report.id")
    filename : str
    caption : str
    section_path : str
    created_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc))