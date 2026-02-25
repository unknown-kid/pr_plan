from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[dict] = None


class UserInDBBase(UserBase):
    id: UUID
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    password_hash: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
