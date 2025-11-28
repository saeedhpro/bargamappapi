from pydantic import BaseModel
from typing import Optional


class SubscriptionPlanOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: int
    duration_days: int
    daily_plant_id_limit: int
    daily_disease_id_limit: int

    class Config:
        from_attributes = True


class PurchaseResult(BaseModel):
    success: bool
    message: str
    expires_at: Optional[str] = None
