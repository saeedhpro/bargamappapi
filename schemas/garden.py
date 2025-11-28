from pydantic import BaseModel


class AddFromHistoryRequest(BaseModel):
    history_id: int
    nickname: str | None = None
