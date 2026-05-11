from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReportCreate(BaseModel):
    title :str
    discipline: str
    teacher : str
    group: str
    goal: str
    sections : Optional[dict] 
    conclusion : Optional[str] 

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