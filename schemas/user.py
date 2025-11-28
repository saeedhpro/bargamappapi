from pydantic import BaseModel
from typing import Optional
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
