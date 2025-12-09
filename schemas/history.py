from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class PlantHistoryResponse(BaseModel):
    id: int
    image_path: Optional[str]
    image_paths: Optional[List[Any]]
    plant_name: str
    common_name: Optional[str]
    accuracy: float
    description: Optional[str]
    details: Optional[Dict[str, Any]]
    created_at: datetime
    in_garden: Optional[bool]
    garden_id: Optional[int]
    diseases: Optional[str]
    pest_control: Optional[str]

    class Config:
        from_attributes = True

