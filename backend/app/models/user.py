import re
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator


Role = Literal["admin", "analyst", "viewer"]
Status = Literal["active", "disabled"]

_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Role

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not _PASSWORD_RE.match(v):
            raise ValueError(
                "Password must be at least 8 characters and contain a letter and a digit"
            )
        return v


class UserUpdate(BaseModel):
    role: Role | None = None
    status: Status | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    role: Role
    status: Status


class UserInDB(UserResponse):
    hashed_password: str
    failed_login_attempts: int = 0
    locked_until: str | None = None
