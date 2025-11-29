from pydantic import BaseModel


class AddFromHistoryRequest(BaseModel):
    history_id: int
    nickname: str | None = None


class GardenListResponse(BaseModel):
    id: int
    plant_name: str
    nickname: str
    image_url: str | None
    details: dict | None = {}


