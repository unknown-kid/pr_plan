from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class AIModelBase(BaseModel):
    name: str
    model_type: str
    provider: str
    api_url: Optional[str] = None
    model_name: str
    config: Optional[dict] = None


class PublicAIModelCreate(AIModelBase):
    api_key: str
    priority: int = 0


class PublicAIModelUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    model_name: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class PublicAIModel(AIModelBase):
    id: UUID
    is_active: bool
    priority: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserAIModelCreate(AIModelBase):
    api_key: Optional[str] = None
    is_default: bool = False


class UserAIModelUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    model_name: Optional[str] = None
    config: Optional[dict] = None
    is_default: Optional[bool] = None


class UserAIModel(AIModelBase):
    id: UUID
    user_id: UUID
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
