from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class PlantHistoryResponse(BaseModel):
    id: int
    image_path: Optional[str]
    plant_name: str
    common_name: Optional[str]
    accuracy: float
    description: Optional[str]
    details: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

