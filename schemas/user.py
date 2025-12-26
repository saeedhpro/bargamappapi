from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ActiveSubscriptionInfo(BaseModel):
    plan_title: str
    is_premium: bool
    expires_at: Optional[datetime] = None
    daily_plant_limit: int
    daily_disease_limit: int


class UserOut(BaseModel):
    id: int
    phone: str
    created_at: datetime
    is_active: bool
    subscription: Optional[ActiveSubscriptionInfo] = None

    class Config:
        from_attributes = True


class RoleOut(BaseModel):
    id: int
    name: str
    display_name: str
    is_active: bool

    class Config:
        from_attributes = True


class UserAdminOut(BaseModel):
    id: int
    phone: str
    full_name: Optional[str]
    role: Optional[RoleOut]
    identified_plants_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UsersListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[UserAdminOut]


class CreateUserIn(BaseModel):
    phone: str
    full_name: Optional[str] = None
    role_id: int
