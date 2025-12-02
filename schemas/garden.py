from pydantic import BaseModel
from typing import List, Optional


class AddFromHistoryRequest(BaseModel):
    history_id: int
    nickname: Optional[str] = None


class GardenListResponse(BaseModel):
    id: int
    plant_name: str
    nickname: str
    image_path: Optional[str] = None
    image_paths: List[str] | None = []
    details: dict | None = {}
