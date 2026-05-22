from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReportCreate(BaseModel):
    title :str
    discipline: str
    teacher : str
    group: str
    goal: str
    sections: Optional[dict] = None
    conclusion: Optional[str] = None

class ReportUpdate(BaseModel):
    title: Optional[str] = None
    discipline: Optional[str] = None
    teacher: Optional[str] = None
    group: Optional[str] = None
    goal: Optional[str] = None
    sections: Optional[dict] = None
    conclusion: Optional[str] = None

class ReportResponse(BaseModel):
    id: int
    title :str
    discipline: str
    teacher : str
    group: str
    goal: str
    sections : Optional[dict] 
    conclusion : Optional[str] 
    created_at: datetime
    updated_at: datetime 

    class Config:
        from_attributes = True