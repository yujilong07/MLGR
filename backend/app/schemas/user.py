from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Literal, Optional


class UserCreate(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль має містити щонайменше 8 символів")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class Profile(BaseModel):
    """Defaults for new reports ("Мої дані"); every field is optional."""
    level: Optional[Literal["university", "school"]] = None
    ministry: Optional[str] = None
    institution: Optional[str] = None
    city: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
    group: Optional[str] = None
    student_name: Optional[str] = None
    student_gender: Optional[Literal["m", "f"]] = None
